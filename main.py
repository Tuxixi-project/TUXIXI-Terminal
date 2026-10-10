#!/usr/bin/env python3
import sys, os, gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib
from settings import load_settings
from ui import TuxixiWindow

class TuxixiApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.tuxixi.Terminal")
        GLib.set_prgname("tuxixi")
        GLib.set_application_name("TUXIXI")

    def do_activate(self):
        settings = load_settings()
        window = TuxixiWindow(self, settings)
        window.present()

if __name__ == "__main__":
    app = TuxixiApplication()
    sys.exit(app.run(sys.argv))
