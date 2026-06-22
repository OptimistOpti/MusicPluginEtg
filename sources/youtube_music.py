"""
YouTube Music source for music.plugin
Requires: Google API key with YouTube Data API v3 enabled
https://console.cloud.google.com/
"""

import requests
import urllib.parse

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.0.0"

# Конфиг ключа — плагин записывает сюда перед загрузкой модуля
_api_key = None


def configure(api_key: str):
    """Вызывается плагином после загрузки модуля."""
    global _api_key
    _api_key = api_key


def is_configured() -> bool:
    return bool(_api_key)


# ── Поиск ─────────────────────────────────────────────────────────────────────

def search(query: str, limit: int = 20) -> list[dict]:
    """
    Ищет треки по запросу.
    Возвращает список dict:
      id, title, artist, duration_sec, thumbnail_url, stream_url
    """
    if not _api_key:
        raise RuntimeError("API ключ не настроен")

    # Шаг 1: поиск видео (videoCategoryId=10 — Music)
    params = {
        "part": "id,snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": limit,
        "key": _api_key,
    }
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        msg = data["error"].get("message", "Неизвестная ошибка")
        raise RuntimeError(f"YouTube API: {msg}")

    items = data.get("items", [])
    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items]

    # Шаг 2: получаем длительность через videos.list
    durations = _fetch_durations(video_ids)

    results = []
    for item in items:
        vid_id = item["id"]["videoId"]
        snippet = item["snippet"]

        title, artist = _parse_title(snippet["title"], snippet["channelTitle"])

        thumb = (
            snippet.get("thumbnails", {})
            .get("medium", {})
            .get("url", "")
        )

        results.append({
            "id": vid_id,
            "title": title,
            "artist": artist,
            "duration_sec": durations.get(vid_id, 0),
            "thumbnail_url": thumb,
            # Прямой аудио ссылки нет — открываем в браузере / через yt-dlp
            "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
            "stream_url": None,
        })

    return results


def _fetch_durations(video_ids: list[str]) -> dict[str, int]:
    """Запрашивает длительность треков (один запрос на batch)."""
    params = {
        "part": "contentDetails",
        "id": ",".join(video_ids),
        "key": _api_key,
    }
    url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for item in data.get("items", []):
            vid_id = item["id"]
            iso = item["contentDetails"]["duration"]  # PT3M45S
            result[vid_id] = _parse_iso_duration(iso)
        return result
    except Exception:
        return {}


def _parse_iso_duration(iso: str) -> int:
    """Конвертирует ISO 8601 duration (PT3M45S) в секунды."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def _parse_title(title: str, channel: str) -> tuple[str, str]:
    """
    Пытается разбить 'Artist - Song Title' на (title, artist).
    Если разделитель не найден — возвращает (title, channel).
    """
    for sep in (" - ", " – ", " — "):
        if sep in title:
            parts = title.split(sep, 1)
            return parts[1].strip(), parts[0].strip()
    # Убираем мусор в конце: (Official Video), [Lyrics] и т.д.
    import re
    clean = re.sub(r"[\(\[].{0,40}[\)\]]", "", title).strip()
    return clean or title, channel


def format_duration(seconds: int) -> str:
    """Форматирует секунды в MM:SS или H:MM:SS."""
    if seconds <= 0:
        return "--:--"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
