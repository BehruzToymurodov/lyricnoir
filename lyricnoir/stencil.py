"""Street-stencil people for Lyric Noir (Film 02 onward).

A person is a small body rig: each body part (legs, torso/clothes, arms, head/hood/hat) is drawn into its own
layer, given a rounded "height" from its distance field, and the parts are stacked so arms sit in front of the
torso. Lighting that height map from the upper left and cutting it into three levels gives the look of a real
three-layer spray stencil (dark base, mid tone, highlight), plus hand-placed face details.

    p = Pose(kind="hoodie", head="side", face=-1)
    st = stencil(p, h=440, ws=2.5)   # .base .mid .light (alpha arrays), .edge, .eyes, .box (world box, feet at 0,0)
"""
import math
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter


@dataclass(frozen=True)
class Pose:
    kind: str = "hoodie"          # hoodie | coat | hat | child | umbrella
    head: str = "side"            # side | q (three-quarter) | front
    face: int = -1                # -1 looks left, +1 looks right
    larm: tuple = (-8, -6)        # (upper, fore) degrees from straight down; + swings toward +x
    rarm: tuple = (8, 6)
    lhand: str = "open"           # open | fist | pocket | chest
    rhand: str = "open"
    stance: float = 0.055         # half distance between feet
    weight: float = 0.0           # -1..1 hip shift onto one leg
    lean: float = 0.0
    tilt: float = 0.0             # head tilt (head-height units)
    eyes: float = 0.0             # 0..1 eye glint (front head only)
    seed: int = 0


def _cap(d, p, q, r1, r2, fill=255):
    dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L, dx / L
    d.polygon([(p[0] + nx * r1, p[1] + ny * r1), (q[0] + nx * r2, q[1] + ny * r2),
               (q[0] - nx * r2, q[1] - ny * r2), (p[0] - nx * r1, p[1] - ny * r1)], fill=fill)
    d.ellipse([p[0] - r1, p[1] - r1, p[0] + r1, p[1] + r1], fill=fill)
    d.ellipse([q[0] - r2, q[1] - r2, q[0] + r2, q[1] + r2], fill=fill)


def _limb(s, a_up, a_fore, l1, l2):
    a1, a2 = math.radians(a_up), math.radians(a_up + a_fore)
    e = (s[0] + math.sin(a1) * l1, s[1] + math.cos(a1) * l1)
    return e, (e[0] + math.sin(a2) * l2, e[1] + math.cos(a2) * l2)


HEAD_SIDE = [(-0.50, -0.05), (-0.46, -0.40), (-0.22, -0.62), (0.12, -0.66), (0.40, -0.50), (0.50, -0.25),
             (0.53, -0.06), (0.66, 0.12), (0.57, 0.18), (0.59, 0.29), (0.54, 0.37), (0.56, 0.47), (0.44, 0.60),
             (0.20, 0.68), (0.06, 0.66), (-0.04, 0.80), (-0.30, 0.78), (-0.44, 0.40)]   # faces +x, unit = head radius
TORSO = [(0.035, -0.84), (0.075, -0.826), (0.112, -0.80), (0.122, -0.765), (0.114, -0.70), (0.106, -0.65),
         (0.092, -0.585), (0.090, -0.545), (0.104, -0.49), (0.100, -0.455), (0.0, -0.44)]


class Parts:
    """One drawing layer per body part, each with a stacking depth."""
    def __init__(s, W, H): s.W, s.H, s.layers = W, H, {}
    def d(s, name, z):
        if name not in s.layers: s.layers[name] = [Image.new("L", (s.W, s.H), 0), z]
        return ImageDraw.Draw(s.layers[name][0])


