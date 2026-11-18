# Lyric Noir studio

Tools for making **Lyric Noir** animated music films: a noir drawing engine, song timing analysis,
neon word-by-word lyrics, and 9:16 Instagram covers. Episode 01: Citizen Cope, "Pablo Picasso".

## Setup
```
./setup.sh            # Linux/macOS: installs Python packages, checks ffmpeg
```
Needs Python 3.10+ and ffmpeg.

## Commands
```
python -m lyricnoir check
python -m lyricnoir new 02-song-name
python -m lyricnoir analyze 02-song-name --song work/02-song-name/song.mp3 --lines work/02-song-name/lines.txt --to 150
python -m lyricnoir fix-timing 02-song-name --set 1=20.8 --audio-start 9
python -m lyricnoir stills 02-song-name 5 20 40 60
python -m lyricnoir render 02-song-name            # --shots 3,4 to redo some shots
python -m lyricnoir package 02-song-name --song work/02-song-name/song.mp3
python -m lyricnoir cover 02-song-name
```

## Folders
```
lyricnoir/        engine: core, scene, figures, props, render, audio, lyrics, cover, overlay_standalone
episodes/NN-slug/ story.py (the film), timing.json (line times, no lyrics), NOTES.md (shot plan)
templates/        story_template.py, HOW_TO.txt (for the lyrics step on Windows)
assets/           fonts (OFL), brand (profile logo)
work/, dist/      scratch and outputs (not in git)
```

## Adding the lyrics (Windows)
See `templates/HOW_TO.txt` (also included in every package):
`python lyrics_overlay.py NN-slug.mp4 lyrics.srt final.mp4 --audio song.mp3`

Songs and lyrics are never stored in this repo.
