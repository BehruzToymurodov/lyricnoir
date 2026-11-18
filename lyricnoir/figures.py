"""Characters. `draw_*` = real figures (gray, with small color accents). `sil_*` = black wall shadows.
All take a Cam `c`; positions are world units, feet on GROUND (860) unless `base` is given."""
import math
from PIL import Image, ImageFilter, ImageDraw
from .core import lerp, lc, ss, cl

RED = (205, 22, 52); RED_HI = (235, 55, 85); RED_DK = (122, 12, 32)


def draw_man(d, c, x, t, red_k=1.0, sl=0.0, phase=0.0, amp=0.0, ar=0.0, flower=True, flower_fall=0.0,
             accent=RED, base=860):
    """Trench coat + fedora. red_k: how much `accent` is in scarf/flower (1 = full, 0 = gray).
    sl = slump 0..1, phase/amp = walk cycle, ar = arms spread 0..1, flower_fall 0..1 drops the flower."""
    by = base - 860
    coat = (112, 112, 112); gh = (165, 165, 165); hat = (34, 34, 34)
    sw = math.sin(phase) * 18 * amp
    for s_ in (sw, -sw):
        fx = x + s_
        d.polygon(c.pts([(x - 10, 780 + by), (x + 10, 780 + by), (fx + 9, base), (fx - 9, base)]), fill=(80, 80, 80))
    d.polygon(c.pts([(x - 22, 590 + sl * 6 + by), (x + 24, 590 + sl * 6 + by), (x + 36, 795 + by), (x - 34, 795 + by)]), fill=coat)
    d.line(c.pts([(x + 1, 610 + sl * 6 + by), (x + 3, 790 + by)]), fill=(90, 90, 90), width=c.lw(3))
    hx, hy = x + 5 + sl * 9, 560 + sl * 10 + by
    d.ellipse(c.box(hx - 22, hy - 24, hx + 22, hy + 24), fill=gh)
    d.rectangle(c.box(hx - 40, hy - 20, hx + 42, hy - 11), fill=hat)
    d.rectangle(c.box(hx - 21, hy - 52, hx + 24, hy - 18), fill=hat)
    scarf = lc((125, 125, 125), accent, red_k)
    d.rectangle(c.box(x - 22, 586 + sl * 6 + by, x + 26, 603 + sl * 6 + by), fill=scarf)
    d.polygon(c.pts([(x + 6, 598 + sl * 6 + by), (x + 22, 598 + sl * 6 + by), (x + 26, 655 + sl * 6 + by), (x + 11, 659 + sl * 6 + by)]), fill=scarf)
    if ar > 0.02:
        lh = (lerp(x - 14, x - 95, ar), lerp(690, 540, ar) + by)
        d.line(c.pts([(x - 16, 608 + by), lh]), fill=(100, 100, 100), width=c.lw(14))
    hand = (lerp(x + 56, x + 100, ar), lerp(690 + sl * 30, 540, ar) + by)
    d.line(c.pts([(x + 16, 608 + sl * 6 + by), hand]), fill=(100, 100, 100), width=c.lw(14))
    if not flower: return
    u = ss(flower_fall)
    top = (lerp(hand[0] + 6 + sl * 18, x + 80, u), lerp(hand[1] - 50 + sl * 40, base - 8, u))
    stem_b = (top[0] - 6 + u * 50, top[1] + 50 - u * 46)
    d.line(c.pts([stem_b, top]), fill=(90, 90, 90), width=c.lw(4))
    fl = lc((115, 115, 115), accent, red_k)
    for ang in range(0, 360, 72):
        px = top[0] + math.cos(math.radians(ang + t * 20)) * 9
        py = top[1] + math.sin(math.radians(ang + t * 20)) * 9
        d.ellipse(c.box(px - 9, py - 9, px + 9, py + 9), fill=fl)
    d.ellipse(c.box(top[0] - 6, top[1] - 6, top[0] + 6, top[1] + 6), fill=lc((80, 80, 80), RED_DK, red_k))


