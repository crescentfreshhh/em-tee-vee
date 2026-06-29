import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config


def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=config.SPOTIFY_SCOPE,
    ))


def fetch_liked_songs(limit=None):
    sp = get_spotify_client()
    songs = []
    results = sp.current_user_saved_tracks(limit=50)

    while results:
        for item in results["items"]:
            track = item["track"]
            songs.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "album": track["album"]["name"],
                "spotify_id": track["id"],
            })
            if limit and len(songs) >= limit:
                return songs

        results = sp.next(results) if results["next"] else None

    return songs
