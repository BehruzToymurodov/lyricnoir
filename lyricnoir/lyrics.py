"""Placeholder SRT from timing.json (song time -> video time). Words are 'word1 word2 ...' — the user types the real lyrics."""
import json


def _ts(x):
    ms = int(round(max(0, x) * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def make_srt(timing_json, out_srt, audio_start=None, duration=None):
    tj = json.load(open(timing_json))
    a0 = tj["audio_start"] if audio_start is None else audio_start
    blocks, k = [], 0
    for row in tj["lines"]:
        if row["start"] is None: continue
        s, e = row["start"] - a0, row["end"] - a0
        if e <= 0 or (duration and s >= duration): continue
        k += 1
        blocks.append(f"{k}\n{_ts(s)} --> {_ts(e)}\n" + " ".join(f"word{i + 1}" for i in range(row["n"])) + "\n")
    with open(out_srt, "w", encoding="utf-8") as f: f.write("\n".join(blocks))
    return out_srt, k
