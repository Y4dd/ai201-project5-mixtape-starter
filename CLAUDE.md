# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This is a CodePath AI201 course assignment ("Project 5: Mixtape Bug Hunt"), forked at `github.com/Y4dd/ai201-project5-mixtape-starter`. `project.md` is the authoritative brief — it defines 4 milestones, the grading checkpoints, and the five bug reports (as written by the reporting users, with their exact repro steps). Read the relevant section of `project.md` before starting a milestone or picking up an issue; don't rely on summaries of it below.

`submission.md` is the graded deliverable built alongside the code: an AI-usage section, a codebase map (already written), and one root-cause-analysis entry per bug fixed (5 required fields each, format defined in `project.md`). Keep it updated per-issue, not as a batch at the end.

All five bugs are already filed as GitHub issues on the fork, numbered to match `project.md` 1:1 (`gh issue list`). Work references these issue numbers throughout.

## Environment & commands

- **Virtual environment**: this machine uses virtualfish, not a plain venv — there's already a `codepath` virtualfish env with deps installed. Use `vf activate codepath` in a shell, or `vf connect codepath` once to link this directory so `cd` auto-activates it. (The README's `python -m venv .venv` steps are the generic fallback for machines without virtualfish.)
- Install deps: `pip install -r requirements.txt`
- Seed/reset the DB (drops and recreates all tables): `python seed_data.py`
- Run the app: `FLASK_APP=app:create_app flask run` — **never `python app.py`**, it double-imports the app/db and throws a SQLAlchemy error.
- Hits `http://127.0.0.1:5000`. On macOS use `127.0.0.1`, not `localhost` (can resolve to IPv6 and hang).
- Run the full suite: `pytest tests/`
- Run one file: `pytest tests/test_streaks.py`
- Run one test: `pytest tests/test_streaks.py::test_streak_increments_on_sunday`
- Inspect DB state directly: `FLASK_APP=app:create_app flask shell`, then e.g. `from models import Song; Song.query.filter_by(title="...").all()`

### Verified baseline test state (as of a clean checkout + seed)

