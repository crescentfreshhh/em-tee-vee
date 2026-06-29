import os

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
SPOTIFY_SCOPE = "user-library-read"

DOWNLOAD_DIR = os.environ.get("MTV_DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "videos"))
PORT = int(os.environ.get("MTV_PORT", 5000))
