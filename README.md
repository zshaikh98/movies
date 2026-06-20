# 🎬 Movie Ranking System

A personal system for ranking movies I've watched — organized by **genre** as the
source of truth, with everything else (favorite films of an actor, a director, a
decade, etc.) derived from those master genre rankings.

The rankings are built conversationally: an assistant (Claude **Haiku**) interviews
me — *"Have you seen this? Where does it land versus this other one?"* — and logs
the results. Each movie is enriched with metadata from **TMDB** (poster, cast,
director, year, runtime) so the dataset can later feed a database and, maybe one
day, a rotating wall of movie posters.

> **Status:** No application stack yet. This is intentionally a manual,
> conversation-driven workflow. The structure here is designed so a real app/DB
> can be layered on later without reshaping the data.

---

## Core idea

```
        ┌─────────────────────────────────────────┐
        │   MASTER RANKINGS  (per genre, ordered)   │  ← the source of truth
        │   data/rankings/<genre>.json              │
        └─────────────────────────────────────────┘
                          │  derived from
                          ▼
        ┌─────────────────────────────────────────┐
        │   SUBCATEGORIES  (filtered + re-sorted)   │  ← views, never ranked by hand
        │   data/subcategories/<type>/<name>.json   │
        │   e.g. "best DiCaprio films",             │
        │        "best films of the 90s"            │
        └─────────────────────────────────────────┘
```

1. **Master rankings are done by genre.** A movie can appear in several genre
   rankings (TMDB usually tags 2–3 genres per film).
2. **Subcategories are derived, not re-ranked.** "Favorite Leonardo DiCaprio
   movies" = take every DiCaprio film I've ranked, pull its position from the
   master genre rankings, and re-sort. No new manual ranking required.
3. **TMDB supplies metadata** for every movie (poster, cast, director, etc.).

---

## How a ranking session works

The interview loop (driven by Haiku — see [`docs/ranking-session.md`](docs/ranking-session.md)):

1. I name a movie (or Haiku suggests one).
2. **Seen it?** If no, it's skipped (optionally logged to a watchlist).
3. TMDB lookup → confirm the right title/year, pull genres + metadata.
4. For each of its genres, Haiku finds its spot via **pairwise comparison**
   ("Is it better than *X*? Better than *Y*?") — a binary insertion into the
   ordered list.
5. The movie's metadata is saved to the catalog, and its rank is written into
   each relevant genre list.

The comparison method is described in [`docs/ranking-method.md`](docs/ranking-method.md).

---

## Repository layout

```
movies/
├── README.md                     ← you are here
├── .env.example                  ← copy to .env, add your TMDB keys
├── .gitignore                    ← keeps .env and cruft out of git
│
├── docs/
│   ├── data-model.md             ← what every file/record looks like
│   ├── ranking-method.md         ← the pairwise-comparison ranking logic
│   ├── ranking-session.md        ← the Haiku interview workflow + prompt
│   └── tmdb.md                   ← TMDB API integration notes
│
├── data/
│   ├── movies.json               ← master catalog of movie metadata
│   ├── genres.json               ← canonical TMDB genre list
│   ├── rankings/                 ← one ordered file per genre
│   │   └── science-fiction.json  ← (example, with sample entries)
│   └── subcategories/            ← derived views (actor, director, decade…)
│       └── actor/
│           └── leonardo-dicaprio.json  ← (example)
│
├── scripts/
│   └── fetch_movie.py            ← pull TMDB metadata into the catalog (stdlib only)
│
└── schemas/                      ← JSON Schemas for future validation / DB import
    ├── movie.schema.json
    └── genre-ranking.schema.json
```

## Adding a movie's metadata

`scripts/fetch_movie.py` is a zero-dependency helper (Python stdlib only) that
looks a film up on TMDB and writes it into `data/movies.json`:

```bash
python scripts/fetch_movie.py "Inception" --year 2010   # search + add
python scripts/fetch_movie.py --id 27205                # exact TMDB id
python scripts/fetch_movie.py "Heat" --year 1995 --dry-run   # preview only
```

It reads your token from `.env` and emits records matching
`schemas/movie.schema.json`. Details + the egress-allowlist note are in
[`docs/tmdb.md`](docs/tmdb.md).

**Or run it from GitHub** — no local setup needed. Store your TMDB token in
repository secrets and use the **Fetch movie metadata** workflow
(`.github/workflows/fetch-movie.yml`): Actions tab → *Run workflow* → type a
title/year, and it commits the result back. Setup steps are in
[`docs/tmdb.md`](docs/tmdb.md#running-it-from-github-actions).

---

## Setup

```bash
cp .env.example .env
# then paste your TMDB credentials into .env
```

Two supported ways to supply credentials — use whichever fits the moment:

- **Local** (`.env`) — best for fast, iterative work (e.g. bulk-adding films
  during a ranking session). Gitignored, never committed.
- **GitHub Secrets** — the secure default for running the fetch from anywhere,
  with no credentials on disk. See
  [running it from Actions](docs/tmdb.md#running-it-from-github-actions).

The credential model, rotation steps, and the CI guardrail are documented in
[`SECURITY.md`](SECURITY.md). The same `fetch_movie.py` reads from either source
(env vars override `.env`), so there's nothing to switch.

---

## Roadmap

- [x] Define the data model and folder structure
- [x] TMDB fetch script to populate the catalog
- [ ] Run the first Haiku ranking sessions, genre by genre
- [ ] Backfill TMDB metadata for everything ranked
- [ ] Generate the first subcategory views (actor / director / decade)
- [ ] *(maybe)* Move JSON → a real database
- [ ] *(long shot)* Feed the DB into a rotating poster display
