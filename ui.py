import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk
from terminal import TuxixiTerminal
from themes import THEMES


class TuxixiWindow(Gtk.ApplicationWindow):
    _css_provider = None

    def __init__(self, app, settings):
        super().__init__(
            application=app,
            title="TUXIXI",
            default_width=700,
            default_height=450,
        )
        self.app = app
        self.settings = settings

        if TuxixiWindow._css_provider is None:
            TuxixiWindow._css_provider = Gtk.CssProvider()
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    TuxixiWindow._css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )

        self.terminal_object = TuxixiTerminal(
            self.settings,
            self.app,
            on_theme_change=self.update_css,
        )
        widget = self.terminal_object.get_widget()

        widget.set_margin_start(0)
        widget.set_margin_end(0)
        widget.set_margin_top(0)
        widget.set_margin_bottom(0)
        self.set_child(widget)

        self.update_css(self.settings.get("theme", "Alacritty Dark"))

    def update_css(self, theme_name):
        bg_hex, _ = THEMES.get(theme_name, THEMES["Alacritty Dark"])
        css = (
            f"window {{ background-color: {bg_hex}; padding: 0; margin: 0; }}"
            f"scrollbar {{ background-color: {bg_hex}; }}"
        )
        if TuxixiWindow._css_provider:
            TuxixiWindow._css_provider.load_from_string(css)