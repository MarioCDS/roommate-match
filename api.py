"""randomuser.me client for seeding roommate candidates."""
from __future__ import annotations

from typing import List

import requests

from models import Profile

API_URL = "https://randomuser.me/api/"


def fetch_candidates(n: int = 30, timeout: float = 10.0) -> List[Profile]:
    """Fetch n random users and wrap them as Profile objects.

    Raises requests.RequestException on network failure.
    """
    resp = requests.get(API_URL, params={"results": n, "nat": "us,gb,es,fr,de,br"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return [Profile.from_randomuser(u) for u in data.get("results", [])]
