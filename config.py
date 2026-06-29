import os

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://localhost:5000/auth/callback")
SPOTIFY_SCOPE = "user-library-read"

DOWNLOAD_DIR = os.environ.get("MTV_DOWNLOAD_DIR", os.path.join(os.path.dirname(__file__), "videos"))

# Per-profile data lives alongside the videos so a single mounted volume holds
# all state (catalog, video metadata, profiles, and Spotify tokens).
DATA_DIR = os.environ.get("MTV_DATA_DIR", DOWNLOAD_DIR)
TOKENS_DIR = os.path.join(DATA_DIR, "tokens")

SECRET_KEY = os.environ.get("MTV_SECRET_KEY", "change-me-em-tee-vee")
PORT = int(os.environ.get("MTV_PORT", 5000))
