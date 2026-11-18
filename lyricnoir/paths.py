"""Repo paths and fonts (all fonts ship in assets/fonts, OFL licensed)."""
import os
from PIL import ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
EPISODES = os.path.join(ROOT, "episodes")
WORK = os.path.join(ROOT, "work")        # renders, stems, scratch (git-ignored)
DIST = os.path.join(ROOT, "dist")        # what gets sent to the user (git-ignored)

FONTS = {
    "lyrics": "Poppins-Regular.ttf",
    "title_italic": "PlayfairDisplay-Italic.woff",
    "title_bold": "PlayfairDisplay-Bold.woff",
    "ui": "Inter-Regular.otf",
    "ui_medium": "Inter-Medium.otf",
}
_SYS = {
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "C:/Windows/Fonts/georgia.ttf"],
    "serif_bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf"],
}

def font(name, size):
    if name in FONTS:
        return ImageFont.truetype(os.path.join(ASSETS, "fonts", FONTS[name]), size)
    for p in _SYS.get(name, []):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.truetype(os.path.join(ASSETS, "fonts", FONTS["title_bold"]), size)

def ep_dir(ep): return os.path.join(EPISODES, ep)
def work_dir(ep):
    p = os.path.join(WORK, ep); os.makedirs(p, exist_ok=True); return p
def dist_dir(ep):
    p = os.path.join(DIST, ep); os.makedirs(p, exist_ok=True); return p
