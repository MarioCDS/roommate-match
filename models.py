"""Profile and Filters data classes.

A Profile now carries a ``role``:

- ``"roomie"`` is someone looking for a place. Their budget is what they can pay.
- ``"host"`` has a place to offer. Their ``rent`` is what they charge, plus a
  short description of the flat and a photo of it.

Roomies are shown host listings; hosts are shown roomie profiles. The rest of
the fields (smoker, pets, schedule, cleanliness) describe the person and are
relevant for both roles since they'll share the flat.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict


SCHEDULES = ["early bird", "night owl", "flexible"]
CLEANLINESS_LEVELS = ["very tidy", "tidy", "relaxed"]
ROLES = ["roomie", "host"]


@dataclass
class Profile:
    id: str
    name: str
    age: int
    photo_url: str
    email: str
    budget: int
    smoker: bool
    schedule: str
    bio: str
    pets: bool = False
    cleanliness: str = "tidy"
    role: str = "roomie"

    # Host-only fields. For roomies these stay at defaults and are ignored.
    rent: int = 0
    house_description: str = ""
    house_photo_urls: list = None  # populated to [] in __post_init__
    rooms: int = 0
    bathrooms: int = 0
    square_meters: int = 0

    # Default the mutable field after initialisation (dataclasses don't allow
    # ``list`` as a default value directly, but ``None`` lets us coerce).
    def __post_init__(self) -> None:
        if self.house_photo_urls is None:
            self.house_photo_urls = []

    # ------- derived helpers -----------------------------------------

    @property
    def effective_price(self) -> int:
        """What this profile implies as a monthly price figure.

        Roomies: the max they can pay. Hosts: the rent they charge.
        """
        return self.rent if self.role == "host" else self.budget

    @property
    def display_photo(self) -> str:
        """Primary photo shown on a swipe card.

        For hosts, the first image in the house gallery. For roomies, the
        personal portrait. Falls back to the portrait if the gallery is empty.
        """
        if self.role == "host" and self.house_photo_urls:
            return self.house_photo_urls[0]
        return self.photo_url

    # ------- serialisation -------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        # Back-compat: older profiles stored a single ``house_photo_url``;
        # new ones carry a ``house_photo_urls`` list.
        urls = list(d.get("house_photo_urls") or [])
        if not urls and d.get("house_photo_url"):
            urls = [d["house_photo_url"]]
        return cls(
            id=d["id"],
            name=d["name"],
            age=d["age"],
            photo_url=d.get("photo_url", ""),
            email=d.get("email", ""),
            budget=d.get("budget", 500),
            smoker=d.get("smoker", False),
            schedule=d.get("schedule", "flexible"),
            bio=d.get("bio", ""),
            pets=d.get("pets", False),
            cleanliness=d.get("cleanliness", "tidy"),
            role=d.get("role", "roomie"),
            rent=d.get("rent", 0),
            house_description=d.get("house_description", ""),
            house_photo_urls=urls,
            rooms=d.get("rooms", 0),
            bathrooms=d.get("bathrooms", 0),
            square_meters=d.get("square_meters", 0),
        )

    @classmethod
    def from_randomuser(cls, d: dict) -> "Profile":
        """Create a demo Profile from a randomuser.me record.

        Randomly assigns ``role`` so the demo pool contains both hosts and
        roomies. Hosts get a gallery of seeded house photos (picsum.photos)
        and a short description; roomies get a personal bio and a budget.

        The portrait comes straight from randomuser.me so the name and the
        face actually correspond.
        """
        name = f"{d['name']['first']} {d['name']['last']}"
        uid = d["login"]["uuid"]
        is_host = random.random() < 0.5
        role = "host" if is_host else "roomie"

        rent = random.choice([350, 400, 450, 500, 550, 600, 700, 800])
        return cls(
            id=uid,
            name=name,
            age=int(d["dob"]["age"]),
            # Use randomuser's native portrait so the person on the card
            # actually matches the name on the card. It's 128x128 but we
            # display it modestly to avoid heavy upscaling.
            photo_url=d["picture"]["large"],
            email=d["email"],
            budget=rent if is_host else random.choice(
                [350, 400, 450, 500, 550, 600, 700, 800, 900],
            ),
            smoker=random.random() < 0.3,
            schedule=random.choice(SCHEDULES),
            bio=random.choice(BIOS),
            pets=random.random() < 0.35,
            cleanliness=random.choice(CLEANLINESS_LEVELS),
            role=role,
            rent=rent if is_host else 0,
            house_description=random.choice(HOUSE_DESCRIPTIONS) if is_host else "",
            house_photo_urls=house_photo_gallery(uid) if is_host else [],
            rooms=random.choice([1, 2, 2, 3, 3, 4]) if is_host else 0,
            bathrooms=random.choice([1, 1, 1, 2]) if is_host else 0,
            square_meters=random.choice([45, 55, 65, 70, 80, 90, 110]) if is_host else 0,
        )

    # ------- filtering -----------------------------------------------

    def matches_filters(self, f: "Filters") -> bool:
        if self.effective_price > f.max_budget:
            return False
        if f.smoker_pref == "no smokers" and self.smoker:
            return False
        if f.smoker_pref == "smokers only" and not self.smoker:
            return False
        if f.schedule_pref != "any" and self.schedule != f.schedule_pref:
            return False
        if f.pets_pref == "no pets" and self.pets:
            return False
        if f.pets_pref == "has pets" and not self.pets:
            return False
        if f.cleanliness_pref != "any" and self.cleanliness != f.cleanliness_pref:
            return False
        return True


@dataclass
class Filters:
    max_budget: int = 2000
    smoker_pref: str = "any"          # "any" | "no smokers" | "smokers only"
    schedule_pref: str = "any"        # "any" | one of SCHEDULES
    pets_pref: str = "any"            # "any" | "has pets" | "no pets"
    cleanliness_pref: str = "any"     # "any" | one of CLEANLINESS_LEVELS

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Filters":
        return cls(
            max_budget=d.get("max_budget", 2000),
            smoker_pref=d.get("smoker_pref", "any"),
            schedule_pref=d.get("schedule_pref", "any"),
            pets_pref=d.get("pets_pref", "any"),
            cleanliness_pref=d.get("cleanliness_pref", "any"),
        )


def avatar_url(seed: str) -> str:
    """Deterministic 500x500 avatar URL from a seed (UUID or username)."""
    return f"https://i.pravatar.cc/500?u={seed}"


# Curated Unsplash photo IDs of apartment / interior shots. Using a fixed
# list keeps the demo pool looking like homes rather than the landscapes
# that picsum.photos tends to return. Each Profile picks ``n`` consecutive
# entries from a deterministic offset so the same listing always gets the
# same gallery.
_INTERIOR_PHOTO_IDS = [
    "photo-1522708323590-d24dbb6b0267",   # modern living room
    "photo-1560448204-e02f11c3d0e2",      # bedroom
    "photo-1502672260266-1c1ef2d93688",   # kitchen
    "photo-1484154218962-a197022b5858",   # open-plan kitchen
    "photo-1493663284031-b7e3aefcae8e",   # dining area
    "photo-1586023492125-27b2c045efd7",   # bathroom
    "photo-1556909114-f6e7ad7d3136",      # living room with couch
    "photo-1505693416388-ac5ce068fe85",   # bedroom grey
    "photo-1555854877-bab0e564b8d5",      # kitchen and dining
    "photo-1513584684374-8bab748fbf90",   # living area
    "photo-1540518614846-7eded433c457",   # minimalist living
    "photo-1524758631624-e2822e304c36",   # apartment living
    "photo-1598928506311-c55ded91a20c",   # cosy corner
    "photo-1586105251261-72a756497a11",   # modern bathroom
    "photo-1521783988139-893ce4f7ed71",   # bedroom
    "photo-1534595038511-9f219fe0c979",   # sofa scene
]


def _unsplash_url(photo_id: str) -> str:
    return (
        f"https://images.unsplash.com/{photo_id}"
        "?w=600&h=400&fit=crop&auto=format"
    )


def _gallery_offset(seed: str) -> int:
    import hashlib
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % len(_INTERIOR_PHOTO_IDS)


def house_photo_url(seed: str) -> str:
    """Deterministic 600x400 apartment-interior stock photo for one listing."""
    idx = _gallery_offset(seed)
    return _unsplash_url(_INTERIOR_PHOTO_IDS[idx])


def house_photo_gallery(seed: str, n: int = 4) -> list:
    """A list of ``n`` deterministic 600x400 interior photos for one listing.

    The photos are picked consecutively from the curated list starting at an
    offset hashed from ``seed``, so (a) the same listing is stable across
    runs and (b) two different listings usually look different.
    """
    offset = _gallery_offset(seed)
    urls = []
    for i in range(n):
        pid = _INTERIOR_PHOTO_IDS[(offset + i) % len(_INTERIOR_PHOTO_IDS)]
        urls.append(_unsplash_url(pid))
    return urls


def compatibility(me: Profile, other: Profile) -> int:
    """Return a 0-100 score estimating how well ``other`` fits ``me``.

    Lifestyle matches (smoker, schedule, pets, cleanliness) are treated the
    same regardless of role. Price compatibility uses each side's
    ``effective_price``.
    """
    # Price fit. 30%.
    diff = abs(me.effective_price - other.effective_price)
    price_s = 100 if diff < 100 else 70 if diff < 300 else 30

    # Schedule. 25%.
    if me.schedule == other.schedule:
        sched_s = 100
    elif "flexible" in (me.schedule, other.schedule):
        sched_s = 70
    else:
        sched_s = 25

    # Smoking agreement. 20%.
    smok_s = 100 if me.smoker == other.smoker else 15

    # Cleanliness. 15%.
    levels = {"very tidy": 2, "tidy": 1, "relaxed": 0}
    lev_diff = abs(
        levels.get(me.cleanliness, 1) - levels.get(other.cleanliness, 1)
    )
    clean_s = {0: 100, 1: 70, 2: 30}.get(lev_diff, 30)

    # Pets. 10%.
    pets_s = 100 if me.pets == other.pets else 55

    total = (
        price_s * 0.30
        + sched_s * 0.25
        + smok_s * 0.20
        + clean_s * 0.15
        + pets_s * 0.10
    )
    return int(round(total))


BIOS = [
    "Grad student. I keep the kitchen spotless and cook most nights. Looking for someone respectful and communicative.",
    "Remote software engineer. Coffee-addicted, plant parent, usually in by 10pm. Happy to share groceries.",
    "Engineering student at FCT. Quiet, tidy, don't throw parties. Gym at 7am so early nights during the week.",
    "Musician. Always use headphones when practising. Love cooking Sunday lunches and would split a Netflix plan.",
    "Weekends: hiking or board-game nights with friends over. Weeknights: quiet.",
    "Early bird. Out the door by 7, in bed by 11. Gym three times a week. Tidy but not uptight.",
    "Night owl coder. Respect quiet hours after midnight. Chill vibe, no drama, split the groceries.",
    "Foodie and a bit of a clean freak (sorry). Will happily cook for the flat on Sundays.",
    "Exchange student from Brazil. Sociable but respect of personal space is important. Love to travel cheap on weekends.",
    "Work in finance. Weeknights in, weekends out. Tidy common areas, own room can be a mess though.",
]


HOUSE_DESCRIPTIONS = [
    "Bright two-bedroom in Alvalade with a small balcony. Private room, shared bathroom. Close to metro and cafes.",
    "Sunny flat in Arroios. The room has a double bed and a desk. Living room is where we mostly hang out.",
    "Large old apartment near Saldanha. High ceilings, wooden floors. Quiet neighbours.",
    "Modern studio annex with its own entrance in Campo de Ourique. Shared kitchen with the main house.",
    "Renovated 3-bedroom near Tecnico. Ideal for students. I'm renting out the smaller room.",
    "Cozy room in a family flat in Benfica. 10 min walk to the park. Pets welcome.",
    "Spacious penthouse in Marques de Pombal. Rooftop access. A bit pricey but fully furnished.",
    "Top-floor flat near Cais do Sodre. Lots of light. I travel a lot for work so the place is mostly yours.",
]
