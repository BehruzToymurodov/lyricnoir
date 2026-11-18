"""Props: neon signs, cars (incl. police), newspaper front page, red drip/puddle."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .core import lc, lerp, ss, cl
from .paths import font

RED = (205, 22, 52)


def heart_pts(cx, cy, s):
    out = []
    for i in range(61):
        a = 2 * math.pi * i / 60
        out.append((cx + 16 * math.sin(a) ** 3 * s,
                    cy - (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) * s))
    return out


def neon_line(d, c, pts_world, n, color=(255, 40, 80), core=(255, 150, 165)):
    """Neon tube along world points. n = brightness 0..1 (0 = unlit dark tube)."""
    P = c.pts(pts_world)
    if n <= 0.02:
        d.line(P, fill=(60, 30, 36), width=c.lw(4), joint="curve"); return
    for w_, a_ in ((26, 18), (16, 30), (9, 55)):
        d.line(P, fill=color + (int(a_ * n),), width=c.lw(w_), joint="curve")
    d.line(P, fill=lc((70, 30, 36), core, n), width=c.lw(4), joint="curve")


def street_neon(d, c, t, n):
    """Default decoration used in episode 01: heart left, two dashes right of the window."""
    neon_line(d, c, heart_pts(170, 160, 3.2), n)
    neon_line(d, c, [(1520, 230), (1610, 230)], n * (1 if (t * 2) % 2 < 1.4 else 0.4))
    neon_line(d, c, [(1520, 270), (1580, 270)], n)


def draw_car(d, c, x, facing=1, body=(26, 26, 26), police=False, strobe=(0, 0), headlight_beam=True):
    """Car on the road (bottom 1035). facing 1 = driving right, -1 = left."""
    f = facing
    def P(dx, y): return c.P(x + dx * f, y)
    if headlight_beam:
        d.polygon([P(205, 985), P(205, 1000), P(900, 1060), P(900, 930)], fill=(255, 255, 230, 26))
    d.polygon([P(-205, 1035), P(205, 1035), P(208, 985), P(150, 972), P(92, 922), P(-92, 922), P(-152, 972), P(-208, 985)], fill=body)
    d.polygon([P(-80, 932), P(-8, 932), P(-8, 970), P(-128, 970)], fill=(70, 70, 70))
    d.polygon([P(8, 932), P(82, 932), P(132, 970), P(8, 970)], fill=(70, 70, 70))
    if police:
        d.polygon([P(-95, 975), P(95, 975), P(95, 1022), P(-95, 1022)], fill=(205, 205, 205))
        a, b = P(-42, 908), P(0, 922); d.rectangle([min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]], fill=lc((60, 60, 60), (255, 255, 255), strobe[0]))
        a, b = P(0, 908), P(42, 922); d.rectangle([min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]], fill=lc((60, 60, 60), (200, 220, 255), strobe[1]))
    for wx in (-125, 125):
        cx_, cy_ = P(wx, 1035)
        r = c.S(30); d.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r], fill=(8, 8, 8))
        r = c.S(11); d.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r], fill=(90, 90, 90))
    hx, hy = P(198, 992); r = c.S(9)
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 235))


def car_pass_x(t, t0, dur=4.2, x_from=-500, x_to=3000, slow_mid=0.6):
    """x of a car passing left->right that slows down mid-frame (to look at something). None if not on screen."""
    u = (t - t0) / dur
    if u < 0 or u > 1: return None
    return x_from + (x_to - x_from) * (u + (slow_mid / (2 * math.pi)) * math.sin(2 * math.pi * u))


def police_strobe(t, t_on, t_off):
    if t < t_on or t > t_off: return 0.0, 0.0
    ph = (t * 3.2) % 1
    return (1.0 if ph < 0.22 else 0.0), (1.0 if 0.5 < ph < 0.72 else 0.0)


def police_lights(d, c, t, x, strobe):
    """Rotating white beams + subtle cold wash. Call before draw_car(..., police=True)."""
    s1, s2 = strobe
    if s1 + s2 <= 0: return
    cxs, cys = c.P(x, 915)
    for k_, on in ((0, s1), (1, s2)):
        if on:
            ang = (t * 6 + k_ * 3) % (2 * math.pi)
            tip1 = (cxs + math.cos(ang - 0.25) * 2200, cys + math.sin(ang - 0.25) * 900)
            tip2 = (cxs + math.cos(ang + 0.25) * 2200, cys + math.sin(ang + 0.25) * 900)
            d.polygon([(cxs, cys), tip1, tip2], fill=(235, 240, 255, 30))

def police_wash(d, c, strobe):
    s = strobe[0] + strobe[1]
    if s > 0: d.rectangle([0, 0, c.W, c.H], fill=(225, 235, 255, int(14 * s)))


# ---------- newspaper ----------
def build_newspaper(masthead="THE EVENING STAR", headline="MAN GUARDS PAINTING",
                    subhead="Standoff at the gallery window", photo_fn=None, size=(1000, 690)):
    """Front page image (RGBA). photo_fn(draw, box) draws the photo; default = man guarding a red painting.
    Use invented headlines only - never song lyrics."""
    NP_W, NP_H = size
    im = Image.new("RGBA", (NP_W, NP_H), (232, 228, 216, 255))
    d = ImageDraw.Draw(im)
    ink = (28, 28, 28)
    d.rectangle([0, 0, NP_W - 1, NP_H - 1], outline=(180, 175, 165), width=4)
    f1 = font("serif_bold", 64); f2 = font("serif_bold", 54); f3 = font("serif", 26); f4 = font("serif", 18)
    d.text((NP_W / 2, 58), masthead, font=f1, fill=ink, anchor="mm")
    d.line([(40, 100), (NP_W - 40, 100)], fill=ink, width=3)
    d.text((40, 116), "LATE CITY EDITION", font=f4, fill=(80, 80, 80))
    d.text((NP_W - 40, 116), "TEN CENTS", font=f4, fill=(80, 80, 80), anchor="ra")
    d.line([(40, 142), (NP_W - 40, 142)], fill=ink, width=1)
    d.text((NP_W / 2, 196), headline, font=f2, fill=ink, anchor="mm")
    d.text((NP_W / 2, 250), subhead, font=f3, fill=(60, 60, 60), anchor="mm")
    box = (40, 285, 470, 650)
    d.rectangle(box, fill=(58, 58, 58))
    (photo_fn or _default_photo)(d, box)
    d.rectangle([box[0], box[3] - 30, box[2], box[3]], fill=(45, 45, 45))
    d.text((box[0] + 10, box[3] - 24), "Photo: staff", font=f4, fill=(170, 170, 170))
    rr = np.random.default_rng(3)
    for col_x in (500, 760):
        y = 290
        while y < 650:
            wl = 220 if rr.random() > 0.15 else rr.integers(80, 200)
            d.rectangle([col_x, y, col_x + wl, y + 7], fill=(150, 146, 138)); y += 17
    d.line([(740, 285), (740, 650)], fill=(180, 175, 165), width=2)
    return im

def _default_photo(d, box):
    px0, py0, px1, py1 = box
    d.rectangle([px0 + 150, py0 + 30, px1 - 40, py0 + 250], fill=(30, 30, 30), outline=(110, 110, 110), width=4)
    d.rectangle([px0 + 205, py0 + 55, px1 - 95, py0 + 220], fill=(12, 12, 12))
    d.polygon([(px0 + 222, py0 + 70), (px1 - 112, py0 + 66), (px1 - 108, py0 + 150), (px0 + 218, py0 + 152)], fill=RED)
    d.polygon([(px0 + 218, py0 + 215), (px0 + 240, py0 + 168), (px1 - 135, py0 + 168), (px1 - 110, py0 + 215)], fill=RED)
    mx_ = px0 + 180
    d.rectangle([mx_ - 16, py0 + 160, mx_ + 18, py0 + 300], fill=(150, 150, 150))
    d.ellipse([mx_ - 16, py0 + 122, mx_ + 18, py0 + 158], fill=(170, 170, 170))
    d.rectangle([mx_ - 30, py0 + 118, mx_ + 32, py0 + 125], fill=(25, 25, 25))
    d.rectangle([mx_ - 16, py0 + 96, mx_ + 18, py0 + 120], fill=(25, 25, 25))
    d.line([(mx_ - 14, py0 + 172), (mx_ - 75, py0 + 120)], fill=(150, 150, 150), width=10)
    d.line([(mx_ + 16, py0 + 172), (mx_ + 78, py0 + 120)], fill=(150, 150, 150), width=10)
    d.rectangle([mx_ - 16, py0 + 160, mx_ + 18, py0 + 170], fill=RED)


def newspaper_spin(t, t_in, t_out, spin_dur=1.5, fall_dur=0.8):
    """(scale, angle, dy, dim) while the paper is on screen, else None. Spins in at t_in, falls at t_out."""
    if t < t_in or t > t_out + fall_dur: return None
    if t < t_in + spin_dur:
        u = ss((t - t_in) / spin_dur); return lerp(0.04, 1.0, u), (1 - u) * 720, 0, 1.0
    if t < t_out: return 1.0, math.sin((t - t_in - spin_dur) * 0.9) * 1.2, 0, 1.0
    u = ss((t - t_out) / fall_dur); return 1.0, -14 * u, 900 * u * u, 1 - u * 0.3

def paste_newspaper(img, paper, state, center, t, t_in, c):
    """Darkens the scene and pastes the spinning paper (screen coords = world at zoom 1, center (960,540))."""
    if state is None: return
    from PIL import ImageDraw as _D
    sc, ang, dy, dim = state
    _D.Draw(img, "RGBA").rectangle([0, 0, c.W, c.H], fill=(0, 0, 0, int(150 * dim * ss((t - t_in) / 0.6))))
    w_, h_ = max(2, int(paper.width * sc)), max(2, int(paper.height * sc))
    p = paper.resize((w_, h_), Image.BILINEAR).rotate(ang, expand=True, resample=Image.BILINEAR)
    cx, cy = c.P(*center)
    img.paste(p, (int(cx - p.width / 2), int(cy + dy - p.height / 2)), p)


def red_drip(d, c, t, t0, x, y_from=605, n=26, color=(215, 25, 55)):
    """Drops falling from (x, y_from) to the ground starting at t0, then a puddle the rain washes away."""
    for i in range(n):
        u = cl((t - t0 - 0.1 - i * 0.11) / 0.55)
        if 0 < u < 1:
            y_ = lerp(y_from, 858, u * u); x_ = x + 8 + math.sin(i * 1.7) * 14
            d.ellipse(c.box(x_ - 5, y_ - 7, x_ + 5, y_ + 7), fill=color + (230,))
    pud = ss((t - t0 - 0.4) / 2.5) * (1 - ss((t - t0 - 4) / 3.5))
    if pud > 0:
        rw = 30 + 110 * ss((t - t0 - 0.4) / 4)
        d.ellipse(c.box(x + 10 - rw, 862 - rw * 0.12, x + 10 + rw, 862 + rw * 0.12), fill=(200, 20, 50, int(170 * pud)))
