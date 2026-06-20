# Security & credentials

This is a personal project, but it talks to a third-party API with a token, so a
small amount of credential hygiene keeps things clean.

## Where credentials live

There is exactly one secret that matters: the **TMDB credentials**
(`TMDB_READ_ACCESS_TOKEN`, optionally `TMDB_API_KEY`). They live in **two**
approved places, and nowhere else:

| Context                | Source                          | Notes                                  |
| ---------------------- | ------------------------------- | -------------------------------------- |
| Local development      | `.env` (gitignored)             | Fast iteration; never committed.       |
| GitHub Actions / CI    | GitHub repository **Secrets**   | The secure default; nothing on disk.   |

`scripts/fetch_movie.py` reads from `.env` first, then lets environment
variables override — so the **same code** runs in both contexts with no changes.

**Never** put a real token in: committed files, `.env.example` (placeholders
only), code, commit messages, PR descriptions, issues, or logs.

## The guardrail

`.github/workflows/guard-secrets.yml` runs on every push and pull request and
**fails the build if any `.env` file is ever tracked by git** (`.env.example` is
allowed). `.gitignore` is the first line of defense; this CI check is the
backstop so a slip can't be merged.

For extra protection, enable GitHub's native **secret scanning + push
protection** (Settings → Code security) — it blocks known token formats at push
time. It's complementary to the guard above.

## If a credential is exposed

Assume any token that has appeared in a chat, a log, a screenshot, or a commit is
**compromised** — rotate it, don't just delete the message.

1. Go to <https://www.themoviedb.org/settings/api>.
2. Regenerate the API key / read access token.
3. Update the value in your local `.env` **and** in GitHub repository Secrets.
4. Done — the old token stops working immediately.

> **Action item:** the TMDB token was shared in plaintext while setting this
> project up, so it should be rotated per the steps above. Until then, treat it
> as public.
