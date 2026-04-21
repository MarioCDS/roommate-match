"""Core swipe screen: shows one candidate at a time with Like / Pass buttons."""
from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests
from PIL import Image, ImageTk

from api import fetch_candidates
from models import Profile
from ui.common import BG, CARD_BG, TEXT, MUTED, placeholder_image

PHOTO_SIZE = (300, 300)


class SwipeScreen(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self._photo_ref: ImageTk.PhotoImage | None = None

        self.queue: list[Profile] = []
        self.index = 0

        self._build()
        self._prepare_queue()

    # --- UI construction ----------------------------------------------

    def _build(self) -> None:
        self.card = tk.Frame(self, bg=CARD_BG, bd=0, highlightthickness=1,
                             highlightbackground="#E5E7EB")
        self.card.pack(padx=24, pady=18, fill="both", expand=True)

        self.photo_label = tk.Label(self.card, bg=CARD_BG)
        self.photo_label.pack(pady=(18, 10))

        self.name_label = tk.Label(self.card, text="", bg=CARD_BG, fg=TEXT,
                                   font=("Segoe UI", 18, "bold"))
        self.name_label.pack()

        self.meta_label = tk.Label(self.card, text="", bg=CARD_BG, fg=MUTED,
                                   font=("Segoe UI", 10))
        self.meta_label.pack(pady=(2, 8))

        self.bio_label = tk.Label(self.card, text="", bg=CARD_BG, fg=TEXT,
                                  font=("Segoe UI", 11), wraplength=380, justify="center")
        self.bio_label.pack(padx=20, pady=(4, 10))

        self.status_label = tk.Label(self.card, text="", bg=CARD_BG, fg=MUTED,
                                     font=("Segoe UI", 10, "italic"))
        self.status_label.pack(pady=(0, 6))

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(0, 14))
        self.pass_btn = ttk.Button(btns, text="Pass", style="Pass.TButton",
                                   command=self._on_pass, width=14)
        self.pass_btn.pack(side="left", padx=8)
        self.like_btn = ttk.Button(btns, text="Like", style="Like.TButton",
                                   command=self._on_like, width=14)
        self.like_btn.pack(side="left", padx=8)

        refresh = tk.Frame(self, bg=BG)
        refresh.pack(pady=(0, 10))
        ttk.Button(refresh, text="Refresh candidates",
                   command=self._refresh).pack()

    # --- queue logic --------------------------------------------------

    def _prepare_queue(self) -> None:
        if not self.app.candidates:
            self._set_status("Loading candidates from randomuser.me \u2026")
            self._disable_actions()
            threading.Thread(target=self._download_initial, daemon=True).start()
            return
        self._apply_filters_and_render()

    def _download_initial(self) -> None:
        try:
            candidates = fetch_candidates(30)
        except requests.RequestException as e:
            self.after(0, lambda err=e: self._network_error(err))
            return
        self.after(0, lambda: self._candidates_ready(candidates))

    def _candidates_ready(self, candidates: list[Profile]) -> None:
        self.app.save_candidates(candidates)
        self._apply_filters_and_render()

    def _network_error(self, err: Exception) -> None:
        self._set_status("")
        messagebox.showerror(
            "Network error",
            f"Could not reach randomuser.me:\n{err}\n\nCheck your internet and press \u201cRefresh candidates\u201d.",
        )
        self._show_empty("No candidates yet. Press \u201cRefresh candidates\u201d once you\u2019re online.")

    def _apply_filters_and_render(self) -> None:
        matched_ids = {m.id for m in self.app.matches}
        self.queue = [
            c for c in self.app.candidates
            if c.id not in matched_ids and c.matches_filters(self.app.filters)
        ]
        self.index = 0
        self._enable_actions()
        if not self.queue:
            self._show_empty(
                "No candidates match your filters.\nTry widening them or refreshing the list.",
            )
        else:
            self._render_current()

    def _render_current(self) -> None:
        if self.index >= len(self.queue):
            self._show_empty("You\u2019ve seen everyone. Try refreshing or loosening filters.")
            return
        p = self.queue[self.index]
        self.name_label.configure(text=f"{p.name}, {p.age}")
        smoker_txt = "smoker" if p.smoker else "non-smoker"
        pets_txt = "has pets" if p.pets else "no pets"
        self.meta_label.configure(
            text=(
                f"\u20ac{p.budget}/mo  \u2022  {p.schedule}  \u2022  {p.cleanliness}\n"
                f"{smoker_txt}  \u2022  {pets_txt}"
            ),
        )
        self.bio_label.configure(text=p.bio)
        self._set_status("")
        self._load_photo_async(p)

    def _show_empty(self, msg: str) -> None:
        self._photo_ref = placeholder_image("?", PHOTO_SIZE, 140)
        self.photo_label.configure(image=self._photo_ref)
        self.name_label.configure(text="No one here")
        self.meta_label.configure(text="")
        self.bio_label.configure(text=msg)
        self._set_status("")
        self._disable_actions()

    # --- photo loading ------------------------------------------------

    def _load_photo_async(self, profile: Profile) -> None:
        # Show a placeholder while we load to avoid UI flicker showing the previous face.
        self._photo_ref = placeholder_image(profile.name[:1].upper(), PHOTO_SIZE, 140)
        self.photo_label.configure(image=self._photo_ref)
        url = profile.photo_url
        if not url:
            return

        def worker(expected_id=profile.id, u=url):
            try:
                resp = requests.get(u, timeout=8)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize(PHOTO_SIZE)
            except (requests.RequestException, OSError):
                return
            self.after(0, lambda i=img, pid=expected_id: self._set_photo(pid, i))

        threading.Thread(target=worker, daemon=True).start()

    def _set_photo(self, expected_id: str, pil_image: Image.Image) -> None:
        if self.index >= len(self.queue) or self.queue[self.index].id != expected_id:
            return  # user already swiped past this one
        self._photo_ref = ImageTk.PhotoImage(pil_image)
        self.photo_label.configure(image=self._photo_ref)

    # --- actions ------------------------------------------------------

    def _on_like(self) -> None:
        if self.index >= len(self.queue):
            return
        self.app.add_match(self.queue[self.index])
        self._set_status("Added to your matches.")
        self.after(650, self._advance)

    def _on_pass(self) -> None:
        self._advance()

    def _advance(self) -> None:
        self.index += 1
        self._render_current()

    def _refresh(self) -> None:
        self._set_status("Refreshing candidates \u2026")
        self._disable_actions()
        threading.Thread(target=self._download_initial, daemon=True).start()

    # --- helpers ------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _disable_actions(self) -> None:
        self.like_btn.state(["disabled"])
        self.pass_btn.state(["disabled"])

    def _enable_actions(self) -> None:
        self.like_btn.state(["!disabled"])
        self.pass_btn.state(["!disabled"])


