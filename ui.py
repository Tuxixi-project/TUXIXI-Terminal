import os
import threading
import time
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango
from settings import APP_VERSION
from terminal import TuxixiTerminal
from themes import (
    THEMES,
    THEME_NAMES,
    detect_wallpaper_path,
    save_custom_theme,
    delete_custom_theme,
    is_custom_theme,
)


def _rgba_to_hex(rgba):
    r = max(0, min(255, int(round(rgba.red * 255))))
    g = max(0, min(255, int(round(rgba.green * 255))))
    b = max(0, min(255, int(round(rgba.blue * 255))))
    return f"#{r:02X}{g:02X}{b:02X}"


class ThemeStudioDialog(Gtk.Window):
    """GTK 4 Vizual Tema Seçici və Yaradıcı (Ctrl+Shift+P və ya '◈' düyməsi)."""

    def __init__(self, parent_window, settings_manager):
        super().__init__(
            title="TUXIXI Theme Studio",
            transient_for=parent_window,
            modal=False,
            resizable=False,
            default_width=380,
        )
        self.add_css_class("tuxixi-studio")
        self.settings = settings_manager
        self._preview_css = Gtk.CssProvider()
        self._syncing = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(14)
        box.set_margin_bottom(16)
        self.set_child(box)

        # 1. Mövcud Temalardan Seçim
        select_label = Gtk.Label(label="Select Theme", xalign=0)
        select_label.add_css_class("tuxixi-studio-heading")
        box.append(select_label)

        self.theme_dropdown = Gtk.DropDown.new_from_strings(THEME_NAMES)
        self.theme_dropdown.connect("notify::selected", self._on_dropdown_changed)
        box.append(self.theme_dropdown)

        # 2. Yeni / Fərdi Tema Yaratma
        create_label = Gtk.Label(label="Create / Edit Custom Theme", xalign=0)
        create_label.add_css_class("tuxixi-studio-heading")
        create_label.set_margin_top(4)
        box.append(create_label)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Theme name (e.g. My Neon)")
        box.append(self.name_entry)

        # Rəng Seçicilər (Background & Text)
        colors_grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        colors_grid.set_hexpand(True)

        bg_lbl = Gtk.Label(label="Background:", xalign=0)
        self.bg_hex_lbl = Gtk.Label(label="#1D1F21", xalign=1)
        self.bg_hex_lbl.add_css_class("tuxixi-studio-hex")
        self.bg_btn = self._make_color_button("#1D1F21", self._on_color_picked)

        fg_lbl = Gtk.Label(label="Text Color:", xalign=0)
        self.fg_hex_lbl = Gtk.Label(label="#C5C8C6", xalign=1)
        self.fg_hex_lbl.add_css_class("tuxixi-studio-hex")
        self.fg_btn = self._make_color_button("#C5C8C6", self._on_color_picked)

        colors_grid.attach(bg_lbl, 0, 0, 1, 1)
        colors_grid.attach(self.bg_hex_lbl, 1, 0, 1, 1)
        colors_grid.attach(self.bg_btn, 2, 0, 1, 1)

        colors_grid.attach(fg_lbl, 0, 1, 1, 1)
        colors_grid.attach(self.fg_hex_lbl, 1, 1, 1, 1)
        colors_grid.attach(self.fg_btn, 2, 1, 1, 1)

        self.bg_hex_lbl.set_hexpand(True)
        self.fg_hex_lbl.set_hexpand(True)
        box.append(colors_grid)

        # 3. Canlı Önizləmə Qutusu
        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.preview_box.add_css_class("tuxixi-studio-preview")
        self.preview_box.get_style_context().add_provider(
            self._preview_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )
        preview_line1 = Gtk.Label(label=f"◆ TUXIXI Terminal v{APP_VERSION}", xalign=0)
        preview_line2 = Gtk.Label(label="~ ❯ echo 'Hello from custom theme!'", xalign=0)
        self.preview_box.append(preview_line1)
        self.preview_box.append(preview_line2)
        box.append(self.preview_box)

        # 4. Düymələr (Delete / Save & Apply)
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.END)

        self.delete_btn = Gtk.Button(label="Delete")
        self.delete_btn.add_css_class("tuxixi-studio-delete")
        self.delete_btn.connect("clicked", self._on_delete_clicked)
        btn_row.append(self.delete_btn)

        self.save_btn = Gtk.Button(label="Save & Apply")
        self.save_btn.add_css_class("tuxixi-studio-save")
        self.save_btn.connect("clicked", self._on_save_clicked)
        btn_row.append(self.save_btn)

        box.append(btn_row)

        self.status_lbl = Gtk.Label(label="", xalign=0)
        self.status_lbl.add_css_class("tuxixi-studio-status")
        box.append(self.status_lbl)

        self._load_current_theme()

    def _make_color_button(self, initial_hex, callback):
        rgba = Gdk.RGBA()
        rgba.parse(initial_hex)
        if hasattr(Gtk, "ColorDialogButton") and hasattr(Gtk, "ColorDialog"):
            dialog = Gtk.ColorDialog()
            btn = Gtk.ColorDialogButton(dialog=dialog)
            btn.set_rgba(rgba)
            btn.connect("notify::rgba", lambda _b, _p: callback())
            return btn
        btn = Gtk.ColorButton.new_with_rgba(rgba)
        btn.connect("color-set", lambda _b: callback())
        return btn

    def _get_button_hex(self, btn):
        return _rgba_to_hex(btn.get_rgba())

    def _set_button_hex(self, btn, hex_color):
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        btn.set_rgba(rgba)

    def _load_current_theme(self):
        current = self.settings.get("theme", "Alacritty Dark")
        self._syncing = True
        try:
            idx = THEME_NAMES.index(current)
        except ValueError:
            idx = 0
        self.theme_dropdown.set_selected(idx)
        self._sync_inputs_from_theme(THEME_NAMES[idx])
        self._syncing = False

    def _sync_inputs_from_theme(self, theme_name):
        bg_hex, fg_hex = THEMES.get(theme_name, ("#1D1F21", "#C5C8C6"))
        custom = is_custom_theme(theme_name)
        self._set_button_hex(self.bg_btn, bg_hex)
        self._set_button_hex(self.fg_btn, fg_hex)
        self.name_entry.set_text(theme_name if custom else "")
        self.delete_btn.set_sensitive(custom)
        self._update_preview(bg_hex, fg_hex)

    def _update_preview(self, bg_hex, fg_hex):
        self.bg_hex_lbl.set_text(bg_hex)
        self.fg_hex_lbl.set_text(fg_hex)
        css = (
            f".tuxixi-studio-preview {{"
            f"  background-color: {bg_hex};"
            f"  color: {fg_hex};"
            f"  border-radius: 6px;"
            f"  padding: 10px 12px;"
            f"  font-family: Monospace;"
            f"  font-size: 12px;"
            f"  border: 1px solid alpha({fg_hex}, 0.25);"
            f"}}"
        )
        self._preview_css.load_from_string(css)

    def _on_dropdown_changed(self, dropdown, _pspec):
        if self._syncing:
            return
        idx = dropdown.get_selected()
        if 0 <= idx < len(THEME_NAMES):
            theme_name = THEME_NAMES[idx]
            self._syncing = True
            self._sync_inputs_from_theme(theme_name)
            self._syncing = False
            self.settings.set("theme", theme_name)
            self.status_lbl.set_text(f"Applied: {theme_name}")

    def _on_color_picked(self):
        if self._syncing:
            return
        bg_hex = self._get_button_hex(self.bg_btn)
        fg_hex = self._get_button_hex(self.fg_btn)
        self._update_preview(bg_hex, fg_hex)

    def _refresh_dropdown(self, select_name):
        self._syncing = True
        self.theme_dropdown.set_model(Gtk.StringList.new(THEME_NAMES))
        try:
            idx = THEME_NAMES.index(select_name)
        except ValueError:
            idx = 0
        self.theme_dropdown.set_selected(idx)
        self.delete_btn.set_sensitive(is_custom_theme(THEME_NAMES[idx]))
        self._syncing = False

    def _on_save_clicked(self, _btn):
        name = self.name_entry.get_text().strip()
        if not name:
            self.status_lbl.set_text("Please enter a theme name first.")
            self.name_entry.grab_focus()
            return

        bg_hex = self._get_button_hex(self.bg_btn)
        fg_hex = self._get_button_hex(self.fg_btn)

        if save_custom_theme(name, bg_hex, fg_hex):
            self._refresh_dropdown(name)
            self.settings.set("theme", name, force=True)
            self.status_lbl.set_text(f"Saved & applied: {name}")
        else:
            self.status_lbl.set_text("Could not save theme.")

    def _on_delete_clicked(self, _btn):
        idx = self.theme_dropdown.get_selected()
        if not (0 <= idx < len(THEME_NAMES)):
            return
        name = THEME_NAMES[idx]
        if delete_custom_theme(name):
            fallback = "Alacritty Dark"
            self._refresh_dropdown(fallback)
            self._sync_inputs_from_theme(fallback)
            self.settings.set("theme", fallback)
            self.status_lbl.set_text(f"Deleted custom theme: {name}")


