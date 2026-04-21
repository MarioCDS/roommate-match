# NOVA Roomie

A web app for NOVA's Introduction to Programming group project. Two-sided
roommate marketplace with a Tinder-style swipe flow:

- **Roomies** look for a place. They swipe on host listings.
- **Hosts** have a place to offer. They swipe on roomie profiles.

Every right-swipe is treated as a match. Matches have a per-pair chat with
canned replies from the other side (it's a demo with no real backend).

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at http://localhost:8501.

## Deploy

See `DEPLOY.md`. Short version: push to GitHub, point Streamlit Community
Cloud at `streamlit_app.py`, done.

## What it does

1. **Sign up** with a username + password (mock auth, SHA-256 hashed).
2. **Create your profile**: name, age, email, budget/rent, schedule,
   cleanliness, smoker, pets, bio. Hosts also give bedroom / bathroom /
   area counts, a description of the flat, and optionally upload photos.
3. **Pick preferences** (max budget, smoker, schedule, pets, cleanliness).
4. **Swipe** through candidates of the opposite role. Host cards show a
   gallery you can browse with prev/next arrows. Each card has a
   compatibility score computed from budget + lifestyle fit.
5. **Match modal** appears when you like someone.
6. **Matches tab** lists everyone you've liked, sortable by recency /
   compatibility / budget / name / age.
7. **Chat** opens a per-match thread with canned replies.

All state persists to `data/*.json` between runs (locally — Streamlit Cloud
wipes it on container restart).

## Project layout

```
streamlit_app.py   Streamlit UI
models.py          Profile, Filters, compatibility(), photo helpers
auth.py            Mock SHA-256 login/signup
api.py             randomuser.me client + featured candidates (Harold)
chat.py            Per-match chat threads
storage.py         JSON file helpers
data/              Runtime JSON + uploaded images (created on first run)
```

## Notes

- External APIs used: `randomuser.me` for demo profiles, `i.pravatar.cc`
  for default avatars, `images.unsplash.com` for curated interior photos.
- Because only one real user exists per browser session, every like
  counts as a match. A production version would need a real backend.
