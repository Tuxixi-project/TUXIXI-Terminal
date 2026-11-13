import os
import pwd
import subprocess
import gi

gi.require_version("Vte", "3.91")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Vte, GLib, Pango, Gdk, Gtk
from themes import get_colors, THEME_NAMES
from settings import save_settings


class TuxixiTerminal:
    def __init__(self, settings, app=None, on_theme_change=None):
        self.settings = settings
        self.app = app
        self.on_theme_change = on_theme_change
        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(10000)
        self.terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.SYSTEM)
        self.terminal.set_cursor_shape(Vte.CursorShape.BLOCK)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.terminal.add_controller(key_controller)
        self.terminal.connect("child-exited", self.on_child_exited)

        self.apply_settings()
        self.spawn_shell()

    def get_default_shell(self):
        try:
            shell = pwd.getpwuid(os.getuid()).pw_shell
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        except (KeyError, OSError):
            pass

        shell = os.environ.get("SHELL", "/bin/sh")
        if os.path.isfile(shell) and os.access(shell, os.X_OK):
            return shell
        return "/bin/sh"

    def get_shell_argv(self, shell):
        shell_name = os.path.basename(shell)
        if shell_name == "fish":
            return [shell, "-l"]
        if shell_name == "zsh":
            return [shell, "-l", "-i"]
        if shell_name == "bash":
            return [shell, "--login", "-i"]
        return [shell, "-i"]

    def show_welcome_help(self, bin_dir):
        tuxixi_bin = os.path.join(bin_dir, "tuxixi")
        try:
            output = subprocess.check_output([tuxixi_bin, "help"])
            formatted = output.replace(b"\n", b"\r\n")
            self.terminal.feed(formatted)
        except Exception:
            pass

    def spawn_shell(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(project_dir, "bin")
        shell = self.get_default_shell()
        argv = self.get_shell_argv(shell)

        self.show_welcome_help(bin_dir)

        env = os.environ.copy()
        env["TUXIXI_SESSION"] = "1"
        env["TUXIXI_BIN_DIR"] = bin_dir

        paths = [p for p in env.get("PATH", "").split(os.pathsep) if p]
        if bin_dir not in paths:
            env["PATH"] = os.pathsep.join(paths + [bin_dir])

        def on_spawn_complete(terminal, pid, error, user_data=None):
            if error:
                print(f"Error: Shell did not work. - {error.message}")

        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.path.expanduser("~"),
            argv,
            [f"{key}={value}" for key, value in env.items()],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            on_spawn_complete,
            None
        )

    def on_child_exited(self, terminal, status):
        window = terminal.get_ancestor(Gtk.Window)
        if window:
            window.close()

    def change_font_size(self, delta):
        current = self.settings.get("font_size", 11)
        new_size = max(6, min(48, current + delta))
        if new_size == current:
            return
        self.settings["font_size"] = new_size
        self.apply_settings()
        save_settings(self.settings)

    def cycle_theme(self):
        current = self.settings.get("theme", "Alacritty Dark")
        try:
            index = THEME_NAMES.index(current)
            next_index = (index + 1) % len(THEME_NAMES)
        except ValueError:
            next_index = 0
        new_theme = THEME_NAMES[next_index]
        self.settings["theme"] = new_theme
        self.apply_settings()
        save_settings(self.settings)
        if self.on_theme_change:
            self.on_theme_change(new_theme)

    def apply_settings(self):
        font = self.settings.get("font", "Monospace")
        size = self.settings.get("font_size", 11)
        description = Pango.FontDescription.new()
        description.set_family(font)
        description.set_size(size * Pango.SCALE)
        self.terminal.set_font(description)

        bg, fg = get_colors(self.settings.get("theme", "Alacritty Dark"))
        self.terminal.set_color_background(bg)
        self.terminal.set_color_foreground(fg)

    def on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if not (ctrl and shift):
            return False

        if keyval in (Gdk.KEY_C, Gdk.KEY_c):
            self.terminal.copy_clipboard()
            return True
        if keyval in (Gdk.KEY_V, Gdk.KEY_v):
            self.terminal.paste_clipboard()
            return True
        if keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.change_font_size(1)
            return True
        if keyval in (Gdk.KEY_minus, Gdk.KEY_underscore, Gdk.KEY_KP_Subtract):
            self.change_font_size(-1)
            return True
        if keyval in (Gdk.KEY_T, Gdk.KEY_t):
            self.cycle_theme()
            return True
        if keyval in (Gdk.KEY_N, Gdk.KEY_n):
            if self.app:
                from ui import TuxixiWindow
                window = TuxixiWindow(self.app, self.settings)
                window.present()
            return True
        return False

    def get_widget(self):
        return self.terminal
