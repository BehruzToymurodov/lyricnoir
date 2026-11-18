"""Lyric Noir — Film No. 01 — Citizen Cope, "Pablo Picasso".
A man loves a woman in a gallery window; everyone else sees a painting. Police take her; he ends up in the papers.
Song section used: 0:08 -> 1:52 of the track (30 lyric lines; timings in timing.json, no lyrics stored here)."""
import math
from PIL import Image, ImageDraw
from lyricnoir.core import Cam, keyframe_camera, Post, lerp, cl, ss, lc, flicker, fade_in_out
from lyricnoir import scene as S, figures as F, props as P

META = dict(
    title="Pablo Picasso", artist="Citizen Cope", number=1,
    audio_start=8.0,            # second of the song where the video starts
    duration=104.0,
    hook=["He loves her.", "Everyone else sees a painting."],
    cover=dict(t=18.6, z=0.95, cx=905, cy=470),     # vertical cover background shot
)

CAM = [
    (0, 6, 1.0, 1.05, 960, 960, 540, 540),          # intro: rain, lamp flickers on
    (6, 14.5, 1.05, 1.0, 960, 960, 540, 540),       # he walks in, window lights, she wakes (line 1)
    (14.5, 20.5, 1.45, 1.55, 700, 730, 520, 520),   # shadows dance (lines 2-3)
    (20.5, 26.2, 2.3, 2.55, 1250, 1250, 400, 400),  # close-up on her (4-5)
    (26.2, 33.6, 1.1, 1.15, 900, 960, 540, 540),    # strangers pass (6-8)
    (33.6, 39.0, 1.5, 1.6, 640, 680, 560, 560),     # him + shadows (9-10)
    (39.0, 52.0, 1.0, 1.06, 960, 980, 540, 540),    # night, cars slow down, headlights hit her (11-15)
    (52.0, 55.4, 1.25, 1.3, 1000, 1020, 500, 500),  # camera flash (16)
    (55.4, 65.9, 1.0, 1.12, 960, 940, 540, 540),    # police arrive, he blocks the window (17-20)
    (65.9, 77.0, 1.3, 1.5, 820, 860, 520, 520),     # movers take her, shadows torn apart (21-23)
    (77.0, 88.0, 1.0, 1.0, 960, 960, 540, 540),     # newspaper (24-25)
    (88.0, 104.0, 1.4, 1.0, 950, 960, 520, 540),    # empty window, red drains, pull back (26-30)
]
camera = keyframe_camera(CAM)
SCENES = [(a[0], a[1]) for a in CAM]

WIN = (1000, 180, 1500, 680)
CANV = (1110, 210, 1390, 580)
CARS = [40.0, 44.4, 47.6]
NEWS_IN, NEWS_OUT = 77.2, 87.4
NEWS_CENTER = (820, 520)
_paper = None

# ---------------- timeline ----------------
def light_on(t):
    if t < 1.5: return 0.0
    f = flicker(t, 1.5, 1.1, (1, 3, 4, 7, 9, 10, 11, 13, 14, 15), rate=14, off=0.15)
    if f is not None: return f
    return lerp(1.0, 0.35, ss((t - 99) / 3)) if t > 99 else 1.0

def window_on(t):
    if t < 11.6: return 0.0
    f = flicker(t, 11.6, 0.9, (2, 3, 6, 8, 9, 10), off=0.0)
    return 1.0 if f is None else f

def neon(t):
    if t < 15.0: return 0.0
    f = flicker(t, 15.0, 1.2, (1, 2, 5, 7, 8, 10, 11, 12, 13))
    if f is not None: return f
    if t < 73.5: return 1.0
    f = flicker(t, 73.5, 1.5, (0, 2, 3, 6, 9, 13), off=0.05)
    return 0.0 if f is None else f

def flat_glitch(t): return (50.4 < t < 50.6) or (53.6 < t < 54.05)
def alive(t):
    if t < 12.8: return 0.0
    if t < 14.3: return ss((t - 12.8) / 1.5)
    if t < 66: return 0.0 if flat_glitch(t) else 1.0
    return 1 - ss((t - 66) / 2)
def canvas_dx(t): return 760 * ss((t - 67) / 6)
def removed(t): return cl((t - 70) / 3)
def red_amount(t): return 1.0 if t < 89 else 1 - ss((t - 89) / 3)
def slump(t): return ss((t - 92) / 3)
def arms(t): return ss((t - 59.3) / 0.8) * (1 - ss((t - 76) / 2))

