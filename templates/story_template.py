"""Lyric Noir — Film No. NN — ARTIST, "TITLE".
One-line story: ...
Song section used: m:ss -> m:ss (timings in timing.json; never store lyrics here).

HOW TO BUILD AN EPISODE (keep it this order):
 1. META: audio_start = song second where the video starts (a few seconds before line 1), duration.
 2. CAM: one shot per group of lyric lines; cut on line starts from timing.json (video t = song t - audio_start).
 3. Timeline functions: small pure functions of t (0..1 values via ss()). Name them after what they mean.
 4. frame(): background -> light pools -> window/subject -> shadows -> people -> cars -> lamp -> rain -> flashes.
 5. anchor(t): world rect the lyrics sit beside (usually the subject). Must exist for every t.
 6. `python -m lyricnoir stills NN-slug ...` at the busiest moments, look, fix, THEN render.
Style rules: STYLE.md (black/white + ONE accent color reserved for the emotional subject).
"""
import math
from PIL import Image, ImageDraw
from lyricnoir.core import Cam, keyframe_camera, Post, lerp, cl, ss, lc, flicker, fade_in_out
from lyricnoir import scene as S, figures as F, props as P

META = dict(
    title="Song Title", artist="Artist", number=2,
    audio_start=0.0, duration=30.0,
    hook=["First hook line.", "Second hook line."],       # original words, NOT lyrics
    cover=dict(t=10.0, z=0.95, cx=905, cy=470),
)

CAM = [
    (0, 10, 1.0, 1.05, 960, 960, 540, 540),
    (10, 20, 1.4, 1.5, 700, 720, 520, 520),
    (20, 30, 1.05, 1.0, 960, 960, 540, 540),
]
camera = keyframe_camera(CAM)
SCENES = [(a[0], a[1]) for a in CAM]

WIN = (1000, 180, 1500, 680)          # the shop window; put the subject inside it
SUBJECT = (1110, 210, 1390, 580)

def light_on(t):
    f = flicker(t, 1.0, 1.1, (1, 3, 4, 7, 9, 10, 11, 13, 14, 15), rate=14, off=0.15)
    return (0.0 if t < 1.0 else 1.0) if f is None else f

def man_x(t): return lerp(-150, 430, 1 - (1 - cl((t - 3) / 5)) ** 2)
def man_walk(t): return (t * 7.0, (1 - cl((t - 3) / 5)) ** 0.5) if 3 <= t <= 8 else (0.0, 0.0)

def anchor(t): return SUBJECT

def frame(t, size=(1920, 1080), cam=None):
    W, H = size
    z, cx, cy = cam or camera(t)
    c = Cam(z, cx, cy, W, H)
    img = Image.new("RGB", (W, H), S.WALL)
    d = ImageDraw.Draw(img, "RGBA")
    L = light_on(t)
    S.background(d, c)
    S.streetlight_pool(d, c, L)
    S.window_interior(d, c, WIN, 1.0)
    d.rectangle(c.box(*SUBJECT), fill=(14, 14, 14), outline=(70, 70, 70), width=c.lw(8))
    # TODO: draw the episode's subject in the accent color inside SUBJECT
    S.window_frame(d, c, WIN)
    mx = man_x(t)
    if L > 0.5 and t > 8:          # shadow only once he stands under the lamp
        d = F.shadow_layer(img, c, lambda ds: F.sil_man(ds, c, mx + 180, 832, 1.15, (0, 0, 0, int(200 * L)), 55, (14, -150)))
    ph, amp = man_walk(t)
    F.draw_man(d, c, mx, t, 1.0, 0, ph, amp)
    S.streetlight_pole(d, c, L)
    S.rain(d, c, t, dry=[WIN])
    return Post.apply(img, t, fade_in_out(t, META["duration"], 1.5, 3.2))
