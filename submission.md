# Mixtape Bug Hunt — Submission

## Codebase Map

### Main files

- **`app.py`** — Flask application factory (`create_app`). Configures the SQLAlchemy database URI (`sqlite:///mixtape.db` by default), holds the single shared `db = SQLAlchemy()` instance that every other module imports, registers the four route blueprints under their URL prefixes (`/songs`, `/playlists`, `/users`, `/feed`), and calls `db.create_all()`.
- **`models.py`** — All SQLAlchemy models: `User`, `Tag`, `Song`, `ListeningEvent`, `Rating`, `Playlist`, `Notification`, plus three raw association tables (`friendships`, `song_tags`, `playlist_entries`). Every model has a `to_dict()` method, and that dict is exactly what the API returns — there's no separate serialization layer. IDs are app-generated UUID strings (`generate_uuid()`), not database auto-increment integers.
- **`routes/songs.py`, `routes/playlists.py`, `routes/users.py`, `routes/feed.py`** — One `Blueprint` per resource. Each route function parses the request (query args or JSON body), calls exactly one service function, and returns JSON, converting a raised `ValueError` into a 400/404 response. No business logic or database queries happen at this layer.
- **`services/streak_service.py`, `services/feed_service.py`, `services/search_service.py`, `services/notification_service.py`, `services/playlist_service.py`** — All business logic and database queries live here, one file per feature area.
- **`seed_data.py`** — Drops and recreates all tables, then populates the database with 5 users and their friendships, 25 songs (a mix of 0-, 1-, and 3+-tag songs), 3 playlists, about two weeks of listening events, per-user starting streak values, and a couple of existing notifications — enough state to exercise every route without creating data by hand first.
- **`tests/`** — Pytest suite: `test_streaks.py`, `test_search.py`, `test_playlists.py`. There is no test file yet for the feed or notification services.

### Data model, worth knowing

- `User` ←`friendships`→ `User`: a self-referential many-to-many via a raw `db.Table` (not a model class), with a symmetric `primaryjoin`/`secondaryjoin` pair. Exposed on `User` as `.friends` (a dynamic relationship).
- `Song.shared_by` → `User.id`: every song has exactly one original sharer (`shared_by_user` backref).
- `Playlist` ←`playlist_entries`→ `Song`: many-to-many, but `playlist_entries` carries extra columns beyond the two foreign keys — `position` (explicit ordering, not insertion order), `added_by`, and `added_at`. A playlist is an ordered, attributed sequence, not just a set of songs.
- `Rating` is its own table (`user_id` + `song_id`, unique together) rather than a column on `Song` — one rating per user per song; re-rating updates the existing row instead of inserting a new one.
- `Notification` is generic: a `notification_type` string plus a free-text `body`. There's no polymorphic link back to "what caused this" — whatever creates the notification is responsible for writing a human-readable `body` itself.

### Data flow: adding a song to a playlist (with notification)