class TuxixiTabItem(Gtk.Box):
    def __init__(self, title, on_select, on_close):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.add_css_class("tuxixi-tab")
        self._on_select = on_select
        self._on_close = on_close

        self.label = Gtk.Label(label=title)
        self.label.add_css_class("tuxixi-tab-title")
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_max_width_chars(20)
        self.append(self.label)

        self.close_btn = Gtk.Button(label="×")
        self.close_btn.add_css_class("tuxixi-tab-close")
        self.close_btn.set_can_focus(False)
        self.close_btn.set_opacity(0.0)
        self.close_btn.connect("clicked", self._on_close_clicked)
        self.append(self.close_btn)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_enter)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_pressed)
        self.add_controller(click)

    def detach(self):
        self._on_select = None
        self._on_close = None

    def _on_close_clicked(self, _btn):
        if self._on_close:
            self._on_close()

    def set_title(self, title, tooltip=None):
        self.label.set_text(title)
        self.set_tooltip_text(tooltip or title)

    def _on_enter(self, _controller, _x, _y):
        self.close_btn.set_opacity(1.0)

    def _on_leave(self, _controller):
        self.close_btn.set_opacity(0.0)

    def _on_pressed(self, gesture, _n_press, x, y):
        button = gesture.get_current_button()
        if button == 2:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            if self._on_close:
                self._on_close()
            return
        if button == 1:
            ok, bounds = self.close_btn.compute_bounds(self)
            if (
                ok
                and bounds.origin.x <= x <= bounds.origin.x + bounds.size.width
                and bounds.origin.y <= y <= bounds.origin.y + bounds.size.height
            ):
                return
            if self._on_select:
                self._on_select()

    def set_active(self, active):
        if active:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")


