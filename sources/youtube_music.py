"""
YouTube Music source for music.plugin
Uses yt-dlp for stream extraction — reliable, no blocked instances
"""

import urllib.parse
import threading

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "2.0.0"
REQUIREMENTS = "yt-dlp"  # устанавливается через __requirements__ в плагине

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
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


def search(query: str, limit: int = 15) -> list:
    import yt_dlp

    _log(f"[music] yt-dlp search: {query!r}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
    }

    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = info.get("entries", []) if info else []
        for entry in entries:
            if not entry:
                continue
            vid_id = entry.get("id", "")
            if not vid_id:
                continue
            results.append({
                "id": vid_id,
                "title": entry.get("title", "Неизвестный трек"),
                "artist": entry.get("uploader", entry.get("channel", "Неизвестный исполнитель")),
                "duration_sec": entry.get("duration", 0) or 0,
                "thumbnail_url": entry.get("thumbnail", ""),
                "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
                "stream_url": None,
                "_instance": None,
            })

    _log(f"[music] yt-dlp search: {len(results)} results")
    return results


def get_stream_url(video_id: str, instance: str = None) -> dict:
    import yt_dlp

    _log(f"[music] yt-dlp get_stream_url: {video_id}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio",
    }

    url = f"https://www.youtube.com/watch?v={video_id}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            _log(f"[music] yt-dlp: no info for {video_id}")
            return {}

        stream_url = info.get("url", "")
        mime = info.get("ext", "m4a")
        if mime == "m4a":
            mime = "audio/mp4"
        elif mime == "webm":
            mime = "audio/webm"
        else:
            mime = f"audio/{mime}"

        _log(f"[music] yt-dlp stream ok: ext={info.get('ext')} abr={info.get('abr')} url={stream_url[:60]}")
        return {"url": stream_url, "mime": mime}


def get_suggestions(query: str) -> list:
    return []
