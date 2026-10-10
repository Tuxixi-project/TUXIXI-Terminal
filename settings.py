import os, json

CONFIG_PATH = os.path.expanduser("~/.config/tuxixi/config.json")

DEFAULT_SETTINGS = {
    "font": "Monospace",
    "font_size": 11,
    "theme": "Alacritty Dark"
}

def load_settings():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass
