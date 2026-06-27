"""
YouTube Music source for music.plugin
Uses self-hosted yt-dlp server (Wispbyte)
"""

import requests

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "3.0.0"

# Замени на свой адрес после деплоя на Wispbyte
SERVER_URL = "http://etgmusic.wisp.uno"

_external_log = [None]
_working_instance = [None]  # для совместимости


def set_logger(fn):
    _external_log[0] = fn


def _log(msg):
    fn = _external_log[0]
    if fn:
        fn(str(msg))


def configure(api_key: str):
    pass


def is_configured() -> bool:
    return "YOUR_WISPBYTE_IP" not in SERVER_URL


def search(query: str, limit: int = 15) -> list:
    _log(f"[music] search: {query!r} via {SERVER_URL}")
    try:
        resp = requests.get(
            f"{SERVER_URL}/search",
            params={"q": query, "limit": limit},
            timeout=15
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        _log(f"[music] search: {len(items)} results")
        return items
    except Exception as e:
        _log(f"[music] search error: {e}")
        raise RuntimeError(f"Ошибка поиска: {e}")


def get_stream_url(video_id: str, instance: str = None) -> dict:
    _log(f"[music] get_stream_url: {video_id}")
    try:
        resp = requests.get(
            f"{SERVER_URL}/stream",
            params={"id": video_id},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        _log(f"[music] stream ok: mime={data.get('mime')} url={data.get('url','')[:60]}")
        return {"url": data.get("url", ""), "mime": data.get("mime", "audio/mp4")}
    except Exception as e:
        _log(f"[music] stream error: {e}")
        return {}


def get_suggestions(query: str) -> list:
    return []


def search_artists(query: str, limit: int = 10) -> list:
    """Поиск исполнителей для онбординга."""
    _log(f"[music] search_artists: {query!r}")
    try:
        resp = requests.get(
            f"{SERVER_URL}/artist/search",
            params={"q": query, "limit": limit},
            timeout=15
        )
        resp.raise_for_status()
        artists = resp.json().get("artists", [])
        _log(f"[music] artists found: {len(artists)}")
        return artists
    except Exception as e:
        _log(f"[music] search_artists error: {e}")
        return []


def get_artist_tracks(artist_name: str, limit: int = 10) -> list:
    """Получить треки исполнителя."""
    _log(f"[music] get_artist_tracks: {artist_name!r}")
    try:
        resp = requests.get(
            f"{SERVER_URL}/artist/tracks",
            params={"name": artist_name, "limit": limit},
            timeout=15
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        _log(f"[music] artist tracks: {len(items)}")
        return items
    except Exception as e:
        _log(f"[music] get_artist_tracks error: {e}")
        return []
