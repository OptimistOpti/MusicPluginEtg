"""
YouTube Music source for music.plugin
Uses yt-dlp for stream extraction
"""

import urllib.parse
import threading
import subprocess
import sys

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "2.1.0"

_external_log = [None]
_working_instance = [None]
_ytdlp_ready = [False]


def set_logger(fn):
    _external_log[0] = fn


def _log(msg):
    fn = _external_log[0]
    if fn:
        fn(str(msg))


def configure(api_key: str):
    pass


def _ensure_ytdlp() -> bool:
    """Устанавливает yt-dlp если не установлен. Возвращает True если готов."""
    if _ytdlp_ready[0]:
        return True
    try:
        import yt_dlp
        _ytdlp_ready[0] = True
        _log(f"[music] yt-dlp already installed: {yt_dlp.version.__version__}")
        return True
    except ImportError:
        pass

    _log("[music] yt-dlp not found, installing...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "yt-dlp", "--quiet", "--no-deps"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            import yt_dlp
            _ytdlp_ready[0] = True
            _log(f"[music] yt-dlp installed: {yt_dlp.version.__version__}")
            return True
        else:
            _log(f"[music] pip install failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        _log(f"[music] install error: {e}")
        return False


def is_configured() -> bool:
    return _ensure_ytdlp()


def search(query: str, limit: int = 15) -> list:
    if not _ensure_ytdlp():
        raise RuntimeError("yt-dlp не установлен")

    import yt_dlp
    _log(f"[music] yt-dlp search: {query!r}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
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
                "duration_sec": int(entry.get("duration", 0) or 0),
                "thumbnail_url": entry.get("thumbnail", ""),
                "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
                "stream_url": None,
                "_instance": None,
            })

    _log(f"[music] search done: {len(results)} results")
    return results


def get_stream_url(video_id: str, instance: str = None) -> dict:
    if not _ensure_ytdlp():
        return {}

    import yt_dlp
    _log(f"[music] yt-dlp get_stream_url: {video_id}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio",
    }

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                _log(f"[music] yt-dlp: no info")
                return {}

            stream_url = info.get("url", "")
            ext = info.get("ext", "m4a")
            if ext == "m4a":
                mime = "audio/mp4"
            elif ext == "webm":
                mime = "audio/webm"
            else:
                mime = f"audio/{ext}"

            _log(f"[music] stream ok ext={ext} abr={info.get('abr')} url={stream_url[:60]}")
            return {"url": stream_url, "mime": mime}
    except Exception as e:
        _log(f"[music] get_stream_url error: {e}")
        return {}


def get_suggestions(query: str) -> list:
    return []
