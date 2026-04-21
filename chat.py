"""Mock chat: per-match JSON threads with the option of a canned reply.

Each thread lives at ``data/users/<username>/chats/<peer_id>.json`` and is
a list of messages. A message is a plain dict::

    {"from": "me" | "them", "text": str, "ts": ISO-8601 string}
"""
from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path
from typing import List

from storage import load_json, save_json, user_dir


CANNED_REPLIES = [
    "Sounds good!",
    "When would you like to visit?",
    "Works for me.",
    "I'm home most evenings after 6.",
    "Rent is negotiable for a 12-month contract.",
    "Pets are fine, small ones anyway.",
    "I can send you the address when you want to come by.",
    "Let me know what works for you.",
    "Tidiness is important to me too.",
    "I'm pretty chill, no drama.",
    "Do you have any questions about the place?",
    "Cool! Let's keep chatting.",
    "No worries, take your time.",
    "Haha, same here.",
    "I travel a bit for work so the flat is mostly yours.",
    "Coffee is my love language.",
    "Happy to meet for a coffee first if you'd like.",
]


def chat_file(username: str, peer_id: str) -> Path:
    return user_dir(username) / "chats" / f"{peer_id}.json"


def load_chat(username: str, peer_id: str) -> List[dict]:
    return load_json(chat_file(username, peer_id), [])


def save_chat(username: str, peer_id: str, messages: List[dict]) -> None:
    save_json(chat_file(username, peer_id), messages)


def append_message(
    username: str, peer_id: str, from_side: str, text: str,
) -> dict:
    msg = {
        "from": from_side,
        "text": text,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    messages = load_chat(username, peer_id)
    messages.append(msg)
    save_chat(username, peer_id, messages)
    return msg


def maybe_canned_reply(reply_chance: float = 0.75) -> str | None:
    """Return a canned reply from the other side, or None.

    The matched profile isn't a real user, so replies are picked from a
    fixed pool. Caller decides when to invoke (typically right after the
    local user sends a message).
    """
    if random.random() > reply_chance:
        return None
    return random.choice(CANNED_REPLIES)
