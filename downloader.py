import json
import os
import subprocess
import hashlib
import config


METADATA_FILE = os.path.join(config.DOWNLOAD_DIR, "metadata.json")
SONGS_FILE = os.path.join(config.DOWNLOAD_DIR, "songs.json")


def _load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def _save_metadata(metadata):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def load_songs_db():
    if os.path.exists(SONGS_FILE):
        with open(SONGS_FILE) as f:
            return json.load(f)
    return {}


def save_songs_db(songs_db):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    with open(SONGS_FILE, "w") as f:
        json.dump(songs_db, f, indent=2)


def song_key(song):
    raw = f"{song['artist']} - {song['title']}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def save_songs(songs):
    songs_db = load_songs_db()
    for s in songs:
        key = song_key(s)
        if key not in songs_db:
            songs_db[key] = s
    save_songs_db(songs_db)
    return songs_db


def get_library():
    songs_db = load_songs_db()
    metadata = _load_metadata()
    library = []
    for key, song in songs_db.items():
        entry = dict(song)
        entry["key"] = key
        if key in metadata:
            vid = metadata[key]
            filepath = os.path.join(config.DOWNLOAD_DIR, vid["file"])
            if os.path.exists(filepath):
                entry["status"] = "downloaded"
                entry["file"] = vid["file"]
                entry["video_title"] = vid.get("video_title", "")
                entry["source_url"] = vid.get("source_url", "")
            else:
                entry["status"] = "missing"
        else:
            entry["status"] = "none"
        library.append(entry)
    return library


def _find_video_file(key):
    for fname in os.listdir(config.DOWNLOAD_DIR):
        if fname.startswith(key) and not fname.endswith(".json"):
            return os.path.join(config.DOWNLOAD_DIR, fname)
    return None


def download_from_url(song, url):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    metadata = _load_metadata()
    key = song_key(song)

    old_file = None
    if key in metadata:
        old_file = os.path.join(config.DOWNLOAD_DIR, metadata[key]["file"])

    output_template = os.path.join(config.DOWNLOAD_DIR, f"{key}.%(ext)s")

    cmd = [
        "yt-dlp",
        url,
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "--embed-thumbnail",
        "--print", "after_move:filepath",
        "--print", "title",
        "--print", "webpage_url",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed for '{url}': {result.stderr}")

    lines = result.stdout.strip().split("\n")
    filepath = lines[-3] if len(lines) >= 3 else None
    video_title = lines[-2] if len(lines) >= 2 else ""
    video_url = lines[-1] if lines else url

    if not filepath or not os.path.exists(filepath):
        for f in os.listdir(config.DOWNLOAD_DIR):
            if f.startswith(key) and f.endswith(".mp4"):
                filepath = os.path.join(config.DOWNLOAD_DIR, f)
                break

    if not filepath or not os.path.exists(filepath):
        raise RuntimeError(f"Download completed but file not found for '{url}'")

    if old_file and os.path.exists(old_file) and os.path.abspath(old_file) != os.path.abspath(filepath):
        os.remove(old_file)

    entry = {
        "key": key,
        "file": os.path.basename(filepath),
        "title": song["title"],
        "artist": song["artist"],
        "album": song.get("album", ""),
        "video_title": video_title,
        "source_url": video_url,
        "spotify_id": song.get("spotify_id", ""),
    }

    metadata[key] = entry
    _save_metadata(metadata)
    return entry


def download_video(song):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    metadata = _load_metadata()
    key = song_key(song)

    if key in metadata and _find_video_file(key):
        return metadata[key]

    query = f"{song['artist']} {song['title']} official music video"
    output_template = os.path.join(config.DOWNLOAD_DIR, f"{key}.%(ext)s")

    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "--embed-thumbnail",
        "--print", "after_move:filepath",
        "--print", "title",
        "--print", "webpage_url",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed for '{query}': {result.stderr}")

    lines = result.stdout.strip().split("\n")
    filepath = lines[-3] if len(lines) >= 3 else None
    video_title = lines[-2] if len(lines) >= 2 else query
    video_url = lines[-1] if lines else ""

    if not filepath or not os.path.exists(filepath):
        for f in os.listdir(config.DOWNLOAD_DIR):
            if f.startswith(key) and f.endswith(".mp4"):
                filepath = os.path.join(config.DOWNLOAD_DIR, f)
                break

    if not filepath or not os.path.exists(filepath):
        raise RuntimeError(f"Download completed but file not found for '{query}'")

    entry = {
        "key": key,
        "file": os.path.basename(filepath),
        "title": song["title"],
        "artist": song["artist"],
        "album": song["album"],
        "video_title": video_title,
        "source_url": video_url,
        "spotify_id": song.get("spotify_id", ""),
    }

    metadata[key] = entry
    _save_metadata(metadata)
    return entry


def get_downloaded_videos():
    metadata = _load_metadata()
    available = []
    for key, entry in metadata.items():
        filepath = os.path.join(config.DOWNLOAD_DIR, entry["file"])
        if os.path.exists(filepath):
            available.append(entry)
    return available


def download_all(songs, progress_callback=None):
    results = {"success": [], "failed": []}
    for i, song in enumerate(songs):
        try:
            entry = download_video(song)
            results["success"].append(entry)
        except Exception as e:
            results["failed"].append({
                "song": song,
                "error": str(e),
            })
        if progress_callback:
            progress_callback(i + 1, len(songs), song)
    return results
