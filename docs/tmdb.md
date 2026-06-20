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
