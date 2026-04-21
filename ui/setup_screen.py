"""Profile setup form: role selector + common fields + role-specific fields."""
from __future__ import annotations

import tkinter as tk
import uuid
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from PIL import Image, ImageTk

from models import (
    Profile, SCHEDULES, CLEANLINESS_LEVELS, avatar_url, house_photo_gallery,
)
from storage import avatar_path
from ui.common import BG, CARD_BG, BORDER, placeholder_image


AVATAR_PREVIEW_SIZE = (84, 84)


class SetupScreen(tk.Frame):
    def __init__(self, parent, app, first_run: bool = False) -> None:
        super().__init__(parent, bg=BG)
        self.app = app
        self.first_run = first_run
        existing = app.my_profile

        title_text = "Welcome! Create your profile" if first_run else "Edit your profile"
        ttk.Label(self, text=title_text, style="Title.TLabel").pack(
            padx=24, pady=(16, 4), anchor="w",
        )
        ttk.Label(
            self,
            text="This info is shown to other people when they swipe on you.",
            style="TLabel", wraplength=440,
        ).pack(padx=24, pady=(0, 8), anchor="w")

        self.role_var = tk.StringVar(value=existing.role if existing else "roomie")
        role_card = tk.Frame(self, bg=CARD_BG, bd=0, highlightthickness=1,
                             highlightbackground=BORDER)
        role_card.pack(padx=24, pady=(0, 10), fill="x")
        ttk.Label(role_card, text="I'm a:", style="H2.TLabel",
                  background=CARD_BG).pack(padx=14, pady=(10, 4), anchor="w")
        radio_row = tk.Frame(role_card, bg=CARD_BG)
        radio_row.pack(padx=14, pady=(0, 12), anchor="w")
        ttk.Radiobutton(
            radio_row, text="Roomie - looking for a place",
            variable=self.role_var, value="roomie",
            command=self._rebuild_role_section,
        ).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(
            radio_row, text="Host - have a place to offer",
            variable=self.role_var, value="host",
            command=self._rebuild_role_section,
        ).pack(side="left")

        form = tk.Frame(self, bg=BG)
        form.pack(padx=24, pady=6, fill="x")

        self.name_var = tk.StringVar(value=existing.name if existing else "")
        self.age_var = tk.StringVar(value=str(existing.age) if existing else "")
        self.email_var = tk.StringVar(value=existing.email if existing else "")
        self.smoker_var = tk.BooleanVar(value=existing.smoker if existing else False)
        self.pets_var = tk.BooleanVar(value=existing.pets if existing else False)
        self.schedule_var = tk.StringVar(
            value=existing.schedule if existing else SCHEDULES[2],
        )
        self.cleanliness_var = tk.StringVar(
            value=existing.cleanliness if existing else CLEANLINESS_LEVELS[1],
        )
        self.budget_var = tk.IntVar(value=existing.budget if existing else 500)
        self.rent_var = tk.IntVar(
            value=existing.rent if existing and existing.rent else 500,
        )
        self.rooms_var = tk.IntVar(
            value=existing.rooms if existing and existing.rooms else 2,
        )
        self.bathrooms_var = tk.IntVar(
            value=existing.bathrooms if existing and existing.bathrooms else 1,
        )
        self.sqm_var = tk.IntVar(
            value=existing.square_meters if existing and existing.square_meters else 60,
        )
        self.house_desc_widget: tk.Text | None = None

        # Photo state
        self.photo_url_var = tk.StringVar(
            value=existing.photo_url if existing else "",
        )
        self._avatar_preview_ref: ImageTk.PhotoImage | None = None

        row = 0
        # ---- photo upload row ---------------------------------------
        ttk.Label(form, text="Profile photo", style="TLabel").grid(
            row=row, column=0, sticky="w", pady=6,
        )
        photo_row = tk.Frame(form, bg=BG)
        photo_row.grid(row=row, column=1, sticky="w", pady=6, padx=(10, 0))
        self.avatar_preview = tk.Label(
            photo_row, bg=BG, bd=0, highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.avatar_preview.pack(side="left")
        self._refresh_avatar_preview()

        upload_col = tk.Frame(photo_row, bg=BG)
        upload_col.pack(side="left", padx=(10, 0))
        ttk.Button(upload_col, text="Upload\u2026",
                   command=self._upload_photo).pack(anchor="w")
        ttk.Button(upload_col, text="Use default",
                   command=self._use_default_avatar).pack(anchor="w", pady=(4, 0))
        row += 1

        self._row(form, row, "Name",
                  ttk.Entry(form, textvariable=self.name_var, width=34))
        row += 1
        self._row(form, row, "Age",
                  ttk.Entry(form, textvariable=self.age_var, width=10))
        row += 1
        self._row(form, row, "Email",
                  ttk.Entry(form, textvariable=self.email_var, width=34))
        row += 1

        ttk.Label(form, text="Smoker", style="TLabel").grid(
            row=row, column=0, sticky="w", pady=6,
        )
        ttk.Checkbutton(form, variable=self.smoker_var).grid(
            row=row, column=1, sticky="w", pady=6,
        )
        row += 1

        ttk.Label(form, text="Has pets", style="TLabel").grid(
            row=row, column=0, sticky="w", pady=6,
        )
        ttk.Checkbutton(form, variable=self.pets_var).grid(
            row=row, column=1, sticky="w", pady=6,
        )
        row += 1

        self._row(
            form, row, "Schedule",
            ttk.Combobox(form, textvariable=self.schedule_var, values=SCHEDULES,
                         state="readonly", width=20),
        )
        row += 1
        self._row(
            form, row, "Cleanliness",
            ttk.Combobox(form, textvariable=self.cleanliness_var,
                         values=CLEANLINESS_LEVELS, state="readonly", width=20),
        )
        row += 1

        self.role_section = tk.Frame(form, bg=BG)
        self.role_section.grid(row=row, column=0, columnspan=2, sticky="ew",
                               pady=(10, 4))
        row += 1

        ttk.Label(form, text="Bio", style="TLabel").grid(
            row=row, column=0, sticky="nw", pady=6,
        )
        bio_wrap = tk.Frame(form, bg=BORDER, bd=0, highlightthickness=1,
                            highlightbackground=BORDER)
        bio_wrap.grid(row=row, column=1, sticky="w", pady=6, padx=(10, 0))
        self.bio_widget = tk.Text(
            bio_wrap, width=40, height=4, wrap="word",
            font=("Segoe UI", 10), relief="flat", bd=4, bg=CARD_BG,
        )
        self.bio_widget.pack()
        if existing and existing.bio:
            self.bio_widget.insert("1.0", existing.bio)

        self._render_role_fields()

        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=18)
        ttk.Button(btns, text="Save and continue", style="Primary.TButton",
                   command=self._save).pack(side="left", padx=6)
        if not first_run:
            ttk.Button(btns, text="Cancel", command=app.show_swipe).pack(
                side="left", padx=6,
            )

    # --- photo handling ----------------------------------------------

    def _upload_photo(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a profile photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB")
        except OSError:
            messagebox.showerror("Upload failed", "Could not read that image.")
            return
        # Crop to a square centred on the shorter side, then resize to 500.
        w, h = img.size
        side = min(w, h)
        img = img.crop(((w - side) // 2, (h - side) // 2,
                       (w + side) // 2, (h + side) // 2)).resize((500, 500))
        user = self.app.current_user
        if not user:
            messagebox.showerror("Not logged in", "Log in before uploading a photo.")
            return
        dest = avatar_path(user)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="JPEG", quality=90)
        self.photo_url_var.set(str(dest))
        self._refresh_avatar_preview()

    def _use_default_avatar(self) -> None:
        existing = self.app.my_profile
        pid = existing.id if existing else "preview"
        self.photo_url_var.set(avatar_url(pid))
        self._refresh_avatar_preview()

    def _refresh_avatar_preview(self) -> None:
        url = self.photo_url_var.get()
        letter = (self.name_var.get()[:1] if self.name_var.get() else "?").upper()
        try:
            if url and Path(url).exists():
                img = Image.open(url).convert("RGB").resize(AVATAR_PREVIEW_SIZE)
                self._avatar_preview_ref = ImageTk.PhotoImage(img)
            else:
                # Remote or unset: show a placeholder; real load happens later.
                self._avatar_preview_ref = placeholder_image(
                    letter, AVATAR_PREVIEW_SIZE, 40,
                )
        except OSError:
            self._avatar_preview_ref = placeholder_image(
                letter, AVATAR_PREVIEW_SIZE, 40,
            )
        self.avatar_preview.configure(image=self._avatar_preview_ref)

    # --- role section ------------------------------------------------

    def _rebuild_role_section(self) -> None:
        for child in self.role_section.winfo_children():
            child.destroy()
        self.house_desc_widget = None
        self._render_role_fields()

    def _render_role_fields(self) -> None:
        parent = self.role_section
        if self.role_var.get() == "host":
            ttk.Label(parent, text="Monthly rent you charge (\u20ac)",
                      style="H2.TLabel").grid(row=0, column=0, sticky="w",
                                              pady=(4, 2))
            tk.Scale(
                parent, from_=200, to=2000, orient="horizontal", resolution=25,
                variable=self.rent_var, length=260, bg=BG, highlightthickness=0,
            ).grid(row=1, column=0, sticky="w")

            # Rooms / bathrooms / square meters on one row.
            specs = tk.Frame(parent, bg=BG)
            specs.grid(row=2, column=0, sticky="w", pady=(12, 4))
            ttk.Label(specs, text="Bedrooms", style="TLabel").grid(row=0, column=0,
                                                                    sticky="w")
            tk.Spinbox(specs, from_=1, to=8, width=4,
                       textvariable=self.rooms_var).grid(row=1, column=0,
                                                         sticky="w", padx=(0, 14))
            ttk.Label(specs, text="Bathrooms", style="TLabel").grid(row=0, column=1,
                                                                     sticky="w")
            tk.Spinbox(specs, from_=1, to=5, width=4,
                       textvariable=self.bathrooms_var).grid(row=1, column=1,
                                                              sticky="w",
                                                              padx=(0, 14))
            ttk.Label(specs, text="Size (m\u00b2)", style="TLabel").grid(row=0,
                                                                          column=2,
                                                                          sticky="w")
            tk.Spinbox(specs, from_=20, to=400, increment=5, width=6,
                       textvariable=self.sqm_var).grid(row=1, column=2, sticky="w")

            ttk.Label(parent, text="About the place", style="H2.TLabel").grid(
                row=3, column=0, sticky="w", pady=(10, 2),
            )
            hd_wrap = tk.Frame(parent, bg=BORDER, bd=0, highlightthickness=1,
                               highlightbackground=BORDER)
            hd_wrap.grid(row=4, column=0, sticky="w")
            self.house_desc_widget = tk.Text(
                hd_wrap, width=40, height=4, wrap="word",
                font=("Segoe UI", 10), relief="flat", bd=4, bg=CARD_BG,
            )
            self.house_desc_widget.pack()
            existing = self.app.my_profile
            if existing and existing.house_description:
                self.house_desc_widget.insert("1.0", existing.house_description)

            ttk.Label(
                parent,
                text="A gallery of 4 stock room photos is attached automatically.",
                style="TLabel", foreground="#6B7280", wraplength=400,
            ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        else:
            ttk.Label(parent, text="Your budget (\u20ac/mo)",
                      style="H2.TLabel").grid(row=0, column=0, sticky="w",
                                              pady=(4, 2))
            tk.Scale(
                parent, from_=200, to=1500, orient="horizontal", resolution=25,
                variable=self.budget_var, length=260, bg=BG, highlightthickness=0,
            ).grid(row=1, column=0, sticky="w")

    def _row(self, parent, row, label, widget) -> None:
        ttk.Label(parent, text=label, style="TLabel").grid(
            row=row, column=0, sticky="w", pady=6,
        )
        widget.grid(row=row, column=1, sticky="w", pady=6, padx=(10, 0))

    # --- save --------------------------------------------------------

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
        role = self.role_var.get()

        existing = self.app.my_profile
        pid = existing.id if existing else str(uuid.uuid4())
        photo = self.photo_url_var.get() or avatar_url(pid)

        if role == "host":
            rent = int(self.rent_var.get())
            house_desc = ""
            if self.house_desc_widget is not None:
                house_desc = self.house_desc_widget.get("1.0", "end-1c").strip()
            house_desc = house_desc or "Comfortable place."
            gallery = (
                list(existing.house_photo_urls)
                if existing and existing.house_photo_urls
                else house_photo_gallery(pid)
            )
            profile = Profile(
                id=pid, name=name, age=age, photo_url=photo, email=email,
                budget=rent, smoker=bool(self.smoker_var.get()),
                schedule=self.schedule_var.get(), bio=bio,
                pets=bool(self.pets_var.get()),
                cleanliness=self.cleanliness_var.get(),
                role="host", rent=rent,
                house_description=house_desc, house_photo_urls=gallery,
                rooms=int(self.rooms_var.get()),
                bathrooms=int(self.bathrooms_var.get()),
                square_meters=int(self.sqm_var.get()),
            )
        else:
            budget = int(self.budget_var.get())
            profile = Profile(
                id=pid, name=name, age=age, photo_url=photo, email=email,
                budget=budget, smoker=bool(self.smoker_var.get()),
                schedule=self.schedule_var.get(), bio=bio,
                pets=bool(self.pets_var.get()),
                cleanliness=self.cleanliness_var.get(),
                role="roomie", rent=0,
                house_description="", house_photo_urls=[],
            )

        self.app.save_my_profile(profile)

        if self.first_run:
            self.app.show_filters()
        else:
            self.app.show_swipe()
