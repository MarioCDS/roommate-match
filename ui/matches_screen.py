"""Screen listing everyone the user has liked."""
from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk

import requests
from PIL import Image, ImageTk

from models import Profile, compatibility
from ui.common import BG, CARD_BG, TEXT, MUTED, PRIMARY, placeholder_image

THUMB_SIZE = (72, 72)


class MatchesScreen(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self._photo_refs: list[ImageTk.PhotoImage] = []

        ttk.Label(self, text=f"Your matches ({len(app.matches)})",
                  style="Title.TLabel").pack(padx=24, pady=(16, 6), anchor="w")

        if not app.matches:
            ttk.Label(
                self,
                text="No matches yet. Head back to Swipe and like some profiles!",
                style="TLabel", wraplength=440,
            ).pack(padx=24, pady=20, anchor="w")
            ttk.Button(self, text="Go to Swipe", style="Primary.TButton",
                       command=app.show_swipe).pack(padx=24, pady=4, anchor="w")
            return

        container, canvas = _scrollable(self)
        for p in reversed(app.matches):
            self._render_row(container, p)

    def _render_row(self, parent, profile: Profile) -> None:
        row = tk.Frame(parent, bg=CARD_BG, bd=0, highlightthickness=1,
                       highlightbackground="#E5E7EB")
        row.pack(fill="x", padx=18, pady=6)

        thumb = tk.Label(row, bg=CARD_BG)
        thumb.pack(side="left", padx=10, pady=10)
        placeholder = placeholder_image(profile.name[:1].upper(), THUMB_SIZE, 36)
        self._photo_refs.append(placeholder)
        thumb.configure(image=placeholder)

        info = tk.Frame(row, bg=CARD_BG)
        info.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=10)

        header = tk.Frame(info, bg=CARD_BG)
        header.pack(anchor="w", fill="x")
        tk.Label(header, text=f"{profile.name}, {profile.age}", bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(side="left")

        me = self.app.my_profile
        if me is not None:
            score = compatibility(me, profile)
            tk.Label(header, text=f"  {score}% match", bg=CARD_BG, fg=PRIMARY,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
        smoker_txt = "smoker" if profile.smoker else "non-smoker"
        pets_txt = "has pets" if profile.pets else "no pets"
        tk.Label(
            info,
            text=(
                f"\u20ac{profile.budget}/mo  \u2022  {profile.schedule}  \u2022  "
                f"{profile.cleanliness}  \u2022  {smoker_txt}  \u2022  {pets_txt}"
            ),
            bg=CARD_BG, fg=MUTED, font=("Segoe UI", 9), anchor="w",
        ).pack(anchor="w")
        tk.Label(info, text=f"Contact: {profile.email}", bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 10), anchor="w").pack(anchor="w", pady=(4, 0))

        if profile.photo_url:
            threading.Thread(
                target=self._load_thumb,
                args=(profile.photo_url, thumb),
                daemon=True,
            ).start()

    def _load_thumb(self, url: str, label: tk.Label) -> None:
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize(THUMB_SIZE)
        except (requests.RequestException, OSError):
            return
        self.after(0, lambda i=img: self._apply_thumb(label, i))

    def _apply_thumb(self, label: tk.Label, pil_image: Image.Image) -> None:
        if not label.winfo_exists():
            return
        photo = ImageTk.PhotoImage(pil_image)
        self._photo_refs.append(photo)
        label.configure(image=photo)


def _scrollable(parent: tk.Widget) -> tuple[tk.Frame, tk.Canvas]:
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    inner = tk.Frame(canvas, bg=BG)
    window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(window, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    return inner, canvas


