"""
YouTube Music source for music.plugin
Uses Piped API — no API key required
https://docs.piped.video/docs/api-documentation/
"""

import requests
import urllib.parse

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.2.0"

# Публичные инстансы Piped — пробуем по очереди
_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://piped-api.garudalinux.org",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.coldforge.xyz",
]


def configure(api_key: str):
    pass


def is_configured() -> bool:
    return True


def search(query: str, limit: int = 15) -> list:
    """Поиск треков. Возвращает список dict с метаданными."""
    encoded = urllib.parse.quote(query)
    last_err = None

    for instance in _INSTANCES:
        try:
            url = f"{instance}/search?q={encoded}&filter=music_songs"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            results = []
            for item in items[:limit]:
                video_url = item.get("url", "")
                # url приходит как /watch?v=VIDEO_ID
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
                    # stream_url получаем отдельно через get_stream_url()
                    "stream_url": None,
                    "_instance": instance,
                })
            return results

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Все инстансы Piped недоступны: {last_err}")


def get_stream_url(video_id: str, instance: str = None) -> str:
    """
    Получает прямую ссылку на аудио поток для воспроизведения.
    Возвращает URL лучшего аудио потока (наибольший битрейт).
    """
    instances_to_try = ([instance] if instance else []) + _INSTANCES

    for inst in instances_to_try:
        try:
            url = f"{inst}/streams/{video_id}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            audio_streams = data.get("audioStreams", [])
            if not audio_streams:
                continue

            # Берём поток с наибольшим битрейтом
            best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
            return best.get("url", "")

        except Exception:
            continue

    return ""


def get_suggestions(query: str) -> list:
    """Поисковые подсказки."""
    encoded = urllib.parse.quote(query)
    for instance in _INSTANCES:
        try:
            url = f"{instance}/suggestions?query={encoded}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json()  # список строк
        except Exception:
            continue
    return []
