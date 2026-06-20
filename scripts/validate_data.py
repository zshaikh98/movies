#!/usr/bin/env python3
"""Validate the data files for structure and referential integrity.

Zero dependencies (stdlib only). Run locally or in CI:

    python scripts/validate_data.py

Checks:
  * data/movies.json   — required fields per record; map key matches tmdb_id.
  * data/rankings/*.json — slug format; rank == position; every tmdb_id and
                           title exists in the catalog (referential integrity).
  * data/subcategories/**/*.json — every referenced tmdb_id exists in the catalog.

Exits non-zero (listing every problem) if anything is wrong. This protects the
catalog that the fetch workflow auto-commits.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
CATALOG_PATH = DATA / "movies.json"
RANKINGS_DIR = DATA / "rankings"
SUBCATS_DIR = DATA / "subcategories"

SLUG_RE = re.compile(r"^[a-z0-9-]+$")

errors: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        err(path.relative_to(REPO_ROOT).as_posix(), f"invalid JSON ({exc})")
        return None


def validate_catalog() -> dict[int, dict]:
    """Validate movies.json and return {tmdb_id: record} for cross-checks."""
    rel = CATALOG_PATH.relative_to(REPO_ROOT).as_posix()
    catalog: dict[int, dict] = {}
    data = load_json(CATALOG_PATH)
    if data is None:
        return catalog
    if not isinstance(data.get("movies"), dict):
        err(rel, "missing top-level 'movies' object")
        return catalog

    for key, rec in data["movies"].items():
        where = f"{rel} -> movies['{key}']"
        if not isinstance(rec, dict):
            err(where, "record is not an object")
            continue
        for field, typ in (("tmdb_id", int), ("title", str), ("release_year", int)):
            if field not in rec:
                err(where, f"missing required field '{field}'")
            elif not isinstance(rec[field], typ):
                err(where, f"'{field}' must be {typ.__name__}")
        if not isinstance(rec.get("genres"), list) or not rec.get("genres"):
            err(where, "'genres' must be a non-empty array")
        if not isinstance(rec.get("watched"), bool):
            err(where, "'watched' must be a boolean")
        if isinstance(rec.get("tmdb_id"), int) and str(rec["tmdb_id"]) != key:
            err(where, f"map key '{key}' != tmdb_id {rec['tmdb_id']}")
        if isinstance(rec.get("tmdb_id"), int):
            catalog[rec["tmdb_id"]] = rec
    return catalog


def validate_rankings(catalog: dict[int, dict]) -> None:
    if not RANKINGS_DIR.exists():
        return
    for path in sorted(RANKINGS_DIR.glob("*.json")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        data = load_json(path)
        if data is None:
            continue
        slug = data.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            err(rel, f"'slug' missing or not a valid slug: {slug!r}")
        elif slug != path.stem:
            err(rel, f"'slug' ({slug}) does not match filename ({path.stem})")
        ranked = data.get("ranked")
        if not isinstance(ranked, list):
            err(rel, "'ranked' must be an array")
            continue
        for i, entry in enumerate(ranked, start=1):
            where = f"{rel} -> ranked[{i - 1}]"
            if entry.get("rank") != i:
                err(where, f"rank should be {i} (got {entry.get('rank')!r})")
            tmdb_id = entry.get("tmdb_id")
            if tmdb_id not in catalog:
                err(where, f"tmdb_id {tmdb_id!r} not found in catalog (data/movies.json)")
            elif entry.get("title") != catalog[tmdb_id].get("title"):
                err(where, f"title {entry.get('title')!r} != catalog title "
                           f"{catalog[tmdb_id].get('title')!r}")


def validate_subcategories(catalog: dict[int, dict]) -> None:
    if not SUBCATS_DIR.exists():
        return
    for path in sorted(SUBCATS_DIR.rglob("*.json")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        data = load_json(path)
        if data is None:
            continue
        ranked = data.get("ranked")
        if not isinstance(ranked, list):
            err(rel, "'ranked' must be an array")
            continue
        for i, entry in enumerate(ranked):
            if entry.get("tmdb_id") not in catalog:
                err(f"{rel} -> ranked[{i}]",
                    f"tmdb_id {entry.get('tmdb_id')!r} not found in catalog")


def main() -> int:
    catalog = validate_catalog()
    validate_rankings(catalog)
    validate_subcategories(catalog)

    if errors:
        print(f"✗ {len(errors)} problem(s) found:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"✓ data is valid — {len(catalog)} movie(s) in the catalog, all references resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
