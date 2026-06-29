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
        if fname.startswith(key) and fname.endswith(".mp4"):
            return os.path.join(config.DOWNLOAD_DIR, fname)
    return None


# Field separator used to emit filepath/title/url in a single yt-dlp --print.
# Emitting them together at the after_move stage avoids relying on the order in
# which yt-dlp prints fields from different stages (default "video" vs
# "after_move"), which is not the order they appear on the command line.
_PRINT_SEP = "\x1f"


def _run_ytdlp(source, key):
    output_template = os.path.join(config.DOWNLOAD_DIR, f"{key}.%(ext)s")
    print_template = (
        f"after_move:%(filepath)s{_PRINT_SEP}%(title)s{_PRINT_SEP}%(webpage_url)s"
    )

    cmd = [
        "yt-dlp",
        source,
        "--quiet",
        "--no-warnings",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        # Re-matching a song reuses the same {key}.mp4 path; without this yt-dlp
        # would see the existing file and skip the new download entirely.
        "--force-overwrites",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "--embed-thumbnail",
        "--print", print_template,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed for '{source}': {result.stderr.strip()}")

    filepath = video_title = video_url = None
    for line in result.stdout.splitlines():
        if _PRINT_SEP in line:
            parts = line.split(_PRINT_SEP)
            if len(parts) == 3:
                filepath, video_title, video_url = parts

    if not filepath or not os.path.exists(filepath):
        filepath = _find_video_file(key)

    if not filepath or not os.path.exists(filepath):
        raise RuntimeError(f"Download completed but output file not found for '{source}'")

    return filepath, (video_title or ""), (video_url or "")


def _record_video(song, key, filepath, video_title, video_url):
    metadata = _load_metadata()
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


def download_from_url(song, url):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    key = song_key(song)
    filepath, video_title, video_url = _run_ytdlp(url, key)
    return _record_video(song, key, filepath, video_title, video_url or url)


def download_video(song):
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    metadata = _load_metadata()
    key = song_key(song)

    if key in metadata and _find_video_file(key):
        return metadata[key]

    query = f"{song['artist']} {song['title']} official music video"
    filepath, video_title, video_url = _run_ytdlp(f"ytsearch1:{query}", key)
    return _record_video(song, key, filepath, video_title or query, video_url)


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
