"""Profile and Filters data classes."""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict, field


SCHEDULES = ["early bird", "night owl", "flexible"]
CLEANLINESS_LEVELS = ["very tidy", "tidy", "relaxed"]


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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        # Tolerate older saved profiles that predate pets/cleanliness.
        return cls(
            id=d["id"],
            name=d["name"],
            age=d["age"],
            photo_url=d.get("photo_url", ""),
            email=d.get("email", ""),
            budget=d["budget"],
            smoker=d["smoker"],
            schedule=d["schedule"],
            bio=d.get("bio", ""),
            pets=d.get("pets", False),
            cleanliness=d.get("cleanliness", "tidy"),
        )

    @classmethod
    def from_randomuser(cls, d: dict) -> "Profile":
        name = f"{d['name']['first']} {d['name']['last']}"
        uid = d["login"]["uuid"]
        # randomuser.me "large" photos are 128x128 and look soft when upscaled.
        # pravatar.cc serves deterministic 500x500 avatars seeded on the UUID.
        return cls(
            id=uid,
            name=name,
            age=int(d["dob"]["age"]),
            photo_url=avatar_url(uid),
            email=d["email"],
            budget=random.choice([350, 400, 450, 500, 550, 600, 700, 800, 900]),
            smoker=random.random() < 0.3,
            schedule=random.choice(SCHEDULES),
            bio=random.choice(BIOS),
            pets=random.random() < 0.35,
            cleanliness=random.choice(CLEANLINESS_LEVELS),
        )


def avatar_url(seed: str) -> str:
    """Deterministic 500x500 avatar URL from a seed (UUID or username)."""
    return f"https://i.pravatar.cc/500?u={seed}"


def compatibility(me: Profile, other: Profile) -> int:
    """Return a 0-100 score estimating how well ``other`` fits ``me``.

    Weights roughly reflect what roommates most commonly argue about: money,
    schedule, smoking, cleanliness, pets.
    """
    # Budget: closer monthly budgets, higher score. 30% weight.
    diff = abs(me.budget - other.budget)
    budget_s = 100 if diff < 100 else 70 if diff < 300 else 30

    # Schedule compatibility. 25%.
    if me.schedule == other.schedule:
        sched_s = 100
    elif "flexible" in (me.schedule, other.schedule):
        sched_s = 70
    else:
        sched_s = 25  # early bird + night owl = probably rough

    # Smoking agreement. 20%.
    smok_s = 100 if me.smoker == other.smoker else 15

    # Cleanliness. 15%. Penalise by level gap.
    levels = {"very tidy": 2, "tidy": 1, "relaxed": 0}
    lev_diff = abs(
        levels.get(me.cleanliness, 1) - levels.get(other.cleanliness, 1)
    )
    clean_s = {0: 100, 1: 70, 2: 30}.get(lev_diff, 30)

    # Pets. 10%.
    pets_s = 100 if me.pets == other.pets else 55

    total = (
        budget_s * 0.30
        + sched_s * 0.25
        + smok_s * 0.20
        + clean_s * 0.15
        + pets_s * 0.10
    )
    return int(round(total))

    def matches_filters(self, f: "Filters") -> bool:
        if self.budget > f.max_budget:
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
