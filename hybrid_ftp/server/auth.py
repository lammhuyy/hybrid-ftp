import json
import hashlib
import os


USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "users.json")


def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def authenticate(username, password):
    users = _load_users()
    if username not in users:
        return False, None
    entry = users[username]
    salt = entry["salt"]
    stored_hash = entry["hash"]
    computed = hashlib.sha256((salt + password).encode()).hexdigest()
    if computed == stored_hash:
        return True, entry.get("root", "")
    return False, None


def user_exists(username):
    users = _load_users()
    return username in users