class TuxixiPaneContainer(Gtk.Box):
    """Hər tab daxilində tək terminal və ya rekursiv Gtk.Paned split ağacını idarə edir."""

    def __init__(
        self,
        settings_manager,
        initial_cwd=None,
        on_terminal_created=None,
        on_state_changed=None,
        on_empty=None,
        terminal_factory=None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.settings = settings_manager
        self._on_terminal_created = on_terminal_created
        self._on_state_changed = on_state_changed
        self._on_empty = on_empty
        self._terminal_factory = terminal_factory or (
            lambda mgr, cwd: TuxixiTerminal(settings_manager=mgr, initial_cwd=cwd)
        )

        self._panes = []
        self._active_pane = None
        self._root_widget = None

        first_pane = self._create_pane(cwd=initial_cwd)
        self._root_widget = first_pane
        self.append(first_pane)
        self.set_active_pane(first_pane, grab_focus=False)

    @property
    def active_pane(self):
        return self._active_pane

    @property
    def panes(self):
        return list(self._panes)

    @property
    def pane_count(self):
        return len(self._panes)

    def _create_pane(self, cwd=None):
        pane = self._terminal_factory(self.settings, cwd)
        pane.set_hexpand(True)
        pane.set_vexpand(True)
        self._panes.append(pane)
        if self._on_terminal_created:
            self._on_terminal_created(self, pane)
        return pane

    def _update_pane_styles(self):
        multi = len(self._panes) > 1
        for pane in self._panes:
            if not multi:
                pane.remove_css_class("tuxixi-pane-active")
                pane.remove_css_class("tuxixi-pane-inactive")
            elif pane is self._active_pane:
                pane.add_css_class("tuxixi-pane-active")
                pane.remove_css_class("tuxixi-pane-inactive")
            else:
                pane.remove_css_class("tuxixi-pane-active")
                pane.add_css_class("tuxixi-pane-inactive")

    def set_active_pane(self, pane, grab_focus=True):
        if pane not in self._panes:
            return
        self._active_pane = pane
        self._update_pane_styles()
        if grab_focus:
            pane.grab_terminal_focus()
        if self._on_state_changed:
            self._on_state_changed(self)

    def grab_active_focus(self):
        if self._active_pane is not None:
            self._active_pane.grab_terminal_focus()

    def split_pane(self, target_pane=None, direction="horizontal"):
        """Aktiv (və ya seçilmiş) paneli horizontal (sol/sağ) və ya vertical (yuxarı/aşağı) bölür."""
        target = target_pane or self._active_pane
        if target is None or target not in self._panes:
            return None

        orientation = (
            Gtk.Orientation.VERTICAL
            if direction == "vertical"
            else Gtk.Orientation.HORIZONTAL
        )
        parent = target.get_parent()
        if parent is None:
            return None

        alloc_size = (
            target.get_height()
            if orientation == Gtk.Orientation.VERTICAL
            else target.get_width()
        )
        new_pane = self._create_pane(cwd=target.get_current_cwd())

        paned = Gtk.Paned(orientation=orientation)
        paned.set_hexpand(True)
        paned.set_vexpand(True)
        paned.set_wide_handle(False)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(True)
        paned.set_shrink_end_child(True)

        if parent is self:
            self.remove(target)
            paned.set_start_child(target)
            paned.set_end_child(new_pane)
            self.append(paned)
            self._root_widget = paned
        elif isinstance(parent, Gtk.Paned):
            old_pos = parent.get_position()
            was_start = parent.get_start_child() is target
            if was_start:
                parent.set_start_child(None)
            else:
                parent.set_end_child(None)

            paned.set_start_child(target)
            paned.set_end_child(new_pane)

            if was_start:
                parent.set_start_child(paned)
            else:
                parent.set_end_child(paned)
            if old_pos > 0:
                parent.set_position(old_pos)
        else:
            self._panes.remove(new_pane)
            new_pane.cleanup()
            return None

        if alloc_size > 1:
            paned.set_position(alloc_size // 2)
        else:
            def _apply_half_position():
                size = (
                    paned.get_height()
                    if orientation == Gtk.Orientation.VERTICAL
                    else paned.get_width()
                )
                if size > 1:
                    paned.set_position(size // 2)
                return False

            GLib.idle_add(_apply_half_position)

        self.set_active_pane(new_pane, grab_focus=True)
        GLib.idle_add(self._ensure_pane_focus, new_pane)
        return new_pane

    def _ensure_pane_focus(self, pane):
        if pane is self._active_pane and pane in self._panes:
            pane.grab_terminal_focus()
        return False

    def _find_leaf(self, widget, prefer_end=False):
        node = widget
        while isinstance(node, Gtk.Paned):
            first = node.get_end_child() if prefer_end else node.get_start_child()
            second = node.get_start_child() if prefer_end else node.get_end_child()
            node = first or second
        return node if node in self._panes else None

    def close_pane(self, target_pane=None):
        """Paneli bağlayır. Tabda heç bir panel qalmadıqda True qaytarır."""
        target = target_pane or self._active_pane
        if target is None or target not in self._panes:
            return False

        was_active = target is self._active_pane
        self._panes.remove(target)
        parent = target.get_parent()
        target.cleanup()

        if not self._panes:
            if parent is self:
                self.remove(target)
            self._root_widget = None
            self._active_pane = None
            if self._on_empty:
                self._on_empty(self)
            return True

        next_pane = None
        if isinstance(parent, Gtk.Paned):
            sibling = (
                parent.get_end_child()
                if parent.get_start_child() is target
                else parent.get_start_child()
            )
            parent.set_start_child(None)
            parent.set_end_child(None)

            grandparent = parent.get_parent()
            if grandparent is self:
                self.remove(parent)
                if sibling is not None:
                    self.append(sibling)
                self._root_widget = sibling
            elif isinstance(grandparent, Gtk.Paned):
                gp_pos = grandparent.get_position()
                was_start = grandparent.get_start_child() is parent
                if was_start:
                    grandparent.set_start_child(None)
                    grandparent.set_start_child(sibling)
                else:
                    grandparent.set_end_child(None)
                    grandparent.set_end_child(sibling)
                if gp_pos > 0:
                    grandparent.set_position(gp_pos)

            if sibling is not None:
                next_pane = self._find_leaf(sibling, prefer_end=False)

        if was_active or self._active_pane not in self._panes:
            if next_pane is None:
                next_pane = self._panes[-1]
            self.set_active_pane(next_pane, grab_focus=True)
            GLib.idle_add(self._ensure_pane_focus, next_pane)
        else:
            self._update_pane_styles()
            if self._on_state_changed:
                self._on_state_changed(self)
        return False

    def focus_direction(self, direction):
        """Aktiv paneldən göstərilən istiqamətdəki qonşu panelə fokus keçirir."""
        if len(self._panes) <= 1 or self._active_pane is None:
            return False

        target = self._find_neighbor_by_geometry(direction)
        if target is None:
            target = self._find_neighbor_by_tree(direction)

        if target is not None and target is not self._active_pane:
            self.set_active_pane(target, grab_focus=True)
            return True
        return False

    def _find_neighbor_by_geometry(self, direction):
        ok, active_rect = self._active_pane.compute_bounds(self)
        if not ok or active_rect.size.width <= 0 or active_rect.size.height <= 0:
            return None

        ax1 = active_rect.origin.x
        ay1 = active_rect.origin.y
        ax2 = ax1 + active_rect.size.width
        ay2 = ay1 + active_rect.size.height
        acx = (ax1 + ax2) / 2.0
        acy = (ay1 + ay2) / 2.0

        best = None
        best_score = None
        tol = 8.0

        for candidate in self._panes:
            if candidate is self._active_pane:
                continue
            c_ok, rect = candidate.compute_bounds(self)
            if not c_ok or rect.size.width <= 0 or rect.size.height <= 0:
                continue

            bx1 = rect.origin.x
            by1 = rect.origin.y
            bx2 = bx1 + rect.size.width
            by2 = by1 + rect.size.height
            bcx = (bx1 + bx2) / 2.0
            bcy = (by1 + by2) / 2.0

            if direction == "right":
                if not (bcx > acx and bx1 >= ax2 - tol):
                    continue
                primary = max(0.0, bx1 - ax2)
                secondary = 0.0 if (by1 <= acy <= by2) else abs(bcy - acy)
            elif direction == "left":
                if not (bcx < acx and bx2 <= ax1 + tol):
                    continue
                primary = max(0.0, ax1 - bx2)
                secondary = 0.0 if (by1 <= acy <= by2) else abs(bcy - acy)
            elif direction == "down":
                if not (bcy > acy and by1 >= ay2 - tol):
                    continue
                primary = max(0.0, by1 - ay2)
                secondary = 0.0 if (bx1 <= acx <= bx2) else abs(bcx - acx)
            elif direction == "up":
                if not (bcy < acy and by2 <= ay1 + tol):
                    continue
                primary = max(0.0, ay1 - by2)
                secondary = 0.0 if (bx1 <= acx <= bx2) else abs(bcx - acx)
            else:
                return None

            score = (primary, secondary)
            if best_score is None or score < best_score:
                best_score = score
                best = candidate

        return best

    def _find_neighbor_by_tree(self, direction):
        want_orientation = (
            Gtk.Orientation.HORIZONTAL
            if direction in ("left", "right")
            else Gtk.Orientation.VERTICAL
        )
        want_end_branch = direction in ("right", "down")

        node = self._active_pane
        while node is not None and node is not self:
            parent = node.get_parent()
            if isinstance(parent, Gtk.Paned) and parent.get_orientation() == want_orientation:
                if want_end_branch and parent.get_start_child() is node:
                    sibling = parent.get_end_child()
                    return self._find_leaf(sibling, prefer_end=False)
                if not want_end_branch and parent.get_end_child() is node:
                    sibling = parent.get_start_child()
                    return self._find_leaf(sibling, prefer_end=True)
            node = parent
        return None

    def cleanup(self):
        self._on_terminal_created = None
        self._on_state_changed = None
        self._on_empty = None
        for pane in list(self._panes):
            pane.cleanup()
        self._panes.clear()
        self._active_pane = None
        self._root_widget = None


class TuxixiWindow(Gtk.ApplicationWindow):
    def __init__(self, app, settings_manager, cwd=None):
        super().__init__(
            application=app,
            title="TUXIXI",
            default_width=700,
            default_height=450,
        )
        self.app = app
        self.settings = settings_manager
        self._tabs = []
        self._uid_seq = 0
        self._settings_handler_id = None
        self._studio_dialog = None
        self._is_closed = False
        self._wallpaper_pic = None
        self._current_wallpaper_sig = None
        self._wallpaper_initialized = False
        self._wallpaper_loading = False
        self._last_wallpaper_check = 0.0
        self.add_css_class("tuxixi-main-window")

        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.static_bg_container = Gtk.Box()
        self.static_bg_container.set_hexpand(True)
        self.static_bg_container.set_vexpand(True)
        self.static_bg_container.set_can_target(False)
        self.static_bg_container.set_visible(False)
        self.static_bg_container.add_css_class("tuxixi-static-blur-fallback")
        self.overlay.set_child(self.static_bg_container)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root_box.set_hexpand(True)
        root_box.set_vexpand(True)
        self.overlay.add_overlay(root_box)

        self.tabbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.tabbar.add_css_class("tuxixi-tabbar")

        self.tabs_scroller = Gtk.ScrolledWindow()
        self.tabs_scroller.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        self.tabs_scroller.set_hexpand(True)
        self.tabs_scroller.set_propagate_natural_width(False)

        self.tabs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.tabs_scroller.set_child(self.tabs_box)

        scroll_ctrl = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll_ctrl.connect("scroll", self._on_tabbar_scroll)
        self.tabs_scroller.add_controller(scroll_ctrl)

        self.tabbar.append(self.tabs_scroller)

        self.add_tab_btn = Gtk.Button(label="+")
        self.add_tab_btn.add_css_class("tuxixi-tab-add")
        self.add_tab_btn.set_can_focus(False)
        self.add_tab_btn.set_tooltip_text("New Tab (Ctrl+Shift+Enter)")
        self.add_tab_btn.connect("clicked", self._on_add_tab_clicked)
        self.tabbar.append(self.add_tab_btn)

        # Split Panel düyməsi (◫ — Sol klik: yan-yana, Sağ klik: alt-üst)
        self.split_btn = Gtk.Button(label="◫")
        self.split_btn.add_css_class("tuxixi-tab-add")
        self.split_btn.set_can_focus(False)
        self.split_btn.set_tooltip_text(
            "Split Right (Ctrl+Shift+D) · Right-click: Split Down (Ctrl+Shift+E)"
        )
        self.split_btn.connect("clicked", self._on_split_btn_clicked)
        split_rclick = Gtk.GestureClick()
        split_rclick.set_button(3)
        split_rclick.connect("pressed", self._on_split_btn_right_clicked)
        self.split_btn.add_controller(split_rclick)
        self.tabbar.append(self.split_btn)

        # Vizual Tema Studiyası düyməsi (◈)
        self.theme_studio_btn = Gtk.Button(label="◈")
        self.theme_studio_btn.add_css_class("tuxixi-tab-add")
        self.theme_studio_btn.set_can_focus(False)
        self.theme_studio_btn.set_tooltip_text("Theme Studio (Ctrl+Shift+P)")
        self.theme_studio_btn.connect("clicked", lambda _b: self.open_theme_studio())
        self.tabbar.append(self.theme_studio_btn)

        self.blur_badge = Gtk.Label(label="")
        self.blur_badge.add_css_class("tuxixi-blur-badge")
        self.blur_badge.set_visible(False)
        self.tabbar.append(self.blur_badge)

        root_box.append(self.tabbar)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        root_box.append(self.stack)

        self._settings_handler_id = self.settings.connect(
            "settings-changed", self._on_settings_changed
        )
        self.connect("notify::is-active", self._on_window_active_changed)
        self.connect("close-request", self._on_close_request)

        self.add_tab(cwd=cwd)
        self._apply_blur_state()

    def open_theme_studio(self):
        if self._studio_dialog is not None:
            self._studio_dialog.present()
            return
        self._studio_dialog = ThemeStudioDialog(self, self.settings)
        self._studio_dialog.connect("close-request", self._on_studio_closed)
        self._studio_dialog.present()

    def _on_studio_closed(self, _dialog):
        self._studio_dialog = None
        return False

    def _on_window_active_changed(self, _window, _pspec):
        if (
            not self._is_closed
            and self.is_active()
            and self.settings.get("blur_mode", "off") == "static"
        ):
            self._refresh_static_blur_layer(force=False)

    def _refresh_static_blur_layer(self, force=False):
        if self._is_closed or self._wallpaper_loading:
            return
        now = time.monotonic()
        if not force and (now - self._last_wallpaper_check) < 1.5:
            return

        self._wallpaper_loading = True
        self._last_wallpaper_check = now

        def _worker():
            wp_path = detect_wallpaper_path()
            sig = None
            if wp_path:
                try:
                    sig = (wp_path, os.stat(wp_path).st_mtime_ns)
                except OSError:
                    wp_path = None
                    sig = None
            GLib.idle_add(self._apply_detected_wallpaper, wp_path, sig)

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_detected_wallpaper(self, wp_path, sig):
        self._wallpaper_loading = False
        if self._is_closed:
            return False
        if self._wallpaper_initialized and sig == self._current_wallpaper_sig:
            return False

        self._wallpaper_initialized = True
        self._current_wallpaper_sig = sig

        if self._wallpaper_pic is not None:
            self.static_bg_container.remove(self._wallpaper_pic)
            self._wallpaper_pic = None

        if wp_path:
            self.static_bg_container.remove_css_class("tuxixi-static-blur-fallback")
            pic = Gtk.Picture.new_for_filename(wp_path)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.set_can_shrink(True)
            pic.set_hexpand(True)
            pic.set_vexpand(True)
            pic.add_css_class("tuxixi-static-blur-pic")
            self.static_bg_container.append(pic)
            self._wallpaper_pic = pic
        else:
            self.static_bg_container.add_css_class("tuxixi-static-blur-fallback")

        return False

    def _on_tabbar_scroll(self, _controller, dx, dy):
        hadj = self.tabs_scroller.get_hadjustment()
        if not hadj:
            return False
        delta = dx if abs(dx) > abs(dy) else dy
        step = 45.0
        new_val = max(
            hadj.get_lower(),
            min(hadj.get_upper() - hadj.get_page_size(), hadj.get_value() + delta * step),
        )
        hadj.set_value(new_val)
        return True

    def _scroll_to_tab_item(self, tab_item):
        def _do_scroll():
            hadj = self.tabs_scroller.get_hadjustment()
            if not hadj:
                return False
            ok, bounds = tab_item.compute_bounds(self.tabs_box)
            if not ok:
                return False
            item_start = bounds.origin.x
            item_end = item_start + bounds.size.width
            view_start = hadj.get_value()
            view_end = view_start + hadj.get_page_size()

            if item_start < view_start:
                hadj.set_value(max(hadj.get_lower(), item_start - 4))
            elif item_end > view_end:
                hadj.set_value(
                    max(
                        hadj.get_lower(),
                        min(
                            hadj.get_upper() - hadj.get_page_size(),
                            item_end - hadj.get_page_size() + 4,
                        ),
                    )
                )
            return False

        GLib.idle_add(_do_scroll)

    def _on_close_request(self, _window):
        self._is_closed = True
        if self._studio_dialog is not None:
            dialog = self._studio_dialog
            self._studio_dialog = None
            dialog.close()
        for entry in list(self._tabs):
            entry["item"].detach()
            entry["container"].cleanup()
        if self._settings_handler_id is not None:
            if self.settings.handler_is_connected(self._settings_handler_id):
                self.settings.disconnect(self._settings_handler_id)
            self._settings_handler_id = None
        return False

    def _on_settings_changed(self, _settings, key, _value):
        if key in ("blur_mode", "transparent"):
            self._apply_blur_state()

    def _apply_blur_state(self):
        blur_mode = self.settings.get("blur_mode", "off")
        self.static_bg_container.set_visible(blur_mode == "static")

        if blur_mode == "static":
            self._refresh_static_blur_layer(force=True)
            self.blur_badge.set_text("◆ Blur: Static")
            self.blur_badge.set_visible(True)
        elif blur_mode == "smoky":
            self.blur_badge.set_text("◆ Blur: Smoky")
            self.blur_badge.set_visible(True)
        else:
            self.blur_badge.set_visible(False)

    def _get_active_container(self):
        visible = self.stack.get_visible_child()
        if isinstance(visible, TuxixiPaneContainer):
            return visible
        return None

    def _get_active_terminal(self):
        container = self._get_active_container()
        if container is not None:
            return container.active_pane
        return None

    def _find_container_for_terminal(self, terminal_view):
        for entry in self._tabs:
            container = entry["container"]
            if terminal_view in container.panes:
                return container
        return None

    def _refresh_tab_titles(self):
        active_container = self._get_active_container()
        for idx, entry in enumerate(self._tabs, start=1):
            container = entry["container"]
            term = container.active_pane
            if term is None:
                continue
            dyn_title = term.get_dynamic_title()
            full_raw = term.vte.get_window_title() or term.get_current_cwd() or dyn_title
            base_title = f"{idx}: {dyn_title}" if dyn_title else f"Terminal {idx}"
            if container.pane_count > 1:
                display_title = f"{base_title} [{container.pane_count}]"
            else:
                display_title = base_title
            entry["item"].set_title(display_title, tooltip=full_raw)
            if container is active_container:
                self.set_title(f"TUXIXI — {dyn_title}" if dyn_title else "TUXIXI")

    def _on_add_tab_clicked(self, _btn):
        active = self._get_active_terminal()
        cwd = active.get_current_cwd() if active else None
        self.add_tab(cwd=cwd)

    def _on_split_btn_clicked(self, _btn):
        container = self._get_active_container()
        if container is not None:
            container.split_pane(direction="horizontal")

    def _on_split_btn_right_clicked(self, gesture, _n_press, _x, _y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        container = self._get_active_container()
        if container is not None:
            container.split_pane(direction="vertical")

    def _wire_terminal_signals(self, _container, terminal_view):
        terminal_view.connect("request-new-window", self._on_request_new_window)
        terminal_view.connect("request-new-tab", self._on_request_new_tab)
        terminal_view.connect("request-close-tab", self._on_request_close_tab)
        terminal_view.connect("request-split", self._on_request_split)
        terminal_view.connect("request-focus-pane", self._on_request_focus_pane)
        terminal_view.connect("pane-focused", self._on_pane_focused)
        terminal_view.connect("request-switch-tab", self._on_request_switch_tab)
        terminal_view.connect("request-select-tab-index", self._on_request_select_tab_index)
        terminal_view.connect("request-theme-studio", self._on_request_theme_studio)
        terminal_view.connect("title-changed", self._on_terminal_title_changed)
        terminal_view.connect("session-closed", self._on_session_closed)

    def add_tab(self, cwd=None):
        self._uid_seq += 1
        page_name = f"tab-{self._uid_seq}"
        tab_number = len(self._tabs) + 1

        pane_container = TuxixiPaneContainer(
            settings_manager=self.settings,
            initial_cwd=cwd,
            on_terminal_created=self._wire_terminal_signals,
            on_state_changed=lambda _c: self._refresh_tab_titles(),
            on_empty=self.close_tab,
        )

        tab_item = TuxixiTabItem(
            title=f"{tab_number}: ~",
            on_select=lambda c=pane_container: self.select_tab(c),
            on_close=lambda c=pane_container: self.close_tab(c),
        )

        self._tabs.append({
            "container": pane_container,
            "item": tab_item,
            "name": page_name,
        })

        self.tabs_box.append(tab_item)
        self.stack.add_named(pane_container, page_name)
        self._refresh_tab_titles()
        self.select_tab(pane_container)

    def select_tab(self, pane_container):
        target_item = None
        for entry in self._tabs:
            is_target = entry["container"] is pane_container
            entry["item"].set_active(is_target)
            if is_target:
                target_item = entry["item"]

        if target_item is not None:
            self.stack.set_visible_child(pane_container)
            pane_container.grab_active_focus()
            self._refresh_tab_titles()
            self._scroll_to_tab_item(target_item)

    def select_tab_by_index(self, index):
        if 0 <= index < len(self._tabs):
            self.select_tab(self._tabs[index]["container"])

    def switch_tab_relative(self, delta):
        if len(self._tabs) <= 1:
            return
        active_container = self._get_active_container()
        current_idx = next(
            (i for i, entry in enumerate(self._tabs) if entry["container"] is active_container),
            0,
        )
        next_idx = (current_idx + delta) % len(self._tabs)
        self.select_tab(self._tabs[next_idx]["container"])

    def close_tab(self, pane_container):
        index = next(
            (i for i, entry in enumerate(self._tabs) if entry["container"] is pane_container),
            None,
        )
        if index is None:
            return

        was_active = self.stack.get_visible_child() is pane_container
        entry = self._tabs.pop(index)

        entry["item"].detach()
        entry["container"].cleanup()
        self.tabs_box.remove(entry["item"])
        self.stack.remove(entry["container"])

        if not self._tabs:
            self.close()
            return

        self._refresh_tab_titles()

        if was_active:
            next_index = min(index, len(self._tabs) - 1)
            self.select_tab(self._tabs[next_index]["container"])

    def _on_request_new_tab(self, terminal_view):
        self.add_tab(cwd=terminal_view.get_current_cwd())

    def _on_request_close_tab(self, terminal_view):
        container = self._find_container_for_terminal(terminal_view)
        if container is not None:
            container.close_pane(terminal_view)

    def _on_request_split(self, terminal_view, direction):
        container = self._find_container_for_terminal(terminal_view)
        if container is not None:
            container.split_pane(target_pane=terminal_view, direction=direction)

    def _on_request_focus_pane(self, terminal_view, direction):
        container = self._find_container_for_terminal(terminal_view)
        if container is not None:
            container.focus_direction(direction)

    def _on_pane_focused(self, terminal_view):
        container = self._find_container_for_terminal(terminal_view)
        if container is not None and container.active_pane is not terminal_view:
            container.set_active_pane(terminal_view, grab_focus=False)

    def _on_request_theme_studio(self, _terminal_view):
        self.open_theme_studio()

    def _on_terminal_title_changed(self, _terminal_view, _title):
        self._refresh_tab_titles()

    def _on_session_closed(self, terminal_view, _status):
        container = self._find_container_for_terminal(terminal_view)
        if container is not None:
            container.close_pane(terminal_view)

    def _on_request_switch_tab(self, _terminal_view, delta):
        self.switch_tab_relative(delta)

    def _on_request_select_tab_index(self, _terminal_view, index):
        self.select_tab_by_index(index)

    def _on_request_new_window(self, _terminal_view, cwd):
        self.app.open_new_window(cwd=cwd)
