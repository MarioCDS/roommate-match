"""Preference filter screen."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models import Filters, SCHEDULES, CLEANLINESS_LEVELS
from ui.common import BG

SMOKER_OPTS = ["any", "no smokers", "smokers only"]
SCHEDULE_OPTS = ["any"] + SCHEDULES
PETS_OPTS = ["any", "has pets", "no pets"]
CLEANLINESS_OPTS = ["any"] + CLEANLINESS_LEVELS


class FilterScreen(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        f = app.filters

        ttk.Label(self, text="Your preferences", style="Title.TLabel").pack(
            padx=24, pady=(20, 6), anchor="w",
        )
        ttk.Label(
            self,
            text="Filter candidates before you start swiping. Leave as \u201cany\u201d to see everyone.",
            style="TLabel", wraplength=440,
        ).pack(padx=24, pady=(0, 16), anchor="w")

        form = tk.Frame(self, bg=BG)
        form.pack(padx=24, fill="x")

        self.budget_var = tk.IntVar(value=f.max_budget)
        self.smoker_var = tk.StringVar(value=f.smoker_pref)
        self.schedule_var = tk.StringVar(value=f.schedule_pref)
        self.pets_var = tk.StringVar(value=f.pets_pref)
        self.cleanliness_var = tk.StringVar(value=f.cleanliness_pref)

        ttk.Label(form, text="Max budget (\u20ac/mo)", style="H2.TLabel").grid(
            row=0, column=0, sticky="w", pady=(6, 2), columnspan=2,
        )
        tk.Scale(
            form, from_=200, to=2000, orient="horizontal", resolution=25,
            variable=self.budget_var, length=380, bg=BG, highlightthickness=0,
        ).grid(row=1, column=0, sticky="w", pady=(0, 14), columnspan=2)

        self._combo_row(form, 2, "Smoker preference", self.smoker_var, SMOKER_OPTS)
        self._combo_row(form, 4, "Schedule preference", self.schedule_var, SCHEDULE_OPTS)
        self._combo_row(form, 6, "Pet preference", self.pets_var, PETS_OPTS)
        self._combo_row(form, 8, "Cleanliness preference", self.cleanliness_var, CLEANLINESS_OPTS)

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=18)
        ttk.Button(btns, text="Start swiping", style="Primary.TButton",
                   command=self._apply).pack(side="left", padx=6)
        ttk.Button(btns, text="Reset", command=self._reset).pack(side="left", padx=6)

    def _combo_row(self, form, row, label, var, values) -> None:
        ttk.Label(form, text=label, style="H2.TLabel").grid(
            row=row, column=0, sticky="w", pady=(6, 2),
        )
        ttk.Combobox(
            form, textvariable=var, values=values, state="readonly", width=24,
        ).grid(row=row + 1, column=0, sticky="w", pady=(0, 12))

    def _apply(self) -> None:
        self.app.save_filters(Filters(
            max_budget=int(self.budget_var.get()),
            smoker_pref=self.smoker_var.get(),
            schedule_pref=self.schedule_var.get(),
            pets_pref=self.pets_var.get(),
            cleanliness_pref=self.cleanliness_var.get(),
        ))
        self.app.show_swipe()

    def _reset(self) -> None:
        self.budget_var.set(2000)
        self.smoker_var.set("any")
        self.schedule_var.set("any")
        self.pets_var.set("any")
        self.cleanliness_var.set("any")
