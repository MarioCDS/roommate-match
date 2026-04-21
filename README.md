# NOVA Roomie

A roommate-matching swipe app built for NOVA's Introduction to Programming group project.
Ships in **two forms** from the same shared codebase (`models.py`, `auth.py`, `api.py`, `storage.py`):

- **Desktop** (Tkinter): run `py main.py` or double-click `dist/NOVA_Roomie.exe`.
- **Web** (Streamlit): run `streamlit run streamlit_app.py`, or deploy to Streamlit Cloud (see `DEPLOY.md`).

## Requirements

- **Python 3.13+** (tested on Python 3.14)
- Internet connection on first launch (to fetch demo profiles from `randomuser.me`)

## Setup

From this folder (`roommate-match`):

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
py main.py
```

## What it does

1. **First launch**: fill out your own profile (name, age, budget, smoker, schedule, bio).
2. **Pick preferences**: filter by max budget, smoker, and schedule.
3. **Swipe**: for each candidate shown, press **Like** or **Pass**.
4. **Matches**: everyone you liked appears in the Matches tab with their contact email.

All state persists to `data/*.json` between runs.

## Project layout

```
main.py          app entry point + Tk App class
models.py        Profile and Filters dataclasses
storage.py       JSON load/save helpers
api.py           randomuser.me client
ui/
  setup_screen.py
  filter_screen.py
  swipe_screen.py
  matches_screen.py
data/            runtime JSON (created on first use)
```

## Notes

Because there is only one real user, every right-swipe is treated as a mutual match.
A production version would need a backend to implement real two-way matching.
