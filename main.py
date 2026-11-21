#!/usr/bin/env python3
import os
import shutil
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib
from settings import SettingsManager
from themes import THEMES, TRANSLUCENT_ALPHA, SMOKY_ALPHA
from ui import TuxixiWindow


class TuxixiApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.tuxixi.Terminal")
        GLib.set_prgname("org.tuxixi.Terminal")
        GLib.set_application_name("TUXIXI")
        self.settings = None
        self.css_provider = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = SettingsManager()
        self.settings.connect("settings-changed", self._on_settings_changed)

        display = Gdk.Display.get_default()
        self._setup_app_icon(display)

        self.css_provider = Gtk.CssProvider()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self._update_global_css()

    def _setup_app_icon(self, display):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(project_dir, "tuxixi-512.png")

        if not os.path.isfile(logo_path):
            Gtk.Window.set_default_icon_name("utilities-terminal")
            return

        user_data = GLib.get_user_data_dir()
        base_icons_dir = os.path.join(user_data, "icons")
        hicolor_512_dir = os.path.join(base_icons_dir, "hicolor", "512x512", "apps")

        for target_dir in (base_icons_dir, hicolor_512_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
                for icon_name in ("org.tuxixi.Terminal.png", "tuxixi.png", "tuxixi-512.png"):
                    dest = os.path.join(target_dir, icon_name)
                    if not os.path.exists(dest):
                        shutil.copy2(logo_path, dest)
            except OSError:
                pass

        if display:
            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_theme.add_search_path(project_dir)
            icon_theme.add_search_path(base_icons_dir)

        Gtk.Window.set_default_icon_name("tuxixi-512")

    def do_activate(self):
        self.open_new_window()

    def open_new_window(self, cwd=None):
        window = TuxixiWindow(self, self.settings, cwd=cwd)
        window.set_icon_name("tuxixi-512")
        window.present()

    def _on_settings_changed(self, _settings, key, _value):
        if key in ("theme", "transparent", "blur_mode"):
            self._update_global_css()

    def _update_global_css(self):
        theme_name = self.settings.get("theme", "Alacritty Dark")
        transparent = bool(self.settings.get("transparent", False))
        blur_mode = self.settings.get("blur_mode", "off")
        bg_hex, fg_hex = THEMES.get(theme_name, THEMES["Alacritty Dark"])

        if blur_mode == "static":
            win_bg = "#0D1117"
            win_image = "none"
            tabbar_bg = "alpha(#080B10, 0.32)"
            term_bg = "transparent"
            text_hex = "#F8FAFC"
        elif blur_mode == "smoky":
            win_bg = f"alpha(#2B2936, {SMOKY_ALPHA})"
            win_image = (
                "linear-gradient(135deg, "
                "alpha(#433F52, 0.25) 0%, "
                "alpha(#2B2936, 0.20) 50%, "
                "alpha(#23212C, 0.28) 100%)"
            )
            tabbar_bg = "alpha(#23212C, 0.30)"
            term_bg = "transparent"
            text_hex = "#F8FAFC"
        elif transparent:
            win_bg = f"alpha(#000000, {TRANSLUCENT_ALPHA})"
            win_image = "none"
            tabbar_bg = "transparent"
            term_bg = "transparent"
            text_hex = "#F8FAFC"
        else:
            win_bg = bg_hex
            win_image = "none"
            tabbar_bg = bg_hex
            term_bg = bg_hex
            text_hex = fg_hex

        css = f"""
        window, window.background {{
            background-color: {win_bg};
            background-image: {win_image};
            padding: 0;
            margin: 0;
        }}
        vte-terminal {{
            background-color: {term_bg};
        }}
        scrollbar {{
            background-color: transparent;
        }}
        .tuxixi-static-blur-pic {{
            filter: blur(8px) brightness(0.62) saturate(1.10);
        }}
        .tuxixi-static-blur-fallback {{
            background-image: linear-gradient(135deg, #111827 0%, #1e293b 50%, #0f172a 100%);
        }}
        .tuxixi-tabbar {{
            background-color: {tabbar_bg};
            border-bottom: 1px solid alpha({text_hex}, 0.14);
            padding: 3px 6px;
            min-height: 26px;
        }}
        .tuxixi-tab {{
            background-color: transparent;
            color: alpha({text_hex}, 0.65);
            border-radius: 5px;
            padding: 2px 6px 2px 10px;
            min-height: 22px;
            transition: background-color 120ms ease, color 120ms ease;
        }}
        .tuxixi-tab:hover {{
            background-color: alpha({text_hex}, 0.10);
            color: {text_hex};
        }}
        .tuxixi-tab.active {{
            background-color: alpha({text_hex}, 0.16);
            color: {text_hex};
            font-weight: 600;
        }}
        .tuxixi-tab-title {{
            font-size: 12px;
        }}
        .tuxixi-tab-close {{
            background: transparent;
            border: none;
            box-shadow: none;
            color: alpha({text_hex}, 0.75);
            border-radius: 4px;
            padding: 0;
            margin-left: 4px;
            min-width: 16px;
            min-height: 16px;
            font-size: 12px;
            transition: opacity 120ms ease, background-color 120ms ease, color 120ms ease;
        }}
        .tuxixi-tab-close:hover {{
            background-color: alpha(#f87171, 0.30);
            color: #f87171;
        }}
        .tuxixi-tab-add {{
            background: transparent;
            border: none;
            box-shadow: none;
            color: alpha({text_hex}, 0.70);
            border-radius: 5px;
            padding: 0;
            min-width: 22px;
            min-height: 22px;
            font-size: 14px;
            font-weight: bold;
            transition: background-color 120ms ease, color 120ms ease;
        }}
        .tuxixi-tab-add:hover {{
            background-color: alpha({text_hex}, 0.14);
            color: {text_hex};
        }}
        .tuxixi-blur-badge {{
            font-size: 11px;
            color: alpha({text_hex}, 0.80);
            background-color: alpha({text_hex}, 0.12);
            border-radius: 4px;
            padding: 1px 7px;
            margin-right: 2px;
        }}
        """
        if self.css_provider:
            self.css_provider.load_from_string(css)


if __name__ == "__main__":
    app = TuxixiApplication()
    sys.exit(app.run(sys.argv))
bu düzgün main.py dosyasıdır?
