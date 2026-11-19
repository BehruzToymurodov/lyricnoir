"""Film 02 — 10 s look test for the upgraded style (song 1:49.6 -> 1:59.9).
Real stencil people (3-layer paint, turned bodies), stop-motion moves with paint ghosts, cuts/shake/flashes on
the drum hits, volumetric searchlight with rain in the beam, foreground passers-by, police headlights + flare.

    python episodes/02-they-dont-care/test_v2.py   -> dist/02-they-dont-care/test_v2.mp4
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scipy.ndimage import gaussian_filter
from lyricnoir.core import Cam, Post, lerp, ss, cl
from lyricnoir.render import load_story
from lyricnoir.stencil import Pose, stencil, place, resized
from lyricnoir.paths import dist_dir, work_dir

ST = load_story("02-they-dont-care")
EP = "02-they-dont-care"
S0, DUR, FPS = 109.6, 10.3, 30
W, H = 1920, 1080
GROUND = 960
HIT0 = 112.24 - S0                         # the drums kick back in: cut to the wall
HITS = [(s - S0, k) for s, k in [(112.24, 1.0), (112.57, .8), (112.91, .8), (113.92, .7), (114.24, .75), (115.24, .7),
                                   (115.58, .8), (116.92, .6), (117.59, .6), (117.91, .85), (118.25, .7), (119.58, .65)]]
RED_PAINT = np.array([150, 18, 36], np.float32); RED_GLOW = np.array([255, 34, 76], np.float32)
TONES = (5.0, 50.0, 120.0)                # dark base, mid, highlight paint

# ------------------------------------------------------------- who stands on the wall, and their stop-motion poses
MAN_X = 1600
def man_pose(t):
    if t < 5.25: return Pose("hoodie", "side", -1, (-6, -4), (8, 6), "pocket", "pocket", 0.05, weight=0.4 if (int(t / 1.333) % 2) else 0.0)
    if t < 5.58: return Pose("hoodie", "q", -1, (-6, -4), (8, 6), "pocket", "pocket", 0.05)
    if t < 6.33: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "pocket", 0.055)
    if t < 7.9: return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "pocket", 0.055, eyes=1.0)
    if t < 8.25: return Pose("hoodie", "front", 1, (-6, -4), (30, -70), "pocket", "open", 0.055, eyes=1.0)
    return Pose("hoodie", "front", 1, (-6, -4), (8, 6), "pocket", "chest", 0.055, eyes=1.0)

OTHERS = [  # x, base pose kwargs, height
    (830, dict(kind="hoodie", head="side", face=-1, lhand="pocket", rhand="open"), 430),
    (1080, dict(kind="hat", head="side", face=-1, larm=(-14, -8), rarm=(8, 4), stance=0.05, lean=0.06), 420),
    (1340, dict(kind="coat", head="side", face=1, rhand="pocket", stance=0.045), 410),
    (1870, dict(kind="umbrella", head="side", face=1, larm=(-8, -6), rarm=(30, -70)), 425),
    (2130, dict(kind="child", head="q", face=-1, larm=(-30, -20)), 430),
    (2380, dict(kind="coat", head="side", face=-1, lhand="pocket"), 405),
]
def other_pose(i, t):
    kw = dict(OTHERS[i][1]); step = int((t + i * 0.37) / 1.333)
    kw["weight"] = 0.5 if step % 2 else -0.2                                     # stop-motion breathing
    if i == 2 and t > 7.0: kw["face"] = -1                                       # she turns away from him
    return Pose(**kw)

GHOST = {}                                                                      # name -> list of (pose, t_left)
def ghosts(name, t, fn):
    """Previous stop-motion poses with the time they were left (computed from the pose timeline)."""
    out, prev = [], None
    for k in range(int(t * 6) + 1):
        tt = k / 6
        p = fn(tt)
        if prev is not None and p != prev: out.append((prev, tt))
        prev = p
    return out[-5:]

# ------------------------------------------------------------- camera: dark close-up, cut on the drums, dolly in
def camera(t):
    if t < HIT0: z, cx, cy = lerp(1.55, 1.7, t / HIT0), 1600, 650
    else:
        u = ss((t - HIT0) / (DUR - HIT0))
        z, cx, cy = lerp(0.98, 1.34, u), lerp(1560, 1610, u), lerp(630, 650, u)
    cx += 3 * math.sin(t * 1.7) + 2 * math.sin(t * 3.1); cy += 2 * math.sin(t * 2.3 + 1)
    sx = sy = 0.0; zp = 0.0
    for th, k in HITS:
        if 0 <= t - th < 0.4:
            e = k * math.exp(-(t - th) / 0.09)
            r = np.random.default_rng(int(th * 100))
            sx += r.normal(0, 9) * e; sy += r.normal(0, 7) * e; zp += 0.025 * e
    return z * (1 + zp), cx + sx / z, cy + sy / z

def flash(t):
    f = 0.0
    for th, k in HITS:
        if 0 <= t - th < 0.15: f = max(f, (1.0 if th == HIT0 else 0.12 * k) * (1 - (t - th) / 0.15) ** 2)
    return f

# ------------------------------------------------------------- light
def beam_target(t):
    return lerp(700, 2500, ss((t - HIT0 + 0.2) / 7.2))

def headlights(t):
    if not (7.4 <= t < 9.9): return None
    u = (t - 7.4) / 2.5
    return lerp(2600, 500, u)                                                    # world x of the light pool

_FOG = np.random.default_rng(1).random((90, 160)).astype(np.float32)
_FOG = gaussian_filter(_FOG, 3, mode="wrap")
def fog(t, lw, lh):
    sh = int(t * 6) % 160
    f = np.roll(_FOG, sh, axis=1)
    f = (f - f.min()) / (f.max() - f.min())
    return np.asarray(Image.fromarray((f * 255).astype(np.uint8)).resize((lw, lh), Image.BILINEAR), np.float32) / 255

def lights(t, c):
    """(wall light multiplier HxW, volumetric beam haze HxW, headlight glow HxW) — built at 1/4 res."""
    lw, lh = W // 4, H // 4
    yy = np.linspace(0, 1, lh)[:, None]
    amb = 0.07 if t < HIT0 else 0.30
    L = np.full((lh, lw), amb, np.float32) * (0.75 + 0.45 * (1 - yy))
    haze = np.zeros((lh, lw), np.float32); hl = np.zeros((lh, lw), np.float32)
    if t >= HIT0:
        tx = beam_target(t)
        src = c.P(tx - 700, -1300); a = c.P(tx - 150, 720); b = c.P(tx + 150, 720)
        far = 2.6
        poly = [(src[0] / 4, src[1] / 4), ((src[0] + (a[0] - src[0]) * far) / 4, (src[1] + (a[1] - src[1]) * far) / 4),
                ((src[0] + (b[0] - src[0]) * far) / 4, (src[1] + (b[1] - src[1]) * far) / 4)]
        im = Image.new("L", (lw, lh), 0); ImageDraw.Draw(im).polygon(poly, fill=255)
        cone = gaussian_filter(np.asarray(im, np.float32) / 255, 3)
        haze = cone * (0.35 + 0.65 * fog(t, lw, lh))
        e = c.P(tx, 720); rx, ry = 160 * c.z / 4, 230 * c.z / 4
        X, Y = np.meshgrid(np.arange(lw), np.arange(lh))
        spot = np.exp(-(((X - e[0] / 4) / rx) ** 2 + ((Y - e[1] / 4) / ry) ** 2) * 1.6)
        L += spot * 1.35 + cone * 0.25
    hx = headlights(t)
    if hx is not None:
        e = c.P(hx, 880)
        X, Y = np.meshgrid(np.arange(lw), np.arange(lh))
        hl = np.exp(-(((X - e[0] / 4) / (420 * c.z / 4)) ** 2 + ((Y - e[1] / 4) / (190 * c.z / 4)) ** 2))
        L += hl * 1.1
    L += flash(t) * 1.5
    up = lambda a: np.asarray(Image.fromarray(np.clip(a * 60, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 60
    return up(L), up(haze), up(hl)

# ------------------------------------------------------------- paint a stencil (current pose + ghosts) into the wall
def paint(img, emit, c, x, pose, h, ghosts_=(), glow_band=0.0, t=0.0):
    for gp, tl in ghosts_:
        st = stencil(gp, h)
        pl = place(st, c, x, GROUND, (W, H))
        if pl is None: continue
        w_, h_, src, dst = pl
        g = (0.30 * math.exp(-(t - tl) / 1.0) + 0.07)
        a = resized(st.base, w_, h_)[src][..., None] * g
        img[dst] = img[dst] * (1 - a) + 20 * a
    st = stencil(pose, h)
    pl = place(st, c, x, GROUND, (W, H))
    if pl is None: return
    w_, h_, src, dst = pl
    b = resized(st.base, w_, h_)[src][..., None]; m = resized(st.mid, w_, h_)[src][..., None]; l = resized(st.light, w_, h_)[src][..., None]
    img[dst] = img[dst] * (1 - b) + TONES[0] * b
    img[dst] = img[dst] * (1 - m) + TONES[1] * m
    img[dst] = img[dst] * (1 - l) + TONES[2] * l
    if glow_band > 0:
        bd = resized(st.band, w_, h_)[src][..., None]
        img[dst] = img[dst] * (1 - bd) + RED_PAINT * bd
        halo = gaussian_filter(bd[..., 0], max(2, 6 * c.z))[..., None]
        emit[dst] += bd * RED_GLOW * glow_band * 0.8 + halo * RED_GLOW * glow_band * 0.45
    if st.eyes is not None:
        ey = resized(np.clip(st.eyes, 0, 1), w_, h_)[src][..., None]
        emit[dst] += ey * np.array([235, 240, 255]) * 1.3

# ------------------------------------------------------------- foreground passers-by (out of focus, walking)
PASSERS = [(0.2, 2.5, -1, "coat"), (4.1, 6.1, 1, "umbrella"), (8.6, 10.6, -1, "hat")]
def passers(img, t):
    for t0, t1, d, kind in PASSERS:
        if not (t0 <= t < t1): continue
        u = (t - t0) / (t1 - t0)
        sx = lerp(-700, W + 700, u) if d < 0 else lerp(W + 700, -700, u)
        step = int(t * 8) % 4
        p = Pose(kind, "side", 1 if d < 0 else -1, (-14 + step * 9, -8), (10 - step * 7, -6), stance=[0.02, 0.09, 0.02, 0.09][step],
                 rhand="open" if kind != "umbrella" else "open")
        st = stencil(p, 1000, 0.45)
        bx0, by0, bx1, by1 = st.box
        wpx, hpx = int((bx1 - bx0) * 1.55), int((by1 - by0) * 1.55)
        a = resized(st.base, wpx // 3, hpx // 3)
        a = gaussian_filter(a, 6)
        a = resized(a, wpx, hpx)
        x0 = int(sx - wpx / 2); y0 = int(H * 1.18 - hpx)
        cx0, cy0, cx1, cy1 = max(0, -x0), max(0, -y0), min(wpx, W - x0), min(hpx, H - y0)
        if cx1 <= cx0 or cy1 <= cy0: continue
        aa = a[cy0:cy1, cx0:cx1][..., None] * 0.94
        img[y0 + cy0:y0 + cy1, x0 + cx0:x0 + cx1] = img[y0 + cy0:y0 + cy1, x0 + cx0:x0 + cx1] * (1 - aa) + 3 * aa

# ------------------------------------------------------------- rain (brighter inside the beam)
_R = np.random.default_rng(3)
RN = 520
RX, RY, RS, RL = _R.random(RN) * (W + 300) - 150, _R.random(RN) * H, _R.uniform(1500, 2300, RN), _R.uniform(16, 44, RN)
def rain_layer(t):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for i in range(RN):
        y = (RY[i] + t * RS[i]) % (H + 60) - 30; x = RX[i] - y * 0.12
        d.line([(x, y), (x - RL[i] * 0.12, y + RL[i])], fill=255, width=2 if i % 6 == 0 else 1)
    return np.asarray(im, np.float32) / 255

DUST = np.random.default_rng(8).random((260, 3))
def dust(t, haze):
    a = np.zeros((H, W), np.float32)
    for k in range(len(DUST)):
        x = int((DUST[k, 0] * W + t * 25 * (DUST[k, 2] - 0.5)) % W); y = int((DUST[k, 1] * H + t * 12) % H)
        if haze[y, x] > 0.08: a[y:y + 2, x:x + 2] = haze[y, x]
    return a

def flare(img, t, c):
    hx = headlights(t)
    if hx is None: return img
    x, y = c.P(hx, 880)[0], H * 0.96
    k = math.sin(math.pi * cl((t - 7.4) / 2.5))
    st = np.zeros((H, W), np.float32)
    yi = int(np.clip(y, 0, H - 1))
    st[max(0, yi - 2):yi + 2, :] = 1.0
    st = gaussian_filter(st, (3, 0)) * np.exp(-((np.arange(W)[None, :] - x) / 700) ** 2)
    core = np.zeros((H, W), np.float32)
    X, Y = np.meshgrid(np.arange(0, W, 4), np.arange(0, H, 4))
    small = np.exp(-(((X - x) / 90) ** 2 + ((Y - y) / 60) ** 2))
    core = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    gx, gy = W - x, H - y                                                       # ghost on the opposite side
    gh = np.exp(-(((X - gx) / 40) ** 2 + ((Y - gy) / 40) ** 2)) * 0.35
    gh = np.asarray(Image.fromarray((gh * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    return img + (st * 0.7 + core * 0.9 + gh)[..., None] * np.array([220, 228, 255]) * k

# ------------------------------------------------------------- frame
def frame(t):
    z, cx, cy = camera(t)
    c = Cam(z, cx, cy, W, H)
    img = ST.wall_crop(c)
    emit = np.zeros_like(img)
    for i, (x, kw, h) in enumerate(OTHERS):
        paint(img, emit, c, x, other_pose(i, t), h, ghosts("o%d" % i, t, lambda tt, i=i: other_pose(i, tt)), 0.0, t)
    band = 0.85 if t < HIT0 else 0.35
    paint(img, emit, c, MAN_X, man_pose(t), 440, ghosts("man", t, man_pose), band, t)
    L, haze, hl = lights(t, c)
    img = img * L[..., None]
    gy = int(round(c.P(0, ST.WALL_END)[1]))                                     # wet sidewalk reflection
    if 0 < gy < H:
        n = min(gy, H - gy); emit[gy:gy + n] += gaussian_filter(emit[gy - n:gy][::-1], (5, 5, 0)) * 0.35
    img += emit
    rl = rain_layer(t)
    img += (rl * (28 + 230 * haze + 120 * hl))[..., None] * np.array([0.92, 0.95, 1.0])
    img += (haze * 70)[..., None] * np.array([0.9, 0.94, 1.0])
    img += (dust(t, haze) * 200)[..., None]
    passers(img, t)
    img = flare(img, t, c)
    br = np.clip(img.mean(-1) - 150, 0, None)                                   # bloom
    bl = np.asarray(Image.fromarray(np.clip(br, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), np.float32)
    img += bl[..., None] * 0.8
    img[..., 0] = np.roll(img[..., 0], 2, axis=1); img[..., 2] = np.roll(img[..., 2], -2, axis=1)   # lens fringing
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return Post.apply(out, t + 8.0, min(1.0, t / 0.4) * min(1.0, (DUR - t) / 0.6))


if __name__ == "__main__":
    only = [float(a) for a in sys.argv[1:]]
    if only:
        for t in only: Image.fromarray(np.asarray(frame(t))).save(f"/tmp/v2_{t:.2f}.png"); print("still", t)
        sys.exit()
    out = os.path.join(dist_dir(EP), "test_v2.mp4")
    song = os.path.join(work_dir(EP), "song.mp3")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-ss", str(S0), "-t", str(DUR), "-i", song, "-map", "0:v", "-map", "1:a",
                            "-af", f"afade=t=in:d=0.4,afade=t=out:st={DUR - 0.6}:d=0.6", "-c:a", "aac", "-b:a", "192k",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", out],
                           stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        enc.stdin.write(np.asarray(frame(i / FPS), np.uint8).tobytes())
        if i % 30 == 0: print(f"{i / FPS:.1f}s", flush=True)
    enc.stdin.close(); enc.wait(); print("saved", out)