def man_x(t):
    if t < 6: return -300
    if t < 11.5:
        u = cl((t - 6) / 5.5); return -150 + 580 * (1 - (1 - u) ** 2)
    if t < 57: return 430
    if t < 59.5: return lerp(430, 960, ss((t - 57) / 2.5))
    return 960
def man_walk(t):
    if 6 <= t <= 11.5: return (t - 6) * 7.0, (1 - cl((t - 6) / 5.5)) ** 0.5
    if 57 <= t <= 59.5: return (t - 57) * 7.0, math.sin(math.pi * (t - 57) / 2.5)
    return 0.0, 0.0
def car_light_hit(t):
    h = 0.0
    for t0 in CARS:
        x = P.car_pass_x(t, t0)
        if x is not None: h = max(h, math.exp(-(((x + 200) - 1250) / 380) ** 2))
    return h
def police_x(t):
    if t < 55.6 or t > 77: return None
    u = cl((t - 55.6) / 1.6); return 2400 - 780 * (1 - (1 - u) ** 2)
def officer_x(t):
    if t < 57.4 or t > 77: return None
    return lerp(1540, 1320, ss((t - 57.4) / 2.6))

# ---------------- lyrics placement (what the words sit beside) ----------------
def anchor(t):
    if NEWS_IN + 0.4 <= t <= NEWS_OUT:
        w, h = 1000, 690; return (NEWS_CENTER[0] - w / 2, NEWS_CENTER[1] - h / 2, NEWS_CENTER[0] + w / 2, NEWS_CENTER[1] + h / 2)
    dx = canvas_dx(t)
    if dx > 560: dx = 0
    return (CANV[0] + dx, CANV[1], CANV[2] + dx, CANV[3])

