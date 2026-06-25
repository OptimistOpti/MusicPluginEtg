"""
YouTube Music source for music.plugin
Uses Piped API — no API key required
https://docs.piped.video/docs/api-documentation/
"""

import requests
import urllib.parse
import threading
import logging
_log = logging.getLogger("music")

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.7.0"

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


def _get(url, timeout=5.0):
    return requests.get(url, headers=_HEADERS, timeout=timeout)


def _find_working_instance(path, timeout=4.0):
    result = [None]
    found = threading.Event()

    def try_inst(inst):
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

    cached = _working_instance[0]
    if cached:
        try:
            resp = _get(f"{cached}{path}", timeout=timeout)
            resp.raise_for_status()
            return cached, resp
        except Exception:
            _working_instance[0] = None

    threads = [threading.Thread(target=try_inst, args=(i,), daemon=True) for i in _INSTANCES]
    for t in threads:
        t.start()
    found.wait(timeout=timeout + 1)

    if result[0]:
        inst, resp = result[0]
        _working_instance[0] = inst
        _log.info(f"[music] working instance: {inst}")
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


def get_stream_url(video_id: str, instance: str = None) -> dict:
    """
    Возвращает dict {"url": ..., "mime": ...} или пустой dict.
    Предпочитаем M4A (audio/mp4) — лучшая совместимость с Android MediaPlayer.
    url уже проксирован через Piped (pipedproxy-*.kavin.rocks/...).
    """
    _log.info(f"[music] get_stream_url: {video_id}")
    path = f"/streams/{video_id}"

    priority = []
    if instance:
        priority.append(instance)
    cached = _working_instance[0]
    if cached and cached not in priority:
        priority.append(cached)

    data = None
    used_inst = None

    for inst in priority:
        try:
            resp = _get(f"{inst}{path}", timeout=8)
            resp.raise_for_status()
            data = resp.json()
            used_inst = inst
            break
        except Exception as e:
            _log.info(f"[music] stream error {inst}: {e}")

    if not data:
        inst, resp = _find_working_instance(path, timeout=8)
        if not inst:
            _log.info("[music] all instances failed")
            return {}
        data = resp.json()
        used_inst = inst

    return _pick_best_stream(data, used_inst)


def _pick_best_stream(data: dict, inst: str) -> dict:
    audio_streams = data.get("audioStreams", [])
    if not audio_streams:
        _log.info(f"[music] no audioStreams, keys: {list(data.keys())}")
        return {}

    _log.info(f"[music] {len(audio_streams)} audio streams from {inst}:")
    for s in audio_streams:
        _log.info(f"  format={s.get('format')} bitrate={s.get('bitrate')} mime={s.get('mimeType')} url={s.get('url','')[:60]}")

    # Предпочитаем M4A — лучшая совместимость с Android MediaPlayer
    m4a = [s for s in audio_streams if s.get("format", "").upper() == "M4A"]
    if m4a:
        best = max(m4a, key=lambda s: s.get("bitrate", 0))
    else:
        # Fallback на любой не-video поток
        non_video = [s for s in audio_streams if not s.get("videoOnly", True)]
        if not non_video:
            non_video = audio_streams
        best = max(non_video, key=lambda s: s.get("bitrate", 0))

    url = best.get("url", "")
    mime = best.get("mimeType", "audio/mp4")
    _log.info(f"[music] selected: format={best.get('format')} bitrate={best.get('bitrate')} mime={mime}")
    return {"url": url, "mime": mime}


def get_suggestions(query: str) -> list:
    encoded = urllib.parse.quote(query)
    inst, resp = _find_working_instance(f"/suggestions?query={encoded}", timeout=3)
    if not inst:
        return []
    try:
        return resp.json()
    except Exception:
        return []