def _build(P, p, T, R):
    k = p.kind; sc = 0.64 if k == "child" else 1.0; f = p.face
    bw = {"side": 0.6, "q": 0.82, "front": 1.0}[p.head]
    def J(x, y):
        y *= sc; x *= sc
        up = max(0.0, -y - 0.45 * sc)
        return T((x + p.lean * up + p.weight * 0.025 * (1 if -y < 0.5 * sc else 0.6), y))
    Rs = lambda v: R(v * sc)
    # legs (behind)
    for side in (-1, 1):
        d = P.d("leg%d" % side, -2 if side == -f else -1)
        if p.head == "side":
            fx = side * f; st_ = p.stance * (1.1 if fx > 0 else 0.7)
            hip = J(side * 0.02, -0.49); ank = J(side * st_ - p.weight * 0.02, -0.035)
            kn = J(side * st_ * 0.6 + f * 0.012, -0.27)
        else:
            hip = J(side * 0.058 * bw, -0.49); ank = J(side * p.stance - p.weight * 0.02, -0.035)
            kn = J(side * (p.stance * 0.55 + 0.03 * bw) - p.weight * 0.012, -0.27)
        _cap(d, hip, kn, Rs(0.056), Rs(0.04)); _cap(d, kn, ank, Rs(0.04), Rs(0.029))
        toe = (ank[0] + (f if True else side) * Rs(0.07), ank[1] + Rs(0.012))
        d.polygon([(ank[0] - f * Rs(0.035), ank[1] - Rs(0.03)), (ank[0] + f * Rs(0.02), ank[1] - Rs(0.035)),
                   (toe[0], toe[1] - Rs(0.006)), (toe[0], ank[1] + Rs(0.035)), (ank[0] - f * Rs(0.04), ank[1] + Rs(0.035))], fill=255)
    # torso + clothes
    d = P.d("torso", 0)
    wide = 1.12 if k == "hoodie" else 1.0
    pts = [(x * wide * bw, y) for x, y in TORSO]
    chest = lambda x, y: x + (f * 0.016 if (p.head == "side" and -0.8 < y < -0.6) else 0.0)
    d.polygon([J(chest(x, y), y) for x, y in pts] + [J(-x, y) for x, y in reversed(pts)], fill=255)
    _cap(d, J(0, -0.86), J(0, -0.80), Rs(0.034), Rs(0.045))
    if k == "hoodie":
        d.polygon([J(-0.12 * bw, -0.79), J(0.12 * bw, -0.79), J(0.128 * bw, -0.47), J(0.115 * bw, -0.43), J(-0.115 * bw, -0.43), J(-0.128 * bw, -0.47)], fill=255)
    if k in ("coat", "hat"):
        d.polygon([J(-0.118 * bw, -0.79), J(0.118 * bw, -0.79), J(0.13 * bw, -0.55), J(0.175 * bw, -0.22), J(0.0, -0.205), J(-0.175 * bw, -0.22), J(-0.13 * bw, -0.55)], fill=255)
    # head (+ hood / hair / hat)
    hc = J(0.0 + p.tilt * 0.3, -0.918); hr = Rs(0.071 if k != "child" else 0.092)
    dh = P.d("head", 2)
    if k == "hoodie":
        off = -f * hr * (0.30 if p.head == "side" else (0.14 if p.head == "q" else 0.0))
        dh.ellipse([hc[0] + off - hr * 1.18, hc[1] - hr * 1.32, hc[0] + off + hr * 1.18, hc[1] + hr * 1.05], fill=255)
        dh.polygon([(hc[0] + off - hr * 1.0, hc[1] + hr * 0.6), (hc[0] + off + hr * 1.0, hc[1] + hr * 0.6),
                    (hc[0] + hr * 1.3, hc[1] + hr * 1.6), (hc[0] - hr * 1.3, hc[1] + hr * 1.6)], fill=255)
    if k == "coat":
        dh.ellipse([hc[0] - hr * 1.12 - f * hr * 0.15, hc[1] - hr * 1.2, hc[0] + hr * 1.12 - f * hr * 0.15, hc[1] + hr * 1.5], fill=255)
    if p.head == "side":
        dh.polygon([(hc[0] + x * hr * f, hc[1] + y * hr * 1.05) for x, y in HEAD_SIDE], fill=255)
    else:
        dh.ellipse([hc[0] - hr * 0.84, hc[1] - hr * 1.1, hc[0] + hr * 0.84, hc[1] + hr * 1.02], fill=255)
        dh.polygon([(hc[0] - hr * 0.7, hc[1] + hr * 0.4), (hc[0] + hr * 0.7, hc[1] + hr * 0.4), (hc[0] + hr * 0.25, hc[1] + hr * 1.12),
                    (hc[0] - hr * 0.25, hc[1] + hr * 1.12)], fill=255)                              # jaw
        if p.head == "q":
            nz = (hc[0] + f * hr * 0.78, hc[1] + hr * 0.1)
            dh.polygon([(nz[0] - f * hr * 0.25, nz[1] - hr * 0.4), (nz[0] + f * hr * 0.14, nz[1] + hr * 0.12), (nz[0] - f * hr * 0.2, nz[1] + hr * 0.24)], fill=255)
    if k == "hat":
        top = hc[1] - hr * (0.66 if p.head == "side" else 1.08) * 1.05
        dh.ellipse([hc[0] - hr * 1.55, top - hr * 0.08, hc[0] + hr * 1.55, top + hr * 0.2], fill=255)
        dh.polygon([(hc[0] - hr * 0.92, top + hr * 0.05), (hc[0] + hr * 0.92, top + hr * 0.05), (hc[0] + hr * 0.82, top - hr * 0.62),
                    (hc[0] - hr * 0.82, top - hr * 0.62)], fill=255)
    # arms (in front)
    shL, shR = J(-0.104 * bw, -0.785), J(0.104 * bw, -0.785)
    if p.head == "side": shL, shR = J(-0.01, -0.785), J(0.01, -0.785)
    ends = {}
    for side, (au, af), hand, sh in ((-1, p.larm, p.lhand, shL), (1, p.rarm, p.rhand, shR)):
        d = P.d("arm%d" % side, 3 if side == f else 1)
        if hand == "pocket": au, af = side * 9, -side * 28
        if hand == "chest": au, af = side * 6, -side * 140
        e, h = _limb(sh, au, af, Rs(0.165), Rs(0.155))
        _cap(d, sh, e, Rs(0.04 if k in ("hoodie", "coat", "hat") else 0.035), Rs(0.032))
        _cap(d, e, h, Rs(0.032), Rs(0.026))
        ends[side] = (sh, e, h)
        if hand == "pocket": continue
        a = math.atan2(h[1] - e[1], h[0] - e[0])
        if hand == "fist":
            d.ellipse([h[0] - Rs(0.037), h[1] - Rs(0.037), h[0] + Rs(0.037), h[1] + Rs(0.037)], fill=255)
        else:
            pc = (h[0] + math.cos(a) * Rs(0.024), h[1] + math.sin(a) * Rs(0.024))
            d.ellipse([pc[0] - Rs(0.027), pc[1] - Rs(0.031), pc[0] + Rs(0.027), pc[1] + Rs(0.031)], fill=255)
            for j in range(4):
                b = a + math.radians(-22 + j * 15)
                _cap(d, (pc[0] + math.cos(b) * Rs(0.018), pc[1] + math.sin(b) * Rs(0.018)),
                     (pc[0] + math.cos(b) * Rs(0.055), pc[1] + math.sin(b) * Rs(0.055)), Rs(0.0078), Rs(0.0062))
            tb = a - math.radians(55) * side
            _cap(d, pc, (pc[0] + math.cos(tb) * Rs(0.042), pc[1] + math.sin(tb) * Rs(0.042)), Rs(0.0095), Rs(0.007))
        if k == "umbrella" and side == 1:
            top = (h[0] + Rs(0.02), J(0, -1.12)[1])
            _cap(d, h, top, Rs(0.006), Rs(0.006))
            w = Rs(0.30); du = P.d("umb", 4)
            du.pieslice([top[0] - w, top[1] - w * 0.5, top[0] + w, top[1] + w * 0.5], 180, 360, fill=255)
            for j in range(5): du.pieslice([top[0] - w + j * w * 0.4, top[1] - w * 0.08, top[0] - w + j * w * 0.4 + w * 0.4, top[1] + w * 0.1], 0, 180, fill=0)
        if k == "hat" and side == -1:
            _cap(d, h, J(-0.17 + p.lean * 0.3, 0.0), Rs(0.011), Rs(0.011))
    return dict(hc=hc, hr=hr, ends=ends, chest=J(0, -0.70), pelvis=J(0, -0.5))


