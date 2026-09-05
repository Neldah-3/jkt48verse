"""Generate the JKT48Verse flat vector-style app icon (1024x1024, transparent PNG).

Usage: python scripts/make_icon.py [output.png]
Renders at 4x supersampling and downsamples for crisp anti-aliased edges.
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

SIZE = 1024
SS = 4  # supersample factor
W = SIZE * SS

FONT_BLACK = "/tmp/fonts/Roboto-Black.ttf"
FONT_SEMI = "/tmp/fonts/Roboto-Medium.ttf"

RED_TL = (0xE1, 0x19, 0x27)
RED_BR = (0x9E, 0x0F, 0x1B)
NAVY = (0x0F, 0x17, 0x2A)
WHITE = (255, 255, 255)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def squircle_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def diagonal_gradient(size):
    # 1-D gradient along the diagonal, then rotate/scale via a small image for speed
    n = 1024
    strip = Image.new("RGB", (n, 1))
    px = strip.load()
    for i in range(n):
        px[i, 0] = lerp(RED_TL, RED_BR, i / (n - 1))
    # build a diagonal by drawing the strip rotated 45deg over a bigger canvas
    diag = int(n * math.sqrt(2)) + 4
    g = strip.resize((diag, diag), Image.BILINEAR)  # horizontal gradient
    g = g.rotate(-45, resample=Image.BICUBIC, expand=True)
    gw, gh = g.size
    box = ((gw - n) // 2, (gh - n) // 2, (gw + n) // 2, (gh + n) // 2)
    return g.crop(box).resize((size, size), Image.BICUBIC)


def navy_glow(size):
    # subtle radial glow in the bottom-right corner
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


def text_layer(size, text, font_path, font_px, tracking, target_width=None):
    """Render text with letter-spacing; return RGBA image cropped to glyph bounds."""
    font = ImageFont.truetype(font_path, font_px)
    widths = []
    for ch in text:
        l, t, r, b = font.getbbox(ch)
        widths.append(font.getlength(ch))
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
    bbox = img.getbbox()
    return img.crop(bbox)


def star(draw, cx, cy, r_out, r_in, fill):
    pts = []
    for i in range(8):
        ang = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0)
        rad = r_out if i % 2 == 0 else r_in
        pts.append((cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
    # order: outer(0), inner(45), outer(90), inner(135)...
    draw.polygon(pts, fill=fill)


def main(out="icon.png"):
    icon_px = int(W * 0.90)
    off = (W - icon_px) // 2
    radius = int(icon_px * 0.22)

    canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    # --- background square: gradient + navy glow, masked to squircle
    bg = diagonal_gradient(icon_px).convert("RGBA")
    glow = navy_glow(icon_px)
    navy = Image.new("RGBA", (icon_px, icon_px), NAVY + (255,))
    bg = Image.composite(navy, bg, glow)
    bg.putalpha(squircle_mask(icon_px, radius))
    canvas.alpha_composite(bg, (off, off))

    # --- wordmark
    line1 = text_layer(icon_px, "JKT48", FONT_BLACK, int(icon_px * 0.245), tracking=-icon_px * 0.006)
    line2 = text_layer(icon_px, "VERSE", FONT_SEMI, int(icon_px * 0.105), tracking=0, target_width=line1.width)
    gap = int(icon_px * 0.035)
    block_h = line1.height + gap + line2.height
    cx = W // 2
    top = W // 2 - block_h // 2
    canvas.alpha_composite(line1, (cx - line1.width // 2, top))
    canvas.alpha_composite(line2, (cx - line2.width // 2, top + line1.height + gap))

    # --- orbit ring (ellipse tilted ~17deg), 75% opacity, with a sparkle upper-right
    ring = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    a, b = icon_px * 0.46, icon_px * 0.225   # semi-axes
    stroke = int(icon_px * 0.008)
    rd.ellipse((cx - a, cx - b, cx + a, cx + b), outline=WHITE + (191,), width=stroke)
    tilt = -17
    ring = ring.rotate(tilt, resample=Image.BICUBIC, center=(cx, cx))
    canvas.alpha_composite(ring)

    # sparkle position: a point on the rotated ellipse in the upper right
    t = math.radians(-62)
    px_, py_ = a * math.cos(t), b * math.sin(t)
    th = math.radians(tilt)
    sx = cx + px_ * math.cos(th) - py_ * math.sin(th)
    sy = cx + px_ * math.sin(th) + py_ * math.cos(th)
    sp = ImageDraw.Draw(canvas)
    star(sp, sx, sy, icon_px * 0.045, icon_px * 0.011, WHITE + (255,))

    final = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    final.save(out, "PNG")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "icon.png")
