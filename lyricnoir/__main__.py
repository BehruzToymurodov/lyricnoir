"""Lyric Noir studio CLI.   python -m lyricnoir <command> ...

  check                               verify tools and libraries
  new  NN-slug                        start an episode from templates/story_template.py
  analyze EP --song S --lines L.txt   time each lyric line from the song (lyrics stay private in work/)
         [--from 0 --to 150 --audio-start 8]
  fix-timing EP --set 1=20.8 --set 24=86.3-89.4   correct flagged lines -> timing.json
  find-phrase EP --at 70.5-71.9 --search 80-130    where is this sung phrase repeated? (fix drifting choruses)
  stills EP t1 t2 ...                 contact sheet -> work/EP/stills.png (check before rendering!)
  render EP [--shots 3,4]             render shots in parallel -> dist/EP/EP.mp4
  srt EP                              placeholder lyrics.srt (video time) -> dist/EP/
  cover EP                            9:16 cover -> dist/EP/cover_9x16.png
  package EP [--song S]               dist/EP/: srt, anchors.json, lyrics_overlay.py, font, HOW_TO (+ preview with song)
  all EP [--song S]                   render + package + cover
"""
import argparse, json, os, shutil, subprocess, sys
from .paths import ROOT, ASSETS, EPISODES, ep_dir, work_dir, dist_dir


def cmd_check(_):
    ok = True
    for tool in ("ffmpeg", "ffprobe", "rsvg-convert"):
        found = shutil.which(tool) is not None
        print(f"{'ok ' if found else 'MISSING'} {tool}"); ok &= found or tool == "rsvg-convert"
    for mod in ("numpy", "PIL", "librosa", "soundfile", "pocketsphinx", "matplotlib"):
        try: __import__(mod); print("ok ", mod)
        except Exception: print("MISSING", mod); ok = False
    print("ready" if ok else "run ./setup.sh"); return 0 if ok else 1


def cmd_new(a):
    d = ep_dir(a.ep)
    if os.path.exists(d): sys.exit(f"{d} exists")
    os.makedirs(d); shutil.copy(os.path.join(ROOT, "templates", "story_template.py"), os.path.join(d, "story.py"))
    open(os.path.join(d, "NOTES.md"), "w").write(f"# {a.ep}\n\nSong:\nArtist:\nSection used:\nStory in one line:\n\n## Shot plan\n")
    print("created", d)


def cmd_analyze(a):
    from . import audio
    w = work_dir(a.ep)
    wav = audio.to_wav(a.song, os.path.join(w, "song.wav"), seconds=a.to)
    stem = audio.vocal_stem(wav, os.path.join(w, "vocals16k.wav"))
    lines = [l.strip() for l in open(a.lines, encoding="utf-8-sig") if l.strip()]
    tm = audio.align(stem, lines, a.frm, a.to)
    out = audio.save_timing(tm, os.path.join(ep_dir(a.ep), "timing.auto.json"), a.audio_start)
    audio.vocal_activity_plot(stem, os.path.join(w, "vocals.png"),
                              [(x, x + 30) for x in range(int(a.frm), int(a.to or 150), 30)], tm)
    print(f"{'line':>4} {'start':>7} {'end':>7} {'words':>5}  check")
    for k, row in enumerate(json.load(open(out))["lines"]):
        s, e = row["start"], row["end"]; flag = ""
        if s is None: flag = "NOT FOUND"
        elif e - s > 6.5: flag = "long - verify (instrumental gap or drift?)"
        elif e - s < 0.35 and row["n"] > 1: flag = "short - verify"
        print(f"{k + 1:>4} {s or 0:7.2f} {e or 0:7.2f} {row['n']:>5}  {flag}")
    print("saved", out, "| vocal plot:", os.path.join(w, "vocals.png"))
    print("next: review flagged lines, then  python -m lyricnoir fix-timing", a.ep, "--set N=start[-end] ...")


def cmd_fix_timing(a):
    """Apply manual corrections to timing.auto.json (or timing.json) and write timing.json."""
    d = ep_dir(a.ep)
    src = os.path.join(d, "timing.auto.json") if os.path.exists(os.path.join(d, "timing.auto.json")) and not a.keep else os.path.join(d, "timing.json")
    tj = json.load(open(src)); rows = tj["lines"]
    for s in a.set or []:
        n, v = s.split("="); n = int(n)
        st, en = (v.split("-") + [None])[:2]
        rows[n - 1]["start"] = float(st)
        if en: rows[n - 1]["end"] = float(en)
    for k in range(len(rows) - 1):
        if rows[k]["end"] and rows[k + 1]["start"]:
            rows[k]["end"] = round(min(rows[k]["end"], rows[k + 1]["start"] - 0.05), 2)
    if a.audio_start is not None: tj["audio_start"] = a.audio_start
    out = os.path.join(d, "timing.json"); json.dump(tj, open(out, "w"), indent=1)
    print("saved", out)


