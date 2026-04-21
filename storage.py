"""JSON persistence helpers.

Paths are rooted next to the .exe (frozen) or next to this file (dev).
User-scoped files live under data/users/<username>/ so multiple accounts
can coexist with separate profiles and matches.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if getattr(sys, "frozen", False):
    # Running from a PyInstaller bundle: store data next to the .exe.
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"

# Shared across all accounts
USERS_FILE = DATA_DIR / "users.json"
CANDIDATES_FILE = DATA_DIR / "candidates.json"


def user_dir(username: str) -> Path:
    return DATA_DIR / "users" / username


def profile_file(username: str) -> Path:
    return user_dir(username) / "profile.json"


def matches_file(username: str) -> Path:
    return user_dir(username) / "matches.json"


def filters_file(username: str) -> Path:
    return user_dir(username) / "filters.json"


def avatar_path(username: str) -> Path:
    return user_dir(username) / "avatar.jpg"


def house_photo_path(username: str, index: int) -> Path:
    return user_dir(username) / f"house_{index}.jpg"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
