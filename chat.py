"""Mock chat: per-match JSON threads with the option of a canned reply.

Each thread lives at ``data/users/<username>/chats/<peer_id>.json`` and is
a list of messages. A message is a plain dict::

    {"from": "me" | "them", "text": str, "ts": ISO-8601 string}
"""
import random
from datetime import datetime

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


def chat_file(username, peer_id):
    return user_dir(username) / "chats" / (peer_id + ".json")


def load_chat(username, peer_id):
    return load_json(chat_file(username, peer_id), [])


def save_chat(username, peer_id, messages):
    save_json(chat_file(username, peer_id), messages)


def append_message(username, peer_id, from_side, text):
    msg = {
        "from": from_side,
        "text": text,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    messages = load_chat(username, peer_id)
    messages.append(msg)
    save_chat(username, peer_id, messages)
    return msg


def maybe_canned_reply(reply_chance=0.75):
    """Return a canned reply from the other side, or None."""
    if random.random() > reply_chance:
        return None
    return random.choice(CANNED_REPLIES)
