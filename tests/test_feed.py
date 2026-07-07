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
        result = get_friends_listening_now(user.id, now=this_morning_9am)

        assert result == []


def test_listen_from_earlier_today_is_shown(app, two_friends):
    """A friend's listen from earlier today should still appear."""
    with app.app_context():
        user = two_friends["user"]
        friend = two_friends["friend"]
        song = two_friends["song"]

        this_morning_7am = datetime(2024, 6, 11, 7, 0, 0, tzinfo=timezone.utc)
        event = ListeningEvent(user_id=friend.id, song_id=song.id, listened_at=this_morning_7am)
        db.session.add(event)
        db.session.commit()

        this_morning_9am = datetime(2024, 6, 11, 9, 0, 0, tzinfo=timezone.utc)
        result = get_friends_listening_now(user.id, now=this_morning_9am)

        assert len(result) == 1
        assert result[0]["friend"]["id"] == friend.id
