"""Lyric Noir — Film No. 02 — Michael Jackson, "They Don't Care About Us".
One-line story: an invisible man on a night-city wall that nobody sees, until the people beside him light up
and the searchlight can't look away.
Song section used: 1:41.6 -> ~3:20 (timings in timing.json; never store lyrics here).

Style (new for this film): dark wet concrete wall at night; people are spray-paint stencils with drips.
v2 look: stencil people from lyricnoir.stencil (3-layer paint, stop-motion with paint ghosts), drum-synced
shake/flashes (beats.json), volumetric searchlights with rain in the beam, passers-by, headlight flare, bloom.
Ignored people = flat gray paint. Whoever stands up turns black with a glowing white light outline.
Red = the armband only (painted, then glowing), passed person to person along a red light line.
Police light / searchlights are cold white. Screen-space scenes: the government building and his profile.
"""
import math, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lyricnoir.core import Cam, keyframe_camera, Post, lerp, cl, ss, fade_in_out
from lyricnoir.paths import font, work_dir

EP = "02-they-dont-care"
META = dict(
    title="They Don't Care About Us", artist="Michael Jackson", number=2,
    audio_start=101.6, duration=98.6, fade_out=3.0, lyric_style="spray",
    hook=["They painted us gray.", "We learned to glow."],       # invented, not lyrics
    cover=dict(t=81.5, z=1.2, cx=1600, cy=760),
)

# ---------------------------------------------------------------- timing (video seconds)
_T = json.load(open(os.path.join(os.path.dirname(__file__), "timing.json")))
A0 = _T["audio_start"]
LS = {r["line"]: r["start"] - A0 for r in _T["lines"]}           # line starts in video time
HITS = [LS[i] for i in range(10, 18)]                             # the fast skin-head lines
SOLO0, SOLO1 = 163.5 - A0, 186.5 - A0                             # guitar solo
SH2, SH3, SH4, SH5A, SH5B, SH6, SH7, SH9 = LS[1], LS[3], LS[5], LS[7], LS[9], LS[10], LS[18], LS[20]
CUT2 = 112.24 - A0                                                # the drums kick back in
END = META["duration"]

# ---------------------------------------------------------------- camera
CAM = [
    (0.0, CUT2, 1.55, 1.75, 1600, 1600, 650, 650),              # 1 hook: darkness + red armband
    (CUT2, SH3, 0.98, 1.30, 1560, 1610, 630, 650),              # 2 the wall; he turns to us
    (SH3, SH4, 1.42, 1.52, 1690, 1705, 600, 590),               # 3 him + poster
    (SH4, SH5A, 1.02, 0.98, 1600, 1600, 650, 650),              # 4 police strobes
    (SH5A, SH5B, 1.0, 1.0, 960, 960, 540, 540),                 # 5a building (screen space)
    (SH5B, SH6, 1.0, 1.0, 960, 960, 540, 540),                  # 5b his profile (screen space)
]
_framings = [(1.5, 1.55, 1600, 700), (2.25, 2.35, 1610, 640), (0.92, 0.96, 1600, 640), (1.6, 1.65, 1600, 690),
             (2.3, 2.4, 1620, 620), (0.95, 0.98, 1600, 640), (1.55, 1.6, 1610, 680), (2.2, 2.35, 1640, 590)]
for i, (z0, z1, x, y) in enumerate(_framings):                  # 6 fast cuts, one per line
    t0 = HITS[i]; t1 = HITS[i + 1] if i + 1 < len(HITS) else SH7
    CAM.append((t0, t1, z0, z1, x, x, y, y))
CAM += [
    (SH7, SOLO0, 1.22, 1.12, 1600, 1600, 680, 670),             # 7 chorus: neighbours light up
    (SOLO0, SH9, 1.12, 0.60, 1600, 1600, 670, 640),             # 8 solo: glow runs along the wall
    (SH9, END - 2.9, 0.60, 0.70, 1600, 1600, 640, 640),         # 9 bridge: searchlight stops on them
    (END - 2.9, END, 0.70, 0.66, 1600, 1600, 640, 630),         # 10 quiet rain, fade
]
camera = keyframe_camera(CAM)
SCENES = [(a[0], a[1]) for a in CAM]

# ---------------------------------------------------------------- world
X0, Y0, X1, Y1 = -200, -600, 3400, 1750        # world texture extent
GROUND = 960                                   # feet line
WALL_END = 995                                 # wall meets the wet sidewalk
MAN_X = 1600
OTHERS = [(300, "child"), (560, "hat"), (820, "woman"), (1080, "old"), (1340, "woman"),
          (1860, "base"), (2120, "woman"), (2380, "hat"), (2640, "old"), (2900, "child")]
LIGHT_T = {1860: SH7 + 0.6, 1340: LS[19] + 0.4}
for k, x in enumerate([2120, 1080, 2380, 820, 2640, 560, 2900, 300]):
    LIGHT_T[x] = SOLO0 + 1.6 + k * 2.55
SOURCE = {1860: MAN_X, 1340: MAN_X, 2120: 1860, 1080: 1340, 2380: 2120, 820: 1080, 2640: 2380, 560: 820,
          2900: 2640, 300: 560}
BAND_Y = GROUND - 0.68 * 440
POSTER = (1664, 330, 1796, 510)
RED_PAINT = np.array([150, 18, 36], np.float32)
RED_GLOW = np.array([255, 34, 76], np.float32)
WHITE = np.array([238, 242, 255], np.float32)


def rng_for(*k): return np.random.default_rng(abs(hash(k)) % (2 ** 32))


