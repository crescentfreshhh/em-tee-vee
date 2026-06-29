import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler
import config
import profiles


class NotAuthenticated(Exception):
    pass


def make_oauth(profile_id):
    """Build a SpotifyOAuth bound to a single profile's token cache.

    `state` carries the profile id through the Spotify redirect so the
    callback knows which profile is being connected.
    """
    cache_handler = CacheFileHandler(cache_path=profiles.token_path_for(profile_id))
    return SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=config.SPOTIFY_SCOPE,
        cache_handler=cache_handler,
        state=profile_id,
        show_dialog=True,
    )


def authorize_url(profile_id):
    return make_oauth(profile_id).get_authorize_url()


def handle_callback(profile_id, code):
    """Exchange the auth code for tokens (cached) and record the Spotify name."""
    oauth = make_oauth(profile_id)
    oauth.get_access_token(code, as_dict=False, check_cache=False)
    sp = spotipy.Spotify(auth_manager=oauth)
    try:
        me = sp.current_user()
        profiles.set_spotify_user(profile_id, me.get("display_name") or me.get("id"))
    except Exception:
        pass


def _client_for(profile_id):
    oauth = make_oauth(profile_id)
    if oauth.cache_handler.get_cached_token() is None:
        raise NotAuthenticated(f"Profile {profile_id} has not connected Spotify")
    return spotipy.Spotify(auth_manager=oauth)


def fetch_liked_songs(profile_id, limit=None):
    sp = _client_for(profile_id)
    songs = []
    results = sp.current_user_saved_tracks(limit=50)

    while results:
        for item in results["items"]:
            track = item["track"]
            if not track:
                continue
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
