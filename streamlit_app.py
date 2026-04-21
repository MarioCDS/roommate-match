"""NOVA Roomie: Streamlit web version.

Run locally:
    streamlit run streamlit_app.py

Deploy to Streamlit Community Cloud:
    1. Push this project to GitHub.
    2. Go to https://share.streamlit.io, click \u201cNew app\u201d.
    3. Point it at this repo and streamlit_app.py as the entry point.

Note: Streamlit Cloud's filesystem is ephemeral, so user data and matches persist
only while the server is warm. For an MVP demo this is fine; for production
you'd swap storage.py for a real database.
"""
from __future__ import annotations

import uuid

import requests
import streamlit as st

from api import fetch_candidates
from auth import authenticate, create_user, validate_new_credentials
from models import Profile, Filters, SCHEDULES, CLEANLINESS_LEVELS, avatar_url, compatibility
from storage import (
    load_json, save_json,
    CANDIDATES_FILE,
    profile_file, matches_file, filters_file,
)

SMOKER_OPTS = ["any", "no smokers", "smokers only"]
SCHEDULE_OPTS = ["any"] + SCHEDULES
PETS_OPTS = ["any", "has pets", "no pets"]
CLEANLINESS_OPTS = ["any"] + CLEANLINESS_LEVELS

st.set_page_config(
    page_title="NOVA Roomie",
    page_icon="\U0001f3e0",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* No hardcoded page background or text colour, so Streamlit's
       light/dark theme toggle (top-right menu) works naturally. */
    .stButton > button { width: 100%; }
    /* Tab labels must stay readable in both themes. Inherit the base
       text colour and distinguish the active tab by brand color. */
    .stTabs [role="tab"] {
        color: inherit !important;
        opacity: 0.7;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: #4F46E5 !important;
        opacity: 1;
    }
    .stTabs [role="tab"]:hover { opacity: 1; }
    .roomie-brand {
        color: #4F46E5;
        font-size: 2.4rem;
        font-weight: 800;
        text-align: center;
        margin: 0.5rem 0 0.2rem 0;
        letter-spacing: -0.02em;
    }
    .roomie-subtitle {
        opacity: 0.7;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .nav-bar {
        background: #4F46E5;
        color: #FFFFFF;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
    }
    .nav-bar b { font-size: 1.1rem; color: #FFFFFF; }
    .nav-bar .who { color: #C7D2FE; font-style: italic; }
    .match-title {
        color: #4F46E5;
        font-size: 2rem;
        font-weight: 800;
        text-align: center;
        margin: 0.25rem 0 0.5rem 0;
    }
    .match-sub {
        opacity: 0.75;
        text-align: center;
        margin-bottom: 1rem;
    }
    .slot-caption {
        text-align: center;
        font-weight: 600;
        margin-top: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------
# Session state helpers
# --------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "view": "auth",
        "current_user": None,
        "my_profile": None,
        "matches": [],
        "filters": Filters(),
        "candidates": None,
        "queue": None,
        "queue_index": 0,
        "show_match": False,          # open match modal on next render
        "matched_profile": None,      # candidate to show in the modal
        "last_action": None,          # ("like" | "pass", Profile) for undo
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def go(view: str) -> None:
    st.session_state.view = view
    st.rerun()


def load_candidates() -> list[Profile]:
    if st.session_state.candidates is not None:
        return st.session_state.candidates
    cached = load_json(CANDIDATES_FILE, [])
    if cached:
        profiles = [Profile.from_dict(c) for c in cached]
    else:
        try:
            profiles = fetch_candidates(30)
            save_json(CANDIDATES_FILE, [p.to_dict() for p in profiles])
        except requests.RequestException as e:
            st.error(f"Could not reach randomuser.me: {e}")
            profiles = []
    st.session_state.candidates = profiles
    return profiles


def build_queue() -> list[Profile]:
    candidates = load_candidates()
    matched_ids = {m.id for m in st.session_state.matches}
    queue = [
        c for c in candidates
        if c.id not in matched_ids and c.matches_filters(st.session_state.filters)
    ]
    # Best matches first, using the compatibility score.
    me = st.session_state.my_profile
    if me is not None:
        queue.sort(key=lambda c: compatibility(me, c), reverse=True)
    st.session_state.queue = queue
    st.session_state.queue_index = 0
    return queue


# --------------------------------------------------------------------
# Auth flow
# --------------------------------------------------------------------

def login(username: str) -> None:
    st.session_state.current_user = username
    my = load_json(profile_file(username), None)
    st.session_state.my_profile = Profile.from_dict(my) if my else None
    ms = load_json(matches_file(username), [])
    st.session_state.matches = [Profile.from_dict(m) for m in ms]
    f = load_json(filters_file(username), None)
    st.session_state.filters = Filters.from_dict(f) if f else Filters()
    st.session_state.queue = None
    st.session_state.queue_index = 0
    go("setup" if st.session_state.my_profile is None else "swipe")


def signup_and_login(username: str) -> None:
    st.session_state.current_user = username
    st.session_state.my_profile = None
    st.session_state.matches = []
    st.session_state.filters = Filters()
    st.session_state.queue = None
    st.session_state.queue_index = 0
    go("setup")


def logout() -> None:
    st.session_state.current_user = None
    st.session_state.my_profile = None
    st.session_state.matches = []
    st.session_state.filters = Filters()
    st.session_state.queue = None
    st.session_state.queue_index = 0
    go("auth")


# --------------------------------------------------------------------
# User-scoped state mutations
# --------------------------------------------------------------------

def save_my_profile(profile: Profile) -> None:
    u = st.session_state.current_user
    st.session_state.my_profile = profile
    save_json(profile_file(u), profile.to_dict())


def add_match(profile: Profile) -> None:
    u = st.session_state.current_user
    if not any(m.id == profile.id for m in st.session_state.matches):
        st.session_state.matches.append(profile)
        save_json(matches_file(u), [m.to_dict() for m in st.session_state.matches])
        st.session_state.show_match = True
        st.session_state.matched_profile = profile


def remove_match(profile: Profile) -> None:
    u = st.session_state.current_user
    st.session_state.matches = [
        m for m in st.session_state.matches if m.id != profile.id
    ]
    save_json(matches_file(u), [m.to_dict() for m in st.session_state.matches])


def save_filters(f: Filters) -> None:
    u = st.session_state.current_user
    st.session_state.filters = f
    save_json(filters_file(u), f.to_dict())
    st.session_state.queue = None
    st.session_state.queue_index = 0


# --------------------------------------------------------------------
# Views
# --------------------------------------------------------------------

def render_nav() -> None:
    if not st.session_state.current_user:
        return
    st.markdown(
        f"<div class='nav-bar'>"
        f"<span><b>\U0001f3e0 NOVA Roomie</b></span>"
        f"<span class='who'>@{st.session_state.current_user}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(5)
    labels_cmds = [
        ("Swipe", lambda: go("swipe")),
        ("Matches", lambda: go("matches")),
        ("Filters", lambda: go("filters")),
        ("Profile", lambda: go("setup")),
        ("Log out", logout),
    ]
    for col, (label, cmd) in zip(cols, labels_cmds):
        if col.button(label, key=f"nav_{label}"):
            cmd()
    st.markdown("---")


def view_auth() -> None:
    st.markdown("<div class='roomie-brand'>\U0001f3e0 NOVA Roomie</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='roomie-subtitle'>Find a roommate who fits your vibe.</div>",
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            username = u.strip()
            if not username or not p:
                st.error("Enter a username and password.")
            elif not authenticate(username, p):
                st.error("Incorrect username or password.")
            else:
                login(username)

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            u = st.text_input("Username", key="signup_u")
            p = st.text_input("Password", type="password", key="signup_p")
            c = st.text_input("Confirm password", type="password", key="signup_c")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            username = u.strip()
            msg = validate_new_credentials(username, p, c)
            if msg:
                st.error(msg)
            elif not create_user(username, p):
                st.error("That username is already taken.")
            else:
                signup_and_login(username)


def view_setup() -> None:
    existing = st.session_state.my_profile
    st.title("Your profile" if existing else "Welcome! Create your profile")
    st.caption("This info is shown to other roommates when they swipe on you.")

    with st.form("setup_form"):
        name = st.text_input("Name", value=existing.name if existing else "")
        col_age, col_email = st.columns([1, 2])
        with col_age:
            age = st.number_input(
                "Age", min_value=16, max_value=100,
                value=existing.age if existing else 22, step=1,
            )
        with col_email:
            email = st.text_input("Email", value=existing.email if existing else "")

        budget = st.slider(
            "Budget (\u20ac/month)", 200, 1500,
            value=existing.budget if existing else 500, step=25,
        )

        col_sched, col_clean = st.columns(2)
        with col_sched:
            schedule = st.selectbox(
                "Schedule", SCHEDULES,
                index=SCHEDULES.index(existing.schedule) if existing else 2,
            )
        with col_clean:
            cleanliness = st.selectbox(
                "Cleanliness", CLEANLINESS_LEVELS,
                index=(CLEANLINESS_LEVELS.index(existing.cleanliness)
                       if existing else 1),
            )

        col_smoker, col_pets = st.columns(2)
        with col_smoker:
            smoker = st.checkbox("I smoke", value=existing.smoker if existing else False)
        with col_pets:
            pets = st.checkbox("I have pets", value=existing.pets if existing else False)

        bio = st.text_area(
            "Bio",
            value=existing.bio if existing else "",
            height=160,
            placeholder="Tell potential roommates a bit about yourself: daily routine, habits, what you're looking for\u2026",
        )

        submitted = st.form_submit_button(
            "Save and continue" if existing is None else "Save",
            use_container_width=True,
        )

    if submitted:
        if not name.strip():
            st.error("Please enter your name.")
            return
        pid = existing.id if existing else str(uuid.uuid4())
        photo = existing.photo_url if existing and existing.photo_url else avatar_url(pid)
        p = Profile(
            id=pid,
            name=name.strip(),
            age=int(age),
            photo_url=photo,
            email=email.strip(),
            budget=int(budget),
            smoker=bool(smoker),
            schedule=schedule,
            bio=bio.strip() or "(no bio)",
            pets=bool(pets),
            cleanliness=cleanliness,
        )
        save_my_profile(p)
        go("filters" if existing is None else "swipe")


def view_filters() -> None:
    st.title("Your preferences")
    st.caption("Filter candidates before you swipe. Leave as \u201cany\u201d to see everyone.")
    f = st.session_state.filters

    with st.form("filters_form"):
        max_budget = st.slider(
            "Max budget (\u20ac/month)", 200, 2000, f.max_budget, step=25,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            smoker_pref = st.selectbox(
                "Smoker preference", SMOKER_OPTS,
                index=SMOKER_OPTS.index(f.smoker_pref),
            )
        with col_b:
            pets_pref = st.selectbox(
                "Pet preference", PETS_OPTS,
                index=PETS_OPTS.index(f.pets_pref),
            )

        col_c, col_d = st.columns(2)
        with col_c:
            schedule_pref = st.selectbox(
                "Schedule preference", SCHEDULE_OPTS,
                index=SCHEDULE_OPTS.index(f.schedule_pref),
            )
        with col_d:
            cleanliness_pref = st.selectbox(
                "Cleanliness preference", CLEANLINESS_OPTS,
                index=CLEANLINESS_OPTS.index(f.cleanliness_pref),
            )

        submitted = st.form_submit_button("Start swiping", use_container_width=True)

    if submitted:
        save_filters(Filters(
            max_budget=int(max_budget),
            smoker_pref=smoker_pref,
            schedule_pref=schedule_pref,
            pets_pref=pets_pref,
            cleanliness_pref=cleanliness_pref,
        ))
        go("swipe")


def view_swipe() -> None:
    st.title("Swipe")

    # Trigger the match dialog when add_match() has queued one. Clear the flag
    # immediately so the modal only opens once per match.
    if st.session_state.show_match and st.session_state.matched_profile is not None:
        st.session_state.show_match = False
        _show_match_dialog(st.session_state.my_profile, st.session_state.matched_profile)
        st.session_state.matched_profile = None

    if st.session_state.queue is None:
        with st.spinner("Loading candidates from randomuser.me\u2026"):
            build_queue()

    queue = st.session_state.queue or []
    idx = st.session_state.queue_index

    if not queue or idx >= len(queue):
        st.info("No more candidates. Try adjusting your filters or refreshing the pool.")
        col_a, col_b = st.columns(2)
        if col_a.button("\U0001f504 Refresh candidates", use_container_width=True):
            try:
                profiles = fetch_candidates(30)
                save_json(CANDIDATES_FILE, [p.to_dict() for p in profiles])
                st.session_state.candidates = profiles
                build_queue()
                st.rerun()
            except requests.RequestException as e:
                st.error(f"Network error: {e}")
        if col_b.button("Edit filters", use_container_width=True):
            go("filters")
        return

    p = queue[idx]
    me = st.session_state.my_profile
    score = compatibility(me, p) if me else None

    with st.container(border=True):
        if p.photo_url:
            left, mid, right = st.columns([1, 2, 1])
            with mid:
                st.image(p.photo_url, use_container_width=True)

        head_cols = st.columns([3, 1])
        head_cols[0].subheader(f"{p.name}, {p.age}")
        if score is not None:
            head_cols[1].markdown(
                f"<div style='text-align:right;color:#4F46E5;"
                f"font-weight:700;font-size:1.15rem;padding-top:0.5rem'>"
                f"{score}% match</div>",
                unsafe_allow_html=True,
            )

        smoker_txt = "smoker" if p.smoker else "non-smoker"
        pets_txt = "has pets" if p.pets else "no pets"
        st.caption(
            f"\u20ac{p.budget}/month  \u2022  {p.schedule}  \u2022  {p.cleanliness}  \u2022  "
            f"{smoker_txt}  \u2022  {pets_txt}"
        )
        st.write(p.bio)

    col_pass, col_undo, col_like = st.columns([1, 1, 1])
    if col_pass.button("Pass", key=f"pass_{p.id}", use_container_width=True):
        st.session_state.last_action = ("pass", p)
        st.session_state.queue_index += 1
        st.rerun()
    undo_disabled = st.session_state.last_action is None or idx == 0
    if col_undo.button("Undo", key=f"undo_{p.id}", use_container_width=True,
                       disabled=undo_disabled):
        kind, prev = st.session_state.last_action
        if kind == "like":
            remove_match(prev)
        st.session_state.last_action = None
        st.session_state.queue_index = max(0, idx - 1)
        st.rerun()
    if col_like.button("Like", key=f"like_{p.id}", type="primary",
                       use_container_width=True):
        add_match(p)
        st.session_state.last_action = ("like", p)
        st.session_state.queue_index += 1
        st.rerun()


def view_matches() -> None:
    matches = st.session_state.matches
    me = st.session_state.my_profile
    st.title(f"Your matches ({len(matches)})")
    if not matches:
        st.info("No matches yet. Head to Swipe and like some profiles!")
        if st.button("Go to Swipe", type="primary"):
            go("swipe")
        return

    sort_by = st.selectbox(
        "Sort by",
        ["Most recent", "Compatibility", "Budget (low to high)", "Name", "Age"],
        index=0,
    )

    sorted_matches = list(matches)
    if sort_by == "Most recent":
        sorted_matches = list(reversed(sorted_matches))
    elif sort_by == "Compatibility" and me is not None:
        sorted_matches.sort(key=lambda m: compatibility(me, m), reverse=True)
    elif sort_by == "Budget (low to high)":
        sorted_matches.sort(key=lambda m: m.budget)
    elif sort_by == "Name":
        sorted_matches.sort(key=lambda m: m.name.lower())
    elif sort_by == "Age":
        sorted_matches.sort(key=lambda m: m.age)

    for m in sorted_matches:
        score = compatibility(me, m) if me else None
        with st.container(border=True):
            cols = st.columns([1, 3])
            with cols[0]:
                if m.photo_url:
                    st.image(m.photo_url, width=80)
            with cols[1]:
                title = f"**{m.name}, {m.age}**"
                if score is not None:
                    title += (
                        f" <span style='color:#4F46E5;font-weight:600'>"
                        f"\u2022 {score}% match</span>"
                    )
                st.markdown(title, unsafe_allow_html=True)
                smoker_txt = "smoker" if m.smoker else "non-smoker"
                pets_txt = "has pets" if m.pets else "no pets"
                st.caption(
                    f"\u20ac{m.budget}/month  \u2022  {m.schedule}  \u2022  "
                    f"{m.cleanliness}  \u2022  {smoker_txt}  \u2022  {pets_txt}"
                )
                st.markdown(f"\U0001f4e7 `{m.email}`")


@st.dialog("It's a Match!")
def _show_match_dialog(my: Profile | None, other: Profile) -> None:
    other_first = other.name.split()[0] if other.name else "them"
    st.markdown(
        f"<div class='match-sub'>You and <b>{other_first}</b> could make "
        "great roommates.</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    with cols[0]:
        if my and my.photo_url:
            st.image(my.photo_url, use_container_width=True)
        my_first = my.name.split()[0] if (my and my.name) else "You"
        st.markdown(f"<div class='slot-caption'>{my_first}</div>",
                    unsafe_allow_html=True)
    with cols[1]:
        if other.photo_url:
            st.image(other.photo_url, use_container_width=True)
        st.markdown(f"<div class='slot-caption'>{other_first}</div>",
                    unsafe_allow_html=True)
    st.write("")
    if st.button("Keep swiping", type="primary", use_container_width=True):
        st.rerun()


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------

init_state()
render_nav()

VIEWS = {
    "auth": view_auth,
    "setup": view_setup,
    "filters": view_filters,
    "swipe": view_swipe,
    "matches": view_matches,
}
VIEWS[st.session_state.view]()