This is the one confirmed end-to-end flow in the app (a friend adding your shared song to a playlist reliably produces a notification — see Issue #4's report), so it's a good one to trace in full:

1. `POST /playlists/<playlist_id>/songs` hits `add_song` in `routes/playlists.py`, which reads `song_id` and `added_by` from the JSON body and calls straight through to `add_to_playlist(playlist_id, song_id, added_by)`.
2. `add_to_playlist` — **defined in `services/notification_service.py`, not `playlist_service.py`** — looks up the `Song`, the adding `User`, and the `Playlist`, raising `ValueError` if any is missing (the route turns that into a 400).
3. If the song isn't already in `playlist.songs`, it appends it and commits. This is the actual playlist mutation.
4. If `song.shared_by != added_by_user_id` (you didn't add your own song), it calls `create_notification(user_id=song.shared_by, notification_type="song_added_to_playlist", body=f"{adder.username} added your song '{song.title}' to the playlist '{playlist.name}'.")`.
5. `create_notification` builds a `Notification` row and commits it — that's the whole function, no other side effects.
6. The sharer later reads it via `GET /users/<user_id>/notifications` → `routes/users.py::notifications` → `notification_service.get_notifications`, which queries `Notification` by `user_id` (optionally `read=False`), orders newest-first, and returns each `to_dict()`.

### Patterns noticed

- **Routes are thin.** Parse input → call one service function → format the response. All logic and all queries live in `services/`.
- **`to_dict()` is the API contract.** Every model serializes itself; routes never reshape the data further.
- **File boundaries don't perfectly match blueprint boundaries.** `add_to_playlist` — a function that mutates a playlist — lives in `notification_service.py`, not `playlist_service.py`, because that action is coupled to firing a notification. Worth remembering when tracing playlist behavior: not everything that touches a playlist is in the playlist service.
- **Notifications are opt-in per action, not automatic.** There's no central hook or event system firing on every relevant DB write — each service function that should notify someone has to call `create_notification(...)` itself, explicitly, at the point of the action (as `add_to_playlist` does, right after appending the song).
- **Timestamps are consistently timezone-aware UTC** (`datetime.now(timezone.utc)`), and code that compares a stored datetime against "now" re-attaches `tzinfo=timezone.utc` first if it's missing (see `streak_service.update_listening_streak`) — so date/time comparisons are meant to be apples-to-apples throughout the services layer.
- **Many-to-many relationships are raw association tables**, not their own model classes, except where they need extra columns (`playlist_entries`), in which case those columns just get bolted onto the `db.Table` directly rather than promoting it to a full model.

## Root Cause Analysis

### Issue #1 — My listening streak keeps resetting

**1. Issue number and title:** Issue #1 — My listening streak keeps resetting (reported by kenji).

**2. How I reproduced it:** Ran the existing (failing) test `tests/test_streaks.py::test_streak_increments_on_sunday`, which encodes the exact reported scenario: call `update_listening_streak(user, saturday)` with a datetime whose `weekday() == 5`, confirm the streak is `1`, then call `update_listening_streak(user, sunday)` — exactly one calendar day later, `weekday() == 6` — and assert the streak becomes `2`. Before the fix this failed with `assert 1 == 2`: the streak reset instead of incrementing, reproducing the reporter's 12 → 1 drop on a Sunday.

**3. How I found the root cause:** Followed the call chain from `routes/users.py`'s `/streak` route → `get_streak()`, and from `routes/songs.py`'s `/listen` route → `record_listening_event()` → `update_listening_streak()` in `services/streak_service.py`. Read `update_listening_streak()` in full, then manually traced variable values for a Saturday (2024-06-15) → Sunday (2024-06-16) listen pair: `days_since_last` correctly computed as `1`, but the `elif` at line 73 also required `today.weekday() != 6`, which evaluates to `False` on a Sunday (confirmed directly: `date(2024, 6, 16).weekday() == 6`). That was the moment of confidence — the day-count arithmetic was correct, but an unrelated weekday guard was silently vetoing the correct branch specifically on Sundays.

**4. The root cause:** In `update_listening_streak()` (`services/streak_service.py:73`), the increment condition was `elif days_since_last == 1 and today.weekday() != 6:`. The `and today.weekday() != 6` clause has no basis in the function's own documented rules (its docstring lists only three cases: same day = no change, one day later = increment, more than one day = reset — no day-of-week exception). Since Python's `weekday()` returns `6` for Sunday, this clause evaluated to `False` every time a consecutive-day listen happened to land on a Sunday, even though exactly one calendar day had passed. Execution then fell through to the unconditional `else: user.listening_streak = 1`, resetting the streak to 1 regardless of its prior length — which is exactly why a 12-day streak collapsed to 1. The following Monday's listen then correctly incremented from that freshly-reset 1 to 2, matching the reporter's account.

**5. My fix and side-effect check:** Removed the erroneous clause, changing line 73 to `elif days_since_last == 1:`, so the increment condition depends only on elapsed days — correct for every day of the week, not just a Sunday carve-out. Verified `tests/test_streaks.py::test_streak_increments_on_sunday` now passes along with all 5 tests in that file. Ran the full suite (`pytest tests/`) to check side effects: 11/13 pass, with the remaining 2 failures being the pre-existing, already-documented Issue #5 playlist bug (`test_playlist_returns_all_songs`, `test_playlist_returns_songs_in_order`) — unrelated to and unaffected by this change. Independently confirmed the fix is weekday-agnostic (not a Sunday-only patch) by grepping the codebase for any other `weekday()`/`isoweekday()` usage (none found) and by reverting/reapplying the change to confirm the regression test genuinely fails before the fix and passes after.

### Issue #2 — Friends Listening Now shows people from yesterday

**1. Issue number and title:** Issue #2 — Friends Listening Now shows people from yesterday (reported by nova).

**2. How I reproduced it:** No test file existed for `services/feed_service.py`, so reproduction started from the report itself: a friend's listening event at 11pm one day, checked the next morning at 9am, should not appear as "listening now." I traced `get_friends_listening_now()` manually with these exact timestamps before writing any test, confirmed the bug by hand, then encoded it as `tests/test_feed.py::test_listen_from_yesterday_evening_not_shown_this_morning` — which failed before the fix (the friend's stale event was still included).

**3. How I found the root cause:** Followed the call chain from `routes/feed.py`'s `/listening-now` route straight into `get_friends_listening_now()` in `services/feed_service.py` (the route does no additional filtering). Read the function in full and found `cutoff = datetime.now(timezone.utc) - RECENT_THRESHOLD` (line 32) where `RECENT_THRESHOLD = timedelta(hours=24)` (line 13). Manually traced the reported scenario: listen at 11pm Day 1, checked at 9am Day 2 → `cutoff = 9am Day2 - 24h = 9am Day1`. Since `11pm Day1 >= 9am Day1`, the event passes the filter — and keeps passing until `now` reaches 11pm Day 2, a full 24 hours after the listen. That confirmed the mismatch: the code implements "recent" as "within the last 24 wall-clock hours," not "since the start of today," which is what "listening now" / "played today" actually means.

**4. The root cause:** `get_friends_listening_now()` (`services/feed_service.py:32`, using the constant at line 13) filtered `ListeningEvent.listened_at >= cutoff` where `cutoff` was a rolling 24-hour lookback anchored to the exact request time, rather than a calendar-day boundary anchored to midnight. Because the window slides with wall-clock time instead of resetting at midnight, any event stays visible for a full 24 hours after it occurred regardless of when the calendar day starts — so an 11pm listen is still "listening now" at 9am the next morning, and remains so until 11pm that day, exactly matching the reporter's observation that stale entries "hang around until the same time the next day."

**5. My fix and side-effect check:** Changed the cutoff computation to `datetime(now.year, now.month, now.day, tzinfo=timezone.utc)` — midnight UTC of the current day — replacing the rolling-24h `RECENT_THRESHOLD` constant (removed, along with the now-unused `timedelta` import). Added an optional `now: datetime | None = None` parameter (defaulting to `datetime.now(timezone.utc)`) so the function is testable without mocking; the existing call site in `routes/feed.py` needed no change. Added `tests/test_feed.py` with two tests: the reported repro (11pm-previous-day listen excluded at 9am) and its inverse (7am-same-day listen still included at 9am) — both pass. Ran the full suite (`pytest tests/`): 2 failed / 13 passed, with the 2 failures being the pre-existing, already-documented Issue #5 playlist bug, unrelated to and unaffected by this change. A `superpowers:code-reviewer` pass confirmed the fix is correct, minimal, and consistent with the codebase's UTC-only datetime convention.