def cmd_find_phrase(a):
    from . import audio
    t0, t1 = map(float, a.at.split("-")); s0, s1 = map(float, a.search.split("-"))
    stem = os.path.join(work_dir(a.ep), "vocals16k.wav")
    for score, t in audio.find_phrase(stem, t0, t1, (s0, s1)): print(f"{t:7.2f}  similarity {score}")


def cmd_stills(a):
    from .render import stills
    print(stills(a.ep, a.times))


def cmd_render(a):
    from .render import render
    shots = [int(x) for x in a.shots.split(",")] if a.shots else None
    print(render(a.ep, shots))


def cmd_srt(a):
    from .lyrics import make_srt
    from .render import load_story
    st = load_story(a.ep)
    out, n = make_srt(os.path.join(ep_dir(a.ep), "timing.json"), os.path.join(dist_dir(a.ep), "lyrics.srt"),
                      st.META["audio_start"], st.META["duration"])
    print(out, f"({n} blocks)")


def cmd_cover(a):
    from .render import cover_background, load_story
    from .cover import make_cover
    st = load_story(a.ep)
    bg = cover_background(a.ep)
    print(make_cover(bg, os.path.join(dist_dir(a.ep), "cover_9x16.png"), st.META["title"], st.META["artist"],
                     st.META["number"], st.META.get("hook", ())))


def cmd_package(a):
    from .render import anchors, load_story
    d = dist_dir(a.ep)
    cmd_srt(a); anchors(a.ep)
    shutil.copy(os.path.join(ROOT, "lyricnoir", "overlay_standalone.py"), os.path.join(d, "lyrics_overlay.py"))
    st = load_story(a.ep)
    lf = {"spray": "SairaStencilOne-Regular.ttf"}.get(st.META.get("lyric_style"), "Poppins-Regular.ttf")
    shutil.copy(os.path.join(ASSETS, "fonts", lf), d)
    shutil.copy(os.path.join(ROOT, "templates", "HOW_TO.txt"), d)
    if a.song:
        subprocess.run([sys.executable, os.path.join(d, "lyrics_overlay.py"), os.path.join(d, f"{a.ep}.mp4"),
                        os.path.join(d, "lyrics.srt"), os.path.join(d, "preview_with_song.mp4"), "--audio", a.song], check=True)
    print("package ready:", d)


def cmd_all(a):
    cmd_render(argparse.Namespace(ep=a.ep, shots=None)); cmd_package(a); cmd_cover(a)


def main():
    ap = argparse.ArgumentParser(prog="python -m lyricnoir", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("check").set_defaults(f=cmd_check)
    p = sp.add_parser("new"); p.add_argument("ep"); p.set_defaults(f=cmd_new)
    p = sp.add_parser("analyze"); p.add_argument("ep"); p.add_argument("--song", required=True); p.add_argument("--lines", required=True)
    p.add_argument("--from", dest="frm", type=float, default=0.0); p.add_argument("--to", type=float, default=None)
    p.add_argument("--audio-start", type=float, default=0.0); p.set_defaults(f=cmd_analyze)
    p = sp.add_parser("fix-timing"); p.add_argument("ep"); p.add_argument("--set", action="append")
    p.add_argument("--audio-start", type=float); p.add_argument("--keep", action="store_true", help="edit timing.json instead of timing.auto.json")
    p.set_defaults(f=cmd_fix_timing)
    p = sp.add_parser("find-phrase"); p.add_argument("ep"); p.add_argument("--at", required=True); p.add_argument("--search", required=True)
    p.set_defaults(f=cmd_find_phrase)
    p = sp.add_parser("stills"); p.add_argument("ep"); p.add_argument("times", nargs="+", type=float); p.set_defaults(f=cmd_stills)
    p = sp.add_parser("render"); p.add_argument("ep"); p.add_argument("--shots"); p.set_defaults(f=cmd_render)
    p = sp.add_parser("srt"); p.add_argument("ep"); p.set_defaults(f=cmd_srt)
    p = sp.add_parser("cover"); p.add_argument("ep"); p.set_defaults(f=cmd_cover)
    p = sp.add_parser("package"); p.add_argument("ep"); p.add_argument("--song"); p.set_defaults(f=cmd_package)
    p = sp.add_parser("all"); p.add_argument("ep"); p.add_argument("--song"); p.set_defaults(f=cmd_all)
    a = ap.parse_args()
    sys.exit(a.f(a) or 0)


if __name__ == "__main__":
    main()
