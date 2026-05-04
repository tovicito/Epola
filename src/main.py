# main.py
import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import EpolaWindow

class EpolaApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='tte.nemas.Epola',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/tte/nemas/Epola')

        # Manually register the schema directory if needed
        # In a real installation this is not needed
        schema_dir = os.path.join(os.getcwd(), 'data')
        if os.path.exists(os.path.join(schema_dir, 'gschemas.compiled')):
             os.environ['XDG_DATA_DIRS'] = schema_dir + ':' + os.environ.get('XDG_DATA_DIRS', '')

        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = EpolaWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(application_name='Epola',
                                application_icon='tte.nemas.Epola',
                                developer_name='Tomas',
                                version='0.1.0',
                                developers=['Tomas'],
                                copyright='© 2026 Tomas')
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        # We now have settings in a tab, but we can also open a dialog or switch to that tab
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
