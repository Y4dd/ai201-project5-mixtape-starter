"""
tests/test_notifications.py — Mixtape

Tests for notification logic in notification_service.py.
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
def seed(app):
    """Create a song sharer, a rater, and a shared song."""
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([sharer, rater])
        db.session.flush()

        song = Song(
            title="Crown Heights Anthem", artist="Borough Kings",
            genre="rap", shared_by=sharer.id
        )
        db.session.add(song)
        db.session.commit()

        yield {"sharer": sharer, "rater": rater, "song": song}


def test_rate_song_notifies_sharer(app, seed):
    """Rating a friend's shared song creates a notification for the sharer."""
    with app.app_context():
        sharer = seed["sharer"]
        rater = seed["rater"]
        song = seed["song"]

        rate_song(user_id=rater.id, song_id=song.id, score=5)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 1
        assert notifications[0]["type"] == "song_rated"
        assert rater.username in notifications[0]["body"]


def test_rate_song_does_not_notify_self_rating(app, seed):
    """Rating your own shared song should not create a notification."""
    with app.app_context():
        sharer = seed["sharer"]
        song = seed["song"]

        rate_song(user_id=sharer.id, song_id=song.id, score=4)

        assert get_notifications(sharer.id) == []


def test_rate_song_notifies_on_updated_rating(app, seed):
    """Updating an existing rating also notifies the sharer."""
    with app.app_context():
        sharer = seed["sharer"]
        rater = seed["rater"]
        song = seed["song"]

        rate_song(user_id=rater.id, song_id=song.id, score=3)
        rate_song(user_id=rater.id, song_id=song.id, score=5)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 2
