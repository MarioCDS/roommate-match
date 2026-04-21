"""Tkinter chat window: Toplevel dialog for one match conversation."""
from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import requests
from PIL import Image, ImageTk

from chat import append_message, load_chat, maybe_canned_reply
from models import Profile
from ui.common import BG, CARD_BG, BORDER, PRIMARY, TEXT, MUTED, placeholder_image


HEADER_AVATAR = (48, 48)


class ChatWindow(tk.Toplevel):
    def __init__(self, parent: tk.Widget, app, peer: Profile) -> None:
        super().__init__(parent)
        self.app = app
        self.peer = peer
        self._photo_refs: list[ImageTk.PhotoImage] = []
        self._avatar_ref: ImageTk.PhotoImage | None = None

        self.title(f"Chat with {peer.name}")
        self.configure(bg=BG)
        self.geometry("480x560")
        self.minsize(400, 460)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build()
        self._render_messages()

    # --- layout ------------------------------------------------------

    def _build(self) -> None:
        header = tk.Frame(self, bg=PRIMARY, height=64)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        self.avatar_label = tk.Label(header, bg=PRIMARY, bd=0)
        self.avatar_label.pack(side="left", padx=(12, 10), pady=8)
        placeholder = placeholder_image(
            (self.peer.name[:1] if self.peer.name else "?").upper(),
            HEADER_AVATAR, 26,
        )
        self._avatar_ref = placeholder
        self.avatar_label.configure(image=placeholder)
        if self.peer.photo_url:
            threading.Thread(target=self._load_avatar, daemon=True).start()

        text_col = tk.Frame(header, bg=PRIMARY)
        text_col.pack(side="left", fill="both", expand=True, pady=8)
        tk.Label(
            text_col, text=self.peer.name, bg=PRIMARY, fg="white",
            font=("Segoe UI", 12, "bold"), anchor="w",
        ).pack(anchor="w")
        role_tag = "Host" if self.peer.role == "host" else "Roomie"
        price = (
            f"\u20ac{self.peer.rent}/mo rent" if self.peer.role == "host"
            else f"\u20ac{self.peer.budget}/mo budget"
        )
        tk.Label(
            text_col, text=f"{role_tag}  \u00b7  {price}", bg=PRIMARY,
            fg="#C7D2FE", font=("Segoe UI", 9), anchor="w",
        ).pack(anchor="w")

        tk.Button(
            header, text="Close", command=self._close, bd=0, relief="flat",
            bg=PRIMARY, fg="white", activebackground="#4338CA",
            activeforeground="white", font=("Segoe UI", 10, "bold"),
            padx=10, pady=4, cursor="hand2",
        ).pack(side="right", padx=10)

        # Scrollable message area.
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scroll.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._messages_frame = tk.Frame(self._canvas, bg=BG)
        self._messages_window = self._canvas.create_window(
            (0, 0), window=self._messages_frame, anchor="nw",
        )

        def _on_configure(_event=None):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfigure(
                self._messages_window, width=self._canvas.winfo_width(),
            )

        self._messages_frame.bind("<Configure>", _on_configure)
        self._canvas.bind("<Configure>", _on_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Input bar.
        input_bar = tk.Frame(self, bg=CARD_BG, bd=0, highlightthickness=1,
                             highlightbackground=BORDER)
        input_bar.pack(side="bottom", fill="x")
        self.entry_var = tk.StringVar()
        entry = tk.Entry(
            input_bar, textvariable=self.entry_var, font=("Segoe UI", 10),
            relief="flat", bd=8, bg=CARD_BG, fg=TEXT,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        entry.bind("<Return>", self._on_send)
        ttk.Button(input_bar, text="Send", style="Primary.TButton",
                   command=self._on_send).pack(side="right", padx=8, pady=6)
        entry.focus_set()

    # --- messages ----------------------------------------------------

    def _render_messages(self) -> None:
        for child in self._messages_frame.winfo_children():
            child.destroy()
        self._photo_refs = [self._avatar_ref] if self._avatar_ref else []

        messages = load_chat(self.app.current_user, self.peer.id)
        if not messages:
            tk.Label(
                self._messages_frame,
                text=(
                    "No messages yet. Say hi to get things started.\n"
                    "Replies are canned responses for demo purposes."
                ),
                bg=BG, fg=MUTED, font=("Segoe UI", 9, "italic"),
                justify="center", wraplength=380,
            ).pack(pady=30)
            return

        for msg in messages:
            self._add_bubble(msg)

        # Scroll to the bottom after the layout settles.
        self.after(50, lambda: self._canvas.yview_moveto(1.0))

    def _add_bubble(self, msg: dict) -> None:
        is_me = msg["from"] == "me"
        side = "right" if is_me else "left"
        bg = PRIMARY if is_me else "#E5E7EB"
        fg = "white" if is_me else TEXT

        row = tk.Frame(self._messages_frame, bg=BG)
        row.pack(fill="x", padx=10, pady=4)

        bubble = tk.Label(
            row, text=msg["text"], bg=bg, fg=fg,
            font=("Segoe UI", 10), wraplength=300, justify="left",
            padx=12, pady=8, anchor="w",
        )
        bubble.pack(side=side)

        stamp = ""
        try:
            ts = datetime.fromisoformat(msg.get("ts", ""))
            stamp = ts.strftime("%H:%M")
        except ValueError:
            pass
        if stamp:
            tk.Label(
                row, text=stamp, bg=BG, fg=MUTED,
                font=("Segoe UI", 8), padx=4,
            ).pack(side=side)

    def _on_send(self, _event=None) -> None:
        text = self.entry_var.get().strip()
        if not text:
            return
        self.entry_var.set("")
        append_message(self.app.current_user, self.peer.id, "me", text)
        reply = maybe_canned_reply()
        if reply:
            # A tiny delay makes it feel less instant without blocking the UI.
            append_message(self.app.current_user, self.peer.id, "them", reply)
        self._render_messages()

    # --- avatar ------------------------------------------------------

    def _load_avatar(self) -> None:
        try:
            if self.peer.photo_url.startswith(("http://", "https://")):
                resp = requests.get(self.peer.photo_url, timeout=8)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content))
            else:
                img = Image.open(self.peer.photo_url)
            img = img.convert("RGB").resize(HEADER_AVATAR)
        except (requests.RequestException, OSError):
            return
        self.after(0, lambda i=img: self._apply_avatar(i))

    def _apply_avatar(self, pil_image: Image.Image) -> None:
        if not self.avatar_label.winfo_exists():
            return
        photo = ImageTk.PhotoImage(pil_image)
        self._avatar_ref = photo
        self.avatar_label.configure(image=photo)

    # --- misc --------------------------------------------------------

    def _on_mousewheel(self, event) -> None:
        if not self._canvas.winfo_exists():
            return
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _close(self) -> None:
        try:
            self._canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.destroy()
