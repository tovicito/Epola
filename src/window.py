# window.py
import threading
import gettext
import os
from gi.repository import Adw, Gtk, Gio, GLib, Gdk
from .managers import PackageManager
from .app_info import AppInfoProvider

# Setup localization
domain = 'epola'
localedir = os.path.join(os.path.dirname(__file__), '../po')
gettext.bindtextdomain(domain, localedir)
gettext.textdomain(domain)
_ = gettext.gettext

@Gtk.Template(resource_path='/tte/nemas/Epola/window.ui')
class EpolaWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'EpolaWindow'

    main_stack = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    apps_flowbox = Gtk.Template.Child()
    updates_list = Gtk.Template.Child()
    updates_status_page = Gtk.Template.Child()
    update_all_button = Gtk.Template.Child()
    managers_box = Gtk.Template.Child()

    # Detail widgets
    detail_icon = Gtk.Template.Child()
    detail_name = Gtk.Template.Child()
    detail_desc = Gtk.Template.Child()
    detail_action_button = Gtk.Template.Child()

    # Setup widgets
    setup_dark_switch = Gtk.Template.Child()
    setup_lang_dropdown = Gtk.Template.Child()

    # Settings widgets
    settings_dark_switch = Gtk.Template.Child()
    settings_lang_dropdown = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_css()
        self.settings = Gio.Settings.new("tte.nemas.Epola")
        self.pkg_manager = PackageManager()
        self.current_pkg = None
        self.available_updates = []

        # Sync settings
        self.settings.bind("dark-mode", self.settings_dark_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("dark-mode", self.setup_dark_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.connect("changed::dark-mode", self.on_dark_mode_changed)
        self.on_dark_mode_changed(self.settings, "dark-mode")

        # Managers in settings
        self.populate_managers_settings()

        # Check first run
        if self.settings.get_boolean("first-run"):
            self.main_stack.set_visible_child_name("setup")
        else:
            self.main_stack.set_visible_child_name("main")
            self.load_home()
            self.check_updates()

    def load_css(self):
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_resource("/tte/nemas/Epola/style.css")
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def on_dark_mode_changed(self, settings, key):
        dark = settings.get_boolean(key)
        style_manager = Adw.StyleManager.get_default()
        if dark:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

    def populate_managers_settings(self):
        enabled = self.settings.get_strv("enabled-managers")
        for name, manager in self.pkg_manager.all_managers.items():
            if manager.is_available():
                row = Adw.ActionRow(title=manager.name)
                switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=(name in enabled))
                switch.connect("state-set", self.on_manager_toggled, name)
                row.add_suffix(switch)
                self.managers_box.append(row)

    def on_manager_toggled(self, switch, state, name):
        enabled = list(self.settings.get_strv("enabled-managers"))
        if state and name not in enabled:
            enabled.append(name)
        elif not state and name in enabled:
            enabled.remove(name)
        self.settings.set_strv("enabled-managers", enabled)
        self.pkg_manager.enabled_managers = enabled
        return False

    @Gtk.Template.Callback()
    def on_setup_finish_clicked(self, button):
        self.settings.set_boolean("first-run", False)
        # Handle language from dropdown
        idx = self.setup_lang_dropdown.get_selected()
        lang = "es" if idx == 0 else "en"
        self.settings.set_string("language", lang)

        self.main_stack.set_visible_child_name("main")
        self.load_home()
        self.check_updates()

    def load_home(self):
        while child := self.apps_flowbox.get_first_child():
            self.apps_flowbox.remove(child)

        # Load random system apps for discovery
        apps = AppInfoProvider.get_random_apps(16)
        for app in apps:
            self.add_app_tile(app)

    def add_app_tile(self, pkg_data):
        button = Gtk.Button()
        button.set_has_frame(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_all(12)

        icon_name = pkg_data.get('icon', 'package-x-generic-symbolic')
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(64)

        label = Gtk.Label(label=pkg_data['name'])
        label.set_ellipsize(3) # Pango.EllipsizeMode.END
        label.add_css_class("caption-heading")

        box.append(icon)
        box.append(label)
        button.set_child(box)
        button.connect("clicked", self.on_app_clicked, pkg_data)

        self.apps_flowbox.append(button)

    def on_app_clicked(self, button, pkg_data):
        self.current_pkg = pkg_data
        self.detail_name.set_label(pkg_data['name'])
        self.detail_desc.set_label(pkg_data.get('description', _('Sin descripción disponible.')))
        self.detail_icon.set_from_icon_name(pkg_data.get('icon', 'package-x-generic-symbolic'))

        self.update_detail_button()
        self.main_stack.set_visible_child_name("details")

    def update_detail_button(self):
        pkg = self.current_pkg
        if pkg.get('can_update'):
             self.detail_action_button.set_label(_("Actualizar"))
             self.detail_action_button.set_css_classes(["pill", "suggested-action"])
        elif pkg['installed']:
            self.detail_action_button.set_label(_("Desinstalar"))
            self.detail_action_button.set_css_classes(["pill", "destructive-action"])
        else:
            self.detail_action_button.set_label(_("Instalar"))
            self.detail_action_button.set_css_classes(["pill", "suggested-action"])

    @Gtk.Template.Callback()
    def on_back_clicked(self, button):
        self.main_stack.set_visible_child_name("main")

    @Gtk.Template.Callback()
    def on_search_activated(self, entry):
        query = entry.get_text()
        if not query:
            self.load_home()
            return

        while child := self.apps_flowbox.get_first_child():
            self.apps_flowbox.remove(child)

        threading.Thread(target=self.do_search, args=(query,), daemon=True).start()

    def do_search(self, query):
        # Search in system apps and via package managers
        results = AppInfoProvider.search_system_apps(query)
        # Add a few results from managers if not enough
        if len(results) < 10:
            mgr_results = self.pkg_manager.search_all(query)
            # Merge and avoid duplicates by ID
            seen_ids = {r['id'] for r in results}
            for r in mgr_results:
                if r['id'] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r['id'])

        for res in results:
            GLib.idle_add(self.add_app_tile, res)

    @Gtk.Template.Callback()
    def on_detail_action_clicked(self, button):
        pkg = self.current_pkg
        manager = self.pkg_manager.all_managers[pkg['manager']]

        button.set_sensitive(False)
        if pkg.get('can_update'):
             threading.Thread(target=self.run_op, args=(manager.update, pkg, _("Actualizado")), daemon=True).start()
        elif pkg['installed']:
            threading.Thread(target=self.run_op, args=(manager.uninstall, pkg, _("Desinstalar")), daemon=True).start()
        else:
            threading.Thread(target=self.run_op, args=(manager.install, pkg, _("Instalar")), daemon=True).start()

    def run_op(self, func, pkg, action_name):
        res = func(pkg['id'])
        GLib.idle_add(self.on_op_complete, res.returncode == 0, action_name, pkg)

    def on_op_complete(self, success, action_name, pkg):
        self.detail_action_button.set_sensitive(True)
        if success:
            if action_name == _("Instalado"): pkg['installed'] = True
            elif action_name == _("Desinstalar"): pkg['installed'] = False
            elif action_name == _("Actualizado"): pkg['can_update'] = False

            self.update_detail_button()
        else:
            # Error toast
            pass

    def check_updates(self):
        self.updates_status_page.set_title(_("Buscando actualizaciones..."))
        self.update_all_button.set_visible(False)
        threading.Thread(target=self.do_check_updates, daemon=True).start()

    def do_check_updates(self):
        updates = self.pkg_manager.get_all_updates()
        GLib.idle_add(self.show_updates, updates)

    def show_updates(self, updates):
        self.available_updates = updates
        while child := self.updates_list.get_first_child():
            self.updates_list.remove(child)

        if not updates:
            self.updates_status_page.set_title(_("Todo al día"))
            self.updates_status_page.set_description(_("No hay actualizaciones disponibles."))
            self.update_all_button.set_visible(False)
        else:
            self.updates_status_page.set_title(f"{len(updates)} " + _("actualizaciones disponibles"))
            self.updates_status_page.set_description("")
            self.update_all_button.set_visible(True)
            for up in updates:
                row = Adw.ActionRow(title=up['name'], subtitle=up['manager'])
                btn = Gtk.Button(label=_("Actualizar"), valign=Gtk.Align.CENTER)
                btn.add_css_class("flat")
                btn.connect("clicked", self.on_single_update_clicked, up)
                row.add_suffix(btn)
                self.updates_list.append(row)

    def on_single_update_clicked(self, button, pkg_up):
        button.set_sensitive(False)
        manager = self.pkg_manager.all_managers[pkg_up['manager']]
        threading.Thread(target=self.run_update, args=(manager, pkg_up, button), daemon=True).start()

    def run_update(self, manager, pkg_up, button):
        res = manager.update(pkg_up['id'])
        GLib.idle_add(self.on_update_done, res.returncode == 0, pkg_up, button)

    def on_update_done(self, success, pkg_up, button):
        if success:
            self.available_updates.remove(pkg_up)
            self.show_updates(self.available_updates)

    @Gtk.Template.Callback()
    def on_update_all_clicked(self, button):
        button.set_sensitive(False)
        threading.Thread(target=self.do_update_all, daemon=True).start()

    def do_update_all(self):
        for up in self.available_updates:
            manager = self.pkg_manager.all_managers[up['manager']]
            manager.update(up['id'])
        GLib.idle_add(self.check_updates)
        GLib.idle_add(self.update_all_button.set_sensitive, True)
