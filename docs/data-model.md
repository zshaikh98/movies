# Data model

Everything is JSON for now — human-readable, easy to hand-edit during a session,
and trivial to import into a real database later. There are three kinds of data:

1. **The movie catalog** — metadata about each film (one source of truth).
2. **Genre rankings** — ordered lists, one file per genre. *The master ranking.*
3. **Subcategories** — derived views, computed from the genre rankings.

The golden rule: **metadata lives once in the catalog; rankings only reference
movies by `tmdb_id`.** (Titles are duplicated into ranking files purely for human
readability while we work by hand — `tmdb_id` is the real link.)

---

## 1. Movie catalog — `data/movies.json`

A map keyed by TMDB id. One entry per movie I've seen and ranked.

```json
{
  "movies": {
    "27205": {
      "tmdb_id": 27205,
      "title": "Inception",
      "release_year": 2010,
      "genres": ["Science Fiction", "Action", "Adventure"],
      "director": "Christopher Nolan",
      "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page", "Tom Hardy"],
      "runtime": 148,
      "poster_path": "/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg",
      "overview": "Cobb steals secrets from within the subconscious...",
      "watched": true,
      "added_at": "2026-06-20"
    }
  }
}
```

| Field          | Source | Notes                                                        |
| -------------- | ------ | ------------------------------------------------------------ |
| `tmdb_id`      | TMDB   | Primary key. Also the link used by ranking files.            |
| `title`        | TMDB   | Display title.                                               |
| `release_year` | TMDB   | Disambiguates remakes / same-title films.                    |
| `genres`       | TMDB   | Drives which genre ranking files the movie appears in.       |
| `director`     | TMDB   | From the `credits` crew (job = "Director").                  |
| `cast`         | TMDB   | Top ~4 billed actors. Powers actor subcategories.            |
| `runtime`      | TMDB   | Minutes.                                                     |
| `poster_path`  | TMDB   | Relative path; build a URL via `docs/tmdb.md`.               |
| `overview`     | TMDB   | Short synopsis.                                              |
| `watched`      | me     | Always `true` for ranked films (kept for future watchlist). |
| `added_at`     | system | Date the entry was created (`YYYY-MM-DD`).                   |

---

## 2. Genre rankings — `data/rankings/<genre>.json`

One file per genre. The filename is the genre **slug** (lowercase, hyphenated):
`Science Fiction` → `science-fiction.json`. The list is ordered best → worst;
`rank` is just the 1-based position and is recomputed whenever the order changes.

```json
{
  "genre": "Science Fiction",
  "slug": "science-fiction",
  "updated_at": "2026-06-20",
  "ranked": [
    { "rank": 1, "tmdb_id": 27205, "title": "Inception" },
    { "rank": 2, "tmdb_id": 157336, "title": "Interstellar" },
    { "rank": 3, "tmdb_id": 78,     "title": "Blade Runner" }
  ]
}
```

A movie tagged with three genres appears in three of these files, each with its
own independent rank.

---

## 3. Subcategories — `data/subcategories/<type>/<name>.json`

**Derived, never hand-ranked.** A subcategory is a filter over the catalog plus a
sort rule that reads from the master genre rankings.

```json
{
  "type": "actor",
  "name": "Leonardo DiCaprio",
  "slug": "leonardo-dicaprio",
  "derived_from": "master genre rankings",
  "sort_rule": "best master genre rank, ties broken by title",
  "generated_at": "2026-06-20",
  "ranked": [
    { "rank": 1, "tmdb_id": 27205,  "title": "Inception",          "best_genre": "Science Fiction", "genre_rank": 1 },
    { "rank": 2, "tmdb_id": 137,    "title": "The Departed",       "best_genre": "Crime",           "genre_rank": 2 }
  ]
}
```

Supported `type` values to start: `actor`, `director`, `decade`. New types are
just new folders — the derivation logic is the same: filter the catalog, then
order by each film's best (lowest) rank across its genres.

> Because subcategories are computed, they can always be regenerated from
> `movies.json` + `rankings/`. If they ever disagree, the genre rankings win.

---

## Slugs

Used for filenames everywhere. Rule: lowercase, spaces → `-`, strip anything that
isn't `a–z`, `0–9`, or `-`. Examples:

| Value             | Slug                |
| ----------------- | ------------------- |
| `Science Fiction` | `science-fiction`   |
| `Leonardo DiCaprio` | `leonardo-dicaprio` |
| `1990s`           | `1990s`             |
