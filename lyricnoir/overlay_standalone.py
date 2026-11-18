"""
Lyric Noir — neon lyrics overlay (standalone; ships to the user with each episode).

Burns word-by-word neon lyrics into the video, beside the subject of each shot
(positions come from anchors.json, made by the studio for this episode).

Usage (in the episode folder):
    python lyrics_overlay.py VIDEO.mp4 lyrics.srt final.mp4 --audio song.mp3

- lyrics.srt: one block per sung line; replace the placeholder words, keep the times
  (times are VIDEO times; the song is trimmed automatically using anchors.json).
- --offset 0.3 shifts all lyrics later (negative = earlier).
Needs: Python 3.8+, `pip install pillow numpy`, ffmpeg on PATH.
"""
import argparse, json, os, re, subprocess, sys
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

def load_font(path):
    here = os.path.dirname(os.path.abspath(__file__))
    tries = ([path] if path else []) + [os.path.join(here, "Poppins-Regular.ttf"), "C:/Windows/Fonts/segoeuil.ttf",
             "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in tries:
        if p and os.path.exists(p): return ImageFont.truetype(p, FONT_SIZE)
    sys.exit("No font found. Put Poppins-Regular.ttf next to this script or pass --font")

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

def main():
    ap = argparse.ArgumentParser(description="Burn word-by-word neon lyrics into a Lyric Noir video.")
    ap.add_argument("video"); ap.add_argument("srt"); ap.add_argument("output")
    ap.add_argument("--audio", help="the original song file (trimmed automatically)")
    ap.add_argument("--anchors", default=None, help="anchors.json (default: next to this script)")
    ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--font")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    meta = json.load(open(args.anchors or os.path.join(here, "anchors.json")))
    W, H = meta["size"]; FPS = meta["fps"]; rects = meta["rects"]
    lines = read_srt(args.srt, args.offset)
    font = load_font(args.font); measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))
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
            for l in active: draw_line(fr, l, t, rect, font, measure, W, H)
            buf = fr.convert("RGB").tobytes()
        enc.stdin.write(buf); n += 1
        if n % 150 == 0: print(f"  {t:5.1f}s done")
    enc.stdin.close(); dec.wait()
    if enc.wait() == 0: os.replace(tmp, args.output); print("Saved", args.output)
    else: sys.exit("ffmpeg failed while writing the video")

if __name__ == "__main__":
    main()