def _details(dl, dd, p, G):
    """Hand-placed highlight (dl) and dark (dd) marks: face, hood opening, seams."""
    hc, hr, f = G["hc"], G["hr"], p.face
    w = lambda v: max(1, int(hr * v))
    if p.head == "front":
        if p.kind == "hoodie":
            dd.ellipse([hc[0] - hr * 0.95, hc[1] - hr * 1.12, hc[0] + hr * 0.95, hc[1] + hr * 1.12], outline=255, width=w(0.16))
        dl.chord([hc[0] - hr * 0.78, hc[1] - hr * 0.9, hc[0] + hr * 0.78, hc[1] + hr * 0.98], 92, 268, fill=255)
        dl.polygon([(hc[0] - hr * 0.02, hc[1] - hr * 0.28), (hc[0] + hr * 0.14, hc[1] + hr * 0.3), (hc[0] - hr * 0.02, hc[1] + hr * 0.32)], fill=255)
        dl.ellipse([hc[0] + hr * 0.12, hc[1] + hr * 0.62, hc[0] + hr * 0.42, hc[1] + hr * 0.78], fill=255)
        for ex in (-0.34, 0.32):
            dd.ellipse([hc[0] + ex * hr - hr * 0.18, hc[1] - hr * 0.24, hc[0] + ex * hr + hr * 0.18, hc[1] - hr * 0.04], fill=255)
        dd.line([(hc[0] - hr * 0.26, hc[1] + hr * 0.55), (hc[0] + hr * 0.24, hc[1] + hr * 0.52)], fill=255, width=w(0.08))
    elif p.head == "q":
        dl.polygon([(hc[0] + f * hr * 0.05, hc[1] - hr * 0.75), (hc[0] + f * hr * 0.9, hc[1] - hr * 0.3), (hc[0] + f * hr * 0.92, hc[1] + hr * 0.35),
                    (hc[0] + f * hr * 0.4, hc[1] + hr * 0.95), (hc[0] - f * hr * 0.05, hc[1] + hr * 0.45)], fill=255)
        ex = hc[0] + f * hr * 0.45
        dd.ellipse([ex - hr * 0.16, hc[1] - hr * 0.24, ex + hr * 0.16, hc[1] - hr * 0.06], fill=255)
        dd.line([(hc[0] + f * hr * 0.2, hc[1] + hr * 0.55), (hc[0] + f * hr * 0.6, hc[1] + hr * 0.52)], fill=255, width=w(0.07))
    else:
        dl.polygon([(hc[0] + f * hr * 0.1, hc[1] - hr * 0.6), (hc[0] + f * hr * 0.5, hc[1] - hr * 0.3), (hc[0] + f * hr * 0.6, hc[1] + hr * 0.1),
                    (hc[0] + f * hr * 0.5, hc[1] + hr * 0.62), (hc[0] + f * hr * 0.08, hc[1] + hr * 0.55)], fill=255)
        ex = hc[0] + f * hr * 0.3
        dd.ellipse([ex - hr * 0.12, hc[1] - hr * 0.22, ex + hr * 0.12, hc[1] - hr * 0.08], fill=255)
        ea = (hc[0] - f * hr * 0.05, hc[1] + hr * 0.05)
        dd.arc([ea[0] - hr * 0.16, ea[1] - hr * 0.22, ea[0] + hr * 0.16, ea[1] + hr * 0.22], 0, 360, fill=255, width=w(0.06))
    c, pv = G["chest"], G["pelvis"]
    if p.kind == "hoodie":
        dd.line([(pv[0] - hr * 0.75, pv[1] - hr * 0.95), (pv[0] + hr * 0.75, pv[1] - hr * 0.95)], fill=255, width=w(0.07))
        for i in (-1, 1):
            dd.line([(c[0] + i * hr * 0.28, c[1] - hr * 1.3), (c[0] + i * hr * 0.34, c[1] - hr * 0.3)], fill=255, width=w(0.05))
        dd.line([(pv[0] - hr * 1.5, pv[1] + hr * 0.7), (pv[0] + hr * 1.5, pv[1] + hr * 0.7)], fill=255, width=w(0.06))   # hem
    if p.kind in ("coat", "hat"):
        dd.line([(c[0] + f * hr * 0.1, c[1] - hr * 1.0), (pv[0] + f * hr * 0.2, pv[1] + hr * 3.8)], fill=255, width=w(0.06))
        dd.line([(c[0] - hr * 0.9, c[1] - hr * 1.2), (c[0], c[1] - hr * 0.2), (c[0] + hr * 0.9, c[1] - hr * 1.2)], fill=255, width=w(0.06))   # lapels
    for side, (_s, e, h) in G["ends"].items():                                     # sleeve cuff
        a = math.atan2(h[1] - e[1], h[0] - e[0]); q = (e[0] + (h[0] - e[0]) * 0.82, e[1] + (h[1] - e[1]) * 0.82)
        nx, ny = -math.sin(a) * hr * 0.42, math.cos(a) * hr * 0.42
        dd.line([(q[0] - nx, q[1] - ny), (q[0] + nx, q[1] + ny)], fill=255, width=w(0.06))