# ---------------- frame ----------------
def frame(t, size=(1920, 1080), cam=None):
    global _paper
    W, H = size
    z, cx, cy = cam or camera(t)
    c = Cam(z, cx, cy, W, H)
    img = Image.new("RGB", (W, H), S.WALL)
    d = ImageDraw.Draw(img, "RGBA")
    L, Wn, N, A = light_on(t), window_on(t), neon(t), alive(t)
    hit = car_light_hit(t)
    strobe = P.police_strobe(t, 55.9, 77)

    S.background(d, c)
    S.streetlight_pool(d, c, L)
    inner = S.window_interior(d, c, WIN, Wn)
    d.rectangle(c.box(*CANV), fill=lc(inner, (88, 88, 88), Wn))      # pale mark where she hangs
    ox = canvas_dx(t)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay, "RGBA")
    if ox < 740:
        dl.rectangle(c.box(CANV[0] + ox, CANV[1], CANV[2] + ox, CANV[3]), fill=lc((10, 10, 10), (20, 20, 20), Wn), outline=(70, 70, 70), width=c.lw(8))
        F.cubist_woman(dl, c, t, A, max(Wn, 0.25) + 0.6 * hit, ox)
    if 65.9 < t < 74:      # movers behind the glass
        ma = int(235 * ss((t - 65.9) / 0.8) * (1 - ss((t - 72.8) / 1.0)))
        for mx_ in (CANV[0] - 30 + ox, CANV[2] + 30 + ox):
            dl.ellipse(c.box(mx_ - 26, 300, mx_ + 26, 352), fill=(8, 8, 8, ma))
            dl.polygon(c.pts([(mx_ - 34, 360), (mx_ + 34, 360), (mx_ + 40, 700), (mx_ - 40, 700)]), fill=(8, 8, 8, ma))
    S.paste_clipped(img, lay, c, WIN)
    d = ImageDraw.Draw(img, "RGBA")
    if hit > 0.01 and ox < 740:
        d.ellipse(c.box(1050, 160, 1450, 640), fill=(255, 255, 240, int(40 * hit)))
    if flat_glitch(t) and Wn > 0:
        d.rectangle(c.box(1225, 600, 1275, 616), fill=(225, 225, 225))   # museum label
    S.window_frame(d, c, WIN)
    S.red_reflection(d, c, t, Wn * (1 - removed(t)) * lerp(0.4, 1, A))
    P.street_neon(d, c, t, N)

    mx, ar = man_x(t), arms(t)
    if L > 0.5 and t > 11.6:
        def shadows(ds):
            sh_a = int(200 * cl((t - 11.6) / 1.0) * L)
            her_a = int(200 * ss((t - 12.8) / 1.5) * (1 - ss((t - 67.5) / 3.5)) * L)
            dancing = ss((t - 13.5) / 1.0) * (1 - ss((t - 55.4) / 1.2))
            sway = math.sin(t * 1.7) * 16 * dancing
            lean = math.sin(t * 1.7) * 30 * dancing
            bob = abs(math.sin(t * 1.7)) * 8 * dancing
            grow = ss((t - 57.5) / 2.5) * (1 - ss((t - 76) / 2))
            hs_s = 1.15 + 0.4 * grow
            hs_x = 610 + sway
            ws_x = 790 + sway + ss((t - 66.5) / 4.5) * 260
            holding = 1 - ss((t - 66.5) / 3)
            meet_x = (hs_x + ws_x) / 2 if holding > 0.5 else ws_x
            if her_a > 5:
                k = max(dancing, holding * (t > 55))
                F.sil_woman(ds, c, ws_x, 832 - bob, 1.15, (0, 0, 0, her_a), lean + 55,
                            (lerp(-30, (meet_x - ws_x) / 1.15 + 14, k), lerp(-120, -230, k)))
            on = 1.0 if her_a > 5 else 0.0
            target = (lerp(14, (ws_x - hs_x) / hs_s - 40, on), lerp(-150, -230, on))
            if t > 71: target = (lerp(target[0], 30, ss((t - 71) / 2)), lerp(target[1], -150, ss((t - 71) / 2)))
            F.sil_man(ds, c, hs_x, 832, hs_s, (0, 0, 0, sh_a), lean * 0.6 + 55, target, sl=slump(t), ar=ar)
            if officer_x(t) is not None:
                of_a = int(210 * ss((t - 57.6) / 1.5) * (1 - ss((t - 75.5) / 1.5)))
                ofx = lerp(1010, 880, ss((t - 58) / 8)) - 50 * ss((t - 66) / 5)
                F.sil_officer(ds, c, ofx, 832, 1.55, (0, 0, 0, of_a), 55, (lerp(-10, -90, ss((t - 66) / 3)), lerp(-120, -300, ss((t - 66) / 3))))
        d = F.shadow_layer(img, c, shadows)

    ofx_ = officer_x(t)
    if ofx_ is not None: F.draw_officer(d, c, ofx_, t, walking=57.4 < t < 60)
    if mx > -250:
        ph, amp = man_walk(t)
        F.draw_man(d, c, mx, t, red_amount(t), slump(t), ph, amp, ar, flower_fall=cl((t - 90) / 0.7))
    if 89 < t < 97: P.red_drip(d, c, t, 89.0, mx)

    if 26.2 <= t < 33.6:     # strangers
        x1 = 2150 - 330 * (t - 26.2) if t < 28.2 else (2150 - 660 if t < 29.6 else 2150 - 660 - 330 * (t - 29.6))
        F.draw_passer(d, c, x1, t, 905, (52, 52, 52), walking=not (28.2 < t < 29.6))
        if t > 27: F.draw_passer(d, c, 2400 - 360 * (t - 27.0), t, 915, (64, 64, 64))
    if 52.0 <= t < 55.4:     # the photographer
        x2 = 1180 if t < 54.5 else 1180 - 300 * (t - 54.5)
        if t < 52.6: x2 = 1180 + 300 * (52.6 - t)
        still = 52.6 <= t < 54.5
        F.draw_passer(d, c, x2, t, 915, (64, 64, 64), walking=not still, phone=still)

    for t0 in CARS:
        x = P.car_pass_x(t, t0)
        if x is not None: P.draw_car(d, c, x, 1)
    px_ = police_x(t)
    if px_ is not None:
        P.police_lights(d, c, t, px_, strobe)
        P.draw_car(d, c, px_, -1, (20, 20, 20), police=True, strobe=strobe, headlight_beam=False)
        P.police_wash(d, c, strobe)

    S.streetlight_pole(d, c, L)
    S.rain(d, c, t, dry=[WIN])
    if 53.6 < t < 54.0: S.flash(d, c, 1 - (t - 53.6) / 0.4)

    st = P.newspaper_spin(t, NEWS_IN, NEWS_OUT)
    if st is not None:
        if _paper is None: _paper = P.build_newspaper()
        P.paste_newspaper(img, _paper, st, NEWS_CENTER, t, NEWS_IN, Cam(1.0, 960, 540, W, H))

    return Post.apply(img, t, fade_in_out(t, META["duration"], 1.5, 3.2))
