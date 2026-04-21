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
from chat import append_message, load_chat, maybe_canned_reply
from models import (
    Profile, Filters, SCHEDULES, CLEANLINESS_LEVELS,
    avatar_url, house_photo_gallery, compatibility,
)
from storage import (
    load_json, save_json,
    CANDIDATES_FILE,
    profile_file, matches_file, filters_file, avatar_path, house_photo_path,
)

MAX_HOUSE_PHOTOS = 6

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
        "gallery_idx": 0,             # photo index within the current listing
        "chat_peer": None,            # Profile we're currently chatting with
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
    profiles = [Profile.from_dict(c) for c in cached] if cached else []
    # A cache built before we added roles would default every candidate to
    # "roomie", leaving roomies with an empty queue. Re-fetch in that case.
    if profiles:
        roles = {p.role for p in profiles}
        stale = (
            "host" not in roles
            or "roomie" not in roles
            or any(
                "picsum.photos" in u
                for p in profiles
                for u in p.house_photo_urls
            )
        )
        if stale:
            profiles = []
    if not profiles:
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
    me = st.session_state.my_profile
    target = "host" if (me and me.role == "roomie") else "roomie"
    queue = [
        c for c in candidates
        if c.role == target
        and c.id not in matched_ids
        and c.matches_filters(st.session_state.filters)
    ]
    # Best matches first, using the compatibility score.
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
    st.caption("This info is shown to other people when they swipe on you.")

    # Role radio is OUTSIDE the form so we can switch the form fields
    # on the fly without the user needing to submit first.
    role = st.radio(
        "I'm a:",
        options=["roomie", "host"],
        format_func=lambda r: (
            "Roomie - looking for a place" if r == "roomie"
            else "Host - have a place to offer"
        ),
        index=(0 if (not existing or existing.role == "roomie") else 1),
        horizontal=True,
    )

    # Profile photo preview + uploader (outside the form so the preview
    # can update immediately when a new file is picked).
    st.markdown("**Profile photo**")
    preview_col, upload_col = st.columns([1, 3])
    with preview_col:
        current_photo = existing.photo_url if existing and existing.photo_url else None
        if current_photo:
            try:
                st.image(current_photo, width=96)
            except Exception:
                st.image(avatar_url(existing.id if existing else "preview"), width=96)
        else:
            st.image(avatar_url("preview"), width=96)
    with upload_col:
        uploaded = st.file_uploader(
            "Upload a square-ish photo (jpg/png)",
            type=["jpg", "jpeg", "png"],
            key="avatar_uploader",
        )
        use_default = st.checkbox(
            "Use an auto-generated avatar instead",
            value=not (existing and existing.photo_url
                       and not str(existing.photo_url).startswith(("http://", "https://"))),
            help="Tick this if you'd rather let the app pick a stock avatar.",
        )

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

        # Role-specific fields.
        if role == "host":
            rent = st.slider(
                "Monthly rent you charge (\u20ac)", 200, 2000,
                value=(existing.rent if existing and existing.rent else 500),
                step=25,
            )
            spec_cols = st.columns(3)
            with spec_cols[0]:
                rooms = st.number_input(
                    "Bedrooms", min_value=1, max_value=8, step=1,
                    value=(existing.rooms if existing and existing.rooms else 2),
                )
            with spec_cols[1]:
                bathrooms = st.number_input(
                    "Bathrooms", min_value=1, max_value=5, step=1,
                    value=(existing.bathrooms
                           if existing and existing.bathrooms else 1),
                )
            with spec_cols[2]:
                square_meters = st.number_input(
                    "Size (m\u00b2)", min_value=15, max_value=500, step=5,
                    value=(existing.square_meters
                           if existing and existing.square_meters else 60),
                )
            house_description = st.text_area(
                "About the place",
                value=existing.house_description if existing else "",
                height=140,
                placeholder="Describe the apartment: neighborhood, amenities, vibe.",
            )
            house_photos = st.file_uploader(
                f"Photos of the place (up to {MAX_HOUSE_PHOTOS})",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="house_uploader",
                help="Leave empty to keep existing photos (or get stock photos on first save).",
            )
            # Show what's currently attached so the host can see what viewers see.
            if existing and existing.house_photo_urls:
                st.caption("Currently attached:")
                thumb_cols = st.columns(min(4, len(existing.house_photo_urls)))
                for i, url in enumerate(existing.house_photo_urls[:4]):
                    with thumb_cols[i % len(thumb_cols)]:
                        try:
                            st.image(url, use_container_width=True)
                        except Exception:
                            st.caption("(preview unavailable)")
            budget = rent
        else:
            budget = st.slider(
                "Your budget (\u20ac/month)", 200, 1500,
                value=existing.budget if existing else 500, step=25,
            )
            rent = 0
            rooms = 0
            bathrooms = 0
            square_meters = 0
            house_description = ""
            house_photos = None

        bio = st.text_area(
            "Bio",
            value=existing.bio if existing else "",
            height=140,
            placeholder="Tell others a bit about yourself: routine, habits, what you\u2019re looking for.",
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

        # Resolve the profile photo URL: a fresh upload > existing value >
        # auto-generated pravatar.
        if uploaded is not None and not use_default:
            photo = _save_uploaded_avatar(
                uploaded, st.session_state.current_user,
            ) or avatar_url(pid)
        elif use_default:
            photo = avatar_url(pid)
        else:
            photo = (
                existing.photo_url if existing and existing.photo_url
                else avatar_url(pid)
            )

        if role == "host":
            if house_photos:
                saved = _save_uploaded_house_photos(
                    house_photos, st.session_state.current_user,
                )
                gallery = saved or (
                    list(existing.house_photo_urls)
                    if existing and existing.house_photo_urls
                    else house_photo_gallery(pid)
                )
            elif existing and existing.house_photo_urls:
                gallery = list(existing.house_photo_urls)
            else:
                gallery = house_photo_gallery(pid)
            hdesc = house_description.strip() or "Comfortable place."
        else:
            gallery = []
            hdesc = ""
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
            role=role,
            rent=int(rent),
            house_description=hdesc,
            house_photo_urls=gallery,
            rooms=int(rooms),
            bathrooms=int(bathrooms),
            square_meters=int(square_meters),
        )
        save_my_profile(p)
        go("filters" if existing is None else "swipe")


