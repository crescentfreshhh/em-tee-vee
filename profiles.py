import json
import os
import time
import uuid
import config

PROFILES_FILE = os.path.join(config.DATA_DIR, "profiles.json")

# Netflix-style accent palette assigned to profiles in order of creation.
_COLORS = ["#ff3366", "#33b5e5", "#9c33ff", "#33cc66", "#ffaa33", "#ff6699", "#00c2a8"]


def _ensure_dirs():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.TOKENS_DIR, exist_ok=True)


def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            return json.load(f)
    return {}


def save_profiles(profiles):
    _ensure_dirs()
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def get_profile(profile_id):
    return load_profiles().get(profile_id)


def create_profile(name):
    name = (name or "").strip()
    if not name:
        raise ValueError("Profile name is required")

    profiles = load_profiles()
    for p in profiles.values():
        if p["name"].lower() == name.lower():
            raise ValueError("A profile with that name already exists")

    profile_id = uuid.uuid4().hex[:12]
    profiles[profile_id] = {
        "id": profile_id,
        "name": name,
        "color": _COLORS[len(profiles) % len(_COLORS)],
        "created": int(time.time()),
        "spotify_user": None,
    }
    save_profiles(profiles)
    return profiles[profile_id]


def set_spotify_user(profile_id, display_name):
    profiles = load_profiles()
    if profile_id in profiles:
        profiles[profile_id]["spotify_user"] = display_name
        save_profiles(profiles)


def delete_profile(profile_id):
    profiles = load_profiles()
    if profile_id in profiles:
        del profiles[profile_id]
        save_profiles(profiles)

    token_path = token_path_for(profile_id)
    if os.path.exists(token_path):
        os.remove(token_path)


def token_path_for(profile_id):
    _ensure_dirs()
    return os.path.join(config.TOKENS_DIR, f"token-{profile_id}.json")


def is_authed(profile_id):
    return os.path.exists(token_path_for(profile_id))
