"""Lyric Noir — Film No. 02 — Michael Jackson, "They Don't Care About Us".
One-line story: an invisible man on a night-city wall that nobody sees, until the people beside him light up
and the searchlight can't look away.
Song section used: 1:41.6 -> ~3:20 (timings in timing.json; never store lyrics here).

Style (new for this film): dark wet concrete wall at night; people are spray-paint stencils with drips.
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
    cover=dict(t=79.0, z=1.25, cx=1600, cy=740),
)

# ---------------------------------------------------------------- timing (video seconds)
_T = json.load(open(os.path.join(os.path.dirname(__file__), "timing.json")))
A0 = _T["audio_start"]
LS = {r["line"]: r["start"] - A0 for r in _T["lines"]}           # line starts in video time
HITS = [LS[i] for i in range(10, 18)]                             # the fast skin-head lines
SOLO0, SOLO1 = 163.5 - A0, 186.5 - A0                             # guitar solo
SH2, SH3, SH4, SH5A, SH5B, SH6, SH7, SH9 = LS[1], LS[3], LS[5], LS[7], LS[9], LS[10], LS[18], LS[20]
END = META["duration"]

# ---------------------------------------------------------------- camera
CAM = [
    (0.0, SH2, 1.22, 1.32, 1600, 1600, 690, 690),               # 1 hook: darkness + red armband
    (SH2, SH3, 0.92, 0.97, 1560, 1640, 640, 640),               # 2 wall of gray stencils
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
BAND_Y = GROUND - 0.70 * 420
WS = 2.5                                       # stencil mask pixels per world unit
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


# ---------------------------------------------------------------- stencil figures
def _seg(p, q, w):
    dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return [(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)]


def _norm(v):
    L = math.hypot(*v) or 1; return (v[0] / L, v[1] / L)


def figure_shapes(kind, rk):
    """Normalized shapes (height 1, feet at y=0, up is -y). rk = raise of the right (+x) arm 0..1."""
    P, E, gaps = [], [], []
    head_r = 0.085 if kind == "child" else 0.066
    lean = 0.07 if kind == "old" else 0.0
    L = lambda x, y: (x + lean * (-y) * 0.6, y)                 # lean the upper body forward
    E.append((L(0, -0.912)[0], -0.912, head_r, head_r * 1.13))
    P.append([L(-0.03, -0.86), L(0.03, -0.86), L(0.035, -0.81), L(-0.035, -0.81)])            # neck
    gaps.append(_seg(L(-0.05, -0.838), L(0.05, -0.838), 0.012))   # stencil bridge at the neck
    P.append([L(-0.128, -0.815), L(0.128, -0.815), L(0.10, -0.51), L(0.112, -0.47), L(-0.112, -0.47), L(-0.10, -0.51)])
    if kind == "woman":
        P.append([(-0.10, -0.52), (0.10, -0.52), (0.17, -0.24), (-0.17, -0.24)])
        E.append((L(0, -0.885)[0], -0.885, head_r * 1.32, head_r * 1.55))
        P.append([(-0.075, -0.25), (-0.025, -0.25), (-0.035, -0.02), (-0.07, -0.02)])
        P.append([(0.025, -0.25), (0.075, -0.25), (0.07, -0.02), (0.035, -0.02)])
    else:
        P.append([(-0.11, -0.48), (-0.012, -0.48), (-0.03, -0.02), (-0.095, -0.02)])
        P.append([(0.012, -0.48), (0.11, -0.48), (0.095, -0.02), (0.03, -0.02)])
    E.append((-0.07, -0.012, 0.05, 0.016)); E.append((0.07, -0.012, 0.05, 0.016))     # shoes
    if kind == "hat":
        P.append([L(-0.115, -0.972), L(0.115, -0.972), L(0.115, -0.955), L(-0.115, -0.955)])
        P.append([L(-0.068, -1.05), L(0.068, -1.05), L(0.072, -0.97), L(-0.072, -0.97)])
    # left arm (hangs)
    sL = L(-0.128, -0.79); eL = (sL[0] - 0.04, sL[1] + 0.17); hL = (eL[0] - 0.01, eL[1] + 0.16)
    P.append(_seg(sL, eL, 0.056)); P.append(_seg(eL, hL, 0.046)); E.append((hL[0], hL[1], 0.03, 0.03))
    E.append((sL[0] + 0.012, sL[1] - 0.004, 0.04, 0.034)); E.append((eL[0], eL[1], 0.027, 0.027))
    if kind == "old":                                                       # cane
        P.append(_seg((hL[0] - 0.01, hL[1]), (hL[0] - 0.06, 0.0), 0.016))
    # right arm: hangs (rk=0) -> raised fist (rk=1)
    sR = L(0.128, -0.79)
    u0, u1 = _norm((0.25, 1)), _norm((0.5, -0.86))
    f0, f1 = _norm((0.06, 1)), _norm((0.12, -1))
    u = _norm((lerp(u0[0], u1[0], rk), lerp(u0[1], u1[1], rk)))
    f = _norm((lerp(f0[0], f1[0], rk), lerp(f0[1], f1[1], rk)))
    eR = (sR[0] + u[0] * 0.17, sR[1] + u[1] * 0.17); hR = (eR[0] + f[0] * 0.16, eR[1] + f[1] * 0.16)
    P.append(_seg(sR, eR, 0.058)); P.append(_seg(eR, hR, 0.047))
    E.append((sR[0] - 0.012, sR[1] - 0.004, 0.04, 0.034)); E.append((eR[0], eR[1], 0.027, 0.027))
    E.append((hR[0], hR[1], 0.036 if rk > 0.5 else 0.03, 0.036 if rk > 0.5 else 0.03))
    a, b = (sR[0] + u[0] * 0.05, sR[1] + u[1] * 0.05), (sR[0] + u[0] * 0.105, sR[1] + u[1] * 0.105)
    band = _seg(a, b, 0.082)
    return P, E, gaps, band


class Stencil:
    """Pre-rendered masks (paint, armband, glow, armband halo) for one figure in one pose."""
    def __init__(s, kind, h, rk, seed):
        P, E, gaps, band = figure_shapes(kind, rk)
        s.h = h; m = 70 / h
        s.bx0, s.by0, s.bx1, s.by1 = -0.42 - m, -1.15 - m, 0.42 + m, 0.22 + m        # normalized local box
        Wp = int((s.bx1 - s.bx0) * h * WS); Hp = int((s.by1 - s.by0) * h * WS)
        T = lambda p: ((p[0] - s.bx0) * h * WS, (p[1] - s.by0) * h * WS)
        paint = Image.new("L", (Wp, Hp), 0); d = ImageDraw.Draw(paint)
        for poly in P: d.polygon([T(p) for p in poly], fill=255)
        for (cx, cy, rx, ry) in E:
            a, b = T((cx - rx, cy - ry)), T((cx + rx, cy + ry)); d.ellipse([a, b], fill=255)
        for g in gaps: d.polygon([T(p) for p in g], fill=0)
        bandm = Image.new("L", (Wp, Hp), 0); ImageDraw.Draw(bandm).polygon([T(p) for p in band], fill=255)
        bandm = Image.fromarray(np.minimum(np.asarray(bandm), np.asarray(paint.filter(ImageFilter.MaxFilter(5)))))
        r = np.random.default_rng(seed)
        pa = np.asarray(paint, np.float32) / 255
        # spray overspray + speckle
        over = np.asarray(paint.filter(ImageFilter.GaussianBlur(3 * WS)), np.float32) / 255
        far = np.asarray(paint.filter(ImageFilter.GaussianBlur(10 * WS)), np.float32) / 255
        spk = (r.random(pa.shape) < 0.05) * far
        # drips from the lowest points and the hands
        dr = Image.new("L", (Wp, Hp), 0); dd = ImageDraw.Draw(dr)
        ys, xs = np.nonzero(pa > 0.5)
        for _ in range(9):
            k = r.integers(len(xs)); x, y = xs[k], ys[k]
            col = np.nonzero(pa[:, x] > 0.5)[0]
            if len(col) == 0: continue
            y = col.max(); L_ = r.uniform(12, 70) * WS
            w = r.uniform(1.6, 2.8) * WS
            dd.line([(x, y), (x, y + L_)], fill=200, width=int(w))
            dd.ellipse([x - w, y + L_ - w, x + w, y + L_ + w], fill=200)
        drip = np.asarray(dr.filter(ImageFilter.GaussianBlur(0.6 * WS)), np.float32) / 255
        tot = np.clip(pa * 0.97 + over * 0.22 + spk * 0.5 + drip * 0.85, 0, 1)
        tot *= (0.88 + 0.12 * r.random(pa.shape))                                    # uneven paint
        s.paint = Image.fromarray((tot * 255).astype(np.uint8))
        s.band = bandm.filter(ImageFilter.GaussianBlur(0.5 * WS))
        edge = np.asarray(paint.filter(ImageFilter.MaxFilter(5)), np.float32) - np.asarray(paint.filter(ImageFilter.MinFilter(5)), np.float32)
        edge_im = Image.fromarray(edge.astype(np.uint8))
        halo = np.asarray(edge_im.filter(ImageFilter.GaussianBlur(9 * WS)), np.float32)
        glow = np.clip(edge * 1.0 + halo * 2.6, 0, 255)
        s.glow = Image.fromarray(glow.astype(np.uint8))
        bh = np.asarray(bandm.filter(ImageFilter.GaussianBlur(14 * WS)), np.float32)
        s.bandhalo = Image.fromarray(np.clip(bh * 2.2, 0, 255).astype(np.uint8))

    def screen_box(s, c, x):
        a = c.P(x + s.bx0 * s.h, GROUND + s.by0 * s.h); b = c.P(x + s.bx1 * s.h, GROUND + s.by1 * s.h)
        return a[0], a[1], b[0], b[1]


_ST = None
def stencils():
    global _ST
    if _ST is None:
        _ST = {"man": [Stencil("base", 430, k / 3, 100 + k) for k in range(4)]}
        H = {"child": 280, "hat": 405, "woman": 400, "old": 395, "base": 415}
        for i, (x, kind) in enumerate(OTHERS):
            _ST[x] = [Stencil(kind, H[kind], 0.0, 10 + i), Stencil(kind, H[kind], 1.0, 10 + i)]
    return _ST


def _masks(st, c, x, which):
    """Resize the stencil's masks to screen; returns (x0, y0, dict of float arrays) clipped to the frame, or None."""
    sx0, sy0, sx1, sy1 = st.screen_box(c, x)
    if sx1 < 0 or sx0 > c.W or sy1 < 0 or sy0 > c.H: return None
    w, h = max(2, int(round(sx1 - sx0))), max(2, int(round(sy1 - sy0)))
    ix, iy = int(round(sx0)), int(round(sy0))
    cx0, cy0 = max(0, -ix), max(0, -iy); cx1, cy1 = min(w, c.W - ix), min(h, c.H - iy)
    if cx1 <= cx0 or cy1 <= cy0: return None
    out = {}
    for k in which:
        m = getattr(st, k).resize((w, h), Image.BILINEAR)
        out[k] = np.asarray(m, np.float32)[cy0:cy1, cx0:cx1] / 255
    return ix + cx0, iy + cy0, out


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
    if t < SH2: return 0.75 * ignite(t, 1.2, 1.0)
    if t < SH6: return 0.12
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


