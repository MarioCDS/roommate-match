"""Core swipe screen.

Shows one candidate of the *opposite* role at a time:
- A roomie sees host listings (house photo carousel + description + rent).
- A host sees roomie profiles (face + bio + budget).
"""
from __future__ import annotations

import io
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

import requests
from PIL import Image, ImageTk

from api import fetch_candidates
from models import Profile, compatibility
from ui.common import BG, CARD_BG, TEXT, MUTED, PRIMARY, placeholder_image
from ui.match_modal import MatchModal

PORTRAIT_SIZE = (220, 220)     # closer to randomuser's native 128 to avoid heavy upscaling
HOUSE_SIZE = (360, 240)
HOST_AVATAR_SIZE = (48, 48)


def _load_image(src: str, size: tuple[int, int], timeout: float = 8.0) -> Image.Image:
    """Open an image from either a local path or an http(s) URL."""
    if src.startswith(("http://", "https://")):
        resp = requests.get(src, timeout=timeout)
        resp.raise_for_status()
        data = io.BytesIO(resp.content)
        img = Image.open(data)
    else:
        img = Image.open(src)
    return img.convert("RGB").resize(size)


class SwipeScreen(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self._photo_ref: ImageTk.PhotoImage | None = None

        self.queue: list[Profile] = []
        self.index = 0
        self._last_action: tuple[str, Profile] | None = None
        self._gallery_index = 0  # which photo within the current host's gallery
        self._host_avatar_ref: ImageTk.PhotoImage | None = None

        self._build()
        self._prepare_queue()
        self._wire_keyboard()

    # --- UI construction ----------------------------------------------

    def _build(self) -> None:
        self.card = tk.Frame(self, bg=CARD_BG, bd=0, highlightthickness=1,
                             highlightbackground="#E5E7EB")
        self.card.pack(padx=24, pady=18, fill="both", expand=True)

        self.badge_label = tk.Label(
            self.card, text="", bg=PRIMARY, fg="white",
            font=("Segoe UI", 9, "bold"), padx=10, pady=2,
        )
        self.badge_label.pack(pady=(14, 6))

        photo_row = tk.Frame(self.card, bg=CARD_BG)
        photo_row.pack(pady=(0, 4))
        self.prev_photo_btn = tk.Button(
            photo_row, text="\u25c0", bd=0, relief="flat",
            bg=CARD_BG, activebackground="#E5E7EB",
            font=("Segoe UI", 14, "bold"),
            cursor="hand2", padx=6, command=self._prev_photo,
        )
        self.prev_photo_btn.pack(side="left", padx=(0, 4))
        self.photo_label = tk.Label(photo_row, bg=CARD_BG)
        self.photo_label.pack(side="left")
        self.next_photo_btn = tk.Button(
            photo_row, text="\u25b6", bd=0, relief="flat",
            bg=CARD_BG, activebackground="#E5E7EB",
            font=("Segoe UI", 14, "bold"),
            cursor="hand2", padx=6, command=self._next_photo,
        )
        self.next_photo_btn.pack(side="left", padx=(4, 0))

        self.photo_index_label = tk.Label(
            self.card, text="", bg=CARD_BG, fg=MUTED, font=("Segoe UI", 8),
        )
        self.photo_index_label.pack(pady=(0, 6))

        self.name_label = tk.Label(self.card, text="", bg=CARD_BG, fg=TEXT,
                                   font=("Segoe UI", 18, "bold"))
        self.name_label.pack()

        self.score_label = tk.Label(
            self.card, text="", bg=CARD_BG, fg=PRIMARY,
            font=("Segoe UI", 11, "bold"),
        )
        self.score_label.pack(pady=(2, 0))

        self.meta_label = tk.Label(self.card, text="", bg=CARD_BG, fg=MUTED,
                                   font=("Segoe UI", 10), justify="center")
        self.meta_label.pack(pady=(2, 8))

        self.bio_label = tk.Label(self.card, text="", bg=CARD_BG, fg=TEXT,
                                  font=("Segoe UI", 11), wraplength=380,
                                  justify="center")
        self.bio_label.pack(padx=20, pady=(4, 10))

        self.status_label = tk.Label(self.card, text="", bg=CARD_BG, fg=MUTED,
                                     font=("Segoe UI", 10, "italic"))
        self.status_label.pack(pady=(0, 6))

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(0, 8))
        self.pass_btn = ttk.Button(btns, text="Pass", style="Pass.TButton",
                                   command=self._on_pass, width=12)
        self.pass_btn.pack(side="left", padx=6)
        self.undo_btn = ttk.Button(btns, text="Undo", command=self._on_undo, width=10)
        self.undo_btn.pack(side="left", padx=6)
        self.undo_btn.state(["disabled"])
        self.like_btn = ttk.Button(btns, text="Like", style="Like.TButton",
                                   command=self._on_like, width=12)
        self.like_btn.pack(side="left", padx=6)

        hint = tk.Label(
            self, text="Tip: \u2190 Left = Pass, \u2192 Right = Like, Backspace = Undo.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9, "italic"),
        )
        hint.pack(pady=(0, 4))

        refresh = tk.Frame(self, bg=BG)
        refresh.pack(pady=(0, 10))
        ttk.Button(refresh, text="Refresh candidates",
                   command=self._refresh).pack()

    def _wire_keyboard(self) -> None:
        root = self.winfo_toplevel()
        root.bind("<Left>", self._key_pass)
        root.bind("<Right>", self._key_like)
        root.bind("<BackSpace>", self._key_undo)
        self.bind("<Destroy>", self._unwire_keyboard)

    def _unwire_keyboard(self, _event=None) -> None:
        try:
            root = self.winfo_toplevel()
            root.unbind("<Left>")
            root.unbind("<Right>")
            root.unbind("<BackSpace>")
        except tk.TclError:
            pass

    def _key_pass(self, _event=None) -> None:
        if self._actions_enabled():
            self._on_pass()

    def _key_like(self, _event=None) -> None:
        if self._actions_enabled():
            self._on_like()

    def _key_undo(self, _event=None) -> None:
        if self._last_action is not None:
            self._on_undo()

    def _actions_enabled(self) -> bool:
        return "disabled" not in self.like_btn.state()

    # --- queue logic --------------------------------------------------

    def _target_role(self) -> str:
        me = self.app.my_profile
        return "host" if (me and me.role == "roomie") else "roomie"

    def _prepare_queue(self) -> None:
        # Invalidate stale caches that predate the host/roomie split. Without
        # this, a roomie would see an empty queue forever against old data.
        candidates = self.app.candidates
        if candidates:
            roles = {c.role for c in candidates}
            stale = (
                "host" not in roles
                or "roomie" not in roles
                or any(
                    "picsum.photos" in u
                    for c in candidates
                    for u in c.house_photo_urls
                )
            )
            if stale:
                self.app.save_candidates([])
                candidates = []
        if not candidates:
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
        me = self.app.my_profile
        target = self._target_role()
        queue = [
            c for c in self.app.candidates
            if c.role == target
            and c.id not in matched_ids
            and c.matches_filters(self.app.filters)
        ]
        if me is not None:
            queue.sort(key=lambda c: compatibility(me, c), reverse=True)
        self.queue = queue
        self.index = 0
        self._last_action = None
        self._refresh_undo_button()
        self._enable_actions()
        if not self.queue:
            who = "hosts" if target == "host" else "roomies"
            self._show_empty(
                f"No {who} match your filters.\n"
                "Try widening them or refreshing the list.",
            )
        else:
            self._render_current()

    def _render_current(self) -> None:
        if self.index >= len(self.queue):
            self._show_empty("You\u2019ve seen everyone. Try refreshing or loosening filters.")
            return

        p = self.queue[self.index]
        me = self.app.my_profile
        self._gallery_index = 0  # reset photo index for the new candidate

        if p.role == "host":
            self.badge_label.configure(text="HOST LISTING")
            price_txt = f"\u20ac{p.rent}/mo rent"
            self.bio_label.configure(text=p.house_description or "(no description)")
        else:
            self.badge_label.configure(text="LOOKING FOR A PLACE")
            price_txt = f"\u20ac{p.budget}/mo budget"
            self.bio_label.configure(text=p.bio)

        self.name_label.configure(text=f"{p.name}, {p.age}")
        self._update_host_avatar(p)

        if me is not None:
            self.score_label.configure(text=f"{compatibility(me, p)}% match")
        else:
            self.score_label.configure(text="")

        smoker_txt = "smoker" if p.smoker else "non-smoker"
        pets_txt = "pets ok" if p.pets else "no pets"
        meta_lines = [
            f"{price_txt}  \u2022  {p.schedule}  \u2022  {p.cleanliness}",
            f"{smoker_txt}  \u2022  {pets_txt}",
        ]
        if p.role == "host" and (p.rooms or p.bathrooms or p.square_meters):
            parts = []
            if p.rooms:
                parts.append(f"{p.rooms} bed")
            if p.bathrooms:
                parts.append(f"{p.bathrooms} bath")
            if p.square_meters:
                parts.append(f"{p.square_meters} m\u00b2")
            meta_lines.insert(1, "  \u2022  ".join(parts))
        self.meta_label.configure(text="\n".join(meta_lines))
        self._set_status("")
        self._update_gallery_controls(p)
        self._load_photo_async(p)

    def _show_empty(self, msg: str) -> None:
        self.badge_label.configure(text="")
        size = PORTRAIT_SIZE
        self._photo_ref = placeholder_image("?", size, 140)
        self.photo_label.configure(image=self._photo_ref)
        self.name_label.configure(text="No one here")
        self.host_avatar_label.pack_forget()
        self.score_label.configure(text="")
        self.meta_label.configure(text="")
        self.bio_label.configure(text=msg)
        self.photo_index_label.configure(text="")
        self.prev_photo_btn.configure(state="disabled")
        self.next_photo_btn.configure(state="disabled")
        self._set_status("")
        self._disable_actions()

    # --- photo loading ------------------------------------------------

    def _current_photo_url(self, profile: Profile) -> str:
        if profile.role == "host" and profile.house_photo_urls:
            idx = self._gallery_index % len(profile.house_photo_urls)
            return profile.house_photo_urls[idx]
        return profile.photo_url

    def _load_photo_async(self, profile: Profile) -> None:
        size = HOUSE_SIZE if profile.role == "host" else PORTRAIT_SIZE
        placeholder_letter = "H" if profile.role == "host" else profile.name[:1].upper()
        self._photo_ref = placeholder_image(placeholder_letter, size, 100)
        self.photo_label.configure(image=self._photo_ref)

        url = self._current_photo_url(profile)
        if not url:
            return
        expected_state = (profile.id, self._gallery_index)

        def worker(u=url, sz=size, state=expected_state):
            try:
                img = _load_image(u, sz)
            except (requests.RequestException, OSError):
                return
            self.after(0, lambda i=img, s=state: self._set_photo(s, i))

        threading.Thread(target=worker, daemon=True).start()

    def _set_photo(self, expected_state, pil_image: Image.Image) -> None:
        if self.index >= len(self.queue):
            return
        current = (self.queue[self.index].id, self._gallery_index)
        if current != expected_state:
            return  # user already swiped past this one or changed photo
        self._photo_ref = ImageTk.PhotoImage(pil_image)
        self.photo_label.configure(image=self._photo_ref)

    # --- gallery ------------------------------------------------------

    def _prev_photo(self) -> None:
        if self.index >= len(self.queue):
            return
        p = self.queue[self.index]
        if p.role != "host" or len(p.house_photo_urls) < 2:
            return
        self._gallery_index = (self._gallery_index - 1) % len(p.house_photo_urls)
        self._update_gallery_controls(p)
        self._load_photo_async(p)

    def _next_photo(self) -> None:
        if self.index >= len(self.queue):
            return
        p = self.queue[self.index]
        if p.role != "host" or len(p.house_photo_urls) < 2:
            return
        self._gallery_index = (self._gallery_index + 1) % len(p.house_photo_urls)
        self._update_gallery_controls(p)
        self._load_photo_async(p)

    def _update_host_avatar(self, profile: Profile) -> None:
        if profile.role != "host" or not profile.photo_url:
            self.host_avatar_label.pack_forget()
            return
        # Placeholder first so it renders immediately; real image loads async.
        initial = profile.name[:1].upper() if profile.name else "?"
        self._host_avatar_ref = placeholder_image(initial, HOST_AVATAR_SIZE, 26)
        self.host_avatar_label.configure(image=self._host_avatar_ref)
        try:
            self.host_avatar_label.pack(side="left", padx=(0, 10),
                                        before=self.name_label)
        except tk.TclError:
            self.host_avatar_label.pack(side="left", padx=(0, 10))

        url = profile.photo_url
        expected_state = (profile.id, self._gallery_index)

        def worker(u=url, state=expected_state):
            try:
                img = _load_image(u, HOST_AVATAR_SIZE)
            except (requests.RequestException, OSError):
                return
            self.after(0, lambda i=img, s=state: self._apply_host_avatar(s, i))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_host_avatar(self, expected_state, pil_image: Image.Image) -> None:
        if self.index >= len(self.queue):
            return
        current = (self.queue[self.index].id, self._gallery_index)
        if current[0] != expected_state[0]:
            return
        self._host_avatar_ref = ImageTk.PhotoImage(pil_image)
        self.host_avatar_label.configure(image=self._host_avatar_ref)

    def _update_gallery_controls(self, profile: Profile) -> None:
        if profile.role == "host" and len(profile.house_photo_urls) > 1:
            n = len(profile.house_photo_urls)
            self.photo_index_label.configure(text=f"{self._gallery_index + 1} / {n}")
            self.prev_photo_btn.configure(state="normal")
            self.next_photo_btn.configure(state="normal")
        else:
            self.photo_index_label.configure(text="")
            self.prev_photo_btn.configure(state="disabled")
            self.next_photo_btn.configure(state="disabled")

    # --- actions ------------------------------------------------------

    def _on_like(self) -> None:
        if self.index >= len(self.queue):
            return
        candidate = self.queue[self.index]
        self.app.add_match(candidate)
        self._last_action = ("like", candidate)
        self._refresh_undo_button()
        self._set_status("")
        if self.app.my_profile is not None:
            MatchModal(self, self.app.my_profile, candidate, on_close=self._advance)
        else:
            self._advance()

    def _on_pass(self) -> None:
        if self.index < len(self.queue):
            self._last_action = ("pass", self.queue[self.index])
            self._refresh_undo_button()
        self._advance()

    def _on_undo(self) -> None:
        if self._last_action is None or self.index == 0:
            return
        kind, profile = self._last_action
        if kind == "like":
            self.app.remove_match(profile)
        self.index -= 1
        self._last_action = None
        self._refresh_undo_button()
        self._set_status("Undid last action.")
        self._render_current()

    def _advance(self) -> None:
        self.index += 1
        self._render_current()

    def _refresh(self) -> None:
        self._set_status("Refreshing candidates \u2026")
        self._disable_actions()
        threading.Thread(target=self._download_initial, daemon=True).start()

    def _refresh_undo_button(self) -> None:
        if self._last_action is not None and self.index > 0:
            self.undo_btn.state(["!disabled"])
        else:
            self.undo_btn.state(["disabled"])

    # --- helpers ------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _disable_actions(self) -> None:
        self.like_btn.state(["disabled"])
        self.pass_btn.state(["disabled"])
        self.undo_btn.state(["disabled"])

    def _enable_actions(self) -> None:
        self.like_btn.state(["!disabled"])
        self.pass_btn.state(["!disabled"])
        self._refresh_undo_button()
