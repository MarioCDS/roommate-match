"""Login / Signup screen: mock auth entry point."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from auth import authenticate, create_user, validate_new_credentials, load_users
from ui.common import BG, CARD_BG, TEXT, MUTED, PRIMARY, BORDER


class AuthScreen(tk.Frame):
    """Single frame that toggles between Login and Sign-up views."""

    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.mode = tk.StringVar(value="login")

        self._build_hero()
        self._build_toggle()

        self.body = tk.Frame(self, bg=BG)
        self.body.pack(padx=24, pady=(4, 10), fill="x")

        self._render_login()

    # --- layout -------------------------------------------------------

    def _build_hero(self) -> None:
        hero = tk.Frame(self, bg=BG)
        hero.pack(pady=(28, 8))
        tk.Label(hero, text="\U0001f3e0 NOVA Roomie", bg=BG, fg=PRIMARY,
                 font=("Segoe UI", 26, "bold")).pack()
        tk.Label(hero, text="Find a roommate who fits your vibe.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(pady=(2, 0))

    def _build_toggle(self) -> None:
        bar = tk.Frame(self, bg=BG)
        bar.pack(pady=(18, 6))

        self.login_btn = tk.Button(
            bar, text="Log in", command=self._show_login,
            bd=0, relief="flat", padx=26, pady=8,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        self.signup_btn = tk.Button(
            bar, text="Sign up", command=self._show_signup,
            bd=0, relief="flat", padx=26, pady=8,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        self.login_btn.pack(side="left", padx=2)
        self.signup_btn.pack(side="left", padx=2)
        self._paint_toggle()

    def _paint_toggle(self) -> None:
        for btn, active in [
            (self.login_btn, self.mode.get() == "login"),
            (self.signup_btn, self.mode.get() == "signup"),
        ]:
            btn.configure(
                bg=PRIMARY if active else "#FFFFFF",
                fg="white" if active else TEXT,
                activebackground=PRIMARY if active else "#EEEEEE",
                activeforeground="white" if active else TEXT,
            )

    # --- mode switching ----------------------------------------------

    def _show_login(self) -> None:
        self.mode.set("login")
        self._paint_toggle()
        self._render_login()

    def _show_signup(self) -> None:
        self.mode.set("signup")
        self._paint_toggle()
        self._render_signup()

    def _reset_body(self) -> tk.Frame:
        for child in self.body.winfo_children():
            child.destroy()
        card = tk.Frame(self.body, bg=CARD_BG, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", padx=6, pady=6)
        return card

    # --- login form --------------------------------------------------

    def _render_login(self) -> None:
        card = self._reset_body()
        users = load_users()
        hint = f"{len(users)} account{'s' if len(users) != 1 else ''} on this machine"

        tk.Label(card, text="Welcome back", bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(18, 2))
        tk.Label(card, text=hint, bg=CARD_BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack()

        u = tk.StringVar()
        p = tk.StringVar()
        err = tk.StringVar()

        form = self._make_form(card)
        self._grid_field(form, 0, "Username", ttk.Entry(form, textvariable=u, width=28))
        self._grid_field(form, 1, "Password",
                         ttk.Entry(form, textvariable=p, show="\u2022", width=28))

        tk.Label(card, textvariable=err, bg=CARD_BG, fg=PRIMARY,
                 font=("Segoe UI", 9)).pack(pady=(2, 6))

        def submit():
            username = u.get().strip()
            password = p.get()
            if not username or not password:
                err.set("Enter a username and password.")
                return
            if not authenticate(username, password):
                err.set("Incorrect username or password.")
                return
            err.set("")
            self.app.login(username)

        ttk.Button(card, text="Log in", style="Primary.TButton",
                   command=submit).pack(pady=(6, 18))

    # --- signup form -------------------------------------------------

    def _render_signup(self) -> None:
        card = self._reset_body()

        tk.Label(card, text="Create your account", bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(18, 2))
        tk.Label(card, text="You\u2019ll build your profile next.", bg=CARD_BG,
                 fg=MUTED, font=("Segoe UI", 9)).pack()

        u = tk.StringVar()
        p = tk.StringVar()
        c = tk.StringVar()
        err = tk.StringVar()

        form = self._make_form(card)
        self._grid_field(form, 0, "Username", ttk.Entry(form, textvariable=u, width=28))
        self._grid_field(form, 1, "Password",
                         ttk.Entry(form, textvariable=p, show="\u2022", width=28))
        self._grid_field(form, 2, "Confirm password",
                         ttk.Entry(form, textvariable=c, show="\u2022", width=28))

        tk.Label(card, textvariable=err, bg=CARD_BG, fg=PRIMARY,
                 font=("Segoe UI", 9), wraplength=360,
                 justify="center").pack(pady=(2, 6))

        def submit():
            username = u.get().strip()
            password = p.get()
            confirm = c.get()
            msg = validate_new_credentials(username, password, confirm)
            if msg:
                err.set(msg)
                return
            if not create_user(username, password):
                err.set("That username is already taken.")
                return
            err.set("")
            self.app.signup_and_login(username)

        ttk.Button(card, text="Create account", style="Primary.TButton",
                   command=submit).pack(pady=(6, 18))

    # --- helpers -----------------------------------------------------

    def _make_form(self, parent) -> tk.Frame:
        """One shared form frame so grid columns line up across all fields."""
        form = tk.Frame(parent, bg=CARD_BG)
        form.pack(pady=(10, 4))
        return form

    def _grid_field(self, form, row, label, widget) -> None:
        tk.Label(form, text=label, bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold"), anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5,
        )
        widget.grid(row=row, column=1, sticky="w", pady=5)