# ---------------------------------------------------------------- light map (low res)
def light_map(t, c):
    lw, lh = c.W // 4, c.H // 4
    base = np.full((lh, lw), ambient(t), np.float32)
    yy = np.linspace(0, 1, lh)[:, None]
    base *= (0.75 + 0.45 * (1 - yy))                                     # soft light from above
    im = Image.new("L", (lw, lh), 0); d = ImageDraw.Draw(im)
    for tx, hw, k in beams(t):
        src = c.P(tx - 500, -900)
        a = c.P(tx - hw, 700); b = c.P(tx + hw, 700)
        dxa, dya = a[0] - src[0], a[1] - src[1]; dxb, dyb = b[0] - src[0], b[1] - src[1]
        far = 3.0
        poly = [(src[0] / 4, src[1] / 4), ((src[0] + dxa * far) / 4, (src[1] + dya * far) / 4),
                ((src[0] + dxb * far) / 4, (src[1] + dyb * far) / 4)]
        d.polygon(poly, fill=int(110 * k))
        e = c.P(tx, 700); rx, ry = hw * c.z * 1.0 / 4, hw * c.z * 1.5 / 4
        d.ellipse([e[0] / 4 - rx, e[1] / 4 - ry, e[0] / 4 + rx, e[1] / 4 + ry], fill=int(255 * k))
    h = hit(t)
    if h > 0:
        e = c.P(MAN_X + 40, 640); r = 95 * c.z / 4
        d.polygon([(e[0] / 4 - r * 0.6, 0), (e[0] / 4 + r * 0.6, 0), (e[0] / 4 + r, lh), (e[0] / 4 - r, lh)], fill=int(255 * h))
    bl = np.asarray(im.filter(ImageFilter.GaussianBlur(max(2, 10 * c.z / 4 * 4 / 4))), np.float32) / 255
    base += bl * 1.25
    sl, sr = strobe(t)
    xx = np.linspace(0, 1, lw)[None, :]
    base += sl * 1.3 * np.clip(1 - xx * 1.6, 0, 1) + sr * 1.3 * np.clip(xx * 1.6 - 0.6, 0, 1)
    base += 0.6 * h
    return np.asarray(Image.fromarray(np.clip(base * 100, 0, 255).astype(np.uint8)).resize((c.W, c.H), Image.BILINEAR), np.float32) / 100


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


