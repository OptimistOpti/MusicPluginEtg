import requests
import urllib.parse

SOURCE_ID = "youtube_music"
SOURCE_NAME = "YouTube Music"
SOURCE_VERSION = "1.1.0"

def configure(api_key: str):
    pass

def is_configured() -> bool:
    return True

def search(query: str, limit: int = 15) -> list[dict]:
    encoded_query = urllib.parse.quote(query)
    # Используем стабильный публичный инстанс Piped API с фильтрацией по музыке
    url = f"https://pipedapi.kavin.rocks/search?q={encoded_query}&filter=music_songs"
    
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    
    results = []
    for item in items[:limit]:
        video_url = item.get("url", "")
        video_id = video_url.split("v=")[-1] if "v=" in video_url else item.get("id", "")
        if not video_id:
            continue
            
        results.append({
            "id": video_id,
            "title": item.get("title", "Неизвестный трек"),
            "artist": item.get("uploaderName", "Неизвестный исполнитель"),
            "duration_sec": item.get("duration", 0),
            "thumbnail_url": item.get("thumbnail", ""),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}"
        })
    return results
