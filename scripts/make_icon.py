"""Generate all JKT48Verse icon assets from the reference logo design.

The reference is frontend/public/jkt48verse-icon.png (1024x1024): a red
diagonal-gradient squircle with the "JKT48 / VERSE" wordmark, a tilted
orbit ring and a sparkle star. This script renders that design from
scratch (4x supersampled) and emits every size referenced by
frontend/app/layout.tsx and frontend/app/manifest.ts:

  jkt48verse-icon.png        1024x1024  master, transparent squircle
  jv-favicon-16.png           16x16     favicon
  jv-favicon-32.png           32x32     favicon
  jv-apple-icon-180.png       180x180   apple-touch-icon
  jv-icon-192.png             192x192   PWA icon (purpose "any")
  jv-icon-512.png             512x512   PWA icon (purpose "any")
  jv-icon-maskable-192.png    192x192   PWA maskable (full-bleed bg, safe-zone content)
  jv-icon-maskable-512.png    512x512   PWA maskable (full-bleed bg, safe-zone content)

Usage:
  python scripts/make_icon.py                    # regenerate everything into frontend/public
  python scripts/make_icon.py --out some/dir     # write all assets into another dir
  python scripts/make_icon.py --master icon.png  # write only the 1024 master

Requires: Pillow  ->  pip install Pillow
Fonts:    bundled at scripts/fonts/ (Roboto, Apache-2.0). No network needed.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required but not installed. Run: pip install Pillow")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PUBLIC_DEFAULT = ROOT / "frontend" / "public"

SIZE = 1024  # master render size
SS = 4       # supersample factor

RED_TL = (0xE1, 0x19, 0x27)
RED_BR = (0x9E, 0x0F, 0x1B)
NAVY = (0x0F, 0x17, 0x2A)
WHITE = (255, 255, 255)

# filename -> (kind, size); kind: "any" (transparent squircle) | "maskable" (full-bleed)
ASSETS = {
    "jkt48verse-icon.png": ("any", 1024),
    "jv-favicon-16.png": ("any", 16),
    "jv-favicon-32.png": ("any", 32),
    "jv-apple-icon-180.png": ("any", 180),
    "jv-icon-192.png": ("any", 192),
    "jv-icon-512.png": ("any", 512),
    "jv-icon-maskable-192.png": ("maskable", 192),
    "jv-icon-maskable-512.png": ("maskable", 512),
}

FONT_BLACK = "Roboto-Black.ttf"
FONT_SEMI = "Roboto-Medium.ttf"


def find_font(name: str) -> Path:
    """Locate a font file. Bundled scripts/fonts/ wins; a few fallbacks follow."""
    candidates = [
        HERE / "fonts" / name,
        ROOT / "scripts" / "fonts" / name,
        Path("/tmp/fonts") / name,
        Path("/usr/share/fonts/truetype/roboto") / name,
        Path("/usr/local/share/fonts/roboto") / name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    sys.exit(
        f"Font '{name}' not found. Bundle it at scripts/fonts/{name} "
        "(Roboto is Apache-2.0; e.g. from fonts.google.com/roboto) and re-run."
    )


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def squircle_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def diagonal_gradient(size):
    # 1-D gradient along the diagonal, rotated 45deg onto a square canvas
    n = 1024
    strip = Image.new("RGB", (n, 1))
    px = strip.load()
    for i in range(n):
        px[i, 0] = lerp(RED_TL, RED_BR, i / (n - 1))
    diag = int(n * math.sqrt(2)) + 4
    g = strip.resize((diag, diag), Image.BILINEAR)  # horizontal gradient
    g = g.rotate(-45, resample=Image.BICUBIC, expand=True)
    gw, gh = g.size
    box = ((gw - n) // 2, (gh - n) // 2, (gw + n) // 2, (gh + n) // 2)
    return g.crop(box).resize((size, size), Image.BICUBIC)


def navy_glow(size):
    # subtle radial navy glow in the bottom-right corner
    n = 256
    layer = Image.new("L", (n, n), 0)
    px = layer.load()
    cx, cy, r = n * 0.98, n * 0.98, n * 0.85
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - cx, y - cy) / r
            if d < 1:
                px[x, y] = int(255 * (1 - d) ** 2 * 0.42)
    return layer.resize((size, size), Image.BICUBIC)


def text_layer(text, font_path, font_px, tracking, target_width=None):
    """Render text with letter-spacing; return RGBA image cropped to glyph bounds."""
    font = ImageFont.truetype(str(font_path), font_px)
    widths = [font.getlength(ch) for ch in text]
    if target_width is not None:
        total_adv = sum(widths)
        tracking = (target_width - total_adv) / (len(text) - 1)
    total = sum(widths) + tracking * (len(text) - 1)
    asc, desc = font.getmetrics()
    img = Image.new("RGBA", (int(total) + font_px, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0
    for i, ch in enumerate(text):
        d.text((x, 10), ch, font=font, fill=WHITE)
        x += widths[i] + tracking
    return img.crop(img.getbbox())


def star(draw, cx, cy, r_out, r_in, fill):
    pts = []
    for i in range(8):
        ang = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0)
        rad = r_out if i % 2 == 0 else r_in
        pts.append((cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def render(size=SIZE, maskable=False):
    """Render the logo at `size` px. maskable=True -> full-bleed background with
    content pulled into the 80% adaptive-icon safe zone."""
    W = size * SS
    if maskable:
        bg_px, content_px, rounded = W, int(W * 0.78), False
    else:
        bg_px = content_px = int(W * 0.90)
        rounded = True

    canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    # --- background: red diagonal gradient + navy glow
    bg = diagonal_gradient(bg_px).convert("RGBA")
    glow = navy_glow(bg_px)
    navy = Image.new("RGBA", (bg_px, bg_px), NAVY + (255,))
    bg = Image.composite(navy, bg, glow)
    if rounded:
        bg.putalpha(squircle_mask(bg_px, int(bg_px * 0.22)))
        off = (W - bg_px) // 2
        canvas.alpha_composite(bg, (off, off))
    else:
        canvas.alpha_composite(bg, (0, 0))

    # --- wordmark "JKT48 / VERSE", sized relative to content_px
    black = find_font(FONT_BLACK)
    semi = find_font(FONT_SEMI)
    line1 = text_layer("JKT48", black, int(content_px * 0.245), tracking=-content_px * 0.006)
    line2 = text_layer("VERSE", semi, int(content_px * 0.105), tracking=0, target_width=line1.width)
    gap = int(content_px * 0.035)
    block_h = line1.height + gap + line2.height
    cx = W // 2
    top = W // 2 - block_h // 2
    canvas.alpha_composite(line1, (cx - line1.width // 2, top))
    canvas.alpha_composite(line2, (cx - line2.width // 2, top + line1.height + gap))

    # --- orbit ring (ellipse tilted ~17deg) + sparkle upper-right
    ring = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    a, b = content_px * 0.46, content_px * 0.225  # semi-axes
    stroke = int(content_px * 0.008)
    rd.ellipse((cx - a, cx - b, cx + a, cx + b), outline=WHITE + (191,), width=stroke)
    tilt = -17
    ring = ring.rotate(tilt, resample=Image.BICUBIC, center=(cx, cx))
    canvas.alpha_composite(ring)

    t = math.radians(-62)
    px_, py_ = a * math.cos(t), b * math.sin(t)
    th = math.radians(tilt)
    sx = cx + px_ * math.cos(th) - py_ * math.sin(th)
    sy = cx + px_ * math.sin(th) + py_ * math.cos(th)
    sp = ImageDraw.Draw(canvas)
    star(sp, sx, sy, content_px * 0.045, content_px * 0.011, WHITE + (255,))

    return canvas.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description="Generate JKT48Verse icon assets")
    ap.add_argument("--out", type=Path, default=PUBLIC_DEFAULT, help="output directory (default: frontend/public)")
    ap.add_argument("--master", type=Path, default=None, help="write only the 1024 master to this file")
    args = ap.parse_args()

    if args.master:
        args.master.parent.mkdir(parents=True, exist_ok=True)
        render(SIZE).save(args.master, "PNG")
        print("wrote", args.master)
        return

    masters = {"any": render(SIZE, maskable=False), "maskable": render(SIZE, maskable=True)}
    args.out.mkdir(parents=True, exist_ok=True)
    for fname, (kind, size) in ASSETS.items():
        out = args.out / fname
        masters[kind].resize((size, size), Image.LANCZOS).save(out, "PNG")
        print("wrote", out, f"({size}x{size}, {kind})")


if __name__ == "__main__":
    main()
