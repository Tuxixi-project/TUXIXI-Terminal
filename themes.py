import glob
import os
import re
import subprocess
import urllib.parse
import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

THEMES = {
    "Matrix": ("#001100", "#00FF00"),
    "Alacritty Dark": ("#1D1F21", "#C5C8C6"),
    "Monokai": ("#272822", "#F8F8F2"),
    "Dracula": ("#282A36", "#F8F8F2"),
    "Nord": ("#2E3440", "#D8DEE9"),
    "Gruvbox Dark": ("#282828", "#EBDBB2"),
    "Solarized Dark": ("#002B36", "#839496"),
    "One Dark": ("#282C34", "#ABB2BF"),
    "Tokyo Night": ("#1A1B26", "#A9B1D6"),
    "Catppuccin": ("#1E1E2E", "#CDD6F4"),
    "Cyberpunk": ("#120B1E", "#00F0FF"),
    "Classic Black/White": ("#000000", "#FFFFFF"),
    "Classic White/Black": ("#FFFFFF", "#000000"),
    "Solarized Light": ("#FDF6E3", "#657B83"),
    "PaperColor Light": ("#EEEEEE", "#444444"),
    "Gruvbox Light": ("#FBF1C7", "#3C3836"),
    "Purple Haze": ("#1A0B2E", "#D8B4FE"),
    "Ocean Breeze": ("#0F172A", "#38BDF8"),
    "Retro Amber": ("#1C160C", "#FFB000"),
}

THEME_NAMES = list(THEMES.keys())
BLUR_MODES = ("off", "static", "smoky")
TRANSLUCENT_ALPHA = 0.52
SMOKY_ALPHA = 0.87


def get_colors(theme_name, transparent=False, blur_mode="off"):
    bg_hex, fg_hex = THEMES.get(theme_name, THEMES["Alacritty Dark"])
    bg = Gdk.RGBA()
    fg = Gdk.RGBA()

    if transparent or blur_mode in ("static", "smoky"):
        bg.parse("#000000")
        bg.alpha = 0.0
        fg.parse("#F8FAFC")
        fg.alpha = 1.0
    else:
        bg.parse(bg_hex)
        bg.alpha = 1.0
        fg.parse(fg_hex)
        fg.alpha = 1.0

    return bg, fg


def _clean_path(raw_path):
    if not raw_path:
        return None
    path = raw_path.strip().strip("'\"")
    if path.startswith("file://"):
        path = path[7:]
    path = urllib.parse.unquote(path)
    path = os.path.expanduser(path)

    if os.path.isfile(path):
        return path

    if os.path.isdir(path):
        for sub in ("contents/images_dark", "contents/images", ""):
            search_dir = os.path.join(path, sub) if sub else path
            if os.path.isdir(search_dir):
                imgs = sorted(
                    glob.glob(os.path.join(search_dir, "*.[jp][pn]*g"))
                    + glob.glob(os.path.join(search_dir, "*.webp"))
                )
                if imgs:
                    return imgs[-1]
    return None


def detect_wallpaper_path():
    home = os.path.expanduser("~")

    kde_cfg = os.path.join(home, ".config/plasma-org.kde.plasma.desktop-appletsrc")
    if os.path.isfile(kde_cfg):
        try:
            with open(kde_cfg, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches = re.findall(r"^Image=(.+)$", content, re.MULTILINE)
            for candidate in reversed(matches):
                resolved = _clean_path(candidate)
                if resolved:
                    return resolved
        except OSError:
            pass

    for cfg in glob.glob(os.path.join(home, ".config/pcmanfm-qt/*/settings.conf")):
        try:
            with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("Wallpaper="):
                        resolved = _clean_path(line.split("=", 1)[1])
                        if resolved:
                            return resolved
        except OSError:
            pass

    xfce_cfg = os.path.join(
        home, ".config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
    )
    if os.path.isfile(xfce_cfg):
        try:
            with open(xfce_cfg, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches = re.findall(
                r'name="(?:last-image|image-path)"[^>]+value="([^"]+)"', content
            )
            for candidate in reversed(matches):
                resolved = _clean_path(candidate)
                if resolved:
                    return resolved
        except OSError:
            pass

    gsettings_queries = (
        ("org.gnome.desktop.background", "picture-uri-dark"),
        ("org.gnome.desktop.background", "picture-uri"),
        ("org.cinnamon.desktop.background", "picture-uri"),
        ("org.mate.background", "picture-filename"),
    )
    for schema, key in gsettings_queries:
        try:
            out = subprocess.check_output(
                ["gsettings", "get", schema, key],
                stderr=subprocess.DEVNULL,
                timeout=0.4,
                text=True,
            ).strip()
            if out and out != "''":
                resolved = _clean_path(out)
                if resolved:
                    return resolved
        except Exception:
            pass

    feh_cfg = os.path.join(home, ".fehbg")
    if os.path.isfile(feh_cfg):
        try:
            with open(feh_cfg, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for candidate in reversed(re.findall(r"'([^']+)'", content)):
                resolved = _clean_path(candidate)
                if resolved:
                    return resolved
        except OSError:
            pass

    nit_cfg = os.path.join(home, ".config/nitrogen/bg-saved.cfg")
    if os.path.isfile(nit_cfg):
        try:
            with open(nit_cfg, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("file="):
                        resolved = _clean_path(line.split("=", 1)[1])
                        if resolved:
                            return resolved
        except OSError:
            pass

    return None
