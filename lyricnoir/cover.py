"""Vertical 9:16 cover (1080x1920) for Instagram. Everything important stays inside the 3:4 grid crop (y 240..1680)."""
import os
from PIL import Image, ImageDraw, ImageFilter
from .paths import font, ASSETS


def _spaced(d, y, text, f, fill, spacing, cx):
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1); x = cx - total / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill); x += w + spacing
    return total


def make_cover(bg_png, out_png, title, artist, number, hook=(), brand="LYRIC NOIR"):
    """title: 'Pablo Picasso' -> first word italic white, rest bold red caps (single word: bold red caps)."""
    im = Image.open(bg_png).convert("RGBA"); W, H = im.size; cx = W / 2
    kicker = f"{brand}  ·  FILM NO. {number:02d}"
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    _spaced(ImageDraw.Draw(glow), 262, kicker, font("ui_medium", 30), (255, 40, 80, 255), 6, cx)
    glow = glow.filter(ImageFilter.GaussianBlur(8)); im.alpha_composite(glow); im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    _spaced(d, 262, kicker, font("ui_medium", 30), (255, 200, 210, 255), 6, cx)
    parts = title.split(" ", 1)
    top, main = (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])
    y = 300
    if top:
        f = font("title_italic", 136); d.text((cx - d.textlength(top, font=f) / 2, y), top, font=f, fill=(242, 242, 242, 255)); y += 140
    size = 128
    while size > 60 and _spaced(ImageDraw.Draw(Image.new("RGB", (1, 1))), 0, main.upper(), font("title_bold", size), (0, 0, 0), 13, 0) > W - 120:
        size -= 6
    _spaced(d, y, main.upper(), font("title_bold", size), (232, 48, 79, 255), 13, cx)
    _spaced(d, y + size * 1.22, "  ".join(artist.upper().split(" ")), font("ui", 32), (190, 190, 190, 255), 8, cx)
    f = font("title_italic", 52)
    for i, h in enumerate(hook):
        d.text((cx - d.textlength(h, font=f) / 2, 1410 + i * 70), h, font=f, fill=(235, 235, 235, 255))
    logo = Image.open(os.path.join(ASSETS, "brand", "profile.png")).convert("RGBA").resize((110, 110), Image.LANCZOS)
    m = Image.new("L", (110, 110), 0); ImageDraw.Draw(m).ellipse([0, 0, 109, 109], fill=255)
    lf = font("ui_medium", 30)
    lw = sum(d.textlength(ch, font=lf) for ch in brand) + 6 * (len(brand) - 1)
    x0 = (W - (110 + 24 + lw)) / 2
    im.paste(logo, (int(x0), 1580), m); d = ImageDraw.Draw(im)
    _spaced(d, 1618, brand, lf, (230, 230, 230, 255), 6, x0 + 110 + 24 + lw / 2)
    im.convert("RGB").save(out_png)
    return out_png
