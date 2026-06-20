#!/usr/bin/env python3
"""Fetch a movie's metadata from TMDB and upsert it into data/movies.json.

Zero dependencies — uses only the Python standard library so it runs anywhere
without a stack. Credentials are read from the gitignored .env file.

Usage:
    python scripts/fetch_movie.py "Inception" --year 2010
    python scripts/fetch_movie.py --id 27205
    python scripts/fetch_movie.py "Dune"                 # interactive pick if ambiguous
    python scripts/fetch_movie.py "Dune" --pick 2        # non-interactive: take 2nd result
    python scripts/fetch_movie.py "Heat" --year 1995 --dry-run   # preview, don't write

The mapping from TMDB -> catalog entry is documented in docs/tmdb.md and
docs/data-model.md. The written record matches schemas/movie.schema.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.themoviedb.org/3"

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
CATALOG_PATH = REPO_ROOT / "data" / "movies.json"


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
CONFIG_KEYS = (
    "TMDB_READ_ACCESS_TOKEN",
    "TMDB_API_KEY",
    "TMDB_IMAGE_BASE_URL",
    "TMDB_POSTER_SIZE",
)


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    """Resolve config from the .env file, then let real environment variables win.

    Locally you keep creds in .env; in CI (GitHub Actions) they're injected as
    environment variables from GitHub Secrets, which take precedence here.
    """
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    # Environment variables override the file (this is how CI supplies secrets).
    for key in CONFIG_KEYS:
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


# --------------------------------------------------------------------------- #
# TMDB HTTP
# --------------------------------------------------------------------------- #
def tmdb_get(path: str, env: dict[str, str], params: dict | None = None) -> dict:
    """GET an API path, authenticating with the v4 token (preferred) or v3 key."""
    params = dict(params or {})
    token = env.get("TMDB_READ_ACCESS_TOKEN", "").strip()
    api_key = env.get("TMDB_API_KEY", "").strip()

    headers = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif api_key:
        params["api_key"] = api_key
    else:
        sys.exit("ERROR: no TMDB credentials found. Copy .env.example to .env and fill it in.")

    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        sys.exit(f"ERROR: TMDB returned HTTP {exc.code} for {path}\n{body}")
    except urllib.error.URLError as exc:
        sys.exit(f"ERROR: could not reach TMDB ({exc.reason}). Check your network policy.")


def search_movies(title: str, env: dict[str, str], year: int | None) -> list[dict]:
    params: dict = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = year
    return tmdb_get("/search/movie", env, params).get("results", [])


def get_movie_details(movie_id: int, env: dict[str, str]) -> dict:
    return tmdb_get(f"/movie/{movie_id}", env, {"append_to_response": "credits"})


# --------------------------------------------------------------------------- #
# Mapping
# --------------------------------------------------------------------------- #
def to_catalog_entry(details: dict, top_cast: int = 4) -> dict:
    """Map a TMDB details+credits payload to a catalog record (schemas/movie.schema.json)."""
    credits = details.get("credits", {})
    director = next(
        (c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"),
        None,
    )
    cast = [c["name"] for c in credits.get("cast", [])[:top_cast]]
    release_date = details.get("release_date") or ""
    release_year = int(release_date[:4]) if release_date[:4].isdigit() else None

    entry = {
        "tmdb_id": details["id"],
        "title": details.get("title") or details.get("original_title"),
        "release_year": release_year,
        "genres": [g["name"] for g in details.get("genres", [])],
        "director": director,
        "cast": cast,
        "runtime": details.get("runtime"),
        "poster_path": details.get("poster_path"),
        "overview": details.get("overview"),
        "watched": True,
        "added_at": __import__("datetime").date.today().isoformat(),
    }
    # Drop keys that came back empty so we don't store nulls.
    return {k: v for k, v in entry.items() if v not in (None, "", [])}


def poster_url(poster_path: str | None, env: dict[str, str]) -> str | None:
    if not poster_path:
        return None
    base = env.get("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p/")
    size = env.get("TMDB_POSTER_SIZE", "w500")
    return f"{base}{size}{poster_path}"


# --------------------------------------------------------------------------- #
# Catalog I/O
# --------------------------------------------------------------------------- #
def load_catalog(path: Path = CATALOG_PATH) -> dict:
    if path.exists():
        data = json.loads(path.read_text())
        data.setdefault("movies", {})
        return data
    return {"movies": {}}


def upsert(entry: dict, path: Path = CATALOG_PATH) -> tuple[dict, bool]:
    catalog = load_catalog(path)
    key = str(entry["tmdb_id"])
    existed = key in catalog["movies"]
    # Preserve the original added_at on update.
    if existed and "added_at" in catalog["movies"][key]:
        entry["added_at"] = catalog["movies"][key]["added_at"]
    catalog["movies"][key] = entry
    # Keep entries sorted by id for stable, reviewable diffs.
    catalog["movies"] = dict(sorted(catalog["movies"].items(), key=lambda kv: int(kv[0])))
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    return entry, existed


# --------------------------------------------------------------------------- #
# Result selection
# --------------------------------------------------------------------------- #
def label(result: dict) -> str:
    year = (result.get("release_date") or "????")[:4]
    return f"{result.get('title', '?')} ({year})  [tmdb:{result['id']}]"


def choose(results: list[dict], pick: int | None) -> dict:
    if not results:
        sys.exit("No results found. Try adding/removing --year or checking the spelling.")
    if pick is not None:
        if not 1 <= pick <= len(results):
            sys.exit(f"--pick {pick} is out of range (1..{len(results)}).")
        return results[pick - 1]
    if len(results) == 1:
        return results[0]
    print("Multiple matches:", file=sys.stderr)
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {label(r)}", file=sys.stderr)
    if not sys.stdin.isatty():
        sys.exit("Ambiguous match in non-interactive mode — re-run with --pick N or --id.")
    raw = input("Pick a number (default 1): ").strip()
    idx = int(raw) if raw.isdigit() else 1
    return results[idx - 1]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch TMDB metadata into data/movies.json")
    parser.add_argument("title", nargs="?", help="Movie title to search for")
    parser.add_argument("--id", type=int, help="Skip search; fetch this exact TMDB id")
    parser.add_argument("--year", type=int, help="Release year to disambiguate the search")
    parser.add_argument("--pick", type=int, help="Non-interactively take the Nth search result")
    parser.add_argument("--dry-run", action="store_true", help="Print the entry but don't write")
    args = parser.parse_args(argv)

    if not args.id and not args.title:
        parser.error("provide a TITLE to search, or --id for an exact TMDB id")

    env = load_env()

    if args.id:
        movie_id = args.id
    else:
        results = search_movies(args.title, env, args.year)
        movie_id = choose(results, args.pick)["id"]

    details = get_movie_details(movie_id, env)
    entry = to_catalog_entry(details)

    print(f"\n{entry['title']} ({entry.get('release_year', '?')})")
    print(f"  genres   : {', '.join(entry.get('genres', [])) or '—'}")
    print(f"  director : {entry.get('director', '—')}")
    print(f"  cast     : {', '.join(entry.get('cast', [])) or '—'}")
    print(f"  runtime  : {entry.get('runtime', '—')} min")
    print(f"  poster   : {poster_url(entry.get('poster_path'), env) or '—'}")

    if args.dry_run:
        print("\n--dry-run: nothing written. Entry preview:")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    _, existed = upsert(entry)
    verb = "Updated" if existed else "Added"
    print(f"\n{verb} {entry['title']} in {CATALOG_PATH.relative_to(REPO_ROOT)}")
    print("Next: rank it into each of its genres — see docs/ranking-method.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
