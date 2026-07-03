import os
import html
import threading
from flask import (
    Flask, render_template, jsonify, send_from_directory, request,
    redirect, abort,
)
import config
import downloader
import profiles
import spotify_client

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Extensions the /videos route is allowed to serve. Videos are always merged to
# mp4; the others are permitted defensively in case the format policy changes.
VIDEO_EXTS = (".mp4", ".webm", ".m4v", ".mkv")

sync_status = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_song": "",
    "profile": "",
    "errors": [],
}
_sync_lock = threading.Lock()


# ---------------------------------------------------------------- pages

@app.route("/")
def home():
    return render_template("profiles.html")


@app.route("/player")
def player():
    return render_template("player.html")


@app.route("/library")
def library():
    return render_template("library.html")


# ------------------------------------------------------------ PWA assets

@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    # Served from the root so its scope covers the whole origin.
    resp = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# --------------------------------------------------------- profiles API

@app.route("/api/profiles")
def api_profiles():
    profs = profiles.load_profiles()
    library_all = downloader.get_library()
    counts = {}
    have = {}
    for song in library_all:
        for pid in song.get("profiles", []):
            counts[pid] = counts.get(pid, 0) + 1
            if song["status"] == "downloaded":
                have[pid] = have.get(pid, 0) + 1

    result = []
    for pid, p in profs.items():
        result.append({
            **p,
            "authed": profiles.is_authed(pid),
            "song_count": counts.get(pid, 0),
            "video_count": have.get(pid, 0),
        })
    result.sort(key=lambda p: p["created"])
    return jsonify(result)


@app.route("/api/profiles", methods=["POST"])
def api_create_profile():
    data = request.get_json(silent=True) or {}
    try:
        profile = profiles.create_profile(data.get("name", ""))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(profile)


@app.route("/api/profiles/<profile_id>", methods=["DELETE"])
def api_delete_profile(profile_id):
    if not profiles.get_profile(profile_id):
        return jsonify({"error": "Profile not found"}), 404
    downloader.remove_profile_memberships(profile_id)
    profiles.delete_profile(profile_id)
    return jsonify({"status": "deleted"})


# -------------------------------------------------------- Spotify OAuth

@app.route("/auth/login/<profile_id>")
def auth_login(profile_id):
    if not profiles.get_profile(profile_id):
        abort(404)
    if not config.SPOTIFY_CLIENT_ID:
        return "Spotify is not configured (set SPOTIPY_CLIENT_ID/SECRET).", 500
    return redirect(spotify_client.authorize_url(profile_id))


@app.route("/auth/callback")
def auth_callback():
    error = request.args.get("error")
    if error:
        return _auth_result_page(f"Spotify authorization failed: {error}", ok=False)

    code = request.args.get("code")
    profile_id = request.args.get("state")
    if not code or not profile_id or not profiles.get_profile(profile_id):
        return _auth_result_page("Invalid authorization response.", ok=False)

    try:
        spotify_client.handle_callback(profile_id, code)
    except Exception as e:
        return _auth_result_page(f"Could not connect Spotify: {e}", ok=False)

    return _auth_result_page("Spotify connected! You can close this tab.", ok=True)


def _auth_result_page(message, ok):
    color = "#33cc66" if ok else "#ff3366"
    # message may include attacker-controllable values (the Spotify `error`
    # query param, exception text), so escape it before embedding in HTML.
    message = html.escape(message)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>em tee vee</title>
<style>body{{background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
.card{{padding:40px;border:1px solid #222;border-radius:12px;background:#111}}
h1{{color:{color};font-size:1.2em}} a{{color:#33b5e5}}</style></head>
<body><div class="card"><h1>{message}</h1>
<p><a href="/">Back to em tee vee</a></p></div>
<script>setTimeout(function(){{location.href="/";}}, 2500);</script></body></html>"""


# ------------------------------------------------------------ media API

@app.route("/api/videos")
def api_videos():
    profile_id = request.args.get("profile")
    return jsonify(downloader.get_downloaded_videos(profile_id))


@app.route("/api/library")
def api_library():
    profile_id = request.args.get("profile")
    return jsonify(downloader.get_library(profile_id))


@app.route("/api/match", methods=["POST"])
def api_match():
    data = request.get_json(silent=True)
    if not data or "key" not in data or "url" not in data:
        return jsonify({"error": "key and url are required"}), 400

    songs_db = downloader.load_songs_db()
    if data["key"] not in songs_db:
        return jsonify({"error": "Song not found"}), 404

    try:
        entry = downloader.download_from_url(songs_db[data["key"]], data["url"])
        return jsonify(entry)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/videos/<path:filename>")
def serve_video(filename):
    # Only ever serve the media files themselves. The download directory also
    # holds the song catalog, profiles, and per-profile Spotify tokens, and this
    # route must never expose those. Reject any subpath or non-video extension.
    if "/" in filename or "\\" in filename or not filename.lower().endswith(VIDEO_EXTS):
        abort(404)
    return send_from_directory(config.DOWNLOAD_DIR, filename)


# ------------------------------------------------------------------ sync

@app.route("/api/sync", methods=["POST"])
def api_sync():
    if sync_status["running"]:
        return jsonify({"error": "Sync already in progress"}), 409

    data = request.get_json(silent=True) or {}
    profile_id = data.get("profile_id", "all")
    limit = data.get("limit")

    if profile_id == "all":
        target_ids = [pid for pid in profiles.load_profiles() if profiles.is_authed(pid)]
    else:
        if not profiles.get_profile(profile_id):
            return jsonify({"error": "Profile not found"}), 404
        if not profiles.is_authed(profile_id):
            return jsonify({"error": "Profile has not connected Spotify"}), 400
        target_ids = [profile_id]

    if not target_ids:
        return jsonify({"error": "No connected profiles to sync"}), 400

    thread = threading.Thread(target=_run_sync, args=(target_ids, limit), daemon=True)
    thread.start()
    return jsonify({"status": "started", "profiles": target_ids})


@app.route("/api/sync/status")
def api_sync_status():
    return jsonify(sync_status)


def _run_sync(profile_ids, limit=None):
    with _sync_lock:
        sync_status.update(running=True, current=0, total=0, current_song="", errors=[])
        all_profs = profiles.load_profiles()
        try:
            # Tag membership per profile and build a deduplicated download set.
            to_download = {}
            for pid in profile_ids:
                name = all_profs.get(pid, {}).get("name", pid)
                sync_status["profile"] = name
                songs = spotify_client.fetch_liked_songs(pid, limit=limit)
                downloader.save_songs(songs, pid)
                for s in songs:
                    to_download[downloader.song_key(s)] = s

            songs = list(to_download.values())
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
            sync_status["profile"] = ""


if __name__ == "__main__":
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    # Debug is opt-in: the Werkzeug debugger allows remote code execution, and
    # this server binds all interfaces. threaded=True lets video streams and API
    # calls be served concurrently instead of blocking one another.
    debug = os.environ.get("MTV_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=config.PORT, debug=debug, threaded=True)
