"""randomuser.me client for seeding roommate candidates."""
from __future__ import annotations

from typing import List

import requests

from models import Profile

API_URL = "https://randomuser.me/api/"


def fetch_candidates(n: int = 30, timeout: float = 10.0) -> List[Profile]:
    """Fetch n random users and wrap them as Profile objects.

    The returned list always starts with our hand-picked featured candidates
    (see ``featured_candidates``) so there is at least one familiar face in
    the demo pool.

    Raises requests.RequestException on network failure.
    """
    resp = requests.get(API_URL, params={"results": n, "nat": "us,gb,es,fr,de,br"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    api_profiles = [Profile.from_randomuser(u) for u in data.get("results", [])]
    return featured_candidates() + api_profiles


def featured_candidates() -> List[Profile]:
    """Always-present seeded candidates mixed into the demo pool."""
    return [
        Profile(
            id="harold-arato",
            name="Harold Arato",
            age=77,
            photo_url=(
                "https://upload.wikimedia.org/wikipedia/en/thumb/"
                "a/a4/Hide_the_Pain_Harold_%28Andr%C3%A1s_Arat%C3%B3%29.jpg/"
                "330px-Hide_the_Pain_Harold_%28Andr%C3%A1s_Arat%C3%B3%29.jpg"
            ),
            email="harold@hidethepain.hu",
            budget=0,
            smoker=False,
            schedule="early bird",
            bio=(
                "Retired electrical engineer from Budapest. Love photography, "
                "long walks, and a tidy kitchen. Everything is fine. Really."
            ),
            pets=False,
            cleanliness="very tidy",
            role="host",
            rent=380,
            house_description=(
                "Cozy two-bedroom near Oktogon. Very quiet building. Everything "
                "works perfectly. No problems at all. You'll love it here."
            ),
            house_photo_urls=[
                f"https://picsum.photos/seed/harold-room-{i}/600/400"
                for i in range(4)
            ],
            rooms=2,
            bathrooms=1,
            square_meters=72,
        ),
    ]
