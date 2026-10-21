import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk
from terminal import TuxixiTerminal


class TuxixiWindow(Gtk.ApplicationWindow):
    def __init__(self, app, settings):
        super().__init__(
            application=app,
            title="TUXIXI",
            default_width=700,
            default_height=450,
        )
        self.app = app
        self.settings = settings

        terminal_object = TuxixiTerminal(self.settings, self.app)
        widget = terminal_object.get_widget()

        widget.set_margin_start(0)
        widget.set_margin_end(0)
        widget.set_margin_top(0)
        widget.set_margin_bottom(0)

        self.set_child(widget)
        self.load_css()

    def load_css(self):
        css = (
            "window { background-color: #1E1E1E; padding: 0; margin: 0; }"
            "scrollbar { background-color: #1E1E1E; }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