3 of 13 tests fail out of the box: `test_playlists.py::test_playlist_returns_all_songs`, `test_playlists.py::test_playlist_returns_songs_in_order` (both issue #5), and `test_streaks.py::test_streak_increments_on_sunday` (issue #1). These already act as regression tests once those two bugs are fixed.

`test_search.py::test_search_no_duplicates_multi_tag_song` **currently passes** even though issue #3 is open — its fixture's assumption ("a song with 3 tags will duplicate") does not actually reproduce the bug against real data (confirmed by calling `search_songs()` directly against seeded data: a 3-tag song returns exactly 1 result). Don't treat that test as proof #3 is fixed or as a description of the trigger condition — the real trigger is something else (per `project.md`'s own hint that it's conditional) and will need its own new/adjusted assertion.

No test file exists yet for `feed_service.py` (issue #2) or `notification_service.py` (issue #4) — either requires a new `tests/test_feed.py` / `tests/test_notifications.py` from scratch. All three existing test files share one fixture pattern (in-memory `sqlite:///:memory:` app fixture + a hand-built seed fixture) — follow that pattern for new test files rather than depending on `seed_data.py`'s state.

Also note: `seed_data.py`'s own docstring says it creates 25 songs; a real run currently produces 13. Don't write assertions against the docstring's counts — query/count from what actually got seeded.

## Architecture

- **App factory** (`app.py`): one shared `db = SQLAlchemy()` instance every other module imports, 4 blueprints registered under `/songs`, `/playlists`, `/users`, `/feed`, `db.create_all()` at factory time — no migrations layer.
- **Models** (`models.py`): all entities plus 3 raw `db.Table` association tables (`friendships`, `song_tags`, `playlist_entries`) — not model classes, except where extra columns are needed. IDs are app-generated UUID4 strings, not autoincrement ints. Every model has `to_dict()`, and that dict **is** the API response shape — there's no separate serialization layer. `playlist_entries` carries `position`/`added_by`/`added_at` beyond the two FKs, so playlist membership is an ordered, attributed relationship, not just a set.
- **Routes** (`routes/*.py`) are thin: parse the request, call exactly one service function, `jsonify` the result, turn a raised `ValueError` into a 400/404. No queries or business logic at this layer — if a route looks wrong, the bug is in the service it calls, not the route.
- **Services** (`services/*.py`) hold all business logic and DB queries, one file per feature area. This is where all five known bugs live.
- **Non-obvious file/blueprint mismatch**: `add_to_playlist()` — which mutates a playlist *and* fires a notification — lives in `notification_service.py`, not `playlist_service.py`. It's grouped by the action it performs (notify-on-add), not by the resource it touches. Don't assume everything that touches a playlist is in `playlist_service.py`.
- **Notifications are opt-in per call site, not event-driven.** There's no central hook firing on relevant writes — each service function that should notify someone calls `create_notification(...)` explicitly, at the point of the action. This is exactly the pattern issue #4 breaks: `rate_song()` in `notification_service.py` saves the `Rating` but has no corresponding `create_notification(...)` call, unlike `add_to_playlist()` right above it in the same file.
- **Datetime convention**: everything is timezone-aware UTC (`datetime.now(timezone.utc)`). Code comparing a stored datetime against "now" re-attaches `tzinfo=timezone.utc` first if it's naive (see `streak_service.update_listening_streak`) — match this convention in any date-comparison fix rather than introducing naive datetimes.

### The five known bugs

| # | Title | Service | Existing test coverage |
|---|-------|---------|------------------------|
| 1 | Listening streak resets every Sunday | `streak_service.py` | `test_streaks.py` (1 failing) |
| 2 | Friends Listening Now shows yesterday's activity | `feed_service.py` | none |
| 3 | Search returns the same song multiple times | `search_service.py` | `test_search.py` (passes, doesn't isolate the real trigger — see baseline note above) |
| 4 | No notification when a song is rated | `notification_service.py` | none |
| 5 | Most-recently-added playlist song is missing | `playlist_service.py` | `test_playlists.py` (2 failing) |

Full user-reported repro steps are in `project.md` under "The Five Open Issues" — read the actual report before touching a service file; it tells you what was observed, not the cause.

## Code navigation

Prefer the `semble` MCP tool (`search`, `find_related`) to locate code by symbol or keyword across this repo. Fall back to direct file reads/grep only when semble doesn't surface what's needed.

## Workflow: per-issue SDLC

Each bug is worked as its own GitHub issue (#1–#5 on the fork) through a full cycle rather than a quick patch:

1. **Plan** the issue before touching anything — reproduction approach, suspected root cause area, test strategy.
2. **Branch**: `gh issue view <N> --json title,body,url` to pull the canonical report, then `gh issue develop <N> --base bugfix/mixtape --name issue-<N>-<slug> --checkout` to create a linked branch off `bugfix/mixtape` and check it out.
3. **Reproduce first** (per `project.md` Milestone 2) — confirm the reported behavior before reading for a fix. For conditional bugs (#1's Sunday boundary, #3's inconsistent duplication), work out the specific state/inputs needed to hit the code path.
4. **Trace to root cause**: read the route, follow the exact call chain into `services/`, verify the diagnosis by running the code (temporary prints, `flask shell`, or isolating the function in a Python shell) — don't fix from a guess.
5. **Implement the smallest fix** that addresses the root cause.
6. **Write a regression test** that fails before the fix and passes after, for every issue worked here (not just the one `project.md` lists as a stretch goal). Put it in `tests/`, matching the existing fixture pattern.
7. **Check side effects**: re-run `pytest tests/` in full, and check other code touching the same data/feature (e.g., a streak fix should be re-checked against both sides of the day boundary).
8. **Commit** on the issue branch using a conventional message: `fix: <description>`.
9. **Comment on the issue** (`gh issue comment <N>`) with the confirmed root cause and what changed, before opening the PR.
10. **Write the root-cause-analysis entry** for this issue in `submission.md` before opening the PR — write it while the investigation is fresh, not in a batch at the end.
11. **Open a PR** from the issue branch into `bugfix/mixtape` (`gh pr create --base bugfix/mixtape`), title = the conventional commit message, body includes `Closes #<N>` and the root-cause analysis writeup from step 10.
12. **Squash-merge** the PR (`gh pr merge --squash`) — this is what keeps `bugfix/mixtape` at one commit per fix, satisfying `project.md`'s submission checkpoint even though the work happened on a branch.
13. **Explicitly close the issue**: `gh issue close <N> --comment "Fixed in <squash-sha> on bugfix/mixtape."` — this repo's default branch is `main`, not `bugfix/mixtape`, so GitHub's `Closes #N` auto-close keyword does not fire on merge here. `Closes #N` in the PR body still creates the cross-reference; closing the issue itself must be explicit.
14. **Clean up**: delete the issue branch after merge.

Each of `project.md`'s 4 milestones also gets its own short planning pass before execution — don't roll straight from finishing one milestone's checklist into the next without at least a brief plan for how you'll approach it.

## Managing context across a long multi-issue run

Executing the bug-fix plan (`docs/superpowers/plans/2026-07-07-mixtape-bug-fix-workflow.md`) across all 5 issues involves many subagent dispatches and can fill the context window well before all 16 tasks are done. Don't try to push through on a nearly-full context — checkpoint and clear instead:

- **Checkpoint before clearing**: check off completed steps in the plan file's `- [ ]` checklists (this is the actual source of truth for progress, not conversation memory), and make sure `git log`, `gh pr list`, and `gh issue list` on the repo reflect reality. If a task is mid-flight (e.g. implemented but not yet reviewed), leave a one-line note under its checkbox saying exactly what's left, the way Task 0's does.
- **Natural clearing boundaries**: the end of any task (0, Na, Nb, Nc), preferably right after a review stage passes or a squash-merge completes — not mid-investigation and not mid-review.
- **On resuming after a clear**: don't reconstruct progress from memory. Re-derive it from the plan file's checkboxes (what's done), `git log --oneline bugfix/mixtape` (what's merged), `gh issue list` (what's still open), and this file. Resume at the first unchecked step.
- This applies beyond this one plan too: for any long-running multi-task execution in this repo, prefer externalizing progress to files (plan checkboxes, commits, GitHub issues/PRs) over relying on context surviving the whole run.
