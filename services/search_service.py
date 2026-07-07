"""
services/search_service.py — Mixtape

Handles song search logic.
"""

from app import db
from models import Song


def search_songs(query: str) -> list[dict]:
    """
    Search for songs by title or artist name.

    Returns all songs where the title or artist contains the query string
    (case-insensitive), deduplicated by (title, artist) so a song shared
    as multiple distinct rows appears once, along with their associated
    tags.

    Args:
        query: The search string to match against title and artist fields.

    Returns:
        A list of song dicts. Each dict includes all song fields plus a
        'tags' list of tag name strings.
    """
    results = (
        db.session.query(Song)
        .filter(
            db.or_(
                Song.title.ilike(f"%{query}%"),
                Song.artist.ilike(f"%{query}%"),
            )
        )
        .all()
    )

    # Multiple Song rows can share the same title/artist (e.g. the same
    # song shared independently by different users). Collapse those to one
    # entry, keeping the most complete record rather than whichever row the
    # DB happens to return first.
    def completeness(song):
        return (len(song.tags), 1 if song.album else 0)

    best_by_key = {}
    order = []
    for song in results:
        key = (song.title.lower(), song.artist.lower())
        if key not in best_by_key:
            order.append(key)
            best_by_key[key] = song
        elif completeness(song) > completeness(best_by_key[key]):
            best_by_key[key] = song

    return [best_by_key[key].to_dict() for key in order]


def get_song(song_id: str) -> dict:
    """
    Get a single song by ID.

    Args:
        song_id: The UUID of the song.

    Returns:
        A song dict, or raises ValueError if not found.
    """
    song = db.session.get(Song, song_id)
    if not song:
        raise ValueError(f"Song {song_id} not found")
    return song.to_dict()
