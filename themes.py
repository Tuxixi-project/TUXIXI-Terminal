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
    "Retro Amber": ("#1C160C", "#FFB000")
}

THEME_NAMES = list(THEMES.keys())

def get_colors(theme_name):
    bg_hex, fg_hex = THEMES.get(theme_name, THEMES["Alacritty Dark"])
    bg = Gdk.RGBA()
    fg = Gdk.RGBA()
    bg.parse(bg_hex)
    fg.parse(fg_hex)
    return bg, fg
