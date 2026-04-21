"""Shared UI constants and helpers used by every screen."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageTk

# Palette (kept here so every screen can import from one place)
BG = "#F7F8FA"
CARD_BG = "#FFFFFF"
PRIMARY = "#4F46E5"        # indigo: utility/trust vibe, not dating-app pink
PRIMARY_DARK = "#4338CA"
TEXT = "#2B2D42"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
LIKE_GREEN = "#10B981"
GREY = "#9E9E9E"

_PLACEHOLDER_COLORS = [
    "#4F46E5", "#0EA5E9", "#10B981",
    "#F59E0B", "#8B5CF6", "#14B8A6",
]


def placeholder_image(letter: str, size: tuple[int, int], font_size: int) -> ImageTk.PhotoImage:
    """Draw an initial on a coloured square as a photo fallback."""
    color = _PLACEHOLDER_COLORS[hash(letter) % len(_PLACEHOLDER_COLORS)]
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    text = letter or "?"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size[0] - w) / 2 - bbox[0], (size[1] - h) / 2 - bbox[1]),
        text, fill="white", font=font,
    )
    return ImageTk.PhotoImage(img)
