import json
import os
import sys
import tempfile
import gi

gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
from gi.repository import GLib, GObject
from themes import THEME_NAMES, BLUR_MODES

DEFAULT_SETTINGS = {
    "font": "Monospace",
    "font_size": 11,
    "theme": "Alacritty Dark",
    "transparent": False,
    "blur_mode": "off",  # "off" | "static" | "smoky"
}


class SettingsManager(GObject.Object):
    __gsignals__ = {
        "settings-changed": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (str, object),
        ),
    }

    def __init__(self, config_path=None):
        super().__init__()
        if config_path is None:
            config_dir = os.path.join(GLib.get_user_config_dir(), "tuxixi")
            config_path = os.path.join(config_dir, "config.json")
        self.config_path = config_path
        self._data = self._load()

    def _validate(self, raw):
        if not isinstance(raw, dict):
            return DEFAULT_SETTINGS.copy()

        validated = DEFAULT_SETTINGS.copy()

        font = raw.get("font")
        if isinstance(font, str) and font.strip():
            validated["font"] = font.strip()

        font_size = raw.get("font_size")
        if isinstance(font_size, int) and not isinstance(font_size, bool):
            validated["font_size"] = max(6, min(48, font_size))

        theme = raw.get("theme")
        if isinstance(theme, str) and theme in THEME_NAMES:
            validated["theme"] = theme

        transparent = raw.get("transparent")
        if isinstance(transparent, bool):
            validated["transparent"] = transparent

        blur_mode = raw.get("blur_mode")
        if isinstance(blur_mode, str) and blur_mode in BLUR_MODES:
            validated["blur_mode"] = blur_mode
        elif raw.get("blur") is True:
            validated["blur_mode"] = "static"

        return validated

    def _load(self):
        if not os.path.exists(self.config_path):
            data = DEFAULT_SETTINGS.copy()
            self._atomic_save(data)
            return data
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return self._validate(raw)
        except Exception as e:
            print(f"Warning: Failed to read config, using defaults: {e}", file=sys.stderr)
            return DEFAULT_SETTINGS.copy()

    def _atomic_save(self, data):
        config_dir = os.path.dirname(self.config_path)
        tmp_path = None
        try:
            os.makedirs(config_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=config_dir,
                prefix=".config.",
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as tmp_file:
                tmp_path = tmp_file.name
                json.dump(data, tmp_file, indent=4)
                tmp_file.write("\n")
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            os.replace(tmp_path, self.config_path)
        except Exception as e:
            print(f"Error: The configuration could not be saved: {e}", file=sys.stderr)
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self._atomic_save(self._data)
        self.emit("settings-changed", key, value)

    def change_font_size(self, delta):
        current = self.get("font_size", 11)
        new_size = max(6, min(48, current + delta))
        self.set("font_size", new_size)

    def cycle_theme(self):
        current = self.get("theme", "Alacritty Dark")
        try:
            index = THEME_NAMES.index(current)
            next_index = (index + 1) % len(THEME_NAMES)
        except ValueError:
            next_index = 0
        self.set("theme", THEME_NAMES[next_index])

    def toggle_transparency(self):
        current = bool(self.get("transparent", False))
        self.set("transparent", not current)

    def cycle_blur_mode(self):
        """off -> static -> smoky -> off"""
        current = self.get("blur_mode", "off")
        try:
            index = BLUR_MODES.index(current)
            next_index = (index + 1) % len(BLUR_MODES)
        except ValueError:
            next_index = 0
        self.set("blur_mode", BLUR_MODES[next_index])