def draw_officer(d, c, x, t, walking=False, base=860):
    by = base - 860
    sw = math.sin(t * 7) * 14 if walking else 0
    col = (58, 58, 58)
    for s_ in (sw, -sw):
        d.polygon(c.pts([(x - 10, 740 + by), (x + 10, 740 + by), (x + s_ + 10, base), (x + s_ - 10, base)]), fill=col)
    d.polygon(c.pts([(x - 32, 580 + by), (x + 32, 580 + by), (x + 30, 750 + by), (x - 30, 750 + by)]), fill=col)
    d.ellipse(c.box(x - 21, 532 + by, x + 21, 578 + by), fill=(70, 70, 70))
    d.polygon(c.pts([(x - 26, 512 + by), (x + 26, 512 + by), (x + 22, 534 + by), (x - 22, 534 + by)]), fill=(30, 30, 30))
    d.rectangle(c.box(x - 40, 532 + by, x + 18, 538 + by), fill=(30, 30, 30))
    d.ellipse(c.box(x - 18, 600 + by, x - 8, 610 + by), fill=(200, 200, 200))


def draw_passer(d, c, x, t, base=905, col=(52, 52, 52), walking=True, umbrella=True, phone=False):
    """Passer-by with umbrella. base slightly > 860 = closer to camera."""
    sw = math.sin(t * 7) * 16 if walking else 0
    for s_ in (sw, -sw):
        d.polygon(c.pts([(x - 10, base - 120), (x + 10, base - 120), (x + s_ + 9, base), (x + s_ - 9, base)]), fill=col)
    d.polygon(c.pts([(x - 28, base - 270), (x + 28, base - 270), (x + 38, base - 110), (x - 38, base - 110)]), fill=col)
    d.ellipse(c.box(x - 22, base - 312, x + 22, base - 268), fill=col)
    if umbrella:
        d.line(c.pts([(x - 18, base - 250), (x - 18, base - 360)]), fill=col, width=c.lw(5))
        d.pieslice(c.box(x - 100, base - 420, x + 64, base - 300), 180, 360, fill=col)
    if phone:
        d.rectangle(c.box(x + 20, base - 265, x + 44, base - 225), fill=(90, 90, 90))


# ---------- wall shadows (draw on a shadow layer, see shadow_layer) ----------
def _proj(c, x, base, s, lean):
    return lambda dx, dy: c.P(x + (dx + lean * (-dy) / 400) * s, base + dy * s)

def sil_man(d, c, x, base, s, col, lean, reach, sl=0, ar=0.0):
    """reach = (dx, dy) of the right hand in shadow units (dy negative = up)."""
    p = _proj(c, x, base, s, lean)
    d.polygon([p(-12, -90), p(12, -90), p(14, 0), p(-14, 0)], fill=col)
    d.polygon([p(-24, -300 + sl * 8), p(26, -300 + sl * 8), p(38, -80), p(-36, -80)], fill=col)
    hx = 6 + sl * 10; hy = -330 + sl * 12
    a = p(hx - 23, hy - 25); b = p(hx + 23, hy + 25); d.ellipse([a[0], a[1], b[0], b[1]], fill=col)
    d.polygon([p(hx - 42, hy - 20), p(hx + 44, hy - 20), p(hx + 44, hy - 11), p(hx - 42, hy - 11)], fill=col)
    d.polygon([p(hx - 22, hy - 54), p(hx + 25, hy - 54), p(hx + 25, hy - 18), p(hx - 22, hy - 18)], fill=col)
    d.line([p(20, -282 + sl * 8), p(20 + reach[0], reach[1])], fill=col, width=c.lw(15 * s))
    if ar > 0.02:
        d.line([p(-18, -282), p(lerp(-10, -110, ar), lerp(-150, -380, ar))], fill=col, width=c.lw(15 * s))

def sil_woman(d, c, x, base, s, col, lean, reach):
    p = _proj(c, x, base, s, lean)
    d.polygon([p(-9, -110), p(9, -110), p(10, 0), p(-10, 0)], fill=col)
    d.polygon([p(-18, -280), p(18, -280), p(62, -90), p(-62, -90)], fill=col)
    a = p(-23, -330); b = p(23, -284); d.ellipse([a[0], a[1], b[0], b[1]], fill=col)
    a = p(8, -342); b = p(36, -314); d.ellipse([a[0], a[1], b[0], b[1]], fill=col)
    d.line([p(-14, -262), p(-14 + reach[0], reach[1])], fill=col, width=c.lw(12 * s))

