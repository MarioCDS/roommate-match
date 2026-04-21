"""Match reveal modal: Tinder-style, two photos side by side."""
from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

import requests
from PIL import Image, ImageTk

from models import Profile
from ui.common import BG, PRIMARY, TEXT, MUTED, placeholder_image

AVATAR_SIZE = (170, 170)


class MatchModal(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        my_profile: Profile,
        other: Profile,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("It's a Match")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._on_close = on_close
        self._photo_refs: list[ImageTk.PhotoImage] = []

        # Modal behaviour: float above parent, block parent interactions.
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build(my_profile, other)
        self._center(parent)

    def _center(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self, my: Profile, other: Profile) -> None:
        tk.Label(self, text="It's a Match!", bg=BG, fg=PRIMARY,
                 font=("Segoe UI", 28, "bold")).pack(pady=(26, 4))
        other_first = other.name.split()[0] if other.name else "them"
        tk.Label(
            self,
            text=f"You and {other_first} could make great roommates.",
            bg=BG, fg=MUTED, font=("Segoe UI", 10),
            wraplength=360, justify="center",
        ).pack(pady=(0, 18), padx=30)

        photos = tk.Frame(self, bg=BG)
        photos.pack(pady=6, padx=28)

        my_slot = self._slot(photos, my, side="left")
        tk.Label(photos, text="\u2022", bg=BG, fg=PRIMARY,
                 font=("Segoe UI", 28)).pack(side="left", padx=8)
        other_slot = self._slot(photos, other, side="left")

        self._load(my, my_slot)
        self._load(other, other_slot)

        ttk.Button(
            self, text="Keep swiping", style="Primary.TButton",
            command=self._close, width=18,
        ).pack(pady=(24, 22))

    def _slot(self, parent: tk.Widget, profile: Profile, side: str) -> tk.Label:
        slot = tk.Frame(parent, bg=BG)
        slot.pack(side=side, padx=10)
        initial = (profile.name[:1] if profile.name else "?").upper()
        ph = placeholder_image(initial, AVATAR_SIZE, 70)
        self._photo_refs.append(ph)
        lbl = tk.Label(slot, image=ph, bg=BG, bd=0)
        lbl.pack()
        first = (profile.name.split()[0] if profile.name else "?")
        tk.Label(slot, text=first, bg=BG, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(8, 0))
        return lbl

    def _load(self, profile: Profile, label: tk.Label) -> None:
        src = profile.photo_url
        if not src:
            return

        def worker(path=src):
            try:
                if path.startswith(("http://", "https://")):
                    resp = requests.get(path, timeout=8)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content))
                else:
                    img = Image.open(path)
                img = img.convert("RGB").resize(AVATAR_SIZE)
            except (requests.RequestException, OSError):
                return
            self.after(0, lambda i=img: self._apply(label, i))

        threading.Thread(target=worker, daemon=True).start()

    def _apply(self, label: tk.Label, img: Image.Image) -> None:
        if not label.winfo_exists():
            return
        photo = ImageTk.PhotoImage(img)
        self._photo_refs.append(photo)
        label.configure(image=photo)

    def _close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        if self._on_close:
            self._on_close()
