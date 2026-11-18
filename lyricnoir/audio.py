"""Song analysis: vocal stem + forced alignment of the user's lyric lines -> per-line timings.

PRIVACY/COPYRIGHT: the lyrics text the user provides is used only as alignment input in work/.
Never print it, never commit it, never write it into outputs. timing.json stores times + word counts only."""
import json, os, subprocess
import numpy as np


def to_wav(song, out, seconds=None, sr=22050):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", song]
    if seconds: cmd += ["-t", str(seconds)]
    subprocess.run(cmd + ["-ar", str(sr), out], check=True)
    return out


def vocal_stem(wav, out16k):
    """Approximate vocal isolation: center channel minus sides, then REPET-SIM foreground. Writes 16 kHz mono."""
    import librosa, soundfile as sf
    y, sr = librosa.load(wav, sr=22050, mono=False)
    if y.ndim == 1: y = np.vstack([y, y])
    L, R = y; mid, side = (L + R) / 2, (L - R) / 2
    n_fft, hop = 2048, 512
    Mc = librosa.stft(mid, n_fft=n_fft, hop_length=hop); M = np.abs(Mc)
    Sd = np.abs(librosa.stft(side, n_fft=n_fft, hop_length=hop))
    center = np.maximum(M - Sd, 0)
    filt = librosa.decompose.nn_filter(center, aggregate=np.median, metric="cosine",
                                       width=int(librosa.time_to_frames(2, sr=sr, hop_length=hop)))
    filt = np.minimum(center, filt)
    mask = librosa.util.softmask(center - filt, 2 * filt, power=2) * (center / (M + 1e-9))
    v = librosa.istft(mask * Mc, hop_length=hop, length=len(mid))
    v = librosa.resample(v, orig_sr=sr, target_sr=16000)
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.9
    sf.write(out16k, v, 16000, subtype="PCM_16")
    return out16k


def _normalize(line):
    import re
    s = line.lower().replace("’", "'").replace("mr.", "mister").replace("mrs.", "missus").replace("&", "and")
    s = re.sub(r"[^a-z' ]+", " ", s)
    return [w.strip("'") if w.startswith("'") else w for w in s.split()]


def align(stem16k, lines, t0=0.0, t1=None):
    """Force-align `lines` (list of lyric lines, user-provided) to the stem between t0..t1 seconds.
    Returns [{'start','end','n'}] per line (song time). Word timings stay in memory only."""
    from pocketsphinx import Decoder
    import soundfile as sf
    v, sr = sf.read(stem16k)
    seg = v[int(t0 * sr): int(t1 * sr) if t1 else None]
    pcm = (seg * 32767).astype(np.int16).tobytes()
    toks = [_normalize(l) for l in lines]
    d = Decoder(samprate=16000, bestpath=False, beam=1e-100, pbeam=1e-100, wbeam=1e-80, maxhmmpf=-1)
    d.set_align_text(" ".join(w for l in toks for w in l))
    d.start_utt(); d.process_raw(pcm, full_utt=True); d.end_utt()
    words = [(g.word, t0 + g.start_frame / 100, t0 + g.end_frame / 100) for g in d.seg()
             if not g.word.startswith("<") and not g.word.startswith("[") and g.word != "(NULL)"]
    out, i = [], 0
    for l in toks:
        segw = words[i:i + len(l)]; i += len(l)
        if not segw: out.append({"start": None, "end": None, "n": len(l)}); continue
        out.append({"start": round(segw[0][1], 2), "end": round(segw[-1][2], 2), "n": len(l),
                    "word_starts": [round(w[1], 2) for w in segw]})
    return out


def vocal_activity_plot(stem16k, out_png, ranges, timings=None):
    """Plot vocal loudness (to spot sung vs instrumental parts) with line starts marked as numbers."""
    import soundfile as sf, matplotlib
    matplotlib.use("Agg"); import matplotlib.pyplot as plt
    v, sr = sf.read(stem16k); hop = 160
    rms = np.sqrt(np.convolve(v ** 2, np.ones(800) / 800, mode="same"))[::hop]
    t = np.arange(len(rms)) * hop / sr
    fig, axes = plt.subplots(len(ranges), 1, figsize=(18, 3 * len(ranges)))
    axes = np.atleast_1d(axes)
    for ax, (a, b) in zip(axes, ranges):
        m = (t >= a) & (t < b); ax.plot(t[m], rms[m], lw=.7); ax.set_xlim(a, b)
        ax.set_xticks(np.arange(int(a), int(b) + 1, 1)); ax.grid(alpha=.3)
        for k, tm in enumerate(timings or []):
            if tm["start"] and a <= tm["start"] < b:
                ax.axvline(tm["start"], color="r", lw=.6); ax.text(tm["start"], ax.get_ylim()[1] * .9, str(k + 1), fontsize=8)
    plt.tight_layout(); plt.savefig(out_png, dpi=60); plt.close(fig)
    return out_png


def find_phrase(stem16k, t0, t1, search=(0, None), top=6):
    """Where else does the phrase sung at t0..t1 occur? (useful when alignment drifts on repeated choruses)."""
    import librosa, soundfile as sf
    v, sr = sf.read(stem16k)
    F = librosa.feature.mfcc(y=v.astype(np.float32), sr=sr, n_mfcc=20, hop_length=160, n_fft=1024)[1:]
    F = (F - F.mean(1, keepdims=True)) / (F.std(1, keepdims=True) + 1e-9)
    T = F[:, int(t0 * 100):int(t1 * 100)]; n = T.shape[1]
    a = int(search[0] * 100); b = int((search[1] or F.shape[1] / 100) * 100) - n
    sc = []
    for s in range(a, b):
        X = F[:, s:s + n]; sc.append((float(np.sum(T * X) / (np.linalg.norm(T) * np.linalg.norm(X) + 1e-9)), s / 100))
    sc.sort(reverse=True); picked = []
    for c, tt in sc:
        if all(abs(tt - p) > 1.5 for _, p in picked): picked.append((round(c, 2), tt))
        if len(picked) == top: break
    return sorted(picked, key=lambda x: x[1])


def save_timing(timings, path, audio_start, overrides=None):
    """Write timing.json: song-time starts/ends + word counts (no words). overrides: {line_no: (start, end)}."""
    rows = []
    for k, tm in enumerate(timings):
        s, e = tm["start"], tm["end"]
        if overrides and (k + 1) in overrides: s, e = overrides[k + 1]
        rows.append({"line": k + 1, "start": s, "end": e, "n": tm["n"]})
    for k in range(len(rows) - 1):     # never overlap the next line
        if rows[k]["end"] and rows[k + 1]["start"]:
            rows[k]["end"] = round(min(rows[k]["end"], rows[k + 1]["start"] - 0.05), 2)
    with open(path, "w") as f:
        json.dump({"audio_start": audio_start, "lines": rows}, f, indent=1)
    return path