# ---------------------------------------------------------------- wall scene
def wall_frame(t, c):
    img = wall_crop(c)                                           # unlit albedo
    emit = np.zeros_like(img)
    ST = stencils()
    sl, sr = strobe(t)
    jit = hit(t)
    # gray / lit others
    for i, (x, kind) in enumerate(OTHERS):
        g, raised = other_state(x, t)
        st = ST[x][1 if raised else 0]
        r = _masks(st, c, x, ("paint", "band", "glow", "bandhalo") if g > 0 else ("paint",))
        if r is None: continue
        ox, oy, M = r; hh, ww = M["paint"].shape; sl_ = (slice(oy, oy + hh), slice(ox, ox + ww))
        vis = 1.0
        if sl + sr > 0 and g == 0 and (int(t * 9) + i * 3) % 4 == 0: vis = 0.3      # flicker under strobes
        tone = lerp(98, 9, min(1, g * 1.4))
        a = M["paint"][..., None] * vis
        img[sl_] = img[sl_] * (1 - a) + tone * a
        if g > 0:
            b = M["band"][..., None]
            img[sl_] = img[sl_] * (1 - b) + RED_PAINT * b
            emit[sl_] += M["glow"][..., None] * WHITE * g * 0.95 + b * RED_GLOW * g * 0.9 + M["bandhalo"][..., None] * RED_GLOW * g * 0.45
    # him
    gm = man_glow(t); st = ST["man"][man_pose(t)]
    mx = MAN_X + (np.random.default_rng(int(t * 30)).normal(0, 7) * jit)
    r = _masks(st, c, mx, ("paint", "band", "glow", "bandhalo"))
    if r is not None:
        ox, oy, M = r; hh, ww = M["paint"].shape; sl_ = (slice(oy, oy + hh), slice(ox, ox + ww))
        tone = lerp(98, 9, min(1, gm * 1.5))
        a = M["paint"][..., None]
        img[sl_] = img[sl_] * (1 - a) + tone * a
        b = M["band"][..., None]
        img[sl_] = img[sl_] * (1 - b) + RED_PAINT * b
        be = man_band(t)
        emit[sl_] += M["glow"][..., None] * WHITE * gm + b * RED_GLOW * be + M["bandhalo"][..., None] * RED_GLOW * be * 0.6
    # gray spray stripe across him (shot 4 -> burns away in shot 6)
    sp = stripe(t)
    if sp > 0:
        k = ss((t - LS[6] - 0.4) / 1.6)
        p0 = (MAN_X - 95, 700); p1 = (lerp(MAN_X - 95, MAN_X + 105, k), lerp(700, 610, k))
        m = Image.new("L", (c.W, c.H), 0); md = ImageDraw.Draw(m)
        md.line([c.P(*p0), c.P(*p1)], fill=255, width=c.lw(34))
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(max(1, 4 * c.z))), np.float32)[..., None] / 255 * sp * 0.9
        img = img * (1 - m) + 122 * m
    # red light line passing the armband from person to person
    tracks = Image.new("L", (c.W, c.H), 0); td = ImageDraw.Draw(tracks)
    for x, lt in LIGHT_T.items():
        src = SOURCE[x]; u = ss((t - (lt - 0.9)) / 0.9)
        if u <= 0: continue
        xe = lerp(src, x, u)
        v = 255 if u < 1 else 120
        td.line([c.P(src, BAND_Y), c.P(xe, BAND_Y)], fill=v, width=c.lw(5))
        if u < 1:
            hx, hy = c.P(xe, BAND_Y); rr = 12 * c.z; td.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=255)
    tr = np.asarray(tracks, np.float32)
    if tr.max() > 0:
        trh = np.asarray(tracks.filter(ImageFilter.GaussianBlur(max(2, 9 * c.z))), np.float32)
        emit += ((tr + trh * 2.5) / 255)[..., None] * RED_GLOW * 0.9
    # lighting
    L = light_map(t, c)
    glue_mark(img, c, t)
    img = img * L[..., None]
    # wet sidewalk reflection of everything that glows
    gy = int(round(c.P(0, WALL_END)[1]))
    if 0 < gy < c.H:
        n = min(gy, c.H - gy)
        refl = emit[gy - n:gy][::-1] * 0.32
        refl = np.asarray(Image.fromarray(np.clip(refl, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(2, 6 * c.z))), np.float32)
        emit[gy:gy + n] += refl
    out = Image.fromarray(np.clip(img + emit, 0, 255).astype(np.uint8))
    if t < SH4:
        px, py = c.P(1730, 420)
        draw_poster(out, c, t, float(L[int(np.clip(py, 0, c.H - 1)), int(np.clip(px, 0, c.W - 1))]))
    rain(out, c, t, 1.4 if SOLO0 <= t < SH9 else 1.0)
    return out


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


def frame(t, size=(1920, 1080), cam=None):
    W, H = size
    if cam is None and SH5A <= t < SH5B: img = building_frame(t, size)
    elif cam is None and SH5B <= t < SH6: img = profile_frame(t, size)
    else:
        z, cx, cy = cam or camera(t)
        img = wall_frame(t, Cam(z, cx, cy, W, H))
    return Post.apply(img, t, fade_in_out(t, META["duration"], 1.0, META["fade_out"]))
