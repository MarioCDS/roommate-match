"""Profile and Filters data classes.

A Profile carries a ``role``:

- ``"roomie"`` is someone looking for a place. Their budget is what they can pay.
- ``"host"`` has a place to offer. Their ``rent`` is what they charge, plus a
  short description of the flat and a photo gallery of the rooms.

Roomies see host listings; hosts see roomie profiles. The rest of the fields
(smoker, pets, schedule, cleanliness) describe the person and matter for both
since they'll share the flat.
"""
import random
from dataclasses import dataclass, field, asdict


SCHEDULES = ["early bird", "night owl", "flexible"]
CLEANLINESS_LEVELS = ["very tidy", "tidy", "relaxed"]
ROLES = ["roomie", "host"]
LEASE_OPTIONS = [1, 3, 6, 12, 24]

# Lisbon neighborhoods we know about. The coords are approximate but good
# enough for st.map. Kept as a plain dict so the intro-level iteration
# patterns (for name in NEIGHBORHOODS) work as expected.
NEIGHBORHOODS = {
    "Alvalade": (38.7516, -9.1443),
    "Arroios": (38.7353, -9.1355),
    "Campo de Ourique": (38.7213, -9.1646),
    "Saldanha": (38.7351, -9.1457),
    "Benfica": (38.7531, -9.2011),
    "Cais do Sodre": (38.7064, -9.1449),
    "Marques de Pombal": (38.7253, -9.1494),
    "Bairro Alto": (38.7137, -9.1447),
    "Chiado": (38.7097, -9.1427),
    "Parque das Nacoes": (38.7684, -9.0958),
    "Belem": (38.6981, -9.2060),
    "Lumiar": (38.7718, -9.1593),
}


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

    # Host-only fields. For roomies these stay at defaults.
    rent: int = 0
    house_description: str = ""
    house_photo_urls: list = field(default_factory=list)
    rooms: int = 0
    bathrooms: int = 0
    square_meters: int = 0
    neighborhood: str = ""
    move_in_date: str = ""       # ISO string, e.g. "2026-06-01"
    lease_months: int = 0
    utilities_included: bool = False
    furnished: bool = False

    # --- helpers ----------------------------------------------------

    def effective_price(self):
        """Rent for hosts; budget for roomies. Used by filters and scoring."""
        if self.role == "host":
            return self.rent
        return self.budget

    def display_photo(self):
        """First house photo for hosts, personal portrait otherwise."""
        if self.role == "host" and self.house_photo_urls:
            return self.house_photo_urls[0]
        return self.photo_url

    def matches_filters(self, f):
        if self.effective_price() > f.max_budget:
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
        # Neighborhood filter only applies to profiles that actually have one
        # (i.e. host listings). Roomies have no neighborhood so we skip.
        if (f.neighborhood_pref != "any" and self.neighborhood
                and self.neighborhood != f.neighborhood_pref):
            return False
        return True

    # --- serialisation ----------------------------------------------

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    @classmethod
    def from_randomuser(cls, d):
        """Create a demo Profile from a randomuser.me record.

        Flips a coin on role so the demo pool mixes hosts and roomies. Hosts
        get a gallery of interior stock photos and a short description;
        roomies get a personal bio and a budget.
        """
        name = d["name"]["first"] + " " + d["name"]["last"]
        uid = d["login"]["uuid"]
        is_host = random.random() < 0.5
        role = "host" if is_host else "roomie"
        rent = random.choice([350, 400, 450, 500, 550, 600, 700, 800])

        if is_host:
            budget = rent
            gallery = house_photo_gallery(uid)
            description = random.choice(HOUSE_DESCRIPTIONS)
            rooms = random.choice([1, 2, 2, 3, 3, 4])
            bathrooms = random.choice([1, 1, 1, 2])
            sqm = random.choice([45, 55, 65, 70, 80, 90, 110])
            neighborhood = random.choice(list(NEIGHBORHOODS.keys()))
            # A move-in date in the next 1-90 days, weekdays mostly.
            from datetime import date, timedelta
            move_in = date.today() + timedelta(days=random.randint(7, 90))
            move_in_date = move_in.isoformat()
            lease_months = random.choice(LEASE_OPTIONS)
            utilities_included = random.random() < 0.55
            furnished = random.random() < 0.65
        else:
            budget = random.choice([350, 400, 450, 500, 550, 600, 700, 800, 900])
            gallery = []
            description = ""
            rooms = 0
            bathrooms = 0
            sqm = 0
            neighborhood = ""
            move_in_date = ""
            lease_months = 0
            utilities_included = False
            furnished = False

        return cls(
            id=uid,
            name=name,
            age=int(d["dob"]["age"]),
            photo_url=d["picture"]["large"],
            email=d["email"],
            budget=budget,
            smoker=random.random() < 0.3,
            schedule=random.choice(SCHEDULES),
            bio=random.choice(BIOS),
            pets=random.random() < 0.35,
            cleanliness=random.choice(CLEANLINESS_LEVELS),
            role=role,
            rent=rent if is_host else 0,
            house_description=description,
            house_photo_urls=gallery,
            rooms=rooms,
            bathrooms=bathrooms,
            square_meters=sqm,
            neighborhood=neighborhood,
            move_in_date=move_in_date,
            lease_months=lease_months,
            utilities_included=utilities_included,
            furnished=furnished,
        )