LIGHT = np.array([-0.52, -0.58, 0.63]); LIGHT = LIGHT / np.linalg.norm(LIGHT)


def render_stencil(p: Pose, h=440, ws=2.5):
    m = 0.6
    bx0, by0, bx1, by1 = -m * h, -1.32 * h, m * h, 0.1 * h
    W, H = int((bx1 - bx0) * ws), int((by1 - by0) * ws)
    T = lambda q: ((q[0] * h - bx0) * ws, (q[1] * h - by0) * ws)
    R = lambda v: v * h * ws
    P = Parts(W, H)
    G = _build(P, p, T, R)
    # stacked rounded heights (each part a soft dome; parts in front sit above the torso)
    Hm = np.zeros((H, W), np.float32); mask = np.zeros((H, W), np.float32)
    for name, (img, z) in sorted(P.layers.items(), key=lambda kv: kv[1][1]):
        a = np.asarray(img, np.float32) / 255
        if a.max() == 0: continue
        dome = gaussian_filter(a, 9 * ws) * 34
        inside = gaussian_filter(a, 0.8 * ws) > 0.5
        Hm = np.where(inside, np.maximum(Hm, dome + max(z, 0) * 6.0) if z > 0 else np.maximum(Hm, dome), Hm)
        mask = np.maximum(mask, gaussian_filter(a, 0.8 * ws))
    mask = np.clip((mask - 0.35) / 0.3, 0, 1)
    Hb = gaussian_filter(Hm * (mask > 0), 1.4 * ws)
    gy, gx = np.gradient(Hb)
    s = 1.0 / ws
    nx, ny, nz = -gx / s * 0.12, -gy / s * 0.12, np.ones_like(gx)
    nl = np.sqrt(nx * nx + ny * ny + nz * nz)
    lam = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / nl
    dl_img, dd_img = Image.new("L", (W, H), 0), Image.new("L", (W, H), 0)
    _details(ImageDraw.Draw(dl_img), ImageDraw.Draw(dd_img), p, G)
    dl = np.asarray(dl_img, np.float32) / 255; dd = np.asarray(dd_img, np.float32) / 255
    mid = (lam > 0.685).astype(np.float32); light = (lam > 0.75).astype(np.float32)
    light = np.maximum(light, dl); mid = np.maximum(mid, dl)
    light *= (1 - dd); mid *= (1 - dd)
    sm = lambda a, r: np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r * ws)), np.float32) / 255
    mid = np.clip((sm(mid, 0.9) - 0.45) * 4, 0, 1) * mask
    light = np.clip((sm(light, 0.9) - 0.45) * 4, 0, 1) * mask
    rng = np.random.default_rng(p.seed + 7)
    over, far = sm(mask, 3), sm(mask, 11)
    base = np.clip(mask * 0.97 + over * 0.2 + (rng.random(mask.shape) < 0.045) * far * 0.5, 0, 1)
    dr = Image.new("L", (W, H), 0); ddr = ImageDraw.Draw(dr)
    ys, xs = np.nonzero(mask > 0.5)
    for _ in range(8):
        if not len(xs): break
        k = rng.integers(len(xs)); x = int(xs[k]); col = np.nonzero(mask[:, x] > 0.5)[0]
        y = int(col.max()); L = rng.uniform(10, 55) * ws; w = rng.uniform(1.5, 2.6) * ws
        ddr.line([(x, y), (x, y + L)], fill=210, width=int(w)); ddr.ellipse([x - w, y + L - w, x + w, y + L + w], fill=210)
    base = np.clip(base + np.asarray(dr, np.float32) / 255 * 0.85, 0, 1) * (0.86 + 0.14 * rng.random(mask.shape))
    paint_jit = 0.85 + 0.15 * rng.random(mask.shape)
    mi = Image.fromarray((mask * 255).astype(np.uint8))
    edge = (np.asarray(mi.filter(ImageFilter.MaxFilter(5)), np.float32) - np.asarray(mi.filter(ImageFilter.MinFilter(5)), np.float32)) / 255
    eyes = None
    if p.head == "front" and p.eyes > 0:
        hc, hr = G["hc"], G["hr"]
        e = Image.new("L", (W, H), 0); ed = ImageDraw.Draw(e)
        for ex in (-0.34, 0.32):
            cx, cy = hc[0] + ex * hr, hc[1] - hr * 0.14
            ed.ellipse([cx - hr * 0.055, cy - hr * 0.055, cx + hr * 0.055, cy + hr * 0.055], fill=255)
        eyes = sm(np.asarray(e, np.float32) / 255, 0.01) + sm(np.asarray(e, np.float32) / 255, hr / ws * 0.2) * 2.0
        eyes = np.clip(eyes, 0, 1.6) * p.eyes
    # armband on the upper arm that faces us
    bm = Image.new("L", (W, H), 0)
    sh_, e_, _h = G["ends"][p.face]
    a0 = (sh_[0] + (e_[0] - sh_[0]) * 0.30, sh_[1] + (e_[1] - sh_[1]) * 0.30)
    a1 = (sh_[0] + (e_[0] - sh_[0]) * 0.58, sh_[1] + (e_[1] - sh_[1]) * 0.58)
    _cap(ImageDraw.Draw(bm), a0, a1, R(0.043), R(0.04))
    band = sm(np.asarray(bm, np.float32) / 255, 0.5) * mask
    st = type("StencilImg", (), {})()
    st.band = band
    st.base, st.mid, st.light = base, mid * paint_jit, light * paint_jit
    st.edge, st.eyes, st.box, st.ws, st.h, st.G = edge, eyes, (bx0, by0, bx1, by1), ws, h, G
    st.glow = np.clip(edge * 1.1 + gaussian_filter(edge, 8 * ws) * 3.2, 0, 1.5) / 1.5
    return st


