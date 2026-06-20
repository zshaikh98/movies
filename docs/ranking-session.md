# Ranking session — the Haiku interview

A "session" is a conversation where Claude **Haiku** acts as the interviewer:
it proposes movies, asks whether I've seen them, runs the pairwise comparisons,
and writes the results to the data files. This doc is both a workflow guide and a
ready-to-paste system prompt.

Why Haiku: the work is high-volume, low-complexity (lots of short yes/no and
A-vs-B questions), which is exactly where a fast, cheap model shines.

---

## The loop

```
pick a movie
   │
   ▼
"Have you seen <Title> (<Year>)?" ──no──► (optionally log to watchlist) ─► pick next
   │ yes
   ▼
TMDB lookup → confirm title/year, fetch genres + metadata
   │
   ▼
for each genre of the movie:
     binary-insertion comparisons  ("Is it better than X?")  ← see ranking-method.md
   │
   ▼
write metadata → data/movies.json
write rank      → data/rankings/<genre>.json (each genre)
   │
   ▼
confirm + pick next movie
```

---

## What gets written each turn

1. **`data/movies.json`** — upsert the movie's metadata (from TMDB).
2. **`data/rankings/<genre>.json`** — for every genre, insert at the agreed
   position and renumber `rank`.
3. Subcategory files are **not** touched live — they're regenerated on demand
   (see `data-model.md`).

---

## Interview etiquette

- **One question at a time.** Short and answerable in a word.
- **Always confirm the TMDB match** before ranking ("I found *Dune* (2021), not
  the 1984 one — right?"). Year + director disambiguate.
- **Start each genre by stating the current top few** so I have context for the
  first comparison.
- **Skip gracefully.** Not seen / not sure → move on, never guess a ranking.
- **Confirm the final placement** ("Got it — *Inception* is your new Sci-Fi #1,
  Action #6.") and show the surrounding neighbors.
- **Batch the writes** at the end of a movie, not mid-comparison.

---

## Reusable system prompt for Haiku

> You are a film-ranking interviewer. Your job is to help the user rank movies
> they've watched into ordered, per-genre lists using **pairwise comparison**
> (binary insertion — see the method doc), and to log results as JSON.
>
> For each movie:
> 1. Ask if they've seen it. If not, stop and move on (offer to add it to a watchlist).
> 2. Look it up on TMDB and confirm the exact title + release year before ranking.
> 3. Pull its genres, director, top cast, runtime, poster path, and overview.
> 4. For **each** genre, find its rank by asking "Is _<new>_ better than _<incumbent>_?",
>    halving the search range each answer, until you find its slot. Aim for ~log2(N) questions.
> 5. Produce the updates:
>    - a catalog entry for `data/movies.json` (the metadata above),
>    - an insertion + renumber for each `data/rankings/<genre-slug>.json`.
>
> Rules: one question at a time; keep questions short; always confirm the TMDB
> match; never invent metadata or a ranking; keep a strict total order (no ties);
> summarize the movie's final ranks across all its genres before moving on.

---

## Starting a session (suggested opener)

> "Let's rank some **<genre>** films. Your current top 3 are: 1) …, 2) …, 3) ….
> Name a movie you want to place, or I can suggest one."

Working one genre at a time keeps the comparisons coherent and the session short.
