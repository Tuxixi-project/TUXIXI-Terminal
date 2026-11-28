import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk, GLib

BUILTIN_THEMES = {
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

CUSTOM_THEMES_PATH = os.path.join(
    GLib.get_user_config_dir(), "tuxixi", "themes.json"
)
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

THEMES = {}
THEME_NAMES = []
_CUSTOM_THEMES = {}
BLUR_MODES = ("off", "static", "smoky")
TRANSLUCENT_ALPHA = 0.52
SMOKY_ALPHA = 0.87

DEFAULT_DARK_PALETTE = (
    "#1E2028", "#F87171", "#4ADE80", "#FACC15",
    "#60A5FA", "#C084FC", "#22D3EE", "#E2E8F0",
    "#475569", "#FCA5A5", "#86EFAC", "#FDE047",
    "#93C5FD", "#D8B4FE", "#67E8F9", "#F8FAFC",
)

DEFAULT_LIGHT_PALETTE = (
    "#1E293B", "#DC2626", "#16A34A", "#CA8A04",
    "#2563EB", "#9333EA", "#0891B2", "#475569",
    "#64748B", "#EF4444", "#22C55E", "#EAB308",
    "#3B82F6", "#A855F7", "#06B6D4", "#0F172A",
)

THEME_PALETTES = {
    "Alacritty Dark": (
        "#1D1F21", "#CC6666", "#B5BD68", "#F0C674",
        "#81A2BE", "#B294BB", "#8ABEB7", "#C5C8C6",
        "#666666", "#D54E53", "#B9CA4A", "#E7C547",
        "#7AA6DA", "#C397D8", "#70C0B1", "#EAEAEA",
    ),
    "Dracula": (
        "#21222C", "#FF5555", "#50FA7B", "#F1FA8C",
        "#BD93F9", "#FF79C6", "#8BE9FD", "#F8F8F2",
        "#6272A4", "#FF6E6E", "#69FF94", "#FFFFA5",
        "#D6ACFF", "#FF92DF", "#A4FFFF", "#FFFFFF",
    ),
    "Nord": (
        "#3B4252", "#BF616A", "#A3BE8C", "#EBCB8B",
        "#81A1C1", "#B48EAD", "#88C0D0", "#E5E9F0",
        "#4C566A", "#BF616A", "#A3BE8C", "#EBCB8B",
        "#81A1C1", "#B48EAD", "#8FBCBB", "#ECEFF4",
    ),
    "Gruvbox Dark": (
        "#282828", "#CC241D", "#98971A", "#D79921",
        "#458588", "#B16286", "#689D6A", "#A89984",
        "#928374", "#FB4934", "#B8BB26", "#FABD2F",
        "#83A598", "#D3869B", "#8EC07C", "#EBDBB2",
    ),
    "Gruvbox Light": (
        "#3C3836", "#9D0006", "#79740E", "#B57614",
        "#076678", "#8F3F71", "#427B58", "#7C6F64",
        "#928374", "#CC241D", "#98971A", "#D79921",
        "#458588", "#B16286", "#689D6A", "#282828",
    ),
    "Solarized Dark": (
        "#073642", "#DC322F", "#859900", "#B58900",
        "#268BD2", "#D33682", "#2AA198", "#EEE8D5",
        "#586E75", "#CB4B16", "#586E75", "#657B83",
        "#839496", "#6C71C4", "#93A1A1", "#FDF6E3",
    ),
    "Solarized Light": (
        "#073642", "#DC322F", "#859900", "#B58900",
        "#268BD2", "#D33682", "#2AA198", "#586E75",
        "#657B83", "#CB4B16", "#839496", "#93A1A1",
        "#268BD2", "#6C71C4", "#2AA198", "#002B36",
    ),
    "One Dark": (
        "#282C34", "#E06C75", "#98C379", "#E5C07B",
        "#61AFEF", "#C678DD", "#56B6C2", "#ABB2BF",
        "#5C6370", "#E06C75", "#98C379", "#E5C07B",
        "#61AFEF", "#C678DD", "#56B6C2", "#FFFFFF",
    ),
    "Tokyo Night": (
        "#15161E", "#F7768E", "#9ECE6A", "#E0AF68",
        "#7AA2F7", "#BB9AF7", "#7DCFFF", "#A9B1D6",
        "#414868", "#F7768E", "#9ECE6A", "#E0AF68",
        "#7AA2F7", "#BB9AF7", "#7DCFFF", "#C0CAF5",
    ),
    "Catppuccin": (
        "#45475A", "#F38BA8", "#A6E3A1", "#F9E2AF",
        "#89B4FA", "#F5C2E7", "#94E2D5", "#BAC2DE",
        "#585B70", "#F38BA8", "#A6E3A1", "#F9E2AF",
        "#89B4FA", "#F5C2E7", "#94E2D5", "#CDD6F4",
    ),
    "Monokai": (
        "#272822", "#F92672", "#A6E22E", "#F4BF75",
        "#66D9EF", "#AE81FF", "#A1EFE4", "#F8F8F2",
        "#75715E", "#F92672", "#A6E22E", "#F4BF75",
        "#66D9EF", "#AE81FF", "#A1EFE4", "#F9F8F5",
    ),
}


def hex_to_luminance(hex_color):
    """WCAG relative luminance in [0.0, 1.0]."""
    if not isinstance(hex_color, str) or not HEX_RE.match(hex_color):
        return 0.0
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0

    def _linear(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def is_dark_color(hex_color):
    return hex_to_luminance(hex_color) < 0.4


def load_custom_themes(path=None):
    target_path = path or CUSTOM_THEMES_PATH
    if not os.path.isfile(target_path):
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        valid = {}
        for name, pair in raw.items():
            if not isinstance(name, str) or not name.strip():
                continue
            if (
                isinstance(pair, (list, tuple))
                and len(pair) == 2
                and isinstance(pair[0], str)
                and isinstance(pair[1], str)
                and HEX_RE.match(pair[0])
                and HEX_RE.match(pair[1])
            ):
                valid[name.strip()] = (pair[0].upper(), pair[1].upper())
        return valid
    except Exception:
        return {}


def _atomic_write_custom_themes(custom_map, path=None):
    target_path = path or CUSTOM_THEMES_PATH
    config_dir = os.path.dirname(target_path)
    tmp_path = None
    try:
        os.makedirs(config_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=config_dir,
            prefix=".themes.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_path = tmp_file.name
            json.dump(
                {k: list(v) for k, v in custom_map.items()},
                tmp_file,
                indent=4,
            )
            tmp_file.write("\n")
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, target_path)
        return True
    except OSError:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False


def reload_themes():
    """Daxili + istifadəçinin şəxsi temalarını THEMES və THEME_NAMES içinə yükləyir."""
    custom = load_custom_themes()
    _CUSTOM_THEMES.clear()
    _CUSTOM_THEMES.update(custom)
    THEMES.clear()
    THEMES.update(BUILTIN_THEMES)
    THEMES.update(_CUSTOM_THEMES)
    THEME_NAMES[:] = list(THEMES.keys())


def is_custom_theme(name):
    return name in _CUSTOM_THEMES


def save_custom_theme(name, bg_hex, fg_hex):
    clean_name = (name or "").strip()
    if not clean_name or not HEX_RE.match(bg_hex) or not HEX_RE.match(fg_hex):
        return False
    custom = dict(_CUSTOM_THEMES)
    custom[clean_name] = (bg_hex.upper(), fg_hex.upper())
    if not _atomic_write_custom_themes(custom):
        return False
    reload_themes()
    return True


def delete_custom_theme(name):
    if name not in _CUSTOM_THEMES:
        return False
    custom = dict(_CUSTOM_THEMES)
    del custom[name]
    if not _atomic_write_custom_themes(custom):
        return False
    reload_themes()
    return True


reload_themes()


def get_effective_fg_hex(theme_name, transparent=False, blur_mode="off"):
    """Şəffaf/blur rejimdə oxunaqlı olan tema mətn rəngini qoruyur, tünd mətni ağa çevirir."""
    _bg_hex, fg_hex = THEMES.get(theme_name, BUILTIN_THEMES["Alacritty Dark"])
    if transparent or blur_mode in ("static", "smoky"):
        if hex_to_luminance(fg_hex) >= 0.22:
            return fg_hex
        return "#F8FAFC"
    return fg_hex


def get_colors(theme_name, transparent=False, blur_mode="off"):
    bg_hex, _fg_hex = THEMES.get(theme_name, BUILTIN_THEMES["Alacritty Dark"])
    eff_fg_hex = get_effective_fg_hex(
        theme_name, transparent=transparent, blur_mode=blur_mode
    )
    bg = Gdk.RGBA()
    fg = Gdk.RGBA()

    if transparent or blur_mode in ("static", "smoky"):
        bg.parse("#000000")
        bg.alpha = 0.0
    else:
        bg.parse(bg_hex)
        bg.alpha = 1.0

    fg.parse(eff_fg_hex)
    fg.alpha = 1.0
    return bg, fg


def get_palette(theme_name, transparent=False, blur_mode="off"):
    """Temaya uyğun 16-rəngli ANSI palitrasını Gdk.RGBA siyahısı olaraq qaytarır."""
    bg_hex, _fg_hex = THEMES.get(theme_name, BUILTIN_THEMES["Alacritty Dark"])
    effective_dark = (
        transparent
        or blur_mode in ("static", "smoky")
        or is_dark_color(bg_hex)
    )

    if effective_dark:
        if theme_name in THEME_PALETTES and is_dark_color(bg_hex):
            hex_palette = THEME_PALETTES[theme_name]
        else:
            hex_palette = DEFAULT_DARK_PALETTE
    else:
        hex_palette = THEME_PALETTES.get(theme_name, DEFAULT_LIGHT_PALETTE)

    palette = []
    for color_hex in hex_palette:
        rgba = Gdk.RGBA()
        rgba.parse(color_hex)
        rgba.alpha = 1.0
        palette.append(rgba)
    return palette


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


def _run_quick_cmd(argv, timeout=0.35):
    if not argv or not shutil.which(argv[0]):
        return ""
    try:
        return subprocess.check_output(
            argv,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            text=True,
        ).strip()
    except Exception:
        return ""


def _detect_swww_wallpaper(home):
    for binary in ("swww", "awww"):
        out = _run_quick_cmd([binary, "query"])
        if out:
            for line in reversed(out.splitlines()):
                m = re.search(r"image:\s*(.+)$", line)
                if m:
                    resolved = _clean_path(m.group(1))
                    if resolved:
                        return resolved

    cache_root = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    cache_files = []
    for folder in ("swww", "awww"):
        cdir = os.path.join(cache_root, folder)
        if os.path.isdir(cdir):
            for entry in os.scandir(cdir):
                if entry.is_file():
                    try:
                        cache_files.append((entry.stat().st_mtime, entry.path))
                    except OSError:
                        pass
    for _mtime, path in sorted(cache_files, reverse=True):
        try:
            with open(path, "rb") as f:
                raw = f.read(8192)
            for chunk in reversed(re.split(rb"[\x00\r\n]+", raw)):
                text = chunk.decode("utf-8", errors="ignore").strip()
                resolved = _clean_path(text)
                if resolved:
                    return resolved
        except OSError:
            pass
    return None


def _detect_hyprpaper_wallpaper(home):
    out = _run_quick_cmd(["hyprctl", "hyprpaper", "listactive"])
    if out:
        for line in reversed(out.splitlines()):
            if "=" in line:
                candidate = line.split("=", 1)[1]
            elif ":" in line:
                candidate = line.split(":", 1)[1]
            else:
                candidate = line
            resolved = _clean_path(candidate)
            if resolved:
                return resolved

    cfg = os.path.join(home, ".config/hypr/hyprpaper.conf")
    if os.path.isfile(cfg):
        try:
            with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # 1) wallpaper = monitor,/path və ya path = /path (yeni blok sintaksisi)
            for pattern in (
                r"^\s*wallpaper\s*=\s*(?:[^,\n]*,)?\s*(.+)$",
                r"^\s*path\s*=\s*(.+)$",
                r"^\s*preload\s*=\s*(.+)$",
            ):
                matches = re.findall(pattern, content, re.MULTILINE)
                for candidate in reversed(matches):
                    cleaned = candidate.split("#", 1)[0].strip()
                    resolved = _clean_path(cleaned)
                    if resolved:
                        return resolved
        except OSError:
            pass
    return None


def _detect_waypaper_wallpaper(home):
    cfg = os.path.join(home, ".config/waypaper/config.ini")
    if not os.path.isfile(cfg):
        return None
    try:
        with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.lstrip().startswith("wallpaper") and "=" in line:
                    resolved = _clean_path(line.split("=", 1)[1])
                    if resolved:
                        return resolved
    except OSError:
        pass
    return None


def _detect_proc_wallpaper():
    """Aktiv swaybg / wbg proseslərindən divar kağızı yolunu oxuyur."""
    uid = os.getuid()
    try:
        entries = list(os.scandir("/proc"))
    except OSError:
        return None

    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            with open(os.path.join(entry.path, "cmdline"), "rb") as f:
                raw = f.read(4096)
        except OSError:
            continue
        if not raw:
            continue
        parts = [p.decode("utf-8", errors="ignore") for p in raw.split(b"\x00") if p]
        if not parts:
            continue
        comm = os.path.basename(parts[0])
        if comm == "swaybg":
            for i, arg in enumerate(parts[1:], start=1):
                if arg in ("-i", "--image") and i + 1 < len(parts):
                    resolved = _clean_path(parts[i + 1])
                    if resolved:
                        return resolved
                elif arg.startswith("--image="):
                    resolved = _clean_path(arg.split("=", 1)[1])
                    if resolved:
                        return resolved
        elif comm == "wbg":
            for arg in reversed(parts[1:]):
                if not arg.startswith("-"):
                    resolved = _clean_path(arg)
                    if resolved:
                        return resolved
    return None


def _detect_common_pointer_wallpaper(home):
    cache_root = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    pointer_candidates = (
        os.path.join(cache_root, "wal", "wal"),
        os.path.join(cache_root, "current_wallpaper"),
        os.path.join(home, ".config/hypr/current_wallpaper"),
    )
    img_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    for p in pointer_candidates:
        if not os.path.isfile(p):
            continue
        real = os.path.realpath(p)
        if real.lower().endswith(img_exts) and os.path.isfile(real):
            return real
        try:
            if os.path.getsize(p) <= 4096:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                resolved = _clean_path(first_line)
                if resolved:
                    return resolved
        except OSError:
            pass
    return None


def _detect_kde_wallpaper(home):
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
    return None


def _detect_lxqt_wallpaper(home):
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
    return None


def _detect_xfce_wallpaper(home):
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
    return None


def _detect_gsettings_wallpaper(_home):
    color_scheme = _run_quick_cmd(
        ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
    )
    if "prefer-dark" in color_scheme:
        gnome_keys = ("picture-uri-dark", "picture-uri")
    else:
        gnome_keys = ("picture-uri", "picture-uri-dark")

    gsettings_queries = (
        ("org.gnome.desktop.background", gnome_keys[0]),
        ("org.gnome.desktop.background", gnome_keys[1]),
        ("org.cinnamon.desktop.background", "picture-uri"),
        ("org.mate.background", "picture-filename"),
    )
    for schema, key in gsettings_queries:
        out = _run_quick_cmd(["gsettings", "get", schema, key])
        if out and out != "''":
            resolved = _clean_path(out)
            if resolved:
                return resolved
    return None


def _detect_feh_wallpaper(home):
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
    return None


def _detect_nitrogen_wallpaper(home):
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


def _detect_wayland_wallpaper(home):
    for fn in (
        _detect_swww_wallpaper,
        _detect_hyprpaper_wallpaper,
        lambda _h: _detect_proc_wallpaper(),
        _detect_waypaper_wallpaper,
        _detect_common_pointer_wallpaper,
    ):
        resolved = fn(home)
        if resolved:
            return resolved
    return None


def detect_wallpaper_path():
    """Aktiv masaüstü mühitinə uyğun cari divar kağızını aşkarlayır."""
    home = os.path.expanduser("~")
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        + ":"
        + os.environ.get("DESKTOP_SESSION", "")
    ).lower()
    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY")) or (
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )

    detectors = []
    if any(w in desktop for w in ("hyprland", "sway", "river", "niri", "wayfire")):
        detectors.append(_detect_wayland_wallpaper)
    elif "kde" in desktop or "plasma" in desktop:
        detectors.append(_detect_kde_wallpaper)
    elif any(g in desktop for g in ("gnome", "ubuntu", "cinnamon", "mate", "budgie")):
        detectors.append(_detect_gsettings_wallpaper)
    elif "xfce" in desktop:
        detectors.append(_detect_xfce_wallpaper)
    elif "lxqt" in desktop:
        detectors.append(_detect_lxqt_wallpaper)
    elif is_wayland:
        detectors.append(_detect_wayland_wallpaper)

    fallback_order = (
        _detect_wayland_wallpaper,
        _detect_kde_wallpaper,
        _detect_lxqt_wallpaper,
        _detect_xfce_wallpaper,
        _detect_gsettings_wallpaper,
        _detect_feh_wallpaper,
        _detect_nitrogen_wallpaper,
        _detect_common_pointer_wallpaper,
    )
    for fn in fallback_order:
        if fn not in detectors:
            detectors.append(fn)

    for fn in detectors:
        resolved = fn(home)
        if resolved:
            return resolved
    return None
