"""JSON persistence helpers.

Paths are rooted next to this file, under a data/ folder. User-scoped files
live under data/users/<username>/ so multiple accounts coexist with separate
profiles, matches, chats, and uploaded images.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Shared across all accounts.
USERS_FILE = DATA_DIR / "users.json"
CANDIDATES_FILE = DATA_DIR / "candidates.json"


def user_dir(username):
    return DATA_DIR / "users" / username


def profile_file(username):
    return user_dir(username) / "profile.json"


def matches_file(username):
    return user_dir(username) / "matches.json"


def filters_file(username):
    return user_dir(username) / "filters.json"


def avatar_path(username):
    return user_dir(username) / "avatar.jpg"


def house_photo_path(username, index):
    return user_dir(username) / ("house_" + str(index) + ".jpg")


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
