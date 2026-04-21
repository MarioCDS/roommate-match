"""First-launch (and edit) profile form."""
from __future__ import annotations

import tkinter as tk
import uuid
from tkinter import ttk, messagebox

from models import Profile, SCHEDULES, CLEANLINESS_LEVELS, avatar_url
from ui.common import BG, CARD_BG, BORDER


class SetupScreen(tk.Frame):
    def __init__(self, parent, app, first_run: bool = False) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.first_run = first_run
        existing = app.my_profile

        pad = {"padx": 24, "pady": 6}

        title_text = "Welcome! Create your profile" if first_run else "Edit your profile"
        ttk.Label(self, text=title_text, style="Title.TLabel").pack(**pad, anchor="w")
        ttk.Label(
            self,
            text="This info is shown to other roommates when they swipe on you.",
            style="TLabel",
            wraplength=440,
        ).pack(padx=24, pady=(0, 12), anchor="w")

        form = tk.Frame(self, bg=BG)
        form.pack(padx=24, pady=6, fill="x")

        self.name_var = tk.StringVar(value=existing.name if existing else "")
        self.age_var = tk.StringVar(value=str(existing.age) if existing else "")
        self.email_var = tk.StringVar(value=existing.email if existing else "")
        self.budget_var = tk.IntVar(value=existing.budget if existing else 500)
        self.smoker_var = tk.BooleanVar(value=existing.smoker if existing else False)
        self.pets_var = tk.BooleanVar(value=existing.pets if existing else False)
        self.schedule_var = tk.StringVar(value=existing.schedule if existing else SCHEDULES[2])
        self.cleanliness_var = tk.StringVar(
            value=existing.cleanliness if existing else CLEANLINESS_LEVELS[1],
        )

        self._row(form, 0, "Name", ttk.Entry(form, textvariable=self.name_var, width=34))
        self._row(form, 1, "Age", ttk.Entry(form, textvariable=self.age_var, width=10))
        self._row(form, 2, "Email", ttk.Entry(form, textvariable=self.email_var, width=34))

        self._row(
            form, 3, "Budget (\u20ac/mo)",
            tk.Scale(form, from_=200, to=1500, orient="horizontal", resolution=25,
                     variable=self.budget_var, length=260, bg=BG, highlightthickness=0),
        )

        ttk.Label(form, text="Smoker", style="TLabel").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Checkbutton(form, variable=self.smoker_var).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Has pets", style="TLabel").grid(row=5, column=0, sticky="w", pady=6)
        ttk.Checkbutton(form, variable=self.pets_var).grid(row=5, column=1, sticky="w", pady=6)

        self._row(
            form, 6, "Schedule",
            ttk.Combobox(form, textvariable=self.schedule_var, values=SCHEDULES,
                         state="readonly", width=20),
        )
        self._row(
            form, 7, "Cleanliness",
            ttk.Combobox(form, textvariable=self.cleanliness_var, values=CLEANLINESS_LEVELS,
                         state="readonly", width=20),
        )

        # Bio gets its own multi-line Text widget.
        ttk.Label(form, text="Bio", style="TLabel").grid(row=8, column=0, sticky="nw", pady=6)
        bio_wrap = tk.Frame(form, bg=BORDER, bd=0, highlightthickness=1,
                            highlightbackground=BORDER)
        bio_wrap.grid(row=8, column=1, sticky="w", pady=6, padx=(10, 0))
        self.bio_widget = tk.Text(
            bio_wrap, width=40, height=5, wrap="word",
            font=("Segoe UI", 10), relief="flat", bd=4, bg=CARD_BG,
        )
        self.bio_widget.pack()
        if existing and existing.bio:
            self.bio_widget.insert("1.0", existing.bio)

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=18)
        ttk.Button(btns, text="Save and continue", style="Primary.TButton",
                   command=self._save).pack(side="left", padx=6)
        if not first_run:
            ttk.Button(btns, text="Cancel", command=app.show_swipe).pack(side="left", padx=6)

    def _row(self, parent, row, label, widget) -> None:
        ttk.Label(parent, text=label, style="TLabel").grid(row=row, column=0, sticky="w", pady=6)
        widget.grid(row=row, column=1, sticky="w", pady=6, padx=(10, 0))

    def _save(self) -> None:
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        try:
            age = int(self.age_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Age must be a number.")
            return
        if not name:
            messagebox.showerror("Invalid input", "Please enter your name.")
            return
        if age < 16 or age > 100:
            messagebox.showerror("Invalid input", "Age must be between 16 and 100.")
            return

        bio = self.bio_widget.get("1.0", "end-1c").strip() or "(no bio)"

        existing = self.app.my_profile
        pid = existing.id if existing else str(uuid.uuid4())
        photo = existing.photo_url if existing and existing.photo_url else avatar_url(pid)
        profile = Profile(
            id=pid,
            name=name,
            age=age,
            photo_url=photo,
            email=email,
            budget=int(self.budget_var.get()),
            smoker=bool(self.smoker_var.get()),
            schedule=self.schedule_var.get(),
            bio=bio,
            pets=bool(self.pets_var.get()),
            cleanliness=self.cleanliness_var.get(),
        )
        self.app.save_my_profile(profile)

        if self.first_run:
            self.app.show_filters()
        else:
            self.app.show_swipe()
