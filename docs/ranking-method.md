# Ranking method — pairwise comparison

We don't ask "rate this 1–10." Absolute scores drift and age badly. Instead we
place each new movie into an already-ordered list using **pairwise comparisons** —
the same way you'd sort a hand of cards: compare to one card, then another, until
you know where it slots in.

This is **binary insertion sort**, one movie at a time.

---

## The insertion algorithm (per genre)

When a movie needs to be placed into a genre list that already has `N` ranked films:

1. If the list is empty, it goes to rank 1. Done.
2. Otherwise, binary-search for its position:
   - Compare the new movie to the film in the **middle** of the current search range.
   - *"Is **New Movie** better than **Middle Movie**?"*
     - **Better** → search the upper half (better positions).
     - **Worse** → search the lower half (worse positions).
   - Repeat, halving the range each time.
3. Insert at the found position; everything below shifts down one rank.

Binary insertion means roughly **log₂(N)** questions per movie — placing a film
into a list of 32 takes about 5 comparisons, not 32.

### Worked example

Placing *Interstellar* into a Sci-Fi list of 7 films (ranks 1–7):

```
range = ranks 1..7   → compare vs rank 4.  Better? → yes → range = 1..3
range = ranks 1..3   → compare vs rank 2.  Better? → no  → range = 3..3
range = rank 3       → compare vs rank 3.  Better? → yes → insert at rank 3
```

3 questions, and *Interstellar* lands at rank 3 (old ranks 3–7 shift to 4–8).

---

## A movie with multiple genres

TMDB tags most films with 2–3 genres. Each genre list is **independent**, so the
movie is inserted into each one separately. *Inception* might be Sci-Fi #1 but
Action #6 — that's expected and exactly what makes the subcategory views useful.

To keep sessions short, Haiku may reuse signal across genres (if you said it beats
*The Matrix* overall, that informs both the Sci-Fi and Action insertions), but each
list's final position is still confirmed.

---

## Re-ranking and ties

- **Moving a movie:** treat it as a removal + a fresh insertion. Don't nudge ranks
  by hand — re-run the comparison so the list stays internally consistent.
- **"They're basically equal":** the tie-breaker is recency of viewing / gut call;
  pick one to sit above the other. We keep a strict total order (no shared ranks)
  so subcategory sorting is deterministic.
- **Recompute `rank`:** after any insert/move, `rank` is just `index + 1`. The
  `tmdb_id` order is the real data.

---

## Why not Elo / scores?

Elo and 1–10 scores were considered. Pairwise insertion wins for this use case
because:

- The output **is** a clean ordered list — no threshold-picking to turn scores into ranks.
- It's stable: adding film #50 doesn't reshuffle films #1–49.
- The questions are natural to answer out loud ("is this better than that?").

If the catalog ever gets large enough that insertion feels slow, an Elo layer can
be added later **on top of** the same comparison data — the pairwise judgments are
exactly what Elo would need.
