"""
Lyric Noir — lyrics overlay (neon or spray-paint stencil) (standalone; ships to the user with each episode).

Burns word-by-word neon lyrics into the video, beside the subject of each shot
(positions come from anchors.json, made by the studio for this episode).

Usage (in the episode folder):
    python lyrics_overlay.py VIDEO.mp4 lyrics.srt final.mp4 --audio song.mp3

- lyrics.srt: one block per sung line; replace the placeholder words, keep the times
  (times are VIDEO times; the song is trimmed automatically using anchors.json).
- --offset 0.3 shifts all lyrics later (negative = earlier).
- The style (neon / spray) comes from anchors.json; --style overrides it.
Needs: Python 3.8+, `pip install pillow numpy`, ffmpeg on PATH.
"""
import argparse, json, os, random, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_SIZE = 60
COLUMN_W = 440
GAP = 46
LINE_HOLD = 0.8
FADE_OUT = 0.35
FLICKER_STEP = 0.075
FLICKER = [1.0, 0.1, 1.0, 0.3, 1.0]
CORE = (255, 222, 228)
GLOW = (255, 30, 75)


def ss(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def parse_time(s):
    h, m, rest = s.strip().replace(".", ",").split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

def read_srt(path, offset):
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    lines = []
    for block in re.split(r"\n\s*\n", text.strip()):
        rows = [r for r in block.split("\n") if r.strip()]
        ti = next((i for i, r in enumerate(rows) if "-->" in r), None)
        if ti is None: continue
        a, b = rows[ti].split("-->")
        words = " ".join(rows[ti + 1:]).split()
        if words:
            lines.append({"start": parse_time(a) + offset, "end": parse_time(b) + offset, "words": words})
    lines.sort(key=lambda l: l["start"])
    for i, l in enumerate(lines):
        nxt = lines[i + 1]["start"] - 0.05 if i + 1 < len(lines) else 1e9
        l["hide"] = min(l["end"] + LINE_HOLD, max(nxt, l["end"]))
        weights = [len(w) + 2 for w in l["words"]]
        total, acc, l["times"] = sum(weights), 0, []
        dur = max(0.2, l["end"] - l["start"])
        for wgt in weights:
            l["times"].append(l["start"] + dur * acc / total); acc += wgt
    return lines

def word_alpha(age):
    if age < 0: return 0.0
    k = int(age / FLICKER_STEP)
    return FLICKER[k] if k < len(FLICKER) else 1.0

def load_font(path, style="neon"):
    here = os.path.dirname(os.path.abspath(__file__))
    size = SPRAY_SIZE if style == "spray" else FONT_SIZE
    first = "SairaStencilOne-Regular.ttf" if style == "spray" else "Poppins-Regular.ttf"
    tries = ([path] if path else []) + [os.path.join(here, first), os.path.join(here, "Poppins-Regular.ttf"), "C:/Windows/Fonts/segoeuil.ttf",
             "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in tries:
        if p and os.path.exists(p): return ImageFont.truetype(p, size)
    sys.exit(f"No font found. Put {first} next to this script or pass --font")

def layout(words, font, draw, col):
    space = draw.textlength(" ", font=font)
    rows, row, width = [], [], 0
    for w in words:
        wl = draw.textlength(w, font=font)
        if row and width + space + wl > col:
            rows.append(row); row, width = [], 0
        row.append((w, wl)); width += (space if len(row) > 1 else 0) + wl
    if row: rows.append(row)
    return rows, space

def draw_line(frame, line, t, rect, font, measure, W, H):
    L, T, R, B = rect
    room = W - (R + GAP) - 30
    right_side = room >= 320
    col = int(min(COLUMN_W, room)) if right_side else COLUMN_W
    x0 = R + GAP if right_side else L - GAP - col
    x0 = max(30, min(W - col - 30, x0))
    rows, space = layout(line["words"], font, measure, col)
    lh = int(FONT_SIZE * 1.25); block_h = lh * len(rows)
    y0 = max(60, min(H - block_h - 80, (T + B) / 2 - block_h / 2))
    fade = 1.0 - ss((t - (line["hide"] - FADE_OUT)) / FADE_OUT)
    pad = 40
    core = Image.new("RGBA", (col + 2 * pad, block_h + 2 * pad), (0, 0, 0, 0)); glow = core.copy()
    dc, dg = ImageDraw.Draw(core), ImageDraw.Draw(glow)
    i = 0
    for r_i, row in enumerate(rows):
        row_w = sum(wl for _, wl in row) + space * (len(row) - 1)
        x = pad + (0 if right_side else col - row_w); y = pad + r_i * lh
        for w, wl in row:
            a = word_alpha(t - line["times"][i]) * fade
            if a > 0:
                dg.text((x, y), w, font=font, fill=GLOW + (int(255 * a),))
                dc.text((x, y), w, font=font, fill=CORE + (int(255 * a),))
            x += wl + space; i += 1
    gw, gm, gt = (glow.filter(ImageFilter.GaussianBlur(r)) for r in (16, 7, 2.5))
    pos = (int(x0 - pad), int(y0 - pad))
    for g in (gw, gw, gw, gm, gm, gt, gt): frame.alpha_composite(g, pos)
    frame.alpha_composite(core.filter(ImageFilter.GaussianBlur(0.6)), pos)


# ---------------------------------------------------------------- spray-paint stencil style
SPRAY_SIZE = 72
SPRAY_COL = 540
PAINT = (234, 232, 224)
_SPRAY = {}

def _spray_block(line, font, measure, col, right_side):
    """Pre-paint every word of a line once (paint, overspray, speckle, drips) in block coordinates."""
    key = (line["start"], col, right_side)
    if key in _SPRAY: return _SPRAY[key]
    words = [w.upper() for w in line["words"]]
    rows, space = layout(words, font, measure, col)
    lh = int(SPRAY_SIZE * 1.22); pad = 50; drip = 95
    Wb, Hb = col + 2 * pad, lh * len(rows) + 2 * pad + drip
    seed = int(line["start"] * 1000) + len(words)
    rng = np.random.default_rng(seed); r2 = random.Random(seed)
    out, i = [], 0
    for r_i, row in enumerate(rows):
        row_w = sum(wl for _, wl in row) + space * (len(row) - 1)
        x = pad + (0 if right_side else col - row_w); y = pad + r_i * lh
        for w, wl in row:
            bx0, by0 = int(x - 30), int(y - 20); bx1, by1 = int(x + wl + 30), int(y + lh + drip)
            bw, bh = bx1 - bx0, by1 - by0
            m = Image.new("L", (bw, bh), 0); ImageDraw.Draw(m).text((x - bx0, y - by0), w, font=font, fill=255)
            a = np.asarray(m, np.float32) / 255
            over = np.asarray(m.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
            far = np.asarray(m.filter(ImageFilter.GaussianBlur(16)), np.float32) / 255
            paint = np.clip(a * 0.96 + over * 0.22 + (rng.random(a.shape) < 0.05) * far * 0.55, 0, 1)
            paint *= 0.86 + 0.14 * rng.random(a.shape)
            dr = Image.new("L", (bw, bh), 0); dd = ImageDraw.Draw(dr)
            ys, xs = np.nonzero(a > 0.5); bottom = int(ys.max()) if len(ys) else bh // 2
            for _ in range(r2.randint(1, 3)):
                if not len(xs): break
                k = r2.randrange(len(xs)); xx = int(xs[k]); col_ = np.nonzero(a[:, xx] > 0.5)[0]
                y0 = int(col_.max()); L = r2.uniform(18, drip - 12); wd = r2.choice([2, 3, 3, 4])
                dd.line([(xx, y0), (xx, y0 + L)], fill=215, width=wd)
                dd.ellipse([xx - wd, y0 + L - wd, xx + wd, y0 + L + wd], fill=215)
            out.append(dict(bx=bx0, by=by0, paint=paint, drip=np.asarray(dr, np.float32) / 255,
                            x0=x - bx0, x1=x + wl - bx0, bottom=bottom, dur=min(0.45, max(0.16, 0.05 * len(w) + 0.06)),
                            t=line["times"][i]))
            x += wl + space; i += 1
    blk = (Wb, Hb, out, lh, pad)
    _SPRAY[key] = blk
    return blk

def draw_line_spray(frame, line, t, rect, font, measure, W, H):
    L_, T, R, B = rect
    room = W - (R + GAP) - 30
    right_side = room >= 360
    col = int(min(SPRAY_COL, room)) if right_side else SPRAY_COL
    x0 = R + GAP if right_side else L_ - GAP - col
    x0 = max(30, min(W - col - 30, x0))
    Wb, Hb, words, lh, pad = _spray_block(line, font, measure, col, right_side)
    text_h = Hb - 2 * pad - 95
    y0 = max(60, min(H - text_h - 120, (T + B) / 2 - text_h / 2))
    fade = 1.0 - ss((t - (line["hide"] - FADE_OUT)) / FADE_OUT)
    A = np.zeros((Hb, Wb), np.float32)
    for w in words:
        age = t - w["t"]
        if age < 0: continue
        p = min(1.0, age / w["dur"])
        bh, bw = w["paint"].shape
        xs = np.arange(bw, dtype=np.float32)[None, :]
        head = w["x0"] - 14 + (w["x1"] - w["x0"] + 40) * p
        wipe = np.clip((head - xs) / 14, 0, 1)
        a = w["paint"] * wipe
        dp = ss((age - w["dur"]) / 0.9)
        if dp > 0:
            ys = np.arange(bh, dtype=np.float32)[:, None]
            a = np.maximum(a, w["drip"] * np.clip((w["bottom"] + 95 * dp - ys) / 6, 0, 1))
        if p < 1:                                   # spray mist at the nozzle
            ys = np.arange(bh, dtype=np.float32)[:, None]
            cy = (w["bottom"] + 10) * 0.55
            g = np.exp(-(((xs - head) / 34) ** 2 + ((ys - cy) / 46) ** 2))
            a = np.maximum(a, g * (np.random.random(g.shape) < 0.3) * 0.45)
        sl = A[w["by"]:w["by"] + bh, w["bx"]:w["bx"] + bw]
        np.maximum(sl, a[:sl.shape[0], :sl.shape[1]], out=sl)
    if A.max() <= 0: return
    A *= fade
    alpha = Image.fromarray((A * 255).astype(np.uint8))
    pos = (int(x0 - pad), int(y0 - pad))
    shade = Image.new("RGBA", (Wb, Hb), (0, 0, 0, 0)); shade.putalpha(alpha.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45)))
    frame.alpha_composite(shade, pos)
    paint = Image.new("RGBA", (Wb, Hb), PAINT + (255,)); paint.putalpha(alpha)
    frame.alpha_composite(paint, pos)

def main():
    ap = argparse.ArgumentParser(description="Burn word-by-word neon lyrics into a Lyric Noir video.")
    ap.add_argument("video"); ap.add_argument("srt"); ap.add_argument("output")
    ap.add_argument("--audio", help="the original song file (trimmed automatically)")
    ap.add_argument("--anchors", default=None, help="anchors.json (default: next to this script)")
    ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--font")
    ap.add_argument("--style", choices=["neon", "spray"], help="override the style from anchors.json")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    meta = json.load(open(args.anchors or os.path.join(here, "anchors.json")))
    W, H = meta["size"]; FPS = meta["fps"]; rects = meta["rects"]
    lines = read_srt(args.srt, args.offset)
    style = args.style or meta.get("style", "neon")
    draw = draw_line_spray if style == "spray" else draw_line
    font = load_font(args.font, style); measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    print(f"{len(lines)} lines, {sum(len(l['words']) for l in lines)} words")

    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", args.video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if args.audio:
        if not os.path.exists(args.audio): sys.exit(f"Song not found: {args.audio}")
        st = meta["duration"] - meta.get("fade_out", 3.2)
        cmd += ["-ss", str(meta["audio_start"]), "-i", args.audio, "-map", "0:v", "-map", "1:a",
                "-af", f"afade=t=in:d=1.5,afade=t=out:st={st}:d={meta.get('fade_out', 3.2)}",
                "-c:a", "aac", "-b:a", "192k", "-shortest"]
    tmp = args.output + ".part.mp4"
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-b:v", "9M", "-maxrate", "11M", "-bufsize", "18M",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n, size = 0, W * H * 3
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size: break
        t = n / FPS
        active = [l for l in lines if l["times"][0] <= t < l["hide"]]
        if active:
            fr = Image.frombuffer("RGB", (W, H), buf).convert("RGBA")
            rect = rects[min(n, len(rects) - 1)]
            for l in active: draw(fr, l, t, rect, font, measure, W, H)
            buf = fr.convert("RGB").tobytes()
        enc.stdin.write(buf); n += 1
        if n % 150 == 0: print(f"  {t:5.1f}s done")
    enc.stdin.close(); dec.wait()
    if enc.wait() == 0: os.replace(tmp, args.output); print("Saved", args.output)
    else: sys.exit("ffmpeg failed while writing the video")

if __name__ == "__main__":
    main()
