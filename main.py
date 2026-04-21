"""Entry point for the NOVA Roomie app.

Run with:
    py main.py
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models import Profile, Filters
from storage import (
    load_json, save_json,
    CANDIDATES_FILE,
    profile_file, matches_file, filters_file,
)
from ui.common import BG, PRIMARY, PRIMARY_DARK, TEXT
from ui.auth_screen import AuthScreen
from ui.setup_screen import SetupScreen
from ui.filter_screen import FilterScreen
from ui.swipe_screen import SwipeScreen
from ui.matches_screen import MatchesScreen


APP_TITLE = "NOVA Roomie"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("520x740")
        self.configure(bg=BG)
        self.minsize(440, 640)

        self._init_style()

        # Shared (account-independent) state
        cands = load_json(CANDIDATES_FILE, [])
        self.candidates: list[Profile] = [Profile.from_dict(c) for c in cands]

        # Per-user state, filled in by login()
        self.current_user: str | None = None
        self.my_profile: Profile | None = None
        self.matches: list[Profile] = []
        self.filters: Filters = Filters()

        self.nav = NavBar(self, self)
        self.nav.pack(side="top", fill="x")
        self.nav.set_logged_out()

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self._current: tk.Frame | None = None
        self.show_auth()

    def _init_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=8, font=("Segoe UI", 10))
        style.configure("Primary.TButton", background=PRIMARY, foreground="white",
                        padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Primary.TButton",
                  background=[("active", PRIMARY_DARK)])
        style.configure("Like.TButton", background="#10B981", foreground="white",
                        padding=12, font=("Segoe UI", 12, "bold"))
        style.map("Like.TButton", background=[("active", "#0E9670")])
        style.configure("Pass.TButton", background="#9E9E9E", foreground="white",
                        padding=12, font=("Segoe UI", 12, "bold"))
        style.map("Pass.TButton", background=[("active", "#757575")])
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT,
                        font=("Segoe UI", 18, "bold"))
        style.configure("H2.TLabel", background=BG, foreground=TEXT,
                        font=("Segoe UI", 13, "bold"))

    # --- navigation ----------------------------------------------------

    def _swap(self, new_frame: tk.Frame) -> None:
        if self._current is not None:
            self._current.destroy()
        self._current = new_frame
        self._current.pack(fill="both", expand=True)

    def show_auth(self) -> None:
        self._swap(AuthScreen(self.container, self))

    def show_setup(self, first_run: bool = False) -> None:
        self._swap(SetupScreen(self.container, self, first_run=first_run))

    def show_filters(self) -> None:
        self._swap(FilterScreen(self.container, self))

    def show_swipe(self) -> None:
        self._swap(SwipeScreen(self.container, self))

    def show_matches(self) -> None:
        self._swap(MatchesScreen(self.container, self))

    # --- auth flow -----------------------------------------------------

    def login(self, username: str) -> None:
        self.current_user = username
        self._load_user_state()
        self.nav.set_logged_in(username)
        if self.my_profile is None:
            self.show_setup(first_run=True)
        else:
            self.show_swipe()

    def signup_and_login(self, username: str) -> None:
        # New account: no profile on disk yet, so send them to the form.
        self.current_user = username
        self.my_profile = None
        self.matches = []
        self.filters = Filters()
        self.nav.set_logged_in(username)
        self.show_setup(first_run=True)

    def logout(self) -> None:
        self.current_user = None
        self.my_profile = None
        self.matches = []
        self.filters = Filters()
        self.nav.set_logged_out()
        self.show_auth()

    def _load_user_state(self) -> None:
        assert self.current_user is not None
        u = self.current_user

        my = load_json(profile_file(u), None)
        self.my_profile = Profile.from_dict(my) if my else None

        ms = load_json(matches_file(u), [])
        self.matches = [Profile.from_dict(m) for m in ms]

        f = load_json(filters_file(u), None)
        self.filters = Filters.from_dict(f) if f else Filters()

    # --- state mutations (scoped to current user) ----------------------

    def _require_user(self) -> str:
        if self.current_user is None:
            raise RuntimeError("No user is logged in.")
        return self.current_user

    def save_my_profile(self, profile: Profile) -> None:
        u = self._require_user()
        self.my_profile = profile
        save_json(profile_file(u), profile.to_dict())

    def save_candidates(self, candidates: list[Profile]) -> None:
        # Candidate pool is shared: everyone browses the same demo users.
        self.candidates = candidates
        save_json(CANDIDATES_FILE, [c.to_dict() for c in candidates])

    def add_match(self, profile: Profile) -> None:
        u = self._require_user()
        if not any(m.id == profile.id for m in self.matches):
            self.matches.append(profile)
            save_json(matches_file(u), [m.to_dict() for m in self.matches])

    def remove_match(self, profile: Profile) -> None:
        u = self._require_user()
        self.matches = [m for m in self.matches if m.id != profile.id]
        save_json(matches_file(u), [m.to_dict() for m in self.matches])

    def save_filters(self, f: Filters) -> None:
        u = self._require_user()
        self.filters = f
        save_json(filters_file(u), f.to_dict())


class NavBar(tk.Frame):
    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, bg=PRIMARY, height=52)
        self.app = app
        self.pack_propagate(False)

        self.brand = tk.Label(self, text="\U0001f3e0 NOVA Roomie", bg=PRIMARY, fg="white",
                              font=("Segoe UI", 14, "bold"), padx=14)
        self.brand.pack(side="left")

        self.user_label = tk.Label(self, text="", bg=PRIMARY, fg="white",
                                   font=("Segoe UI", 9, "italic"))
        self.user_label.pack(side="left", padx=(0, 8))

        self._nav_buttons: list[tk.Button] = []
        self._logout_button: tk.Button | None = None

        for label, cmd in [
            ("Swipe", app.show_swipe),
            ("Matches", app.show_matches),
            ("Filters", app.show_filters),
            ("Profile", lambda: app.show_setup(first_run=False)),
        ]:
            btn = self._make_button(label, cmd)
            btn.pack(side="left", padx=2)
            self._nav_buttons.append(btn)

        self._logout_button = self._make_button("Log out", app.logout)
        self._logout_button.pack(side="right", padx=(2, 10))

    def _make_button(self, label, cmd) -> tk.Button:
        return tk.Button(
            self, text=label, command=cmd, bd=0, relief="flat",
            bg=PRIMARY, fg="white", activebackground=PRIMARY_DARK,
            activeforeground="white", font=("Segoe UI", 10, "bold"),
            padx=10, pady=6, cursor="hand2",
        )

    def set_logged_in(self, username: str) -> None:
        self.user_label.configure(text=f"@{username}")
        for b in self._nav_buttons:
            b.configure(state="normal")
        if self._logout_button:
            self._logout_button.configure(state="normal")

    def set_logged_out(self) -> None:
        self.user_label.configure(text="")
        for b in self._nav_buttons:
            b.configure(state="disabled")
        if self._logout_button:
            self._logout_button.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()
