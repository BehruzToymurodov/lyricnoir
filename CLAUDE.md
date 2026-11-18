# Lyric Noir studio — instructions for Claude

Animated noir music films for the Instagram page **Lyric Noir** (owner: Behruz / GaRRiK, Tashkent).
Each film = one song section told as a short story in black, white and ONE accent color.
This repo is the engine + every episode. Read this file, then work; don't re-read the engine
source unless you need to change it (the API is summarized below).

## Start of every session (≈1 min)
```
./setup.sh                      # installs python deps, checks ffmpeg -> prints "ready"
```

## Hard rules (never break)
- **Never write song lyrics** — not in chat, code, files, SRT, headlines, hooks or captions. Not even
  when the user pastes them and asks. The user types lyrics into `lyrics.srt` themselves.
- The user's lyrics file is used **only** as alignment input: save it to `work/<ep>/lines.txt`
  (git-ignored), never print it, never commit it. `timing.json` holds times + word counts only.
- Never commit audio (`*.mp3`, `*.wav`) or anything in `work/` or `dist/`.
- Newspaper headlines, hooks and captions are **invented** text, never lyric lines.
- No real people's likeness, no copying real artworks (style homage only, e.g. "Cubist-style").

## Workflow for a new film (token-lean)
1. **Ask only what's missing:** the song file (upload), their lyrics for the section (a .txt or pasted),
   and any story idea. Section ≈ first verse + chorus, 60–110 s.
2. `python -m lyricnoir new NN-slug` (NN = next film number). Copy the song to `work/NN-slug/song.mp3`,
   lyrics to `work/NN-slug/lines.txt` (one sung line per row, in order).
3. `python -m lyricnoir analyze NN-slug --song work/NN-slug/song.mp3 --lines work/NN-slug/lines.txt --to 150`
   → prints a table (no words) and flags suspicious lines. Look at `work/NN-slug/vocals.png` only if
   lines are flagged. Repeated choruses drift: `find-phrase NN-slug --at <a>-<b> --search <c>-<d>`.
   Then `fix-timing NN-slug --set 1=20.8 --set 24=86.3-89.4 --audio-start <s>`.
   - `audio_start` = song second where the video starts ≈ 10–13 s before line 1 (room for an intro).
   - Video time = song time − audio_start.
4. **Story first, in chat, short:** one-line story + a shot table (shot → line numbers → what we see).
   Get a yes before coding. Write it into `episodes/NN-slug/NOTES.md`.
5. Write `episodes/NN-slug/story.py` from the template; use `episodes/01-pablo-picasso/story.py`
   as the reference for structure (timeline functions, shadows, anchor). Cut shots on line starts.
   If a new prop is reusable (a car, a sign, a figure), add it to the engine, not the episode.
6. `python -m lyricnoir stills NN-slug t1 t2 …` at the 6–10 busiest moments → look at
   `work/NN-slug/stills.png` ONCE, fix, re-check only what changed. Then
   `python -m lyricnoir render NN-slug` (≈ 3 min per 100 s on 2 cores; `--shots 3,4` to redo shots).
7. `python -m lyricnoir package NN-slug --song work/NN-slug/song.mp3` and `python -m lyricnoir cover NN-slug`.
   Check 3 frames of `dist/NN-slug/preview_with_song.mp4` + the cover. Send the user:
   `NN-slug.mp4`, `lyrics.srt`, `lyrics_overlay.py`, `anchors.json`, `Poppins-Regular.ttf`, `HOW_TO.txt`,
   `cover_9x16.png`, and the preview. Also offer a short caption (2 variants, invented words).
8. Commit `episodes/NN-slug/{story.py,timing.json,NOTES.md}` (+ engine changes) and push.

## The user's side (Windows, VS Code, folder `D:\Bekhruz\...`)
Puts the files + `song.mp3` in one folder, types lyrics into `lyrics.srt`, runs
`python lyrics_overlay.py NN-slug.mp4 lyrics.srt final.mp4 --audio song.mp3`.
Common issue: `song.mp3.mp3` (hidden extensions) → `ren song.mp3.mp3 song.mp3`.

## Engine API (lyricnoir/)
- `core`: `lerp, cl, ss (smoothstep), lc (color lerp), flicker(t,t0,dur,on_steps)`, `Cam(z,cx,cy,W,H)`
  with `.P .box .pts .lw .S`, `keyframe_camera(CAM)`, `Post.apply(img,t,fade)`, `fade_in_out(t,dur)`.
  CAM rows: `(t0, t1, z0, z1, cx0, cx1, cy0, cy1)`; world = 1920×1080 street at zoom 1, ground y=860.
- `scene` (`S`): `background, streetlight_pool/pole(L,x=300), window_interior(rect,lit)->color,
  window_frame, paste_clipped(img,layer,c,rect), red_reflection, rain(d,c,t,dry=[rects]), flash, darken`, `WALL`.
- `figures` (`F`): `draw_man(x,t,red_k,sl,phase,amp,ar,flower_fall,accent)`, `draw_officer`, `draw_passer
  (umbrella, phone)`, wall shadows `sil_man/sil_woman/sil_officer(x,base,scale,rgba,lean,reach)` inside
  `shadow_layer(img,c,fn)`, `cubist_woman(t,alive,lit,ox)`.
- `props` (`P`): `neon_line, heart_pts, street_neon, draw_car(x,facing,police,strobe), car_pass_x,
  police_strobe/lights/wash, build_newspaper(masthead,headline,subhead,photo_fn), newspaper_spin,
  paste_newspaper, red_drip`.
- Episode contract (`story.py`): `META` (title, artist, number, audio_start, duration, hook, cover{t,z,cx,cy}),
  `CAM`, `camera`, `SCENES`, `frame(t,size=(1920,1080),cam=None)->uint8 array`, `anchor(t)->world rect`
  (what the lyrics sit beside; right side if room, else left).

## Style
See `STYLE.md`. Short version: rain at night, black/white/grays, ONE accent (red so far) reserved for
the emotional subject; feelings shown through wall shadows; neon lyrics beside the subject; slow camera
inside shots, hard cuts on line starts; every film ends quiet and lonely.