def sil_officer(d, c, x, base, s, col, lean, reach):
    p = _proj(c, x, base, s, lean)
    for sx in (-14, 14):
        d.polygon([p(sx - 11, -120), p(sx + 11, -120), p(sx + 12, 0), p(sx - 12, 0)], fill=col)
    d.polygon([p(-40, -300), p(40, -300), p(36, -110), p(-36, -110)], fill=col)
    a = p(-22, -350); b = p(22, -302); d.ellipse([a[0], a[1], b[0], b[1]], fill=col)
    d.polygon([p(-30, -372), p(30, -372), p(26, -345), p(-26, -345)], fill=col)
    d.polygon([p(-28, -348), p(44, -348), p(44, -340), p(-28, -340)], fill=col)
    d.line([p(-34, -285), p(-34 + reach[0], reach[1])], fill=col, width=c.lw(17 * s))


def shadow_layer(img, c, draw_fn, blur=3.5):
    """Soft wall shadows: draw_fn(ds) draws sil_* in black with alpha; returns a fresh Draw on img."""
    shl = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(shl, "RGBA"))
    shl = shl.filter(ImageFilter.GaussianBlur(blur * c.z))
    img.paste(shl, (0, 0), shl)
    return ImageDraw.Draw(img, "RGBA")


# ---------- the Cubist painted woman (episode 01, reusable for any "painting" subject) ----------
def cubist_woman(d, c, t, a, lit, ox=0, origin=(1130, 230), scale=4.14):
    """a = alive 0..1 (sway, blink, smile). lit = brightness (>1 = extra light hitting her). ox = slide offset."""
    def wmap(x, y): return (origin[0] + (x - 222) * scale + ox, origin[1] + (y - 82) * scale)
    k = lerp(0.55, 1.0, a) * lerp(0.4, 1.0, cl(lit)) * (1 + 0.35 * max(0, lit - 1))
    def col(cc): return tuple(min(255, int(v * k)) for v in cc)
    sway = a * math.sin(t * 1.3) * 7
    tilt = a * math.sin(t * 0.9) * 4
    cxm = origin[0] + 120 + ox
    def hp(x, y):
        X, Y = wmap(x, y); return c.P(X + sway, Y + tilt * (X - cxm) / 120)
    def bp(x, y):
        X, Y = wmap(x, y); return c.P(X + sway * 0.4, Y)
    o = (14, 14, 14); w = c.lw(4)
    d.polygon([bp(x, y) for x, y in [(226, 160), (238, 134), (262, 134), (276, 160)]], fill=col(RED), outline=o, width=w)
    d.polygon([bp(x, y) for x, y in [(246, 122), (255, 122), (255, 135), (246, 135)]], fill=col(RED_HI), outline=o, width=w)
    d.polygon([hp(x, y) for x, y in [(230, 88), (268, 86), (272, 124), (226, 126)]], fill=col(RED), outline=o, width=w)
    d.polygon([hp(x, y) for x, y in [(238, 94), (251, 92), (251, 124), (240, 124)]], fill=col(RED_HI), outline=o, width=w)
    d.polygon([hp(x, y) for x, y in [(251, 92), (263, 96), (266, 110), (259, 124), (251, 124)]], fill=col(RED_DK), outline=o, width=w)
    blink = 0.15 if (a > 0.5 and (t % 3.4) < 0.14) else 1.0
    ex, ey = wmap(245, 106); e1 = c.P(ex + sway, ey)
    ry = max(8.8 * blink, 1.5)
    d.ellipse([e1[0] - c.S(18), e1[1] - c.S(ry), e1[0] + c.S(18), e1[1] + c.S(ry)], fill=(235, 235, 235), outline=o, width=c.lw(2))
    if blink > 0.5: d.ellipse([e1[0] - c.S(4), e1[1] - c.S(4), e1[0] + c.S(4), e1[1] + c.S(4)], fill=o)
    ex2, ey2 = wmap(258.5, 104.5); e2 = c.P(ex2 + sway, ey2)
    d.polygon([(e2[0] - c.S(14), e2[1] + c.S(2)), (e2[0] + c.S(14), e2[1] - c.S(8 * blink)), (e2[0] + c.S(10), e2[1] + c.S(6 * blink))], fill=(235, 235, 235), outline=o)
    if blink > 0.5: d.ellipse([e2[0] - c.S(3), e2[1] - c.S(3), e2[0] + c.S(3), e2[1] + c.S(3)], fill=o)
    lx, ly = wmap(246, 117); L = c.P(lx + sway, ly); sm = a * 7
    d.line([(L[0] - c.S(18), L[1] - c.S(sm * 0.6)), (L[0], L[1] + c.S(sm * 0.5)), (L[0] + c.S(16), L[1] - c.S(sm * 0.6))],
           fill=(20, 4, 8) if a > 0.3 else col((90, 10, 25)), width=c.lw(4), joint="curve")
