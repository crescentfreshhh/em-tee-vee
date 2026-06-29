import os
import json
import threading
from flask import Flask, render_template, jsonify, send_from_directory, request
import config
import downloader
import spotify_client

app = Flask(__name__)

sync_status = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_song": "",
    "errors": [],
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/videos")
def api_videos():
    videos = downloader.get_downloaded_videos()
    return jsonify(videos)


@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(config.DOWNLOAD_DIR, filename)


@app.route("/api/sync", methods=["POST"])
def api_sync():
    if sync_status["running"]:
        return jsonify({"error": "Sync already in progress"}), 409

    limit = request.json.get("limit") if request.is_json else None
    thread = threading.Thread(target=_run_sync, args=(limit,), daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/sync/status")
def api_sync_status():
    return jsonify(sync_status)


def _run_sync(limit=None):
    sync_status["running"] = True
    sync_status["current"] = 0
    sync_status["errors"] = []

    try:
        songs = spotify_client.fetch_liked_songs(limit=limit)
        sync_status["total"] = len(songs)

        def on_progress(current, total, song):
            sync_status["current"] = current
            sync_status["current_song"] = f"{song['artist']} - {song['title']}"

        results = downloader.download_all(songs, progress_callback=on_progress)
        sync_status["errors"] = [
            f"{e['song']['artist']} - {e['song']['title']}: {e['error']}"
            for e in results["failed"]
        ]
    except Exception as e:
        sync_status["errors"] = [str(e)]
    finally:
        sync_status["running"] = False
        sync_status["current_song"] = ""


if __name__ == "__main__":
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=config.PORT, debug=True)
