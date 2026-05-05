# main.py
import sys
import os
import gi
import signal
import gettext

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import EpolaWindow

class EpolaApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='tte.nemas.Epola',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/tte/nemas/Epola')

        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = EpolaWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(
            application_name='Epola',
            application_icon='tte.nemas.Epola',
            developer_name='Tomas',
            version='1.0.0',
            developers=['Tomas', 'Jules (AI Engineer)'],
            copyright='© 2026 Tomas & Tovicito',
            website='https://github.com/tovicito/epola',
            issue_url='https://github.com/tovicito/epola/issues',
            license_type=Gtk.License.GPL_3_0
        )
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        win = self.props.active_window
        if win:
            win.view_stack.set_visible_child_name("settings")

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

def main(version):
    app = EpolaApplication()
    return app.run(sys.argv)