@dataclass
class Filters:
    max_budget: int = 2000
    smoker_pref: str = "any"          # "any" | "no smokers" | "smokers only"
    schedule_pref: str = "any"        # "any" | one of SCHEDULES
    pets_pref: str = "any"            # "any" | "has pets" | "no pets"
    cleanliness_pref: str = "any"     # "any" | one of CLEANLINESS_LEVELS
    neighborhood_pref: str = "any"    # "any" | name from NEIGHBORHOODS

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


# --- stock photo helpers -------------------------------------------

# Curated Unsplash photo IDs of apartment / interior shots. Picsum returns
# mostly landscapes, which didn't fit a roommate app, so we use this list
# instead. All images are CC0.
_INTERIOR_PHOTO_IDS = [
    "photo-1522708323590-d24dbb6b0267",
    "photo-1560448204-e02f11c3d0e2",
    "photo-1502672260266-1c1ef2d93688",
    "photo-1484154218962-a197022b5858",
    "photo-1493663284031-b7e3aefcae8e",
    "photo-1586023492125-27b2c045efd7",
    "photo-1556909114-f6e7ad7d3136",
    "photo-1505693416388-ac5ce068fe85",
    "photo-1555854877-bab0e564b8d5",
    "photo-1513584684374-8bab748fbf90",
    "photo-1540518614846-7eded433c457",
    "photo-1524758631624-e2822e304c36",
    "photo-1598928506311-c55ded91a20c",
    "photo-1586105251261-72a756497a11",
    "photo-1521783988139-893ce4f7ed71",
    "photo-1534595038511-9f219fe0c979",
]


def avatar_url(seed):
    """Deterministic 500x500 avatar URL from a seed (UUID or username)."""
    return "https://i.pravatar.cc/500?u=" + seed


def _unsplash_url(photo_id):
    return (
        "https://images.unsplash.com/" + photo_id
        + "?w=600&h=400&fit=crop&auto=format"
    )


def house_photo_url(seed):
    """A single interior photo, deterministic per seed."""
    rng = random.Random(seed)
    return _unsplash_url(rng.choice(_INTERIOR_PHOTO_IDS))


def house_photo_gallery(seed, n=4):
    """A list of n different interior photos, deterministic per seed.

    Using random.Random(seed) instead of hash arithmetic keeps the shape of
    the code closer to what the course teaches (the random module).
    """
    rng = random.Random(seed)
    return [_unsplash_url(pid) for pid in rng.sample(_INTERIOR_PHOTO_IDS, n)]


def compatibility(me, other):
    """A 0-100 score estimating how well ``other`` fits ``me``.

    Lifestyle matches (smoker, schedule, pets, cleanliness) are treated the
    same regardless of role. Price uses each side's effective_price().
    """
    # Price fit. 30%.
    diff = abs(me.effective_price() - other.effective_price())
    if diff < 100:
        price_s = 100
    elif diff < 300:
        price_s = 70
    else:
        price_s = 30

    # Schedule. 25%.
    if me.schedule == other.schedule:
        sched_s = 100
    elif "flexible" in (me.schedule, other.schedule):
        sched_s = 70
    else:
        sched_s = 25

    # Smoking agreement. 20%.
    smok_s = 100 if me.smoker == other.smoker else 15

    # Cleanliness. 15%. Penalise by level gap.
    levels = {"very tidy": 2, "tidy": 1, "relaxed": 0}
    lev_diff = abs(
        levels.get(me.cleanliness, 1) - levels.get(other.cleanliness, 1)
    )
    if lev_diff == 0:
        clean_s = 100
    elif lev_diff == 1:
        clean_s = 70
    else:
        clean_s = 30

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


# --- seed text ------------------------------------------------------

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
