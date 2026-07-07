# Mixtape Bug Fix Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 5 filed GitHub issues (#1–#5) on `Y4dd/ai201-project5-mixtape-starter`, each through the pipeline defined in `docs/superpowers/specs/2026-07-07-mixtape-bug-fix-workflow-design.md`, landing as one squash-merged commit per issue on `bugfix/mixtape`, with a matching root-cause-analysis entry in `submission.md`.

**Architecture:** Each issue is split into 3 tasks instead of 1 — **Investigate** (dispatches a subagent that must stop at an unconfirmed hypothesis, no fix code), **Confirm & Fix** (starts with a human-confirmation gate, then TDD), and **Review & Integrate** (code review, RCA doc, PR, squash-merge, explicit issue close). A dispatched subagent cannot pause mid-run to ask the actual user a question, so the mandatory human gate must fall *between* tasks, never inside one — this split makes that true regardless of whether the plan is executed via subagent-driven-development (whose natural between-task review point becomes the gate) or executing-plans. Issue order (1→5 below) is not fixed by the design — reorder freely at execution time.

**Tech Stack:** Flask, SQLAlchemy 2.0, pytest, `gh` CLI, git.

**Workflow change (2026-07-07, effective from Issue #2 onward):** user decided all fixes commit directly onto `bugfix/mixtape` — no per-issue branch (`gh issue develop`), no PR, no squash-merge, no branch cleanup. For every remaining issue task below (2b/2c through 5b/5c), skip any step that creates a branch, pushes it, opens a PR, merges a PR, or deletes a branch — everything else (investigate, human-confirmation gate, TDD fix, commit directly to `bugfix/mixtape`, issue comment, code review, RCA entry in `submission.md`, explicit `gh issue close <N>`) still applies. This also sidesteps a sandbox restriction in this environment where `gh issue develop`'s branch-tracking setup needs to write `.git/config`, which is blocked by default.

**Cross-issue entanglement:** if any Investigate task's confirmed root cause turns out to overlap with another of the 5 issues, stop before starting that issue's Confirm & Fix task and surface it — decide with the user whether to split the fix or handle it as a combined PR closing both issues, rather than silently bundling two issues into one branch.

**Note on deferred content:** Task steps below contain complete, exact commands and prompts for everything that's knowable now. The one narrow exception is fix/test code tied to a not-yet-confirmed root cause (Tasks 1b/2b/3b/4b/5b, Step 3 onward) — that content is discovered by the Investigate task and confirmed by the human, which is the pipeline's entire purpose, not an oversight. Each such step says exactly what to base the code on and where it goes.

---

### Task 0: Correct the GitHub issue-closing assumption in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [x] **Step 1: Update branch-creation step**

In `CLAUDE.md`'s "Workflow: per-issue SDLC" section, find:
```
2. **Branch**: `git checkout -b issue-<N>-<slug> bugfix/mixtape`.
```
Replace with:
```
2. **Branch**: `gh issue view <N> --json title,body,url` to pull the canonical report, then `gh issue develop <N> --base bugfix/mixtape --name issue-<N>-<slug> --checkout` to create a linked branch off `bugfix/mixtape` and check it out.
```

- [x] **Step 2: Update integration steps**

Find:
```
9. **Open a PR** from the issue branch into `bugfix/mixtape` (`gh pr create --base bugfix/mixtape`), title = the conventional commit message, body includes `Closes #<N>` and the root-cause analysis writeup.
10. **Squash-merge** the PR (`gh pr merge --squash`) — this is what keeps `bugfix/mixtape` at one commit per fix, satisfying `project.md`'s submission checkpoint even though the work happened on a branch. Delete the issue branch after merge.
```
Replace with:
```
9. **Comment on the issue** (`gh issue comment <N>`) with the confirmed root cause and what changed, before opening the PR.
10. **Open a PR** from the issue branch into `bugfix/mixtape` (`gh pr create --base bugfix/mixtape`), title = the conventional commit message, body includes `Closes #<N>` and the root-cause analysis writeup.
11. **Squash-merge** the PR (`gh pr merge --squash`) — this is what keeps `bugfix/mixtape` at one commit per fix, satisfying `project.md`'s submission checkpoint even though the work happened on a branch.
12. **Explicitly close the issue**: `gh issue close <N> --comment "Fixed in <squash-sha> on bugfix/mixtape."` — this repo's default branch is `main`, not `bugfix/mixtape`, so GitHub's `Closes #N` auto-close keyword does not fire on merge here. `Closes #N` in the PR body still creates the cross-reference; closing the issue itself must be explicit.
13. Delete the issue branch after merge.
```

- [x] **Step 3: Commit directly to bugfix/mixtape**

  Done — commit `9e32e83`. Spec-compliance review: passed clean. Code-quality review: found one Important issue (step 10 referenced an RCA writeup not authored until step 14) and one related Minor issue (lost bold lead-ins on steps 13/14) — both fixed in commit `f6e15d1`. Task 0 fully complete; ready to start Task 1a.

```bash
git add CLAUDE.md
git commit -m "docs: correct issue-closing workflow to use explicit gh issue close"
```

---

## Issue #1 — Listening streak resets every Sunday

### Task 1a: Investigate Issue #1

**Files:** None — read-only investigation.

- [ ] **Step 1: Fetch the issue and create the linked branch**

```bash
gh issue view 1 --repo Y4dd/ai201-project5-mixtape-starter --json title,body,url -q '.title, .url, .body'
```
Expected output (verified):
```
Issue #1: My listening streak keeps resetting
https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/1
**Reported by:** kenji

I listen to something on Mixtape every single day — I haven't missed a day in weeks. On Saturday night my streak was at 12. Sunday morning I played a song like always, checked my profile, and my streak said **1**. This is the second time it's happened, and both times it was a Sunday. Listening again on Monday bumped it to 2, so it's counting again — it just threw away my whole streak.

**Steps I took:**
1. Listened to a song every calendar day, including Saturday.
2. Listened again Sunday morning and checked my streak (`GET /users/<my_id>/streak`).

**Expected:** streak goes from 12 to 13 — I listened on consecutive days.
**Actual:** streak shows 1, as if I'd skipped a day.
```
Then:
```bash
gh issue develop 1 --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape --name issue-1-streak-sunday-reset --checkout
```

- [ ] **Step 2: Dispatch the investigation subagent**

Use the Agent tool (`subagent_type: "Explore"`, `run_in_background: false`) with exactly this prompt:

```
Investigate GitHub issue #1 on the Mixtape app (Flask + SQLAlchemy). Do NOT write, edit, or suggest fix code — your only job is to reproduce, trace, and propose ONE hypothesis with evidence, then stop.

Issue report (verbatim from GitHub):
"""
I listen to something on Mixtape every single day — I haven't missed a day in weeks. On Saturday night my streak was at 12. Sunday morning I played a song like always, checked my profile, and my streak said 1. This is the second time it's happened, and both times it was a Sunday. Listening again on Monday bumped it to 2, so it's counting again — it just threw away my whole streak.

Steps taken: (1) Listened to a song every calendar day, including Saturday. (2) Listened again Sunday morning and checked the streak (GET /users/<my_id>/streak).

Expected: streak goes from 12 to 13 — listened on consecutive days.
Actual: streak shows 1, as if a day was skipped.
"""

Known context (already verified, don't re-derive):
- The relevant code is services/streak_service.py, function update_listening_streak().
- routes/users.py's /streak route calls get_streak(); routes/songs.py's /listen route calls record_listening_event(), which calls update_listening_streak().
- Datetimes in this codebase are timezone-aware UTC; code comparing a stored datetime to "now" re-attaches tzinfo=timezone.utc if it's missing.
- tests/test_streaks.py already has a test named test_streak_increments_on_sunday that currently FAILS — run `pytest tests/test_streaks.py -v` and read that test as a second, independent description of expected behavior.

Your task:
1. Read services/streak_service.py in full.
2. Run `pytest tests/test_streaks.py -v` and report the exact failure.
3. Trace update_listening_streak() line by line for the case of listening on a Saturday then a Sunday.
4. Form exactly ONE hypothesis: "I think X is the root cause because Y" — name the exact line and the exact incorrect comparison/condition.
5. Report: your hypothesis, the file/line, the evidence (test output and/or a manual trace of variable values), and any open uncertainty.

Do not modify any files. Do not propose fix code. Stop after reporting the hypothesis.
```

- [ ] **Step 3: Relay the hypothesis**

Report the subagent's hypothesis, file/line, and evidence back to the user in full. This is the handoff to Task 1b — do not proceed further in this task.

### Task 1b: Confirm & fix Issue #1

**Files:**
- Modify: `services/streak_service.py`
- Test: `tests/test_streaks.py`

- [ ] **Step 1: Human confirmation gate**

Ask the user exactly this, as a 3-way choice:
```
Confirmed — implement the fix
Not the root cause — re-investigate
Let me look first, pause here
```
If not confirmed, stop and return to Task 1a with whatever steer is given.

- [ ] **Step 2: Verify the existing regression test fails correctly**

```bash
pytest tests/test_streaks.py::test_streak_increments_on_sunday -v
```
Expected: FAIL, for the reason matching the confirmed hypothesis. If it fails for a different reason, stop and return to Task 1a — the hypothesis is wrong.

- [ ] **Step 3: Implement the minimal fix**

In `services/streak_service.py`, modify `update_listening_streak()` per the confirmed root cause (the exact line/condition named in Task 1a's hypothesis). Change only that condition — no restructuring.

- [ ] **Step 4: Verify green**

```bash
pytest tests/test_streaks.py -v
```
Expected: all tests in this file PASS.

- [ ] **Step 5: Run the full suite**

```bash
pytest tests/ -v
```
Expected: no new failures versus the baseline recorded in `CLAUDE.md`.

- [ ] **Step 6: Commit**

```bash
git add services/streak_service.py
git commit -m "fix: correct Sunday boundary condition in streak reset logic"
```

### Task 1c: Review & integrate Issue #1

**Files:**
- Modify: `submission.md`

- [ ] **Step 1: Comment on the issue**

```bash
gh issue comment 1 --repo Y4dd/ai201-project5-mixtape-starter --body "Root cause confirmed: <confirmed root cause from Task 1a/1b>. Fixed in services/streak_service.py::update_listening_streak(). Regression test: tests/test_streaks.py::test_streak_increments_on_sunday."
```

- [ ] **Step 2: Request code review**

```bash
BASE_SHA=$(git merge-base HEAD bugfix/mixtape)
HEAD_SHA=$(git rev-parse HEAD)
```
Dispatch the `superpowers:code-reviewer` subagent per the `requesting-code-review` skill, with `WHAT_WAS_IMPLEMENTED` = "Fix for Mixtape issue #1 (streak resets every Sunday)", `PLAN_OR_REQUIREMENTS` = this task, `BASE_SHA`, `HEAD_SHA`. Fix Critical/Important feedback as follow-up commits before continuing.

- [ ] **Step 3: Write the RCA entry**

In `submission.md`, add a `## Root Cause Analysis` section (first entry) with a `### Issue #1 — My listening streak keeps resetting` subsection covering all 5 required fields (issue/title; how reproduced — the report steps plus the Task 1b Step 2 test run; how root cause was found — the Task 1a navigation path; the root cause in plain English; the fix plus the Task 1b Step 5 side-effect check).

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin issue-1-streak-sunday-reset
gh pr create --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape \
  --title "fix: correct Sunday boundary condition in streak reset logic" \
  --body "Closes #1

<paste the RCA entry from Step 3>"
```

- [ ] **Step 5: Confirm and squash-merge**

Ask the user to confirm the PR is ready. Once confirmed:
```bash
gh pr merge --repo Y4dd/ai201-project5-mixtape-starter --squash
```

- [ ] **Step 6: Explicitly close the issue**

```bash
git fetch origin bugfix/mixtape
SHA=$(git rev-parse origin/bugfix/mixtape)
gh issue close 1 --repo Y4dd/ai201-project5-mixtape-starter --comment "Fixed in $SHA on bugfix/mixtape."
```

- [ ] **Step 7: Clean up**

```bash
git checkout bugfix/mixtape
git pull
git branch -d issue-1-streak-sunday-reset
```

---

## Issue #2 — Friends Listening Now shows people from yesterday

### Task 2a: Investigate Issue #2

**Files:** None — read-only investigation.

- [x] **Step 1: Fetch the issue**

```bash
gh issue view 2 --repo Y4dd/ai201-project5-mixtape-starter --json title,body,url -q '.title, .url, .body'
```
Expected output (verified):
```
Issue #2: Friends Listening Now shows people from yesterday
https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/2
**Reported by:** nova

"Friends Listening Now" is supposed to show me what my friends are playing right now — or at least what they've played *today*. This morning around 9am it showed darius "listening now" to a song he told me he played at **11pm last night**, before he went to bed. He hadn't opened the app all morning. Stuff from yesterday evening keeps hanging around in the feed until the same time the next day.

**Steps I took:**
1. Opened my feed in the morning (`GET /feed/<my_id>/listening-now`).
2. Cross-checked with darius: his last listen was the previous night.

**Expected:** only friends who have listened **today** appear.
**Actual:** friends whose last listen was yesterday evening still show up the next morning.
```

**Workflow change (2026-07-07):** user decided all bug fixes from Issue #2 onward commit directly onto `bugfix/mixtape` — no per-issue branch, no PR, no squash-merge. No linked branch is created for this issue; work happens directly on `bugfix/mixtape`. See CLAUDE.md's per-issue SDLC steps 2, 9-11, which this supersedes for the remainder of this plan.

- [x] **Step 2: Dispatch the investigation subagent**

Use the Agent tool (`subagent_type: "Explore"`, `run_in_background: false`) with exactly this prompt:

```
Investigate GitHub issue #2 on the Mixtape app (Flask + SQLAlchemy). Do NOT write, edit, or suggest fix code — your only job is to reproduce, trace, and propose ONE hypothesis with evidence, then stop.

Issue report (verbatim from GitHub):
"""
"Friends Listening Now" is supposed to show what a friend is playing right now, or at least what they've played today. This morning around 9am it showed darius "listening now" to a song he played at 11pm the previous night, before he went to bed. He hadn't opened the app all morning. Stuff from yesterday evening keeps hanging around in the feed until the same time the next day.

Steps taken: (1) Opened the feed in the morning (GET /feed/<my_id>/listening-now). (2) Cross-checked with darius: his last listen was the previous night.

Expected: only friends who listened today appear.
Actual: friends whose last listen was yesterday evening still show up the next morning.
"""

Known context (already verified, don't re-derive):
- The relevant code is services/feed_service.py, function get_friends_listening_now() (there is a second function, get_activity_feed(), which is a different, non-recency-filtered feed — not the one this issue is about).
- routes/feed.py's /listening-now route calls get_friends_listening_now() directly.
- Datetimes in this codebase are timezone-aware UTC.
- There is no existing test file for feed_service.py.

Your task:
1. Read services/feed_service.py in full.
2. Trace get_friends_listening_now() and identify exactly how it decides whether a friend's most recent listen counts as "now" (or "today").
3. Manually work through the reported scenario: a listen at 11pm one day, checked at 9am the next day — does the current logic include or exclude it, and why?
4. Form exactly ONE hypothesis: "I think X is the root cause because Y" — name the exact line/variable and explain the mismatch between what it computes and what "today" should mean.
5. Report: your hypothesis, the file/line, the evidence (the manual trace from step 3), and any open uncertainty.

Do not modify any files. Do not propose fix code. Stop after reporting the hypothesis.
```

- [x] **Step 3: Relay the hypothesis**

Report the subagent's hypothesis, file/line, and evidence back to the user in full. Handoff to Task 2b — do not proceed further here.

### Task 2b: Confirm & fix Issue #2

**Files:**
- Modify: `services/feed_service.py`
- Create: `tests/test_feed.py`

- [x] **Step 1: Human confirmation gate**

Confirmed by user: rolling 24h window (line 32/13) is the root cause. Proceeded to implement the fix.

- [x] **Step 2: Write the failing regression test**

No test file exists yet for this service. Create `tests/test_feed.py` starting from this exact boilerplate (copied from the existing fixture pattern used in `tests/test_streaks.py` and `tests/test_playlists.py`):

```python
"""
tests/test_feed.py — Mixtape

Tests for the "Friends Listening Now" feed logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent, friendships
from services.feed_service import get_friends_listening_now


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def two_friends(app):
    """Create two friended users and a song."""
    with app.app_context():
        user = User(username="me", email="me@example.com")
        friend = User(username="friend", email="friend@example.com")
        db.session.add_all([user, friend])
        db.session.flush()

        db.session.execute(friendships.insert().values(user_id=user.id, friend_id=friend.id))
        db.session.execute(friendships.insert().values(user_id=friend.id, friend_id=user.id))

        song = Song(title="Test Song", artist="Test Artist", shared_by=user.id)
        db.session.add(song)
        db.session.commit()
        yield {"user": user, "friend": friend, "song": song}


def test_listen_from_yesterday_evening_not_shown_this_morning(app, two_friends):
    """
    A friend's listen from 11pm the previous day should NOT appear in
    "listening now" at 9am the next day, even though it's within a
    rolling 24-hour window.
    """
    with app.app_context():
        user = two_friends["user"]
        friend = two_friends["friend"]
        song = two_friends["song"]

        yesterday_11pm = datetime(2024, 6, 10, 23, 0, 0, tzinfo=timezone.utc)
        event = ListeningEvent(user_id=friend.id, song_id=song.id, listened_at=yesterday_11pm)
        db.session.add(event)
        db.session.commit()

        this_morning_9am = datetime(2024, 6, 11, 9, 0, 0, tzinfo=timezone.utc)
        # <fill in based on confirmed hypothesis: call get_friends_listening_now
        # with "now" fixed at this_morning_9am, and assert the friend does NOT
        # appear. The exact mechanism for fixing "now" depends on how the
        # confirmed root cause is fixed in Step 3 below — e.g. if the fix
        # takes an explicit `now` parameter, pass this_morning_9am directly;
        # if it stays on datetime.now(timezone.utc), use unittest.mock.patch
        # on the datetime import in services.feed_service instead.>
```

Run:
```bash
pytest tests/test_feed.py -v
```
Expected: FAIL (or error, if `get_friends_listening_now` doesn't yet support fixing "now" — resolve that first) for the reason matching the confirmed hypothesis.

- [x] **Step 3: Implement the minimal fix**

In `services/feed_service.py`, modify `get_friends_listening_now()` per the confirmed root cause from Task 2a — replace whatever comparison currently treats "now" as "within the last 24 hours" with one that correctly identifies "since the start of today" per the confirmed hypothesis. If the fix requires the function to accept an explicit `now` for testability, add it as an optional parameter defaulting to `datetime.now(timezone.utc)` so the existing call site in `routes/feed.py` needs no change.

- [x] **Step 4: Verify green**

```bash
pytest tests/test_feed.py -v
```
Expected: PASS. Confirmed: both tests pass.

- [x] **Step 5: Run the full suite**

```bash
pytest tests/ -v
```
Expected: no new failures versus the baseline in `CLAUDE.md`. Confirmed: 2 failed / 13 passed — the 2 failures are the pre-existing, documented issue #5 baseline failures, unrelated to this change.

- [x] **Step 6: Verify before claiming this fixed**

Confirmed via actual pytest output (not memory): regression test passes, full suite has no new failures. code-reviewer subagent confirmed the fix is correct, minimal, and consistent with the codebase's UTC convention — no functional issues raised.

- [x] **Step 7: Commit**

Committed directly to `bugfix/mixtape` as `7c1be0a` (workflow change — see Task 2a Step 1 note; no separate branch).

```bash
git add services/feed_service.py tests/test_feed.py
git commit -m "fix: use calendar-day boundary instead of rolling 24h window in friends listening now"
```

### Task 2c: Review & integrate Issue #2

**Files:**
- Modify: `submission.md`

**Note:** Steps 4-5 and 7 below (PR, squash-merge, branch cleanup) are skipped per the Task 2a Step 1 workflow-change note — the fix is already a direct commit on `bugfix/mixtape`.

- [x] **Step 1: Comment on the issue**

Posted: https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/2#issuecomment-4909934227

- [x] **Step 2: Request code review**

Dispatched `superpowers:code-reviewer` comparing `6c356e6` (BASE, prior bugfix/mixtape commit) to `7c1be0a` (HEAD, this fix). Result: fix is correct/minimal/well-tested, no functional issues. Flagged the branch/PR bypass as a process deviation — acknowledged as an intentional, user-confirmed workflow change, not an oversight.

- [ ] **Step 3: Write the RCA entry**

In `submission.md`, add a `### Issue #2 — Friends Listening Now shows people from yesterday` subsection under `## Root Cause Analysis`, covering all 5 required fields as in Task 1c Step 3.

- [x] **Step 4-5: Skipped** — no PR/squash-merge; fix already lands as commit `7c1be0a` directly on `bugfix/mixtape`.

- [ ] **Step 6: Explicitly close the issue**

```bash
gh issue close 2 --repo Y4dd/ai201-project5-mixtape-starter --comment "Fixed in 7c1be0a on bugfix/mixtape."
```

- [x] **Step 7: Skipped** — no branch to clean up.

---

## Issue #3 — The same song shows up twice (or three times) in search

### Task 3a: Investigate Issue #3

**Files:** None — read-only investigation.

- [ ] **Step 1: Fetch the issue and create the linked branch**

```bash
gh issue view 3 --repo Y4dd/ai201-project5-mixtape-starter --json title,body,url -q '.title, .url, .body'
```
Expected output (verified):
```
Issue #3: The same song keeps showing up twice in search
https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/3
**Reported by:** simone

When I search, some songs come back two or even three times — identical entries, same song. I searched "Anthem" and *Crown Heights Anthem* by Borough Kings showed up **three times** in the results. Other songs only show up once. Nothing about the duplicates looks different; it's just the same result repeated.

**Steps I took:**
1. Searched for a song (`GET /songs/search?q=Anthem`).
2. Counted the results.

**Expected:** each matching song appears exactly once.
**Actual:** some songs appear once, others two or three times, for a single-song match.
```
Then:
```bash
gh issue develop 3 --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape --name issue-3-search-duplicate-results --checkout
```

- [ ] **Step 2: Dispatch the investigation subagent**

Use the Agent tool (`subagent_type: "Explore"`, `run_in_background: false`) with exactly this prompt:

```
Investigate GitHub issue #3 on the Mixtape app (Flask + SQLAlchemy). Do NOT write, edit, or suggest fix code — your only job is to reproduce, trace, and propose ONE hypothesis with evidence, then stop.

Issue report (verbatim from GitHub):
"""
Some songs come back two or three times in search results — identical entries, same song. Searching "Anthem" returned Crown Heights Anthem by Borough Kings three times. Other songs only show up once. Nothing about the duplicates looks different; it's the same result repeated.

Steps taken: (1) Searched for a song (GET /songs/search?q=Anthem). (2) Counted the results.

Expected: each matching song appears exactly once.
Actual: some songs appear once, others two or three times, for a single-song match.
"""

Known context (already verified, don't re-derive):
- The relevant code is services/search_service.py, function search_songs().
- IMPORTANT — a false lead already ruled out: tests/test_search.py has a fixture where a song has 3 tags, under the assumption that tag count alone causes duplication via the outerjoin(song_tags, ...) in search_songs(). This is WRONG — verified empirically: calling search_songs() directly against real seeded data, a song with 3 tags returns exactly 1 result, not 3. Do not re-verify this; it's already disproven. Find the ACTUAL condition that produces duplicates.
- Search results are built from `db.session.query(Song).outerjoin(song_tags, ...).filter(...).all()` — investigate what specifically differs between a song that comes back once and one that comes back multiple times.

Your task:
1. Read services/search_service.py in full.
2. Since the tag-count theory is already disproven, form a hypothesis about what data condition WOULD cause outerjoin(song_tags, ...) to multiply rows for a matching song, and design a concrete reproduction (e.g. via flask shell or a small script) using the real seeded data (run `python seed_data.py` first if needed) to confirm it.
3. Reproduce actual duplication (not just theorize) — find a real search query against the seeded data that returns a duplicate, and inspect what's different about that song/query versus one that doesn't duplicate.
4. Form exactly ONE hypothesis: "I think X is the root cause because Y" — name the exact condition that causes the fan-out.
5. Report: your hypothesis, the file/line, the evidence (the actual reproduction you found), and any open uncertainty.

Do not modify any files (seeding the db for local testing is fine, but don't commit any changes). Do not propose fix code. Stop after reporting the hypothesis.
```

- [ ] **Step 3: Relay the hypothesis**

Report the subagent's hypothesis, file/line, and evidence back to the user in full. Handoff to Task 3b — do not proceed further here.

### Task 3b: Confirm & fix Issue #3

**Files:**
- Modify: `services/search_service.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Human confirmation gate**

Ask the user exactly this, as a 3-way choice:
```
Confirmed — implement the fix
Not the root cause — re-investigate
Let me look first, pause here
```
If not confirmed, stop and return to Task 3a with whatever steer is given.

- [ ] **Step 2: Write a regression test that actually reproduces the bug**

`tests/test_search.py::test_search_no_duplicates_multi_tag_song` does NOT reproduce the real bug (verified in Task 3a). Based on the confirmed hypothesis from Task 3a, add a new test to `tests/test_search.py` (following that file's existing `app`/`seed_songs`-style fixture pattern) whose fixture recreates the actual confirmed triggering condition, not the tag-count assumption. Name it to describe the real condition, e.g. `test_search_no_duplicates_<real_condition>`.

Run:
```bash
pytest tests/test_search.py -v
```
Expected: the new test FAILS for the reason matching the confirmed hypothesis. If it passes immediately, the fixture doesn't actually reproduce the condition — fix the fixture, not the assertion.

- [ ] **Step 3: Implement the minimal fix**

In `services/search_service.py`, modify `search_songs()` per the confirmed root cause from Task 3a. If the root cause is join-based row fan-out, the typical minimal fix is adding `.distinct()` to the query (or restructuring to avoid the join entirely if it isn't needed for filtering) — but implement whatever the confirmed hypothesis actually points to, not this default assumption.

- [ ] **Step 4: Verify green**

```bash
pytest tests/test_search.py -v
```
Expected: all tests in this file PASS, including the pre-existing `test_search_no_duplicates_multi_tag_song` and the new test from Step 2.

- [ ] **Step 5: Run the full suite**

```bash
pytest tests/ -v
```
Expected: no new failures versus the baseline in `CLAUDE.md`.

- [ ] **Step 6: Verify before claiming this fixed**

Apply `verification-before-completion`: confirm via actual command output (not memory) that the regression test passes, the full suite passes, and — where practical — the exact repro steps from the issue report no longer produce the reported symptom. If 3+ distinct fix attempts have been tried in this task without success, stop and apply `systematic-debugging`'s escalation rule: raise it as a possible architecture problem rather than attempting a 4th patch.

- [ ] **Step 7: Commit**

```bash
git add services/search_service.py tests/test_search.py
git commit -m "fix: eliminate duplicate results in song search"
```

### Task 3c: Review & integrate Issue #3

**Files:**
- Modify: `submission.md`

- [ ] **Step 1: Comment on the issue**

```bash
gh issue comment 3 --repo Y4dd/ai201-project5-mixtape-starter --body "Root cause confirmed: <confirmed root cause from Task 3a/3b>. Fixed in services/search_service.py::search_songs(). Regression test: tests/test_search.py (new test added — the pre-existing tag-count test didn't actually reproduce this)."
```

- [ ] **Step 2: Request code review**

```bash
BASE_SHA=$(git merge-base HEAD bugfix/mixtape)
HEAD_SHA=$(git rev-parse HEAD)
```
Dispatch the `superpowers:code-reviewer` subagent with `WHAT_WAS_IMPLEMENTED` = "Fix for Mixtape issue #3 (duplicate search results)", `PLAN_OR_REQUIREMENTS` = this task, `BASE_SHA`, `HEAD_SHA`. Fix Critical/Important feedback as follow-up commits before continuing.

- [ ] **Step 3: Write the RCA entry**

In `submission.md`, add a `### Issue #3 — The same song keeps showing up twice in search` subsection under `## Root Cause Analysis`, covering all 5 required fields as in Task 1c Step 3. Explicitly note the disproven tag-count false lead as part of "how you found the root cause."

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin issue-3-search-duplicate-results
gh pr create --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape \
  --title "fix: eliminate duplicate results in song search" \
  --body "Closes #3

<paste the RCA entry from Step 3>"
```

- [ ] **Step 5: Confirm and squash-merge**

```bash
gh pr merge --repo Y4dd/ai201-project5-mixtape-starter --squash
```
(after user confirmation)

- [ ] **Step 6: Explicitly close the issue**

```bash
git fetch origin bugfix/mixtape
SHA=$(git rev-parse origin/bugfix/mixtape)
gh issue close 3 --repo Y4dd/ai201-project5-mixtape-starter --comment "Fixed in $SHA on bugfix/mixtape."
```

- [ ] **Step 7: Clean up**

```bash
git checkout bugfix/mixtape
git pull
git branch -d issue-3-search-duplicate-results
```

---

## Issue #4 — No notification when a friend rates my song

### Task 4a: Investigate Issue #4

**Files:** None — read-only investigation.

- [ ] **Step 1: Fetch the issue and create the linked branch**

```bash
gh issue view 4 --repo Y4dd/ai201-project5-mixtape-starter --json title,body,url -q '.title, .url, .body'
```
Expected output (verified):
```
Issue #4: No notification when a friend rates my song (playlist-add notifications work)
https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/4
**Reported by:** aaliya

Notifications work when someone adds a song I shared to a playlist — I get "kenji added your song…" right away. But when kenji **rated** one of my songs (he showed me, 5 stars), I never got a notification. No delay, just nothing, and there's nothing in my notification list (`GET /users/<my_id>/notifications`) either. Ratings notifications seem to just not happen, for anyone I've asked.

**Steps I took:**
1. Had a friend add my shared song to a playlist → notification arrived. ✅
2. Had the same friend rate a different song I shared (`POST /songs/<song_id>/rate`) → checked my notifications.

**Expected:** a notification for the rating, same as for the playlist add.
**Actual:** rating is saved (it shows on the song), but no notification is ever created.
```
Then:
```bash
gh issue develop 4 --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape --name issue-4-notification-missing-rating --checkout
```

- [ ] **Step 2: Dispatch the investigation subagent**

Use the Agent tool (`subagent_type: "Explore"`, `run_in_background: false`) with exactly this prompt:

```
Investigate GitHub issue #4 on the Mixtape app (Flask + SQLAlchemy). Do NOT write, edit, or suggest fix code — your only job is to reproduce, trace, and propose ONE hypothesis with evidence, then stop.

Issue report (verbatim from GitHub):
"""
Notifications work when someone adds a shared song to a playlist ("kenji added your song..." arrives right away). But when a friend rated a song (5 stars), no notification ever arrived — nothing in the notification list either. The rating itself is saved correctly (shows on the song), but no notification is created for it.

Steps taken: (1) A friend added a shared song to a playlist -> notification arrived (working). (2) The same friend rated a different shared song -> checked notifications, nothing there.

Expected: a notification for the rating, same as for the playlist add.
Actual: rating is saved, but no notification is ever created.
"""

Known context (already verified, don't re-derive):
- The relevant code is services/notification_service.py, which contains BOTH the working case (add_to_playlist()) and the broken case (rate_song()) in the same file.
- routes/songs.py's /rate route calls rate_song(); routes/playlists.py's add-song route calls add_to_playlist().
- This codebase's notification pattern is opt-in per call site, not event-driven: there's no central hook that fires on every write. Each service function that should notify someone has to call create_notification(...) itself, explicitly, at the point of the action.
- project.md's own hint for this issue: "the root cause is architectural, not a typo. Look at the pattern used for the working notification and compare it line-by-line to the missing one."

Your task:
1. Read add_to_playlist() and rate_song() in services/notification_service.py side by side.
2. Compare them line by line: what does add_to_playlist() do after its main side effect that rate_song() does not do after its main side effect?
3. Confirm by checking: does rate_song() call create_notification() anywhere? Does anything else in the codebase call create_notification() on a rating event?
4. Form exactly ONE hypothesis: "I think X is the root cause because Y" — name the exact missing call/step.
5. Report: your hypothesis, the file/line(s), the evidence (the line-by-line comparison), and any open uncertainty (e.g. who should the notification recipient be for a rating — the song's original sharer, by analogy with add_to_playlist's song.shared_by?).

Do not modify any files. Do not propose fix code. Stop after reporting the hypothesis.
```

- [ ] **Step 3: Relay the hypothesis**

Report the subagent's hypothesis, file/line, and evidence back to the user in full. Handoff to Task 4b — do not proceed further here.

### Task 4b: Confirm & fix Issue #4

**Files:**
- Modify: `services/notification_service.py`
- Create: `tests/test_notifications.py`

- [ ] **Step 1: Human confirmation gate**

Ask the user exactly this, as a 3-way choice:
```
Confirmed — implement the fix
Not the root cause — re-investigate
Let me look first, pause here
```
If not confirmed, stop and return to Task 4a with whatever steer is given.

- [ ] **Step 2: Write the failing regression test**

No test file exists yet for this service. Create `tests/test_notifications.py` starting from this exact boilerplate (copied from the existing fixture pattern):

```python
"""
tests/test_notifications.py — Mixtape

Tests for notification creation logic.
"""

import pytest
from app import create_app, db
from models import User, Song
from services.notification_service import rate_song, get_notifications


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def shared_song(app):
    """A song shared by one user, to be rated by another."""
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([sharer, rater])
        db.session.flush()

        song = Song(title="Test Song", artist="Test Artist", shared_by=sharer.id)
        db.session.add(song)
        db.session.commit()
        yield {"sharer": sharer, "rater": rater, "song": song}


def test_rating_a_song_notifies_the_sharer(app, shared_song):
    """Rating someone else's shared song should notify the original sharer."""
    with app.app_context():
        sharer = shared_song["sharer"]
        rater = shared_song["rater"]
        song = shared_song["song"]

        rate_song(rater.id, song.id, 5)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 1
        assert notifications[0]["type"] == "song_rated"


def test_rating_your_own_song_does_not_notify_yourself(app, shared_song):
    """Rating your own shared song should not create a self-notification."""
    with app.app_context():
        sharer = shared_song["sharer"]
        song = shared_song["song"]

        rate_song(sharer.id, song.id, 4)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 0
```

Run:
```bash
pytest tests/test_notifications.py -v
```
Expected: `test_rating_a_song_notifies_the_sharer` FAILS (0 notifications instead of 1), matching the confirmed hypothesis.

- [ ] **Step 3: Implement the minimal fix**

In `services/notification_service.py`, modify `rate_song()` to call `create_notification(...)` after saving the rating, following the exact pattern in `add_to_playlist()`: only notify when `song.shared_by != user_id` (don't self-notify), with `notification_type="song_rated"` and a body message analogous to the playlist-add one (e.g. referencing the rater's username, the score, and the song title).

- [ ] **Step 4: Verify green**

```bash
pytest tests/test_notifications.py -v
```
Expected: both tests PASS.

- [ ] **Step 5: Run the full suite**

```bash
pytest tests/ -v
```
Expected: no new failures versus the baseline in `CLAUDE.md`.

- [ ] **Step 6: Verify before claiming this fixed**

Apply `verification-before-completion`: confirm via actual command output (not memory) that the regression test passes, the full suite passes, and — where practical — the exact repro steps from the issue report no longer produce the reported symptom. If 3+ distinct fix attempts have been tried in this task without success, stop and apply `systematic-debugging`'s escalation rule: raise it as a possible architecture problem rather than attempting a 4th patch.

- [ ] **Step 7: Commit**

```bash
git add services/notification_service.py tests/test_notifications.py
git commit -m "fix: send a notification when a song is rated"
```

### Task 4c: Review & integrate Issue #4

**Files:**
- Modify: `submission.md`

- [ ] **Step 1: Comment on the issue**

```bash
gh issue comment 4 --repo Y4dd/ai201-project5-mixtape-starter --body "Root cause confirmed: <confirmed root cause from Task 4a/4b>. Fixed in services/notification_service.py::rate_song(). Regression test: tests/test_notifications.py."
```

- [ ] **Step 2: Request code review**

```bash
BASE_SHA=$(git merge-base HEAD bugfix/mixtape)
HEAD_SHA=$(git rev-parse HEAD)
```
Dispatch the `superpowers:code-reviewer` subagent with `WHAT_WAS_IMPLEMENTED` = "Fix for Mixtape issue #4 (missing rating notification)", `PLAN_OR_REQUIREMENTS` = this task, `BASE_SHA`, `HEAD_SHA`. Fix Critical/Important feedback as follow-up commits before continuing.

- [ ] **Step 3: Write the RCA entry**

In `submission.md`, add a `### Issue #4 — No notification when a friend rates my song` subsection under `## Root Cause Analysis`, covering all 5 required fields as in Task 1c Step 3.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin issue-4-notification-missing-rating
gh pr create --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape \
  --title "fix: send a notification when a song is rated" \
  --body "Closes #4

<paste the RCA entry from Step 3>"
```

- [ ] **Step 5: Confirm and squash-merge**

```bash
gh pr merge --repo Y4dd/ai201-project5-mixtape-starter --squash
```
(after user confirmation)

- [ ] **Step 6: Explicitly close the issue**

```bash
git fetch origin bugfix/mixtape
SHA=$(git rev-parse origin/bugfix/mixtape)
gh issue close 4 --repo Y4dd/ai201-project5-mixtape-starter --comment "Fixed in $SHA on bugfix/mixtape."
```

- [ ] **Step 7: Clean up**

```bash
git checkout bugfix/mixtape
git pull
git branch -d issue-4-notification-missing-rating
```

---

## Issue #5 — The last song added to a playlist never shows up

### Task 5a: Investigate Issue #5

**Files:** None — read-only investigation.

- [ ] **Step 1: Fetch the issue and create the linked branch**

```bash
gh issue view 5 --repo Y4dd/ai201-project5-mixtape-starter --json title,body,url -q '.title, .url, .body'
```
Expected output (verified):
```
Issue #5: The last song added to a playlist never shows up
https://github.com/Y4dd/ai201-project5-mixtape-starter/issues/5
**Reported by:** darius

Our collaborative playlist "Friday Energy" says it has 7 songs, but when I open it only **6** show. The missing one is always whatever was added **most recently**. Weirder: when simone added a new song, the previously-missing song suddenly appeared — and *her* new song became the missing one. So the playlist is always hiding exactly one song: the last one added.

**Steps I took:**
1. Opened the playlist (`GET /playlists/<playlist_id>/songs`) and counted the songs.
2. Added one more song (`POST /playlists/<playlist_id>/songs`) and re-fetched.

**Expected:** every song in the playlist is returned, including the newest.
**Actual:** the most recently added song is always missing; adding another song "frees" the previous one and hides the new one instead.
```
Then:
```bash
gh issue develop 5 --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape --name issue-5-playlist-missing-last-song --checkout
```

- [ ] **Step 2: Dispatch the investigation subagent**

Use the Agent tool (`subagent_type: "Explore"`, `run_in_background: false`) with exactly this prompt:

```
Investigate GitHub issue #5 on the Mixtape app (Flask + SQLAlchemy). Do NOT write, edit, or suggest fix code — your only job is to reproduce, trace, and propose ONE hypothesis with evidence, then stop.

Issue report (verbatim from GitHub):
"""
A collaborative playlist says it has 7 songs, but only 6 show when opened. The missing one is always whatever was added most recently. When another song was added, the previously-missing song appeared and the new song became the missing one instead — the playlist always hides exactly one song: the last one added.

Steps taken: (1) Opened the playlist (GET /playlists/<playlist_id>/songs) and counted songs. (2) Added one more song (POST /playlists/<playlist_id>/songs) and re-fetched.

Expected: every song in the playlist is returned, including the newest.
Actual: the most recently added song is always missing; adding another song "frees" the previous one and hides the new one instead.
"""

Known context (already verified, don't re-derive):
- The relevant code is services/playlist_service.py, function get_playlist_songs().
- Playlist membership/order is tracked via the playlist_entries association table (columns: playlist_id, song_id, position, added_by, added_at) — position is an explicit ordering column, not insertion order.
- tests/test_playlists.py already has 2 failing tests (test_playlist_returns_all_songs, test_playlist_returns_songs_in_order) that both encode this bug — run `pytest tests/test_playlists.py -v` to see them fail.

Your task:
1. Read get_playlist_songs() in services/playlist_service.py in full, including the exact return statement.
2. Run `pytest tests/test_playlists.py -v` and report the exact failures.
3. Trace what the query returns versus what actually gets returned to the caller — is there a step between the query result and the return that could drop an item?
4. Form exactly ONE hypothesis: "I think X is the root cause because Y" — name the exact line/expression responsible.
5. Report: your hypothesis, the file/line, the evidence (test output and/or a manual trace), and any open uncertainty.

Do not modify any files. Do not propose fix code. Stop after reporting the hypothesis.
```

- [ ] **Step 3: Relay the hypothesis**

Report the subagent's hypothesis, file/line, and evidence back to the user in full. Handoff to Task 5b — do not proceed further here.

### Task 5b: Confirm & fix Issue #5

**Files:**
- Modify: `services/playlist_service.py`
- Test: `tests/test_playlists.py`

- [ ] **Step 1: Human confirmation gate**

Ask the user exactly this, as a 3-way choice:
```
Confirmed — implement the fix
Not the root cause — re-investigate
Let me look first, pause here
```
If not confirmed, stop and return to Task 5a with whatever steer is given.

- [ ] **Step 2: Verify the existing regression tests fail correctly**

```bash
pytest tests/test_playlists.py -v
```
Expected: `test_playlist_returns_all_songs` and `test_playlist_returns_songs_in_order` FAIL, for the reason matching the confirmed hypothesis.

- [ ] **Step 3: Implement the minimal fix**

In `services/playlist_service.py`, modify `get_playlist_songs()` per the confirmed root cause from Task 5a — remove whatever slices or drops the last element of the ordered result set, while keeping the existing ascending-by-position ordering intact.

- [ ] **Step 4: Verify green**

```bash
pytest tests/test_playlists.py -v
```
Expected: all tests in this file PASS, including `test_empty_playlist_returns_empty_list` (verify an empty playlist still returns `[]` rather than erroring — this is the boundary case on the other side of the fix).

- [ ] **Step 5: Run the full suite**

```bash
pytest tests/ -v
```
Expected: no new failures versus the baseline in `CLAUDE.md`.

- [ ] **Step 6: Verify before claiming this fixed**

Apply `verification-before-completion`: confirm via actual command output (not memory) that the regression test passes, the full suite passes, and — where practical — the exact repro steps from the issue report no longer produce the reported symptom. If 3+ distinct fix attempts have been tried in this task without success, stop and apply `systematic-debugging`'s escalation rule: raise it as a possible architecture problem rather than attempting a 4th patch.

- [ ] **Step 7: Commit**

```bash
git add services/playlist_service.py
git commit -m "fix: return the most recently added song in playlist listings"
```

### Task 5c: Review & integrate Issue #5

**Files:**
- Modify: `submission.md`

- [ ] **Step 1: Comment on the issue**

```bash
gh issue comment 5 --repo Y4dd/ai201-project5-mixtape-starter --body "Root cause confirmed: <confirmed root cause from Task 5a/5b>. Fixed in services/playlist_service.py::get_playlist_songs(). Regression tests: tests/test_playlists.py::test_playlist_returns_all_songs and test_playlist_returns_songs_in_order."
```

- [ ] **Step 2: Request code review**

```bash
BASE_SHA=$(git merge-base HEAD bugfix/mixtape)
HEAD_SHA=$(git rev-parse HEAD)
```
Dispatch the `superpowers:code-reviewer` subagent with `WHAT_WAS_IMPLEMENTED` = "Fix for Mixtape issue #5 (last playlist song missing)", `PLAN_OR_REQUIREMENTS` = this task, `BASE_SHA`, `HEAD_SHA`. Fix Critical/Important feedback as follow-up commits before continuing.

- [ ] **Step 3: Write the RCA entry**

In `submission.md`, add a `### Issue #5 — The last song in a playlist never shows up` subsection under `## Root Cause Analysis`, covering all 5 required fields as in Task 1c Step 3.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin issue-5-playlist-missing-last-song
gh pr create --repo Y4dd/ai201-project5-mixtape-starter --base bugfix/mixtape \
  --title "fix: return the most recently added song in playlist listings" \
  --body "Closes #5

<paste the RCA entry from Step 3>"
```

- [ ] **Step 5: Confirm and squash-merge**

```bash
gh pr merge --repo Y4dd/ai201-project5-mixtape-starter --squash
```
(after user confirmation)

- [ ] **Step 6: Explicitly close the issue**

```bash
git fetch origin bugfix/mixtape
SHA=$(git rev-parse origin/bugfix/mixtape)
gh issue close 5 --repo Y4dd/ai201-project5-mixtape-starter --comment "Fixed in $SHA on bugfix/mixtape."
```

- [ ] **Step 7: Clean up**

```bash
git checkout bugfix/mixtape
git pull
git branch -d issue-5-playlist-missing-last-song
```

---

## Final check

- [ ] Run `git log --oneline bugfix/mixtape` and confirm 5 `fix:` commits (plus the `docs:` commit from Task 0) appear, one per issue, matching `project.md`'s submission checkpoint.
- [ ] Run `gh issue list --repo Y4dd/ai201-project5-mixtape-starter` and confirm all issues worked are closed.
- [ ] Confirm `submission.md` has one complete 5-field RCA entry per issue worked.
