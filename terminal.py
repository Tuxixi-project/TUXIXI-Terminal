import os
import pwd
import stat
import gi

gi.require_version("Vte", "3.91")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Vte, GLib, Gio, GObject, Pango, Gdk, Gtk
from themes import get_colors

MANAGED_BINARIES = ("tuxixi", "ll", "cls")

ALT_NUMBER_KEYS = {
    Gdk.KEY_1: 0,
    Gdk.KEY_2: 1,
    Gdk.KEY_3: 2,
    Gdk.KEY_4: 3,
    Gdk.KEY_5: 4,
    Gdk.KEY_6: 5,
    Gdk.KEY_7: 6,
    Gdk.KEY_8: 7,
    Gdk.KEY_9: 8,
    Gdk.KEY_KP_1: 0,
    Gdk.KEY_KP_2: 1,
    Gdk.KEY_KP_3: 2,
    Gdk.KEY_KP_4: 3,
    Gdk.KEY_KP_5: 4,
    Gdk.KEY_KP_6: 5,
    Gdk.KEY_KP_7: 6,
    Gdk.KEY_KP_8: 7,
    Gdk.KEY_KP_9: 8,
}


class TuxixiTerminal(Gtk.Box):
    __gsignals__ = {
        "request-new-window": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (str,),
        ),
        "request-new-tab": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (),
        ),
        "request-close-tab": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (),
        ),
        "request-switch-tab": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (int,),
        ),
        "request-select-tab-index": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (int,),
        ),
        "title-changed": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (str,),
        ),
        "session-closed": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (int,),
        ),
    }

    def __init__(self, settings_manager, initial_cwd=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.settings = settings_manager
        self.initial_cwd = initial_cwd or os.path.expanduser("~")
        self._banner_proc = None
        self._settings_handler_id = None

        self.vte = Vte.Terminal()
        self.vte.set_hexpand(True)
        self.vte.set_vexpand(True)
        self.vte.set_scrollback_lines(10000)
        self.vte.set_cursor_blink_mode(Vte.CursorBlinkMode.SYSTEM)
        self.vte.set_cursor_shape(Vte.CursorShape.BLOCK)
        self.append(self.vte)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.vte.add_controller(key_controller)

        self.vte.connect("child-exited", self._on_child_exited)
        self.vte.connect("window-title-changed", self._on_vte_title_changed)
        self.vte.connect("current-directory-uri-changed", self._on_vte_title_changed)

        self._settings_handler_id = self.settings.connect(
            "settings-changed", self._on_settings_changed
        )
        self.connect("destroy", self._on_destroy)

        self._apply_font()
        self._apply_theme()
        self._start_session()

    def cleanup(self):
        if self._settings_handler_id is not None:
            if self.settings.handler_is_connected(self._settings_handler_id):
                self.settings.disconnect(self._settings_handler_id)
            self._settings_handler_id = None

    def _on_destroy(self, _widget):
        self.cleanup()

    def grab_terminal_focus(self):
        self.vte.grab_focus()

    def get_current_cwd(self):
        uri = self.vte.get_current_directory_uri()
        if uri:
            try:
                path, _ = GLib.filename_from_uri(uri)
                if path and os.path.isdir(path):
                    return path
            except GLib.Error:
                pass
        return self.initial_cwd

    def get_dynamic_title(self):
        """VTE-nin başlıq və ya cari qovluq məlumatından qısa, oxunaqlı tab adı çıxarır."""
        home = os.path.expanduser("~")
        raw_title = (self.vte.get_window_title() or "").strip()

        if raw_title:
            # 'user@host: ~/Projeler' formatındadırsa yalnız sağ tərəfi götür
            if ":" in raw_title and "@" in raw_title.split(":", 1)[0]:
                raw_title = raw_title.split(":", 1)[1].strip()

            if raw_title.startswith(home):
                raw_title = "~" + raw_title[len(home):]

            if raw_title in ("~", "/"):
                return raw_title

            # Əgər yol şəklindədirsə ('~/Projeler/tuxixi'), yalnız son qovluq adını götür
            if "/" in raw_title and not raw_title.startswith("-"):
                base = os.path.basename(raw_title.rstrip("/"))
                if base:
                    return base
            return raw_title

        # Əgər window-title yoxdursa, cari qovluq URI-sindən (OSC 7) adı çıxar
        cwd = self.get_current_cwd()
        if cwd:
            if os.path.normpath(cwd) == os.path.normpath(home):
                return "~"
            base = os.path.basename(cwd.rstrip("/"))
            return base or "/"

        return "Terminal"

    def _on_vte_title_changed(self, _vte):
        self.emit("title-changed", self.get_dynamic_title())

    def _on_settings_changed(self, _settings, key, _value):
        if key in ("font", "font_size"):
            self._apply_font()
        elif key in ("theme", "transparent", "blur_mode"):
            self._apply_theme()

    def _apply_font(self):
        font = self.settings.get("font", "Monospace")
        size = self.settings.get("font_size", 11)
        description = Pango.FontDescription.new()
        description.set_family(font)
        description.set_size(size * Pango.SCALE)
        self.vte.set_font(description)

    def _apply_theme(self):
        theme_name = self.settings.get("theme", "Alacritty Dark")
        transparent = bool(self.settings.get("transparent", False))
        blur_mode = self.settings.get("blur_mode", "off")
        is_glass = transparent or blur_mode in ("static", "smoky")

        bg, fg = get_colors(theme_name, transparent=transparent, blur_mode=blur_mode)

        if hasattr(self.vte, "set_clear_background"):
            self.vte.set_clear_background(not is_glass)

        self.vte.set_color_background(bg)
        self.vte.set_color_foreground(fg)

    def _get_default_shell(self):
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

    def _get_shell_argv(self, shell):
        shell_name = os.path.basename(shell)
        if shell_name == "fish":
            return [shell, "-l"]
        if shell_name == "zsh":
            return [shell, "-l", "-i"]
        if shell_name == "bash":
            return [shell, "--login", "-i"]
        return [shell, "-i"]

    def _ensure_user_exec_if_needed(self, path):
        if os.access(path, os.X_OK):
            return
        try:
            st = os.stat(path)
            if st.st_uid == os.getuid():
                os.chmod(path, st.st_mode | stat.S_IXUSR)
        except OSError:
            pass

    def _check_managed_binaries(self, bin_dir):
        if not os.path.isdir(bin_dir):
            return
        self._ensure_user_exec_if_needed(bin_dir)
        for name in MANAGED_BINARIES:
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                self._ensure_user_exec_if_needed(path)

    def _start_session(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(project_dir, "bin")
        self._check_managed_binaries(bin_dir)

        tuxixi_bin = os.path.join(bin_dir, "tuxixi")
        if not (os.path.isfile(tuxixi_bin) and os.access(tuxixi_bin, os.X_OK)):
            self._spawn_shell_pty(bin_dir)
            return

        try:
            self._banner_proc = Gio.Subprocess.new(
                [tuxixi_bin, "--welcome"],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE,
            )
            self._banner_proc.communicate_utf8_async(
                None, None, self._on_banner_ready, bin_dir
            )
        except GLib.Error:
            self._banner_proc = None
            self._spawn_shell_pty(bin_dir)

    def _on_banner_ready(self, proc, result, bin_dir):
        try:
            ok, stdout, _ = proc.communicate_utf8_finish(result)
            if ok and stdout:
                formatted = stdout.replace("\n", "\r\n").encode("utf-8")
                self.vte.feed(formatted)
        except GLib.Error:
            pass
        finally:
            self._banner_proc = None
            self._spawn_shell_pty(bin_dir)

    def _spawn_shell_pty(self, bin_dir):
        shell = self._get_default_shell()
        argv = self._get_shell_argv(shell)

        env = os.environ.copy()
        env["TUXIXI_SESSION"] = "1"
        env["TUXIXI_BIN_DIR"] = bin_dir

        raw_paths = env.get("PATH", "").split(os.pathsep)
        paths = []
        for p in raw_paths:
            if p and p not in paths:
                paths.append(p)
        if os.path.isdir(bin_dir) and bin_dir not in paths:
            paths.append(bin_dir)
        env["PATH"] = os.pathsep.join(paths)

        cwd = (
            self.initial_cwd
            if os.path.isdir(self.initial_cwd)
            else os.path.expanduser("~")
        )

        def on_spawn_complete(_terminal, _pid, error, _user_data=None):
            if error:
                print(f"Error: Shell did not work. - {error.message}")

        self.vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            argv,
            [f"{key}={value}" for key, value in env.items()],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            on_spawn_complete,
            None,
        )

    def _on_child_exited(self, _terminal, status):
        self.emit("session-closed", status)

    def _on_key_pressed(self, _controller, keyval, _keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        alt = bool(state & Gdk.ModifierType.ALT_MASK)

        if alt and not ctrl and not shift and keyval in ALT_NUMBER_KEYS:
            self.emit("request-select-tab-index", ALT_NUMBER_KEYS[keyval])
            return True

        if not ctrl:
            return False

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_KP_Tab):
            self.emit("request-switch-tab", -1 if shift else 1)
            return True
        if not shift and keyval == Gdk.KEY_Page_Down:
            self.emit("request-switch-tab", 1)
            return True
        if not shift and keyval == Gdk.KEY_Page_Up:
            self.emit("request-switch-tab", -1)
            return True

        if not shift:
            return False

        if keyval in (Gdk.KEY_C, Gdk.KEY_c):
            self.vte.copy_clipboard()
            return True
        if keyval in (Gdk.KEY_V, Gdk.KEY_v):
            self.vte.paste_clipboard()
            return True
        if keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.settings.change_font_size(1)
            return True
        if keyval in (Gdk.KEY_minus, Gdk.KEY_underscore, Gdk.KEY_KP_Subtract):
            self.settings.change_font_size(-1)
            return True
        if keyval in (Gdk.KEY_T, Gdk.KEY_t):
            self.settings.cycle_theme()
            return True
        if keyval in (Gdk.KEY_O, Gdk.KEY_o):
            self.settings.toggle_transparency()
            return True
        if keyval in (Gdk.KEY_B, Gdk.KEY_b):
            self.settings.cycle_blur_mode()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.emit("request-new-tab")
            return True
        if keyval in (Gdk.KEY_W, Gdk.KEY_w):
            self.emit("request-close-tab")
            return True
        if keyval in (Gdk.KEY_N, Gdk.KEY_n):
            self.emit("request-new-window", self.get_current_cwd())
            return True
        return False
