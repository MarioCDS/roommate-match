"""randomuser.me client for seeding roommate candidates.

The fetch_candidates() function always prepends our featured profiles
(see ``featured_candidates``) so there is at least one familiar face in
the demo pool.
"""
import requests

from models import Profile, house_photo_gallery

API_URL = "https://randomuser.me/api/"


def fetch_candidates(n=30, timeout=10.0):
    """Fetch n random users and wrap them as Profile objects.

    Raises requests.RequestException on network failure.
    """
    resp = requests.get(
        API_URL,
        params={"results": n, "nat": "us,gb,es,fr,de,br"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    api_profiles = [Profile.from_randomuser(u) for u in data.get("results", [])]
    return featured_candidates() + api_profiles


def featured_ids():
    """IDs of hand-picked candidates that should always surface first."""
    return {c.id for c in featured_candidates()}


def featured_candidates():
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
            house_photo_urls=house_photo_gallery("harold-arato"),
            rooms=2,
            bathrooms=1,
            square_meters=72,
        ),
    ]