from collections import OrderedDict
_CACHE = OrderedDict()
CACHE_MAX = 40
def _u8(a): return None if a is None else (np.clip(a, 0, 1) * 255).astype(np.uint8)

def stencil(p: Pose, h=440, ws=2.5):
    """Cached stencil; masks kept as uint8 and the cache is LRU-capped (poses add up fast in stop-motion)."""
    k = (p, h, ws)
    if k in _CACHE:
        _CACHE.move_to_end(k); return _CACHE[k]
    st = render_stencil(p, h, ws)
    for n in ("base", "mid", "light", "band", "glow", "eyes", "edge"):
        setattr(st, n, _u8(getattr(st, n, None)))
    _CACHE[k] = st
    while len(_CACHE) > CACHE_MAX: _CACHE.popitem(last=False)
    return st


def place(st, c, x, ground, size):
    """Screen placement: (w, h, src slices, dst slices) or None when off screen."""
    bx0, by0, bx1, by1 = st.box
    a = c.P(x + bx0, ground + by0); b = c.P(x + bx1, ground + by1)
    w, h = max(2, int(round(b[0] - a[0]))), max(2, int(round(b[1] - a[1])))
    ix, iy = int(round(a[0])), int(round(a[1])); W, H = size
    cx0, cy0, cx1, cy1 = max(0, -ix), max(0, -iy), min(w, W - ix), min(h, H - iy)
    if cx1 <= cx0 or cy1 <= cy0: return None
    return w, h, (slice(cy0, cy1), slice(cx0, cx1)), (slice(iy + cy0, iy + cy1), slice(ix + cx0, ix + cx1))


def resized(a, w, h):
    if a.dtype != np.uint8: a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(a).resize((w, h), Image.BILINEAR), np.float32) / 255