# ---------------------------------------------------------------- wall texture (cached)
def _wall_levels():
    p = os.path.join(work_dir(EP), "wall_v2.npz")
    if os.path.exists(p):
        d = np.load(p); return {1.0: d["l1"], 2.5: d["l25"]}
    out = {}
    for s in (1.0, 2.5):
        W, H = int((X1 - X0) * s), int((Y1 - Y0) * s)
        r = np.random.default_rng(11)
        low = Image.fromarray((r.random((H // 40 + 2, W // 40 + 2)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        mid = Image.fromarray((r.random((H // 8 + 2, W // 8 + 2)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        a = 52 + (np.asarray(low, np.float32) - 128) * 0.10 + (np.asarray(mid, np.float32) - 128) * 0.06
        a += r.normal(0, 7, (H, W)).astype(np.float32)
        yy = (np.arange(H) / s + Y0)[:, None]; xx = (np.arange(W) / s + X0)[None, :]
        a -= 16 * ((np.abs(((yy - 40) % 280) - 140) > 137.5) & (yy < WALL_END))       # panel seams
        a -= 16 * ((np.abs(((xx + 60) % 420) - 210) > 207.5) & (yy < WALL_END))
        stain = np.asarray(Image.fromarray((r.random((4, W // 30 + 2)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
        a -= np.clip(stain - 150, 0, 255) * 0.10 * (yy < WALL_END)                         # rain stains
        a = np.where(yy >= WALL_END, 20 + (np.asarray(mid, np.float32) - 128) * 0.05, a)    # wet sidewalk
        a = np.where((yy >= WALL_END) & (yy < WALL_END + 6), 70, a)                        # curb edge
        out[s] = np.clip(a, 0, 255).astype(np.uint8)
    np.savez_compressed(p, l1=out[1.0], l25=out[2.5])
    return out


_WALL = None
def wall_crop(c):
    global _WALL
    if _WALL is None: _WALL = _wall_levels()
    s = 1.0 if c.z <= 1.0 else 2.5
    tex = _WALL[s]
    wx0 = c.cx - c.W / 2 / c.z; wy0 = c.cy - c.H / 2 / c.z
    box = ((wx0 - X0) * s, (wy0 - Y0) * s, (wx0 + c.W / c.z - X0) * s, (wy0 + c.H / c.z - Y0) * s)
    im = Image.fromarray(tex).resize((c.W, c.H), Image.BILINEAR, box=box)
    a = np.asarray(im, np.float32)
    return np.stack([a, a, a * 1.04], -1)



# ---------------------------------------------------------------- timeline
def ignite(t, t0, dur=0.7):
    """0 before t0, neon-style flicker for dur, then 1."""
    if t < t0: return 0.0
    if t >= t0 + dur: return 1.0
    k = int((t - t0) * 20)
    return [0.6, 0.0, 0.9, 0.2, 1.0, 0.4, 1.0, 0.7, 1.0, 1.0, 0.85, 1.0, 1.0, 1.0][min(k, 13)]


def hit(t):
    """Searchlight 'blow' at each fast line start (shot 6): 1 -> 0 over 0.35 s."""
    for h0 in HITS:
        if 0 <= t - h0 < 0.35: return 1 - (t - h0) / 0.35
    return 0.0


def man_glow(t):
    if t < SH6: return 0.0
    if t >= SH7: return 1.0
    n = sum(1 for h0 in HITS if t >= h0)
    last = max(h0 for h0 in HITS if t >= h0)
    return min(1.0, (0.2 + 0.1 * n) * ignite(t, last, 0.35) + (0.2 + 0.1 * (n - 1)) * (1 - ignite(t, last, 0.35)))


def man_pose(t):
    if t < LS[14]: return 0
    if t < LS[15]: return 1
    if t < LS[16]: return 2
    return 3


def man_band(t):
    if t < CUT2: return 0.85 * ignite(t, 1.2, 1.0)
    if t < SH2: return 0.35
    if t < SH6: return 0.3
    return 0.3 + 0.7 * man_glow(t)


def other_state(x, t):
    """(glow 0..1, raised pose?, paint visibility)."""
    g = ignite(t, LIGHT_T[x], 0.8)
    return g, t > LIGHT_T[x] + 0.7


def strobe(t):
    """(left, right) police flash strengths."""
    amp = 1.0 if SH4 <= t < SH5A else (0.35 if SH6 <= t < SH7 else 0.0)
    if amp == 0: return 0.0, 0.0
    ph = (t * 7.5) % 2.0
    on = lambda a: 1.0 if (a % 1.0) < 0.22 or 0.35 < (a % 1.0) < 0.5 else 0.0
    return amp * (on(ph) if ph < 1 else 0.0), amp * (on(ph) if ph >= 1 else 0.0)


def ambient(t):
    if t < SH2: return 0.07 + 0.06 * ss((t - 9.0) / 1.8) * (t < 8.4 or t > 9.9)
    if SH4 <= t < SH5A: return 0.22
    if t >= SH9: return 0.42
    return 0.40


def beams(t):
    """List of (target_x on the wall at y=700, half-width at the wall, strength)."""
    B = []
    if t < 8.4:
        B.append((lerp(500, 2700, ss((t - 1.0) / 7.2)), 120, 1.0 * ss((t - 0.6) / 0.8)))
    elif SH2 <= t < SH3:
        B.append((lerp(800, 2500, (t - SH2 - 0.3) / (SH3 - SH2 - 0.3)), 125, 1.0))
    elif SH7 <= t < SOLO0:
        B.append((1600 + 1100 * math.sin(t * 0.55 + 1.0), 120, 0.7))
    elif SOLO0 <= t < SH9:
        B.append((1600 + 1350 * math.sin(t * 0.83), 130, 0.85))
        B.append((1600 + 1250 * math.sin(t * 0.61 + 2.4), 115, 0.75))
    elif t >= SH9:
        arrive = ss((t - SH9) / 3.0)
        x = lerp(-300, 1600, arrive)
        w = lerp(130, 1650, ss((t - SH9 - 2.6) / 3.2))
        B.append((x, w, 1.0))
    return B


def stripe(t):
    """Gray spray stripe across him (shot 4), burns away as he starts to glow."""
    if t < LS[6] + 0.4: return 0.0
    return ss((t - LS[6] - 0.4) / 1.6) * (1 - man_glow(t))





# ---------------------------------------------------------------- poster (shots 2-3)
_POSTER_TEX = None
def poster_tex():
    global _POSTER_TEX
    if _POSTER_TEX is None:
        w, h = (POSTER[2] - POSTER[0]) * 3, (POSTER[3] - POSTER[1]) * 3
        r = np.random.default_rng(5)
        a = 200 + r.normal(0, 9, (h, w))
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB"); d = ImageDraw.Draw(im)
        f1, f2 = font("title_bold", 78), font("ui_medium", 40)
        for txt, f, y in [("LIBERTY", f1, 120), ("FOR ALL", f2, 230)]:
            d.text(((w - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=(25, 25, 25))
        d.rectangle([24, 24, w - 24, h - 24], outline=(40, 40, 40), width=5)
        d.line([(60, 330), (w - 60, 330)], fill=(60, 60, 60), width=3)
        d.text((60, 360), "A PROMISE TO EVERY CITIZEN", font=font("ui", 20), fill=(60, 60, 60))
        _POSTER_TEX = im
    return _POSTER_TEX


def draw_poster(img, c, t, L):
    """Paste the poster (peeling, then falling) onto img (PIL RGB, already lit). L = local light level."""
    if t >= SH4 or t < SH2:
        return
    peel = ss((t - (SH3 + 0.8)) / 3.0)
    fall = cl((t - (SH4 - 1.7)) / 1.3)
    x0, y0, x1, y1 = POSTER
    tex = poster_tex().copy()
    tw, th = tex.size
    mask = Image.new("L", (tw, th), 255); md = ImageDraw.Draw(mask)
    if peel > 0:                                     # top-right corner folds down
        k = peel * 0.85
        md.polygon([(tw * (1 - k), 0), (tw, 0), (tw, th * k)], fill=0)
    dy = 900 * fall ** 2; rot = -25 * fall
    a = c.P(x0, y0 + dy); b = c.P(x1, y1 + dy)
    w, h = int(b[0] - a[0]), int(b[1] - a[1])
    if w < 2 or h < 2: return
    tl = tex.resize((w, h), Image.BILINEAR); ml = mask.resize((w, h), Image.BILINEAR)
    lit = Image.eval(tl, lambda v: int(v * min(0.75, L * 0.9)))
    if rot:
        lit = lit.rotate(rot, expand=True, resample=Image.BILINEAR); ml = ml.rotate(rot, expand=True, resample=Image.BILINEAR)
    if fall > 0: ml = Image.eval(ml, lambda v: int(v * (1 - fall)))
    img.paste(lit, (int(a[0]), int(a[1])), ml)
    if peel > 0 and fall == 0:                       # the folded flap (paper back side)
        k = peel * 0.85
        p = [c.P(x1 - (x1 - x0) * k, y0), c.P(x1, y0 + (y1 - y0) * k), c.P(x1 - (x1 - x0) * k * 0.7, y0 + (y1 - y0) * k * 0.7)]
        ImageDraw.Draw(img).polygon(p, fill=tuple(int(v * min(0.75, L * 0.9)) for v in (170, 166, 158)))


def glue_mark(img_arr, c, t):
    if t < SH4 - 1.0: return
    a = c.P(POSTER[0], POSTER[1]); b = c.P(POSTER[2], POSTER[3])
    x0, y0, x1, y1 = [int(round(v)) for v in (a[0], a[1], b[0], b[1])]
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(c.W, x1), min(c.H, y1)
    if x1 > x0 and y1 > y0: img_arr[y0:y1, x0:x1] *= 1.18



# ---------------------------------------------------------------- rain
def rain(img, c, t, amount=1.0):
    d = ImageDraw.Draw(img, "RGBA"); W, H = img.size
    r = np.random.default_rng(3)
    n = int(260 * amount)
    xs = r.random(n) * (W + 200) - 100; y0 = r.random(n) * H; sp = r.uniform(1400, 2100, n)
    ln = r.uniform(18, 42, n); al = r.integers(28, 70, n)
    for i in range(n):
        y = (y0[i] + t * sp[i]) % (H + 60) - 30; x = xs[i] - (y - y0[i]) * 0.12 % 40
        d.line([(x, y), (x - ln[i] * 0.12, y + ln[i])], fill=(225, 228, 235, int(al[i])), width=2 if i % 5 == 0 else 1)




# ---------------------------------------------------------------- 5a: the government building
_BLD = None
def building_base(W, H):
    global _BLD
    if _BLD is None or _BLD[0].size != (W, H):
        r = np.random.default_rng(21)
        sky = np.linspace(26, 8, H)[:, None] * np.ones((1, W)) + r.normal(0, 5, (H, W))
        im = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).convert("RGB"); d = ImageDraw.Draw(im)
        fx0, fx1, top = W * 0.12, W * 0.88, H * 0.30
        d.polygon([(fx0 - 30, top), (W / 2, H * 0.12), (fx1 + 30, top)], fill=(44, 44, 46))           # pediment
        d.polygon([(fx0 + 30, top - 12), (W / 2, H * 0.155), (fx1 - 30, top - 12)], outline=(60, 60, 62), width=4)
        d.rectangle([fx0 - 40, top, fx1 + 40, top + 40], fill=(52, 52, 54))
        d.rectangle([fx0, top + 40, fx1, H], fill=(30, 30, 32))
        wins = []
        cols, rows = 8, 3
        for j in range(rows):
            for i in range(cols):
                x = fx0 + 70 + i * (fx1 - fx0 - 140) / (cols - 1); y = top + 120 + j * 190
                wins.append((x - 34, y, x + 34, y + 120))
        for k in range(7):                                                              # columns
            x = fx0 + 20 + k * (fx1 - fx0 - 40) / 6
            d.rectangle([x - 26, top + 40, x + 26, H], fill=(58, 58, 60))
            for g in range(5): d.line([(x - 18 + g * 9, top + 46), (x - 18 + g * 9, H)], fill=(48, 48, 50), width=2)
        d.rectangle([fx0 - 60, H - 70, fx1 + 60, H], fill=(40, 40, 42))
        order = list(r.permutation(len(wins)))
        _BLD = (im, wins, order)
    return _BLD


def building_frame(t, size):
    W, H = size
    base, wins, order = building_base(W, H)
    im = base.copy(); d = ImageDraw.Draw(im, "RGBA")
    u0, u1 = SH5A + 0.6, SH5B - 0.5
    glow = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(glow)
    for n, k in enumerate(order):
        toff = u0 + (u1 - u0) * (n / len(order)) ** 0.8
        on = 1.0 - ignite(t, toff, 0.4)
        x0, y0, x1, y1 = wins[k]
        if on > 0:
            d.rectangle([x0, y0, x1, y1], fill=(int(235 * on + 12), int(235 * on + 12), int(238 * on + 13)))
            gd.rectangle([x0, y0, x1, y1], fill=int(150 * on))
        else:
            d.rectangle([x0, y0, x1, y1], fill=(10, 10, 11))
        d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=(20, 20, 22, 255), width=4)
    g = np.asarray(glow.filter(ImageFilter.GaussianBlur(28)), np.float32)[..., None] * 0.9
    arr = np.asarray(im, np.float32) + g
    # searchlight on the roof, sweeping the sky
    ang = math.sin((t - SH5A) * 0.9) * 0.6 - 1.5708
    bm = Image.new("L", (W, H), 0); bd = ImageDraw.Draw(bm)
    sx, sy = W / 2, H * 0.12
    bd.polygon([(sx, sy), (sx + math.cos(ang - 0.06) * 2200, sy + math.sin(ang - 0.06) * 2200),
                (sx + math.cos(ang + 0.06) * 2200, sy + math.sin(ang + 0.06) * 2200)], fill=90)
    arr += np.asarray(bm.filter(ImageFilter.GaussianBlur(14)), np.float32)[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    rain(out, Cam(1, 960, 540, W, H), t, 1.2)
    z = lerp(1.0, 1.08, ss((t - SH5A) / (SH5B - SH5A)))               # slow push in
    if z > 1.0:
        cw, ch = W / z, H / z
        out = out.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) * 0.35, (W + cw) / 2, (H - ch) * 0.35 + ch))
    return out


# ---------------------------------------------------------------- 5b: his profile, close
PROFILE = [(0.12, 0.30), (0.20, 0.13), (0.32, 0.04), (0.46, 0.0), (0.58, 0.04), (0.65, 0.12), (0.685, 0.22),
           (0.70, 0.30), (0.688, 0.335), (0.70, 0.37), (0.75, 0.43), (0.79, 0.475), (0.775, 0.49), (0.735, 0.50),
           (0.74, 0.525), (0.745, 0.545), (0.722, 0.565), (0.738, 0.585), (0.718, 0.61), (0.722, 0.65),
           (0.715, 0.685), (0.68, 0.72), (0.61, 0.755), (0.585, 0.80), (0.60, 0.87), (0.67, 0.94), (0.85, 1.0),
           (0.95, 1.06), (0.98, 1.2), (-0.10, 1.2), (-0.06, 1.0), (0.06, 0.93), (0.19, 0.83), (0.20, 0.72),
           (0.14, 0.60), (0.10, 0.47), (0.10, 0.38)]
PROF_BOX = (330, 90, 980, 1090)                 # screen rect of the head (also the lyrics anchor)
_PROF = None
def profile_masks(W, H):
    global _PROF
    if _PROF is None:
        x0, y0, x1, y1 = PROF_BOX; s = (y1 - y0) / 1.1
        T = lambda p: (x0 + p[0] * s, y0 + p[1] * s)
        m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m); d.polygon([T(p) for p in PROFILE], fill=255)
        eye = Image.new("L", (W, H), 0); ed = ImageDraw.Draw(eye)
        ex, ey = T((0.60, 0.345)); ed.ellipse([ex - 32, ey - 9, ex + 30, ey + 9], fill=255)
        d.ellipse([ex - 32, ey - 9, ex + 30, ey + 9], fill=0)
        ear = T((0.36, 0.40)); d.arc([ear[0] - 40, ear[1] - 60, ear[0] + 40, ear[1] + 60], 300, 120, fill=0, width=8)
        r = np.random.default_rng(9)
        pa = np.asarray(m, np.float32) / 255
        over = np.asarray(m.filter(ImageFilter.GaussianBlur(7)), np.float32) / 255
        dr = Image.new("L", (W, H), 0); dd = ImageDraw.Draw(dr)
        for _ in range(7):
            xx = r.uniform(T((0.62, 0))[0], T((0.74, 0))[0]); yy = T((0, r.uniform(0.66, 0.72)))[1]
            dd.line([(xx, yy), (xx, yy + r.uniform(40, 150))], fill=210, width=int(r.uniform(4, 7)))
        paint = np.clip(pa * 0.97 + over * 0.2 + np.asarray(dr, np.float32) / 255 * 0.8, 0, 1) * (0.88 + 0.12 * r.random(pa.shape))
        edge = np.asarray(m.filter(ImageFilter.MaxFilter(7)), np.float32) - np.asarray(m.filter(ImageFilter.MinFilter(7)), np.float32)
        halo = np.asarray(Image.fromarray(edge.astype(np.uint8)).filter(ImageFilter.GaussianBlur(26)), np.float32)
        eg = np.asarray(eye.filter(ImageFilter.GaussianBlur(10)), np.float32)
        _PROF = (paint[..., None], (np.clip(edge + halo * 2.6, 0, 255) / 255)[..., None],
                 (np.clip(np.asarray(eye, np.float32) + eg * 2.0, 0, 255) / 255)[..., None])
    return _PROF


def profile_frame(t, size):
    W, H = size
    z = lerp(2.3, 2.45, ss((t - SH5B) / (SH6 - SH5B)))
    c = Cam(z, 1250, 520, W, H)
    img = wall_crop(c)
    paint, glow, eye = profile_masks(W, H)
    u = ss((t - SH5B - 1.2) / (SH6 - SH5B - 1.2))                  # his outline begins to burn
    tone = lerp(98, 40, u)
    img = img * (1 - paint) + tone * paint
    L = 0.42 + 0.25 * np.linspace(1, 0, H)[:, None, None]
    img = img * L
    g = u * 0.55 * (ignite(t, SH5B + 1.2, 1.2) if t < SH5B + 2.4 else 1.0)
    e = ignite(t, SH5B + 2.2, 0.8) * (0.4 + 0.6 * u)
    img = img + glow * WHITE * g + eye * WHITE * e
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    rain(out, c, t, 1.0)
    return out



# ---------------------------------------------------------------- frame + anchor
def anchor(t):
    if SH5A <= t < SH5B: return (1500, 300, 1700, 420)            # beside the building's roof
    if SH5B <= t < SH6: return PROF_BOX
    if t < SH2: return (MAN_X - 120, 520, MAN_X + 150, 960)
    return (MAN_X - 110, 500, MAN_X + 160, 960)



# ================================================================= v2 look (stencil rig, drums, volumetric light)
from scipy.ndimage import gaussian_filter
from lyricnoir.stencil import Pose, stencil, place, resized

BEATS = [tuple(b) for b in json.load(open(os.path.join(os.path.dirname(__file__), "beats.json")))]
BIG = [CUT2, SH7, SOLO0, SH9]                      # hard white-flash cuts
TONES = (5.0, 50.0, 120.0)                         # stencil paint: dark base, mid, highlight
MAN_H = 440
WHO = {300: ("child", "q", -1, 430), 560: ("hat", "side", 1, 420), 820: ("coat", "side", -1, 405),
       1080: ("hoodie", "side", 1, 430), 1340: ("coat", "side", 1, 410), 1860: ("umbrella", "side", 1, 425),
       2120: ("child", "q", -1, 430), 2380: ("hat", "side", -1, 420), 2640: ("hoodie", "side", -1, 430),
       2900: ("coat", "side", 1, 405)}
LIT_KIND = {"umbrella": "plain"}


def _breath(t, x):
    return 0.5 if int((t + x * 0.0013) / 1.333) % 2 else -0.2


def man_pose_v2(t):
    w = _breath(t, MAN_X)
    if t < CUT2 + 2.61: return Pose("hoodie", "side", -1, (-6, -4), (8, 6), "pocket", "pocket", 0.05, weight=w)
    if t < CUT2 + 2.94: return Pose("hoodie", "q", -1, (-6, -4), (8, 6), "pocket", "pocket", 0.05)
    if t < CUT2 + 3.69: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "pocket", 0.055)
    if t < CUT2 + 5.26: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "pocket", 0.055, eyes=1.0)
    if t < CUT2 + 5.61: return Pose("hoodie", "front", 1, (-6, -4), (30, -70), "pocket", "open", 0.055, eyes=1.0)
    if t < SH4: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "chest", 0.055, eyes=1.0)
    if t < LS[14]: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "pocket", 0.055, eyes=0.5 + 0.5 * man_glow(t))
    if t < LS[15]: return Pose("hoodie", "front", 1, (-6, -4), (60, -40), "pocket", "fist", 0.06, eyes=1.0)
    if t < LS[16]: return Pose("hoodie", "front", 1, (-6, -4), (115, -10), "pocket", "fist", 0.06, eyes=1.0)
    return Pose("hoodie", "front", 1, (-8, -5), (165, 15), "pocket", "fist", 0.065, eyes=1.0)


def other_pose_v2(x, t):
    kind, head, face, h = WHO[x]
    lt = LIGHT_T[x]
    lk = LIT_KIND.get(kind, kind)
    if t >= lt + 0.5: return Pose(lk, "front" if kind != "child" else "q", 1, (-8, -5), (165, 15), "pocket", "fist", 0.06)
    if t >= lt: return Pose(lk, "front" if kind != "child" else "q", 1, (-8, -5), (90, -30), "pocket", "fist", 0.06)
    kw = dict(kind=kind, head=head, face=face, weight=_breath(t, x), stance=0.05)
    if kind == "hat": kw.update(larm=(-14, -8), lean=0.06)
    if kind == "umbrella": kw.update(rarm=(30, -70))
    if kind == "child": kw.update(larm=(-30, -20))
    if kind in ("coat", "hoodie"): kw.update(lhand="pocket")
    if x == 1340 and SH3 + 2.0 <= t < SH7: kw["face"] = -1                      # she turns her back on him
    return Pose(**kw)


def ghost_list(fn, t, keep=5):
    out, prev = [], None
    k0 = max(0, int((t - 4.0) * 6))
    for k in range(k0, int(t * 6) + 1):
        p = fn(k / 6)
        if prev is not None and p != prev: out.append((prev, k / 6))
        prev = p
    return out[-keep:]


def beat_kick(t, min_k=0.75):
    """Camera shake offsets + zoom punch from the drum hits."""
    sx = sy = zp = 0.0
    amp = 0.0 if (SH5A <= t < SH6) else (0.6 if SOLO0 <= t < SH9 else 1.0)
    for bt, k in BEATS:
        if k < min_k or not (0 <= t - bt < 0.4): continue
        e = k * math.exp(-(t - bt) / 0.09) * amp
        r = np.random.default_rng(int(bt * 1000))
        sx += r.normal(0, 8) * e; sy += r.normal(0, 6) * e; zp += 0.02 * e
    for bt in BIG:
        if 0 <= t - bt < 0.5:
            e = math.exp(-(t - bt) / 0.12); r = np.random.default_rng(int(bt * 999))
            sx += r.normal(0, 16) * e; sy += r.normal(0, 12) * e; zp += 0.04 * e
    return sx, sy, zp


def flash(t):
    f = 0.0
    for bt in BIG:
        if 0 <= t - bt < 0.16: f = max(f, (1 - (t - bt) / 0.16) ** 2)
    for bt, k in BEATS:
        if k > 0.85 and 0 <= t - bt < 0.1: f = max(f, 0.10 * k * (1 - (t - bt) / 0.1))
    return f


def beams_v2(t):
    if t < CUT2:
        return [(lerp(400, 2800, ss((t - 2.5) / 6.0)), 110, 0.35 * ss((t - 2.5) / 0.8) * (1 - ss((t - 8.6) / 0.8)))]
    if t < SH3: return [(lerp(700, 2500, ss((t - CUT2 + 0.2) / 7.2)), 150, 1.0)]
    if SH3 <= t < SH4: return [(lerp(2300, 3000, (t - SH3) / (SH4 - SH3)), 140, 0.6)]
    return beams(t)


HEADLIGHTS = [(CUT2 + 4.76, 2.5, 2600, 500), (SOLO0 + 9.0, 2.6, 300, 2900), (SH4 + 1.0, 2.2, 2700, 600)]
def headlights(t):
    for t0, d, xa, xb in HEADLIGHTS:
        if t0 <= t < t0 + d: return lerp(xa, xb, (t - t0) / d), math.sin(math.pi * (t - t0) / d)
    return None


_FOG = gaussian_filter(np.random.default_rng(1).random((90, 160)).astype(np.float32), 3, mode="wrap")
_FOG = (_FOG - _FOG.min()) / (_FOG.max() - _FOG.min())
def lights(t, c):
    W, H = c.W, c.H; lw, lh = W // 4, H // 4
    yy = np.linspace(0, 1, lh)[:, None]
    amb = 0.07 if t < CUT2 else (0.18 if SH4 <= t < SH5A else (0.40 if t >= SH9 else 0.30))
    L = np.full((lh, lw), amb, np.float32) * (0.75 + 0.45 * (1 - yy))
    haze = np.zeros((lh, lw), np.float32)
    X, Y = np.meshgrid(np.arange(lw), np.arange(lh))
    fog = np.asarray(Image.fromarray((np.roll(_FOG, int(t * 6) % 160, axis=1) * 255).astype(np.uint8)).resize((lw, lh), Image.BILINEAR), np.float32) / 255
    bl = list(beams_v2(t))
    h = hit(t)
    if h > 0: bl.append((MAN_X + 30, 120, 1.6 * h))
    for tx, hw, k in bl:
        if k <= 0: continue
        src = c.P(tx - 700, -1300); a = c.P(tx - hw, 720); b = c.P(tx + hw, 720)
        poly = [(src[0] / 4, src[1] / 4), ((src[0] + (a[0] - src[0]) * 2.6) / 4, (src[1] + (a[1] - src[1]) * 2.6) / 4),
                ((src[0] + (b[0] - src[0]) * 2.6) / 4, (src[1] + (b[1] - src[1]) * 2.6) / 4)]
        im = Image.new("L", (lw, lh), 0); ImageDraw.Draw(im).polygon(poly, fill=255)
        cone = gaussian_filter(np.asarray(im, np.float32) / 255, 3)
        haze = np.maximum(haze, cone * (0.35 + 0.65 * fog) * min(1.0, k))
        e = c.P(tx, 720); rx, ry = (hw + 30) * c.z / 4, (hw * 1.4 + 60) * c.z / 4
        L += np.exp(-(((X - e[0] / 4) / rx) ** 2 + ((Y - e[1] / 4) / ry) ** 2) * 1.6) * 1.35 * k + cone * 0.25 * k
    hl = np.zeros((lh, lw), np.float32)
    hd = headlights(t)
    if hd is not None:
        e = c.P(hd[0], 880)
        hl = np.exp(-(((X - e[0] / 4) / (420 * c.z / 4)) ** 2 + ((Y - e[1] / 4) / (190 * c.z / 4)) ** 2)) * hd[1]
        L += hl * 1.1
    sl, sr = strobe(t)
    xx = np.linspace(0, 1, lw)[None, :]
    L += sl * 1.3 * np.clip(1 - xx * 1.6, 0, 1) + sr * 1.3 * np.clip(xx * 1.6 - 0.6, 0, 1) + 0.5 * h
    L += flash(t) * 1.6
    up = lambda a: np.asarray(Image.fromarray(np.clip(a * 60, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 60
    return up(L), up(haze), up(hl)


def paint_person(img, emit, c, x, pose, h, gl, glow=0.0, band=0.0, vis=1.0, t=0.0, dx=0.0):
    for gp, tl in gl:
        st = stencil(gp, h); pl = place(st, c, x + dx, GROUND, (c.W, c.H))
        if pl is None: continue
        w_, h_, src, dst = pl
        a = resized(st.base, w_, h_)[src][..., None] * (0.30 * math.exp(-(t - tl) / 1.0) + 0.07) * vis
        img[dst] = img[dst] * (1 - a) + 20 * a
    st = stencil(pose, h); pl = place(st, c, x + dx, GROUND, (c.W, c.H))
    if pl is None: return
    w_, h_, src, dst = pl
    for arr, tone in ((st.base, TONES[0]), (st.mid, TONES[1]), (st.light, TONES[2])):
        a = resized(arr, w_, h_)[src][..., None] * vis
        img[dst] = img[dst] * (1 - a) + tone * a
    if glow > 0:
        emit[dst] += resized(st.glow, w_, h_)[src][..., None] * WHITE * glow
    if st.eyes is not None:
        emit[dst] += resized(st.eyes, w_, h_)[src][..., None] * np.array([235, 240, 255]) * 1.8
    if band > 0:                                                                # only those who carry the red
        bd = resized(st.band, w_, h_)[src][..., None] * vis
        img[dst] = img[dst] * (1 - bd) + RED_PAINT * bd
        emit[dst] += bd * RED_GLOW * band * 0.8 + gaussian_filter(bd[..., 0], max(2, 6 * c.z))[..., None] * RED_GLOW * band * 0.45


PASSERS = [(CUT2 - 2.44, 2.3, -1, "coat"), (CUT2 + 1.46, 2.0, 1, "umbrella"), (CUT2 + 5.96, 2.0, -1, "hat"),
           (SH4 + 1.6, 2.2, 1, "hoodie"), (SOLO0 + 2.5, 2.4, -1, "coat"), (SOLO0 + 13.0, 2.4, 1, "umbrella")]
def passers(img, t):
    W, H = img.shape[1], img.shape[0]
    for t0, d, dirn, kind in PASSERS:
        if not (t0 <= t < t0 + d): continue
        u = (t - t0) / d
        sx = lerp(-700, W + 700, u) if dirn < 0 else lerp(W + 700, -700, u)
        step = int(t * 8) % 4
        p = Pose(kind, "side", 1 if dirn < 0 else -1, (-14 + step * 9, -8), (10 - step * 7, -6), stance=[0.02, 0.09, 0.02, 0.09][step])
        st = stencil(p, 1000, 0.45)
        bx0, by0, bx1, by1 = st.box
        wpx, hpx = int((bx1 - bx0) * 1.55), int((by1 - by0) * 1.55)
        a = resized(gaussian_filter(resized(st.base, wpx // 3, hpx // 3), 6), wpx, hpx)
        x0 = int(sx - wpx / 2); y0 = int(H * 1.18 - hpx)
        cx0, cy0, cx1, cy1 = max(0, -x0), max(0, -y0), min(wpx, W - x0), min(hpx, H - y0)
        if cx1 <= cx0 or cy1 <= cy0: continue
        aa = a[cy0:cy1, cx0:cx1][..., None] * 0.94
        img[y0 + cy0:y0 + cy1, x0 + cx0:x0 + cx1] = img[y0 + cy0:y0 + cy1, x0 + cx0:x0 + cx1] * (1 - aa) + 3 * aa


_R = np.random.default_rng(3); RN = 520
RX, RY, RSP, RL = _R.random(RN) * 2220 - 150, _R.random(RN) * 1080, _R.uniform(1500, 2300, RN), _R.uniform(16, 44, RN)
def rain_layer(t, W, H, amount=1.0):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for i in range(int(RN * amount)):
        y = (RY[i % RN] * H / 1080 + t * RSP[i % RN]) % (H + 60) - 30; x = RX[i % RN] * W / 1920 - y * 0.12
        d.line([(x, y), (x - RL[i % RN] * 0.12, y + RL[i % RN])], fill=255, width=2 if i % 6 == 0 else 1)
    return np.asarray(im, np.float32) / 255


DUST = np.random.default_rng(8).random((260, 3))
def dust(t, haze):
    H, W = haze.shape; a = np.zeros((H, W), np.float32)
    for k in range(len(DUST)):
        x = int((DUST[k, 0] * W + t * 25 * (DUST[k, 2] - 0.5)) % W); y = int((DUST[k, 1] * H + t * 12) % H)
        if haze[y, x] > 0.08: a[y:y + 2, x:x + 2] = haze[y, x]
    return a


def flare(img, t, c):
    hd = headlights(t)
    if hd is None: return img
    W, H = c.W, c.H
    x, y, k = c.P(hd[0], 880)[0], H * 0.96, hd[1]
    stp = np.zeros((H, W), np.float32); yi = int(y); stp[yi - 2:yi + 2, :] = 1.0
    stp = gaussian_filter(stp, (3, 0)) * np.exp(-((np.arange(W)[None, :] - x) / 700) ** 2)
    X, Y = np.meshgrid(np.arange(0, W, 4), np.arange(0, H, 4))
    small = np.exp(-(((X - x) / 90) ** 2 + ((Y - y) / 60) ** 2)) + np.exp(-(((X - (W - x)) / 40) ** 2 + ((Y - (H - y)) / 40) ** 2)) * 0.35
    core = np.asarray(Image.fromarray(np.clip(small * 255, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    return img + (stp * 0.7 + core * 0.9)[..., None] * np.array([220, 228, 255]) * k


def finish(img):
    """Bloom + slight lens fringing (all scenes)."""
    H, W = img.shape[:2]
    br = np.clip(img.mean(-1) - 150, 0, None)
    bl = np.asarray(Image.fromarray(np.clip(br, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
                    .filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), np.float32)
    img = img + bl[..., None] * 0.8
    img[..., 0] = np.roll(img[..., 0], 2, axis=1); img[..., 2] = np.roll(img[..., 2], -2, axis=1)
    return img


def wall_frame(t, c):
    img = wall_crop(c); emit = np.zeros_like(img)
    sl, sr = strobe(t)
    for i, x in enumerate(sorted(WHO)):
        g = ignite(t, LIGHT_T[x], 0.8)
        vis = 0.35 if (sl + sr > 0 and g == 0 and (int(t * 9) + i * 3) % 4 == 0) else 1.0
        paint_person(img, emit, c, x, other_pose_v2(x, t), WHO[x][3], ghost_list(lambda tt, x=x: other_pose_v2(x, tt), t),
                     glow=g * 0.95, band=g * 0.9, vis=vis, t=t)
    gm = man_glow(t)
    jit = np.random.default_rng(int(t * 30)).normal(0, 7) * hit(t)
    paint_person(img, emit, c, MAN_X, man_pose_v2(t), MAN_H, ghost_list(man_pose_v2, t), glow=gm, band=man_band(t), t=t, dx=jit)
    sp = stripe(t)                                                              # gray spray stripe (shot 4 -> burns away)
    if sp > 0:
        k = ss((t - LS[6] - 0.4) / 1.6)
        p0 = (MAN_X - 95, 700); p1 = (lerp(MAN_X - 95, MAN_X + 105, k), lerp(700, 610, k))
        m = Image.new("L", (c.W, c.H), 0); ImageDraw.Draw(m).line([c.P(*p0), c.P(*p1)], fill=255, width=c.lw(34))
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(max(1, 4 * c.z))), np.float32)[..., None] / 255 * sp * 0.9
        img = img * (1 - m) + 122 * m
    tracks = Image.new("L", (c.W, c.H), 0); td = ImageDraw.Draw(tracks)        # red line passing the armband on
    for x, lt in LIGHT_T.items():
        src = SOURCE[x]; u = ss((t - (lt - 0.9)) / 0.9)
        if u <= 0: continue
        xe = lerp(src, x, u)
        td.line([c.P(src, BAND_Y), c.P(xe, BAND_Y)], fill=255 if u < 1 else 120, width=c.lw(5))
        if u < 1:
            hx, hy = c.P(xe, BAND_Y); rr = 12 * c.z; td.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=255)
    tr = np.asarray(tracks, np.float32)
    if tr.max() > 0:
        trh = np.asarray(tracks.filter(ImageFilter.GaussianBlur(max(2, 9 * c.z))), np.float32)
        emit += ((tr + trh * 2.5) / 255)[..., None] * RED_GLOW * 0.9
    L, haze, hl = lights(t, c)
    glue_mark(img, c, t)
    img = img * L[..., None]
    gy = int(round(c.P(0, WALL_END)[1]))
    if 0 < gy < c.H:
        n = min(gy, c.H - gy); emit[gy:gy + n] += gaussian_filter(emit[gy - n:gy][::-1], (5, 5, 0)) * 0.35
    img += emit
    rl = rain_layer(t, c.W, c.H, 1.4 if SOLO0 <= t < SH9 else 1.0)
    img += (rl * (28 + 230 * haze + 120 * hl))[..., None] * np.array([0.92, 0.95, 1.0])
    img += (haze * 70)[..., None] * np.array([0.9, 0.94, 1.0])
    img += (dust(t, haze) * 200)[..., None]
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    if SH2 <= t < SH4:
        px, py = c.P(1730, 420)
        draw_poster(out, c, t, float(L[int(np.clip(py, 0, c.H - 1)), int(np.clip(px, 0, c.W - 1))]))
    img = np.asarray(out, np.float32).copy()
    passers(img, t)
    return flare(img, t, c)


def frame(t, size=(1920, 1080), cam=None):
    W, H = size
    if cam is None and SH5A <= t < SH5B: img = np.asarray(building_frame(t, size), np.float32).copy()
    elif cam is None and SH5B <= t < SH6: img = np.asarray(profile_frame(t, size), np.float32).copy()
    else:
        z, cx, cy = cam or camera(t)
        if cam is None:
            sx, sy, zp = beat_kick(t)
            cx += 3 * math.sin(t * 1.7) + 2 * math.sin(t * 3.1) + sx / z; cy += 2 * math.sin(t * 2.3 + 1) + sy / z; z *= 1 + zp
        img = wall_frame(t, Cam(z, cx, cy, W, H))
        if cam is None: img = img + flash(t) * 0  # flash already lights the wall
    img = finish(img)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return Post.apply(out, t, fade_in_out(t, META["duration"], 1.0, META["fade_out"]))
