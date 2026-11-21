import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, GLib, Pango
from terminal import TuxixiTerminal
from themes import detect_wallpaper_path


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
        self.close_btn.connect("clicked", lambda _btn: self._on_close())
        self.append(self.close_btn)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_enter)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_pressed)
        self.add_controller(click)

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
            self._on_close()
            return
        if button == 1:
            alloc = self.close_btn.get_allocation()
            if alloc.x <= x <= alloc.x + alloc.width and alloc.y <= y <= alloc.y + alloc.height:
                return
            self._on_select()

    def set_active(self, active):
        if active:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")


class TuxixiWindow(Gtk.ApplicationWindow):
    _cached_wallpaper_path = None
    _wallpaper_checked = False

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

        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.static_bg_container = Gtk.Box()
        self.static_bg_container.set_hexpand(True)
        self.static_bg_container.set_vexpand(True)
        self.static_bg_container.set_can_target(False)
        self.static_bg_container.set_visible(False)
        self._setup_static_blur_layer()
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
        self.connect("close-request", self._on_close_request)

        self.add_tab()
        self._apply_blur_state()

    def _setup_static_blur_layer(self):
        if not TuxixiWindow._wallpaper_checked:
            TuxixiWindow._cached_wallpaper_path = detect_wallpaper_path()
            TuxixiWindow._wallpaper_checked = True

        wp_path = TuxixiWindow._cached_wallpaper_path
        if wp_path:
            pic = Gtk.Picture.new_for_filename(wp_path)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.set_can_shrink(True)
            pic.set_hexpand(True)
            pic.set_vexpand(True)
            pic.add_css_class("tuxixi-static-blur-pic")
            self.static_bg_container.append(pic)
        else:
            self.static_bg_container.add_css_class("tuxixi-static-blur-fallback")

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
                    min(hadj.get_upper() - hadj.get_page_size(), item_end - hadj.get_page_size() + 4)
                )
            return False

        GLib.idle_add(_do_scroll)

    def _on_close_request(self, _window):
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
            self.blur_badge.set_text("◆ Blur: Static")
            self.blur_badge.set_visible(True)
        elif blur_mode == "smoky":
            self.blur_badge.set_text("◆ Blur: Smoky")
            self.blur_badge.set_visible(True)
        else:
            self.blur_badge.set_visible(False)

    def _get_active_terminal(self):
        visible = self.stack.get_visible_child()
        if isinstance(visible, TuxixiTerminal):
            return visible
        return None

    def _refresh_tab_titles(self):
        active_term = self._get_active_terminal()
        for idx, entry in enumerate(self._tabs, start=1):
            term = entry["terminal"]
            dyn_title = term.get_dynamic_title()
            full_raw = term.vte.get_window_title() or term.get_current_cwd() or dyn_title
            display_title = f"{idx}: {dyn_title}" if dyn_title else f"Terminal {idx}"
            entry["item"].set_title(display_title, tooltip=full_raw)
            if term is active_term:
                self.set_title(f"TUXIXI — {dyn_title}" if dyn_title else "TUXIXI")

    def _on_add_tab_clicked(self, _btn):
        # Hər yeni tab digərindən asılı olmayaraq müstəqil (~ ev qovluğunda) açılır
        self.add_tab()

    def add_tab(self, cwd=None):
        self._uid_seq += 1
        page_name = f"tab-{self._uid_seq}"
        tab_number = len(self._tabs) + 1

        terminal_view = TuxixiTerminal(
            settings_manager=self.settings,
            initial_cwd=None,
        )

        tab_item = TuxixiTabItem(
            title=f"{tab_number}: ~",
            on_select=lambda: self.select_tab(terminal_view),
            on_close=lambda: self.close_tab(terminal_view),
        )

        terminal_view.connect("request-new-window", self._on_request_new_window)
        terminal_view.connect("request-new-tab", self._on_request_new_tab)
        terminal_view.connect("request-close-tab", lambda _t: self.close_tab(terminal_view))
        terminal_view.connect("request-switch-tab", self._on_request_switch_tab)
        terminal_view.connect("request-select-tab-index", self._on_request_select_tab_index)
        terminal_view.connect("title-changed", lambda _t, _title: self._refresh_tab_titles())
        terminal_view.connect("session-closed", lambda _t, _s: self.close_tab(terminal_view))

        self._tabs.append({
            "terminal": terminal_view,
            "item": tab_item,
            "name": page_name,
        })

        self.tabs_box.append(tab_item)
        self.stack.add_named(terminal_view, page_name)
        self._refresh_tab_titles()
        self.select_tab(terminal_view)

    def select_tab(self, terminal_view):
        target_item = None
        for entry in self._tabs:
            is_target = entry["terminal"] is terminal_view
            entry["item"].set_active(is_target)
            if is_target:
                target_item = entry["item"]

        if target_item is not None:
            self.stack.set_visible_child(terminal_view)
            terminal_view.grab_terminal_focus()
            self._refresh_tab_titles()
            self._scroll_to_tab_item(target_item)

    def select_tab_by_index(self, index):
        if 0 <= index < len(self._tabs):
            self.select_tab(self._tabs[index]["terminal"])

    def switch_tab_relative(self, delta):
        if len(self._tabs) <= 1:
            return
        active_term = self._get_active_terminal()
        current_idx = next(
            (i for i, entry in enumerate(self._tabs) if entry["terminal"] is active_term),
            0,
        )
        next_idx = (current_idx + delta) % len(self._tabs)
        self.select_tab(self._tabs[next_idx]["terminal"])

    def close_tab(self, terminal_view):
        index = next(
            (i for i, entry in enumerate(self._tabs) if entry["terminal"] is terminal_view),
            None,
        )
        if index is None:
            return

        was_active = self.stack.get_visible_child() is terminal_view
        entry = self._tabs.pop(index)

        entry["terminal"].cleanup()
        self.tabs_box.remove(entry["item"])
        self.stack.remove(entry["terminal"])

        if not self._tabs:
            self.close()
            return

        self._refresh_tab_titles()

        if was_active:
            next_index = min(index, len(self._tabs) - 1)
            self.select_tab(self._tabs[next_index]["terminal"])

    def _on_request_new_tab(self, _terminal_view):
        self.add_tab()

    def _on_request_switch_tab(self, _terminal_view, delta):
        self.switch_tab_relative(delta)

    def _on_request_select_tab_index(self, _terminal_view, index):
        self.select_tab_by_index(index)

    def _on_request_new_window(self, _terminal_view, _cwd):
        self.app.open_new_window()
