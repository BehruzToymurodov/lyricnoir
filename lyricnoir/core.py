"""Math helpers, camera, and film post-processing shared by every episode."""
import math
import numpy as np

FPS = 30
SIZE = (1920, 1080)          # default output size (16:9). Covers render at (1080, 1920).


def lerp(a, b, u): return a + (b - a) * u
def cl(u): return max(0.0, min(1.0, u))
def ss(u):
    """Smoothstep 0..1 (ease in-out). Use for every timed transition."""
    u = cl(u); return u * u * (3 - 2 * u)
def lc(c1, c2, u): return tuple(int(lerp(a, b, u)) for a, b in zip(c1, c2))
def flicker(t, t0, dur, on_steps, rate=12, off=0.1):
    """Neon/lamp style flicker between t0 and t0+dur; returns None outside the window."""
    if t < t0 or t >= t0 + dur: return None
    return 1.0 if int((t - t0) * rate) in on_steps else off


class Cam:
    """World -> screen transform. World units ~ pixels at zoom 1 on a 1920x1080 frame."""
    def __init__(s, z, cx, cy, W=1920, H=1080):
        s.z, s.cx, s.cy, s.W, s.H = z, cx, cy, W, H
    def P(s, x, y): return ((x - s.cx) * s.z + s.W / 2, (y - s.cy) * s.z + s.H / 2)
    def S(s, v): return v * s.z
    def pts(s, lst): return [s.P(x, y) for x, y in lst]
    def box(s, x0, y0, x1, y1):
        a, b = s.P(x0, y0), s.P(x1, y1); return [a[0], a[1], b[0], b[1]]
    def lw(s, w): return max(1, int(round(w * s.z)))


def keyframe_camera(CAM):
    """CAM = [(t0, t1, z0, z1, cx0, cx1, cy0, cy1), ...]; smooth move inside each shot, hard cut between."""
    def camera(t):
        for t0, t1, z0, z1, x0, x1, y0, y1 in CAM:
            if t < t1 or t1 == CAM[-1][1]:
                u = ss((t - t0) / (t1 - t0))
                return lerp(z0, z1, u), lerp(x0, x1, u), lerp(y0, y1, u)
    return camera


class Post:
    """Film grain + vignette + fade, cached per output size."""
    _cache = {}

    @classmethod
    def _get(cls, W, H):
        if (W, H) not in cls._cache:
            rng = np.random.default_rng(7)
            grain = [rng.normal(0, 9, (H, W, 1)).astype(np.float32) for _ in range(6)]
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
            vign = np.clip(1.15 - 0.55 * r ** 1.6, 0.25, 1.0)[..., None].astype(np.float32)
            cls._cache[(W, H)] = (grain, vign)
        return cls._cache[(W, H)]

    @classmethod
    def apply(cls, img, t, fade=1.0, fps=FPS):
        W, H = img.size
        grain, vign = cls._get(W, H)
        arr = np.asarray(img).astype(np.float32) * vign + grain[int(t * fps) % 6]
        arr *= fade
        return np.clip(arr, 0, 255).astype(np.uint8)


def fade_in_out(t, duration, fade_in=1.5, fade_out=3.2):
    return ss(t / fade_in) * (1 - ss((t - (duration - fade_out)) / fade_out))