def _save_uploaded_house_photos(files, username: str) -> list[str]:
    """Crop to 3:2, resize to 600x400, and save each uploaded file.

    Returns the list of on-disk paths (strings). Silently skips files that
    Pillow can't open.
    """
    if not username or not files:
        return []
    try:
        from PIL import Image as _PILImage
    except ImportError:
        return []

    saved: list[str] = []
    for i, uploaded in enumerate(files[:MAX_HOUSE_PHOTOS]):
        try:
            img = _PILImage.open(uploaded).convert("RGB")
        except Exception:
            continue
        w, h = img.size
        target_ratio = 600 / 400
        ratio = w / h
        if ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
        img = img.resize((600, 400))
        dest = house_photo_path(username, i)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="JPEG", quality=88)
        saved.append(str(dest))
    return saved


def _save_uploaded_avatar(uploaded, username: str) -> str | None:
    """Resize the uploaded image to a 500x500 square and save it to disk.

    Returns the resulting path on success, otherwise None.
    """
    if not username:
        return None
    try:
        from PIL import Image as _PILImage
        img = _PILImage.open(uploaded).convert("RGB")
    except Exception:
        return None
    w, h = img.size
    side = min(w, h)
    img = img.crop(
        ((w - side) // 2, (h - side) // 2,
         (w + side) // 2, (h + side) // 2),
    ).resize((500, 500))
    dest = avatar_path(username)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="JPEG", quality=90)
    return str(dest)


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
    is_host = p.role == "host"

    # Reset the photo gallery index when we move to a different candidate.
    if st.session_state.get("gallery_for") != p.id:
        st.session_state.gallery_idx = 0
        st.session_state.gallery_for = p.id

    badge = "HOST LISTING" if is_host else "LOOKING FOR A PLACE"
    st.markdown(
        f"<div style='display:inline-block;background:#4F46E5;color:white;"
        f"padding:2px 10px;border-radius:6px;font-size:0.8rem;"
        f"font-weight:700;margin-bottom:6px'>{badge}</div>",
        unsafe_allow_html=True,
    )

    description = p.house_description if is_host else p.bio
    price_txt = (
        f"\u20ac{p.rent}/month rent" if is_host else f"\u20ac{p.budget}/month budget"
    )

    with st.container(border=True):
        if is_host and p.house_photo_urls:
            n = len(p.house_photo_urls)
            gi = st.session_state.gallery_idx % n
            st.image(p.house_photo_urls[gi], use_container_width=True)
            if n > 1:
                nav_cols = st.columns([1, 2, 1])
                with nav_cols[0]:
                    if st.button("\u25c0", key=f"gprev_{p.id}",
                                 use_container_width=True):
                        st.session_state.gallery_idx = (gi - 1) % n
                        st.rerun()
                with nav_cols[1]:
                    st.markdown(
                        f"<div style='text-align:center;opacity:0.7;"
                        f"padding-top:0.3rem'>{gi + 1} / {n}</div>",
                        unsafe_allow_html=True,
                    )
                with nav_cols[2]:
                    if st.button("\u25b6", key=f"gnext_{p.id}",
                                 use_container_width=True):
                        st.session_state.gallery_idx = (gi + 1) % n
                        st.rerun()
        elif p.photo_url:
            left, mid, right = st.columns([1, 2, 1])
            with mid:
                st.image(p.photo_url, use_container_width=True)

        # Host cards show a small portrait next to the name so the roomie
        # sees who's behind the listing.
        if is_host and p.photo_url:
            head_cols = st.columns([1, 4, 2])
            with head_cols[0]:
                try:
                    st.image(p.photo_url, width=58)
                except Exception:
                    pass
            head_cols[1].subheader(f"{p.name}, {p.age}")
            score_col = head_cols[2]
        else:
            head_cols = st.columns([3, 1])
            head_cols[0].subheader(f"{p.name}, {p.age}")
            score_col = head_cols[1]
        if score is not None:
            score_col.markdown(
                f"<div style='text-align:right;color:#4F46E5;"
                f"font-weight:700;font-size:1.15rem;padding-top:0.5rem'>"
                f"{score}% match</div>",
                unsafe_allow_html=True,
            )

        # Property specs line (hosts only).
        if is_host and (p.rooms or p.bathrooms or p.square_meters):
            specs = []
            if p.rooms:
                specs.append(f"{p.rooms} bed")
            if p.bathrooms:
                specs.append(f"{p.bathrooms} bath")
            if p.square_meters:
                specs.append(f"{p.square_meters} m\u00b2")
            st.caption("  \u2022  ".join(specs))

        smoker_txt = "smoker" if p.smoker else "non-smoker"
        pets_txt = "pets ok" if p.pets else "no pets"
        st.caption(
            f"{price_txt}  \u2022  {p.schedule}  \u2022  {p.cleanliness}  \u2022  "
            f"{smoker_txt}  \u2022  {pets_txt}"
        )
        st.write(description)

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

    # Always-visible refresh so stale caches can be blown away without
    # needing to reach the empty state first.
    with st.expander("Pool options"):
        if st.button("Refresh candidates from randomuser.me",
                     key="swipe_refresh", use_container_width=True):
            try:
                profiles = fetch_candidates(30)
                save_json(CANDIDATES_FILE, [p.to_dict() for p in profiles])
                st.session_state.candidates = profiles
                build_queue()
                st.rerun()
            except requests.RequestException as e:
                st.error(f"Network error: {e}")


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
        sorted_matches.sort(key=lambda m: m.effective_price)
    elif sort_by == "Name":
        sorted_matches.sort(key=lambda m: m.name.lower())
    elif sort_by == "Age":
        sorted_matches.sort(key=lambda m: m.age)

    for m in sorted_matches:
        score = compatibility(me, m) if me else None
        with st.container(border=True):
            cols = st.columns([1, 3, 1])
            with cols[0]:
                # Always show the person photo in the matches list so names
                # and faces line up; the house photo shows on the swipe card.
                if m.photo_url:
                    try:
                        st.image(m.photo_url, width=80)
                    except Exception:
                        pass
            with cols[1]:
                role_tag = "Host" if m.role == "host" else "Roomie"
                price_txt = (
                    f"\u20ac{m.rent}/mo rent" if m.role == "host"
                    else f"\u20ac{m.budget}/mo budget"
                )
                title = f"**{m.name}, {m.age}**"
                if score is not None:
                    title += (
                        f" <span style='color:#4F46E5;font-weight:600'>"
                        f"\u2022 {score}% match</span>"
                    )
                st.markdown(title, unsafe_allow_html=True)
                smoker_txt = "smoker" if m.smoker else "non-smoker"
                pets_txt = "pets ok" if m.pets else "no pets"
                st.caption(
                    f"{role_tag}  \u00b7  {price_txt}  \u2022  {m.schedule}  \u2022  "
                    f"{m.cleanliness}  \u2022  {smoker_txt}  \u2022  {pets_txt}"
                )
                st.markdown(f"\U0001f4e7 `{m.email}`")
            with cols[2]:
                # Chat opener with a small message-count hint.
                peer_msgs = load_chat(st.session_state.current_user, m.id)
                label = f"Chat ({len(peer_msgs)})" if peer_msgs else "Chat"
                if st.button(label, key=f"chat_open_{m.id}",
                             use_container_width=True):
                    st.session_state.chat_peer = m
                    go("chat")


