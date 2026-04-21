"""Mock authentication: SHA-256 hashed passwords in a local JSON file.

NOT PRODUCTION. There is no salt, no rate limiting, no password-strength
enforcement. The goal is only to demonstrate a login/signup flow for the
university project.
"""
import hashlib
import string

from storage import USERS_FILE, load_json, save_json

MIN_USERNAME_LEN = 3
MIN_PASSWORD_LEN = 6
# Any character that Python's standard library considers punctuation counts
# as a "symbol". That covers the usual suspects: ! @ # $ % ^ & * etc.
SYMBOLS = string.punctuation

PASSWORD_RULES = (
    "At least 6 characters, including one uppercase letter and one symbol "
    "(for example ! @ # $ %)."
)


def _hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users):
    save_json(USERS_FILE, users)


def authenticate(username, password):
    users = load_users()
    stored = users.get(username)
    return stored is not None and stored == _hash(password)


def validate_new_credentials(username, password, confirm):
    """Return an error message, or None if the inputs are acceptable."""
    username = username.strip()
    if len(username) < MIN_USERNAME_LEN:
        return "Username must be at least " + str(MIN_USERNAME_LEN) + " characters."
    if not username.replace("_", "").isalnum():
        return "Username can only contain letters, numbers, and underscores."
    if len(password) < MIN_PASSWORD_LEN:
        return (
            "Password must be at least " + str(MIN_PASSWORD_LEN)
            + " characters long."
        )
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c in SYMBOLS for c in password):
        return (
            "Password must contain at least one symbol "
            "(for example ! @ # $ %)."
        )
    if password != confirm:
        return "Passwords do not match."
    return None


def create_user(username, password):
    """Create a new account. Returns False if the username is already taken."""
    users = load_users()
    if username in users:
        return False
    users[username] = _hash(password)
    save_users(users)
    return True
