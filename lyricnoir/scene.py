"""The noir street set: wall, sidewalk, streetlight, shop window, rain, flashes.
All coordinates are WORLD units (the 1920x1080 street at zoom 1). Ground line is y=860."""
import math
import numpy as np
from .core import lc

GROUND = 860
WALL = (30, 30, 30)
WALK = (12, 12, 12)


def background(d, c, wall_panels=True):
    """Call right after Image.new(..., WALL)."""
    if wall_panels:
        for px in range(-400, 2400, 170):
            d.line(c.pts([(px, -400), (px, GROUND)]), fill=(38, 38, 38), width=c.lw(3))
    d.polygon([c.P(-2000, GROUND), c.P(4000, GROUND), (c.W + 50, c.H + 50), (-50, c.H + 50)], fill=WALK)
    d.line(c.pts([(-2000, GROUND), (4000, GROUND)]), fill=(48, 48, 48), width=c.lw(4))


def streetlight_pool(d, c, L, x=300):
    """Light on the wall and ground from the lamp at world x. Draw early (behind figures)."""
    if L <= 0: return
    dx = x - 300
    for k in range(7):
        e = k * 45
        d.ellipse(c.box(220 + e + dx, 280 + e, 1040 - e + dx, 1000 - e), fill=(255, 255, 255, int(6 * L)))
    d.polygon(c.pts([(318 + dx, 290), (352 + dx, 290), (600 + dx, GROUND), (80 + dx, GROUND)]), fill=(255, 255, 255, int(9 * L)))
    d.ellipse(c.box(90 + dx, 830, 600 + dx, 900), fill=(255, 255, 255, int(22 * L)))


def streetlight_pole(d, c, L, x=300):
    """The lamp itself. Draw late (in front)."""
    dx = x - 300
    d.rectangle(c.box(296 + dx, 280, 312 + dx, GROUND), fill=(58, 58, 58))
    d.rectangle(c.box(290 + dx, 260, 380 + dx, 276), fill=(58, 58, 58))
    d.rectangle(c.box(330 + dx, 276, 350 + dx, 292), fill=lc((70, 70, 70), (250, 250, 240), L))
    if L > 0.5:
        d.ellipse(c.box(312 + dx, 270, 368 + dx, 314), fill=(255, 255, 240, int(40 * L)))


def window_interior(d, c, rect, lit):
    """Shop/gallery window background. Returns the interior color (for pale marks etc.)."""
    inner = lc((16, 16, 16), (52, 52, 52), lit)
    d.rectangle(c.box(*rect), fill=inner)
    x0, y0, x1, y1 = rect
    if lit > 0:
        d.ellipse(c.box(x0 + 60, y0 + 20, x1 - 60, y1 - 80), fill=(255, 255, 255, int(14 * lit)))
        d.polygon(c.pts([(x0, y1), (x1, y1), (x1 + 60, GROUND), (x0 - 60, GROUND)]), fill=(255, 255, 255, int(10 * lit)))
    return inner


def window_frame(d, c, rect):
    d.rectangle(c.box(*rect), outline=(105, 105, 105), width=c.lw(10))
    x0, y0, x1, y1 = rect
    for gx in (x0 + 40, x0 + 80, x1 - 80):
        d.line(c.pts([(gx, y0 + 20), (gx + 60, y0 + 80)]), fill=(255, 255, 255, 22), width=c.lw(6))


def paste_clipped(img, layer, c, rect):
    """Paste an RGBA full-frame layer only inside a world rect (e.g. things behind the glass)."""
    x0s, y0s = c.P(rect[0], rect[1]); x1s, y1s = c.P(rect[2], rect[3])
    bx = [int(max(0, x0s)), int(max(0, y0s)), int(min(c.W, x1s)), int(min(c.H, y1s))]
    if bx[2] > bx[0] and bx[3] > bx[1]:
        crop = layer.crop(bx); img.paste(crop, (bx[0], bx[1]), crop)


def red_reflection(d, c, t, amount, x0=1150, x1=1360):
    """Wet-pavement reflection of something red above (the painting, a sign...)."""
    if amount <= 0: return
    for i, px in enumerate(range(x0, x1, 22)):
        wob = math.sin(t * 3 + i) * 6
        d.rectangle(c.box(px + wob, 880, px + wob + 12, 880 + 60 + (i % 3) * 25), fill=(210, 20, 50, int(45 * amount)))


class Rain:
    """Screen-space rain + ground splashes. Never drawn inside the `dry` world rects (glass)."""
    def __init__(self, W, H, n=320, seed=7):
        rng = np.random.default_rng(seed)
        self.W, self.H, self.n = W, H, n
        self.x = rng.uniform(-100, W + 300, n); self.y0 = rng.uniform(0, H + 200, n)
        self.sp = rng.uniform(1300, 1800, n); self.ln = rng.uniform(26, 50, n)
        self.sx = rng.uniform(0, W, 60); self.sph = rng.uniform(0, 1, 60)

    def draw(self, d, c, t, dry=()):
        W, H = self.W, self.H
        drys = [(*c.P(r[0], r[1]), *c.P(r[2], r[3])) for r in dry]
        ys = (self.y0 + self.sp * t) % (H + 200) - 100
        xs = ((self.x - 0.18 * (self.sp * t % (H + 200))) % (W + 400)) - 100
        for i in range(self.n):
            x0, y0, ln = xs[i], ys[i], self.ln[i]
            mx, my = x0 - 0.09 * ln, y0 + ln / 2
            if any(a < mx < b and e < my < f for a, e, b, f in drys): continue
            d.line([(x0, y0), (x0 - 0.18 * ln, y0 + ln)], fill=(185, 185, 185, 80), width=2)
        gy = c.P(0, GROUND + 15)[1]
        for i in range(60):
            ph = (self.sph[i] + t * 1.7) % 1
            if ph < 0.25 and gy < H:
                rr = 4 + ph * 30
                d.ellipse([self.sx[i] - rr, gy + (i % 7) * 18 - rr * 0.25, self.sx[i] + rr, gy + (i % 7) * 18 + rr * 0.25],
                          outline=(150, 150, 150, int(120 * (1 - ph * 4))), width=2)

_rain = {}
def rain(d, c, t, dry=()):
    key = (c.W, c.H)
    if key not in _rain: _rain[key] = Rain(c.W, c.H)
    _rain[key].draw(d, c, t, dry)


def flash(d, c, amount, color=(255, 255, 255)):
    """Full-frame flash (camera flash, lightning). amount 0..1."""
    if amount > 0: d.rectangle([0, 0, c.W, c.H], fill=color + (int(150 * amount),))


def darken(d, c, amount):
    if amount > 0: d.rectangle([0, 0, c.W, c.H], fill=(0, 0, 0, int(150 * amount)))