def view_chat() -> None:
    peer = st.session_state.chat_peer
    me_user = st.session_state.current_user
    if peer is None or not me_user:
        go("matches")
        return

    top = st.columns([1, 5])
    with top[0]:
        if st.button("\u2190 Back", use_container_width=True):
            st.session_state.chat_peer = None
            go("matches")
    with top[1]:
        head = st.columns([1, 5])
        with head[0]:
            if peer.photo_url:
                try:
                    st.image(peer.photo_url, width=56)
                except Exception:
                    pass
        with head[1]:
            st.subheader(f"Chat with {peer.name.split()[0]}")
            role_tag = "Host" if peer.role == "host" else "Roomie"
            st.caption(
                f"{role_tag}  \u00b7  "
                + (
                    f"\u20ac{peer.rent}/mo rent"
                    if peer.role == "host" else f"\u20ac{peer.budget}/mo budget"
                )
            )

    st.markdown("---")
    messages = load_chat(me_user, peer.id)
    if not messages:
        st.caption(
            "Say hi to kick things off. Replies are canned responses for demo "
            "purposes."
        )

    for m in messages:
        role = "user" if m["from"] == "me" else "assistant"
        avatar = None
        if m["from"] == "them" and peer.photo_url:
            avatar = peer.photo_url
        with st.chat_message(role, avatar=avatar):
            st.write(m["text"])

    prompt = st.chat_input("Type a message\u2026")
    if prompt:
        text = prompt.strip()
        if text:
            append_message(me_user, peer.id, "me", text)
            reply = maybe_canned_reply()
            if reply is not None:
                append_message(me_user, peer.id, "them", reply)
            st.rerun()


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
    "chat": view_chat,
}
VIEWS[st.session_state.view]()
