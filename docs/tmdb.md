# TMDB integration

[TMDB](https://www.themoviedb.org/) is the metadata source: titles, genres,
directors, cast, runtimes, overviews, and **posters** (which keeps the long-shot
"rotating poster wall" idea alive).

## Credentials

Two credentials, both kept in `.env` (gitignored — never committed):

| Variable                  | TMDB API version | Auth style                         |
| ------------------------- | ---------------- | ---------------------------------- |
| `TMDB_READ_ACCESS_TOKEN`  | v4 (preferred)   | `Authorization: Bearer <token>`    |
| `TMDB_API_KEY`            | v3 (fallback)    | `?api_key=<key>` query parameter   |

Copy `.env.example` → `.env` and paste the values in. Prefer the v4 read access
token; keep the v3 key for tools/endpoints that still expect it.

> 🔐 **Security:** the token/key were shared in plaintext while setting this up.
> Consider rotating them at <https://www.themoviedb.org/settings/api> once things
> are running, and only ever keep the live values in the gitignored `.env`.

## Endpoints we actually use

Base URL: `https://api.themoviedb.org/3`

| Purpose                       | Endpoint                                        |
| ----------------------------- | ----------------------------------------------- |
| Find a movie by title         | `GET /search/movie?query=<title>&year=<year>`   |
| Full details (genres, runtime)| `GET /movie/{movie_id}`                          |
| Director + cast               | `GET /movie/{movie_id}/credits`                 |
| Image config (sizes)          | `GET /configuration`                            |

Tip: `GET /movie/{movie_id}?append_to_response=credits` returns details **and**
credits in a single call.

### Mapping a TMDB response → our catalog entry

- `director`  → from `credits.crew`, the member whose `job` is `"Director"`.
- `cast`      → first ~4 of `credits.cast` (already billing-ordered), their `name`s.
- `genres`    → `genres[].name` (these become our genre ranking files).
- `poster_path`, `runtime`, `overview`, `release_date` (→ `release_year`) map directly.

## Building a poster URL

```
poster_url = TMDB_IMAGE_BASE_URL + TMDB_POSTER_SIZE + poster_path
```

e.g. `https://image.tmdb.org/t/p/w500/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg`

Common poster sizes: `w92`, `w154`, `w185`, `w342`, `w500`, `w780`, `original`.
We store only `poster_path` in the catalog and build full URLs on demand, so we
can change sizes later without rewriting data.

## The fetch script — `scripts/fetch_movie.py`

A zero-dependency (stdlib-only) helper that does the search → details → credits →
catalog mapping for you and upserts the result into `data/movies.json`.

```bash
# Search by title (interactive pick if several films match)
python scripts/fetch_movie.py "Inception" --year 2010

# Skip search and fetch an exact TMDB id
python scripts/fetch_movie.py --id 27205

# Non-interactive: take the Nth search result (good for scripts/CI)
python scripts/fetch_movie.py "Dune" --pick 2

# Preview the mapped entry without writing
python scripts/fetch_movie.py "Heat" --year 1995 --dry-run
```

It reads credentials from `.env`, prefers the v4 Bearer token, preserves the
original `added_at` on updates, keeps `data/movies.json` sorted by id (clean
diffs), and emits a record that matches `schemas/movie.schema.json`. After it
adds a movie, rank it into each of its genres (see `ranking-method.md`).

> **Network note:** the script talks to `api.themoviedb.org` (and posters come
> from `image.tmdb.org`). In a sandboxed environment with an egress allowlist,
> add both hosts to the network settings, or run the script locally where
> outbound HTTPS is open.

## Quick connectivity check

With the v4 token loaded into your shell:

```bash
source .env
curl -s --request GET \
  --url 'https://api.themoviedb.org/3/search/movie?query=Inception&year=2010' \
  --header "Authorization: Bearer $TMDB_READ_ACCESS_TOKEN" \
  --header 'accept: application/json'
```

A JSON payload with an `Inception` result confirms the token works.
