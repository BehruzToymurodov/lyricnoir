"""Rendering: stills/contact sheets, parallel per-shot encoding, final file, anchors for lyrics."""
import importlib.util, json, math, os, subprocess, sys
from multiprocessing import Pool
from PIL import Image
from .core import FPS
from .paths import ep_dir, work_dir, dist_dir, ROOT


def load_story(ep):
    path = os.path.join(ep_dir(ep), "story.py")
    if ROOT not in sys.path: sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location(f"story_{ep.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def stills(ep, times, cols=2, thumb=960):
    """Contact sheet of frames at `times` -> work/<ep>/stills.png (look at it before any full render)."""
    st = load_story(ep)
    ims = [Image.fromarray(st.frame(float(t))) for t in times]
    w = thumb; h = int(thumb * ims[0].height / ims[0].width)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (w * cols, h * rows))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    out = os.path.join(work_dir(ep), "stills.png"); sheet.save(out)
    return out


def _render_shot(args):
    ep, i = args
    st = load_story(ep)
    t0, t1 = st.SCENES[i]
    W, H = getattr(st, "SIZE", (1920, 1080))
    n0, n1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    d = os.path.join(work_dir(ep), "shots")
    os.makedirs(d, exist_ok=True)
    tmp, final = os.path.join(d, f"tmp_{i:02d}.mp4"), os.path.join(d, f"shot_{i:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                          "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for k in range(n0, n1):
        p.stdin.write(st.frame(k / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError(f"shot {i} failed")
    os.replace(tmp, final)
    return final


def render(ep, shots=None, workers=None):
    """Render shots in parallel (only `shots` if given, e.g. to redo one), then join -> dist/<ep>/<ep>.mp4."""
    st = load_story(ep)
    idx = list(range(len(st.SCENES))) if shots is None else list(shots)
    workers = workers or max(1, os.cpu_count() or 1)
    with Pool(min(workers, len(idx))) as pool:
        pool.map(_render_shot, [(ep, i) for i in idx])
    d = os.path.join(work_dir(ep), "shots")
    lst = os.path.join(d, "list.txt")
    with open(lst, "w") as f:
        for i in range(len(st.SCENES)): f.write(f"file 'shot_{i:02d}.mp4'\n")
    joined = os.path.join(d, "joined.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined], check=True)
    out = os.path.join(dist_dir(ep), f"{ep}.mp4"); tmp = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-c:v", "libx264", "-preset", "veryfast",
                    "-b:v", "9M", "-maxrate", "11M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    return out


def anchors(ep):
    """Screen-space rect the lyrics sit beside, per frame -> dist/<ep>/anchors.json (read by lyrics_overlay.py)."""
    st = load_story(ep)
    W, H = getattr(st, "SIZE", (1920, 1080))
    n = int(round(st.META["duration"] * FPS))
    rects = []
    for k in range(n):
        t = k / FPS
        z, cx, cy = st.camera(t)
        a = st.anchor(t)
        r = [(a[0] - cx) * z + W / 2, (a[1] - cy) * z + H / 2, (a[2] - cx) * z + W / 2, (a[3] - cy) * z + H / 2]
        rects.append([round(v, 1) for v in r])
    meta = {"fps": FPS, "size": [W, H], "duration": st.META["duration"], "audio_start": st.META["audio_start"],
            "fade_out": st.META.get("fade_out", 3.2), "rects": rects}
    out = os.path.join(dist_dir(ep), "anchors.json")
    with open(out, "w") as f: json.dump(meta, f, separators=(",", ":"))
    return out


def cover_background(ep, out=None):
    """Vertical 1080x1920 still of the scene for the cover (story.META['cover'] picks the moment and framing)."""
    st = load_story(ep)
    cv = st.META["cover"]
    im = Image.fromarray(st.frame(cv["t"], size=(1080, 1920), cam=(cv["z"], cv["cx"], cv["cy"])))
    out = out or os.path.join(work_dir(ep), "cover_bg.png"); im.save(out)
    return out
