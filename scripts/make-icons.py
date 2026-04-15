#!/usr/bin/env python3
"""
make-icons.py — Generate PWA icons for the EuroPCR app.
Uses Pillow to draw the icons (no external dependencies besides PIL).

Produces:
  app/icons/icon-192.png
  app/icons/icon-512.png
  app/icons/icon-maskable-512.png  (safe zone padding)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
ICONS_DIR = ROOT / "app" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)


def render_icon(size: int, maskable: bool = False) -> Image.Image:
    """Draw a 512x512 canvas then downsample if needed."""
    canvas = 1024  # draw at higher res for quality
    img = Image.new("RGB", (canvas, canvas), "#0b1d3a")
    draw = ImageDraw.Draw(img)

    # Gradient background (simple manual)
    for y in range(canvas):
        t = y / canvas
        r = int(0x0b + (0x1e - 0x0b) * t)
        g = int(0x1d + (0x3a - 0x1d) * t)
        b = int(0x3a + (0x8a - 0x3a) * t)
        draw.line([(0, y), (canvas, y)], fill=(r, g, b))

    # Rounded rect mask (only if NOT maskable; maskable keeps full square)
    if not maskable:
        mask = Image.new("L", (canvas, canvas), 0)
        mdraw = ImageDraw.Draw(mask)
        radius = int(canvas * 0.19)
        mdraw.rounded_rectangle([0, 0, canvas, canvas], radius=radius, fill=255)
        bg = Image.new("RGB", (canvas, canvas), "#ffffff")
        img_masked = Image.composite(img, bg, mask)
        img = img_masked

    draw = ImageDraw.Draw(img)

    # Safe zone for maskable: content must fit within center 80%
    safe_pad = 0.12 if maskable else 0.05
    margin = int(canvas * safe_pad)
    cx, cy = canvas // 2, canvas // 2

    # Stylized heart (two symmetric arcs)
    heart_w = int(canvas * 0.55)
    heart_h = int(canvas * 0.55)
    # Draw as filled polygon (heart shape)
    # Simple heart: two circles + triangle
    from math import sin, cos, pi

    def heart_points(cx, cy, w, h):
        pts = []
        for t in range(0, 360):
            a = t * pi / 180
            x = 16 * (sin(a) ** 3)
            y = 13 * cos(a) - 5 * cos(2 * a) - 2 * cos(3 * a) - cos(4 * a)
            pts.append((cx + x * w / 32, cy - y * h / 28))
        return pts

    heart_pts = heart_points(cx, cy - int(canvas * 0.02), heart_w, heart_h)
    draw.polygon(heart_pts, fill="#dc2626")

    # Horizontal "catheter" line
    line_y = cy + int(canvas * 0.02)
    line_pad = int(canvas * 0.18) if maskable else int(canvas * 0.12)
    draw.rounded_rectangle(
        [line_pad, line_y - 12, canvas - line_pad, line_y + 12],
        radius=12, fill="#fbbf24"
    )

    # ECG spike
    spike_x = cx
    draw.line(
        [(spike_x - 40, line_y),
         (spike_x - 10, line_y - 60),
         (spike_x + 15, line_y + 30),
         (spike_x + 45, line_y)],
        fill="#fbbf24", width=14, joint="curve"
    )

    # Text "EuroPCR" + "'26"
    try:
        font_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(canvas * 0.11))
        font_year = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(canvas * 0.06))
    except OSError:
        font_main = ImageFont.load_default()
        font_year = ImageFont.load_default()

    text_y = int(canvas * 0.80) if not maskable else int(canvas * 0.78)
    bbox = draw.textbbox((0, 0), "EuroPCR", font=font_main)
    text_w = bbox[2] - bbox[0]
    draw.text(((canvas - text_w) // 2, text_y), "EuroPCR",
              font=font_main, fill="#e8ecf5")

    year_y = text_y + int(canvas * 0.09)
    bbox = draw.textbbox((0, 0), "'26", font=font_year)
    text_w = bbox[2] - bbox[0]
    draw.text(((canvas - text_w) // 2, year_y), "'26",
              font=font_year, fill="#fbbf24")

    # Downsample to requested size
    img = img.resize((size, size), Image.LANCZOS)
    return img


def main():
    sizes = [
        (192, "icon-192.png", False),
        (512, "icon-512.png", False),
        (512, "icon-maskable-512.png", True),
    ]
    for size, name, maskable in sizes:
        img = render_icon(size, maskable=maskable)
        out = ICONS_DIR / name
        img.save(out, "PNG", optimize=True)
        print(f"Wrote {out.name} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
