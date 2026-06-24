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
SOURCE_VERSION = "1.5.0"

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

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android 14; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0",
    "Accept": "application/json",
}

_working_instance = [None]


def configure(api_key: str):
    pass


def is_configured() -> bool:
    return True


def _get(url: str, timeout: float = 5.0):
    return requests.get(url, headers=_HEADERS, timeout=timeout)


def _find_working_instance(path: str, timeout: float = 4.0):
    result = [None]
    found = threading.Event()

    def try_instance(inst):
        if found.is_set():
            return
        try:
            resp = _get(f"{inst}{path}", timeout=timeout)
            resp.raise_for_status()
            if not found.is_set():
                result[0] = (inst, resp)
                found.set()
        except Exception:
            pass

    # Сначала кешированный
    cached = _working_instance[0]
    if cached:
        try:
            resp = _get(f"{cached}{path}", timeout=timeout)
            resp.raise_for_status()
            return cached, resp
        except Exception:
            _working_instance[0] = None

    threads = [threading.Thread(target=try_instance, args=(i,), daemon=True) for i in _INSTANCES]
    for t in threads:
        t.start()
    found.wait(timeout=timeout + 1)

    if result[0]:
        inst, resp = result[0]
        _working_instance[0] = inst
        print(f"[music] working instance: {inst}")
        return inst, resp

    return None, None


def search(query: str, limit: int = 15) -> list:
    encoded = urllib.parse.quote(query)
    instance, resp = _find_working_instance(f"/search?q={encoded}&filter=music_songs")
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
    path = f"/streams/{video_id}"
    print(f"[music] fetching stream for {video_id}")

    # Пробуем приоритетные инстансы
    priority = []
    if instance:
        priority.append(instance)
    cached = _working_instance[0]
    if cached and cached not in priority:
        priority.append(cached)

    for inst in priority:
        try:
            resp = _get(f"{inst}{path}", timeout=8)
            resp.raise_for_status()
            data = resp.json()
            audio_streams = data.get("audioStreams", [])
            if audio_streams:
                best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
                url = best.get("url", "")
                if url:
                    print(f"[music] stream ok from {inst} bitrate={best.get('bitrate')}")
                    return url
            print(f"[music] no audioStreams from {inst}: {list(data.keys())}")
        except Exception as e:
            print(f"[music] stream error {inst}: {e}")

    # Параллельный перебор
    inst, resp = _find_working_instance(path, timeout=8)
    if not inst:
        print(f"[music] all instances failed for streams/{video_id}")
        return ""

    data = resp.json()
    audio_streams = data.get("audioStreams", [])
    if not audio_streams:
        print(f"[music] no audioStreams in response: {list(data.keys())}")
        return ""

    best = max(audio_streams, key=lambda s: s.get("bitrate", 0))
    url = best.get("url", "")
    print(f"[music] stream ok from {inst} bitrate={best.get('bitrate')}")
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
