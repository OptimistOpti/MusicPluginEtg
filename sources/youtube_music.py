"""
YouTube Music source for music.plugin
Uses Piped API — no API key required
https://docs.piped.video/docs/api-documentation/
"""

import requests
import urllib.parse
import threading

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.4.0"

_INSTANCES = [
    "https://pipedapi.adminforge.de",
    "https://pipedapi.owo.si",
    "https://pipedapi.reallyaweso.me",
    "https://api.piped.yt",
    "https://piped-api.privacy.com.de",
    "https://pipedapi.ducks.party",
    "https://pipedapi-libre.kavin.rocks",
    "https://pipedapi.leptons.xyz",
    "https://api.piped.private.coffee",
    "https://piped-api.codespace.cz",
    "https://pipedapi.nosebs.ru",
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.drgns.space",
    "https://pipedapi.darkness.services",
]

# Кешируем рабочий инстанс между вызовами
_working_instance = [None]


def configure(api_key: str):
    pass


def is_configured() -> bool:
    return True


def _find_working_instance(path: str, timeout: float = 4.0) -> tuple:
    """
    Параллельно опрашивает все инстансы, возвращает (instance, response)
    первого ответившего. Возвращает (None, None) если все недоступны.
    """
    result = [None]  # [instance, response]
    found = threading.Event()

    def try_instance(inst):
        if found.is_set():
            return
        try:
            url = f"{inst}{path}"
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            if not found.is_set():
                result[0] = (inst, resp)
                found.set()
        except Exception:
            pass

    # Сначала пробуем кешированный
    cached = _working_instance[0]
    if cached:
        try:
            url = f"{cached}{path}"
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return cached, resp
        except Exception:
            _working_instance[0] = None

    threads = []
    for inst in _INSTANCES:
        t = threading.Thread(target=try_instance, args=(inst,), daemon=True)
        threads.append(t)
        t.start()

    found.wait(timeout=timeout + 1)

    if result[0]:
        instance, resp = result[0]
        _working_instance[0] = instance
        return instance, resp

    return None, None


def search(query: str, limit: int = 15) -> list:
    encoded = urllib.parse.quote(query)
    instance, resp = _find_working_instance(
        f"/search?q={encoded}&filter=music_songs"
    )

    if not instance:
        raise RuntimeError("Все инстансы Piped недоступны")

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


def get_stream_url(video_id: str, instance: str = None) -> str:
    """Получает прямую ссылку на аудио поток через параллельный запрос."""
    # Сначала пробуем переданный инстанс
    instances_to_try = []
    if instance:
        instances_to_try.append(instance)
    cached = _working_instance[0]
    if cached and cached != instance:
        instances_to_try.append(cached)

    # Пробуем приоритетные инстансы напрямую
    for inst in instances_to_try:
        try:
            resp = requests.get(f"{inst}/streams/{video_id}", timeout=6)
            resp.raise_for_status()
            data = resp.json()
            audio_streams = data.get("audioStreams", [])
            if audio_streams:
                best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
                url = best.get("url", "")
                if url:
                    print(f"[music] stream ok from {inst}, bitrate={best.get('bitrate')}")
                    return url
        except Exception as e:
            print(f"[music] stream error {inst}: {e}")
            continue

    # Параллельный перебор всех
    inst, resp = _find_working_instance(f"/streams/{video_id}", timeout=6)
    if not inst:
        print(f"[music] get_stream_url: all instances failed for {video_id}")
        return ""

    data = resp.json()
    audio_streams = data.get("audioStreams", [])
    if not audio_streams:
        print(f"[music] get_stream_url: no audioStreams for {video_id}")
        return ""

    best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
    url = best.get("url", "")
    print(f"[music] stream ok from {inst}, bitrate={best.get('bitrate')}")
    return url


def get_suggestions(query: str) -> list:
    encoded = urllib.parse.quote(query)
    inst, resp = _find_working_instance(f"/suggestions?query={encoded}", timeout=3)
    if not inst:
        return []
    try:
        return resp.json()
    except Exception:
        return []
