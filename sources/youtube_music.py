"""
YouTube Music source for music.plugin
Uses Piped API — no API key required
https://docs.piped.video/docs/api-documentation/
"""

import requests
import urllib.parse

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.3.0"

# Инстансы отсортированы по приоритету: Европа первой (ближе к UA)
_INSTANCES = [
    "https://pipedapi.adminforge.de",       # 🇩🇪
    "https://pipedapi.owo.si",               # 🇩🇪
    "https://pipedapi.reallyaweso.me",       # 🇩🇪
    "https://api.piped.yt",                  # 🇩🇪
    "https://piped-api.privacy.com.de",      # 🇩🇪
    "https://pipedapi.ducks.party",          # 🇳🇱
    "https://pipedapi-libre.kavin.rocks",    # 🇳🇱
    "https://pipedapi.leptons.xyz",          # 🇦🇹
    "https://api.piped.private.coffee",      # 🇦🇹
    "https://piped-api.codespace.cz",        # 🇨🇿
    "https://pipedapi.nosebs.ru",            # 🇫🇮
    "https://pipedapi.orangenet.cc",         # 🇸🇮
    "https://pipedapi.kavin.rocks",          # 🇺🇸/🇳🇱 официальный
    "https://pipedapi.drgns.space",          # 🇺🇸
    "https://pipedapi.darkness.services",    # 🇺🇸
]


def configure(api_key: str):
    pass


def is_configured() -> bool:
    return True


def search(query: str, limit: int = 15) -> list:
    encoded = urllib.parse.quote(query)
    last_err = None

    for instance in _INSTANCES:
        try:
            url = f"{instance}/search?q={encoded}&filter=music_songs"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            results = []
            for item in items[:limit]:
                video_url = item.get("url", "")
                video_id = ""
                if "v=" in video_url:
                    video_id = video_url.split("v=")[-1].split("&")[0]
                elif item.get("id"):
                    video_id = item["id"]
                if not video_id:
                    continue

                results.append({
                    "id": video_id,
                    "title": item.get("title", "Неизвестный трек"),
                    "artist": item.get("uploaderName", "Неизвестный исполнитель"),
                    "duration_sec": item.get("duration", 0),
                    "thumbnail_url": item.get("thumbnail", ""),
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                    "stream_url": None,
                    "_instance": instance,
                })
            return results

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Все инстансы Piped недоступны: {last_err}")


def get_stream_url(video_id: str, instance: str = None) -> str:
    instances_to_try = ([instance] if instance else []) + _INSTANCES
    for inst in instances_to_try:
        try:
            resp = requests.get(f"{inst}/streams/{video_id}", timeout=8)
            resp.raise_for_status()
            audio_streams = resp.json().get("audioStreams", [])
            if not audio_streams:
                continue
            best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
            return best.get("url", "")
        except Exception:
            continue
    return ""


def get_suggestions(query: str) -> list:
    encoded = urllib.parse.quote(query)
    for instance in _INSTANCES:
        try:
            resp = requests.get(f"{instance}/suggestions?query={encoded}", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            continue
    return []
