import os, sys, gi
gi.require_version("Vte", "3.91")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Vte, GLib, Pango, Gdk, Gtk
from themes import get_colors, THEME_NAMES
from settings import save_settings

class TuxixiTerminal:
    def __init__(self, settings, app=None):
        self.settings = settings
        self.app = app
        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(10000)
        self.terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.SYSTEM)
        self.terminal.set_cursor_shape(Vte.CursorShape.BLOCK)
        
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.terminal.add_controller(key_controller)
        
        self.apply_settings()
        self.spawn_shell()

    def paste_clean_text(self):
        display = Gdk.Display.get_default()
        if not display:
            return
        clipboard = display.get_clipboard()
        
        def on_text_read(source, result):
            try:
                text = clipboard.read_text_finish(result)
                if text:
                    clean_text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
                    self.terminal.feed_child(clean_text.encode("utf-8"))
            except Exception:
                pass

        clipboard.read_text_async(None, on_text_read)

    def change_font_size(self, delta):
        current_size = self.settings.get("font_size", 11)
        new_size = max(6, min(48, current_size + delta))
        if new_size != current_size:
            self.settings["font_size"] = new_size
            self.apply_settings()
            save_settings(self.settings)

    def cycle_theme(self):
        current_theme = self.settings.get("theme", "Alacritty Dark")
        try:
            current_index = THEME_NAMES.index(current_theme)
            next_index = (current_index + 1) % len(THEME_NAMES)
        except ValueError:
            next_index = 0
        
        new_theme = THEME_NAMES[next_index]
        self.settings["theme"] = new_theme
        self.apply_settings()
        save_settings(self.settings)

    def on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if ctrl and shift:
            if keyval in (Gdk.KEY_C, Gdk.KEY_c):
                self.terminal.copy_clipboard_format(Vte.Format.TEXT)
                return True
            elif keyval in (Gdk.KEY_V, Gdk.KEY_v):
                self.paste_clean_text()
                return True
            elif keyval in (Gdk.KEY_plus, Gdk.KEY_equal):
                self.change_font_size(1)
                return True
            elif keyval in (Gdk.KEY_minus, Gdk.KEY_underscore):
                self.change_font_size(-1)
                return True
            elif keyval in (Gdk.KEY_T, Gdk.KEY_t):
                self.cycle_theme()
                return True
            elif keyval in (Gdk.KEY_N, Gdk.KEY_n):
                if self.app:
                    from ui import TuxixiWindow
                    new_win = TuxixiWindow(self.app, self.settings.copy())
                    new_win.present()
                return True
        return False

    def apply_settings(self):
        font = self.settings.get("font", "Monospace")
        size = self.settings.get("font_size", 11)
        font_description = Pango.FontDescription.new()
        font_description.set_family(font)
        font_description.set_size(size * Pango.SCALE)
        self.terminal.set_font(font_description)
        bg, fg = get_colors(self.settings.get("theme", "Alacritty Dark"))
        self.terminal.set_color_background(bg)
        self.terminal.set_color_foreground(fg)

    def spawn_shell(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        shell_file = os.path.join(project_dir, "tuxixi_shell.py")
        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT, os.path.expanduser("~"), [sys.executable, shell_file],
            None, GLib.SpawnFlags.DEFAULT, None, None, -1, None, None
        )

    def get_widget(self):
        return self.terminal
