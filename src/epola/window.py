# window.py
import threading
import gettext
import os
import time
from datetime import datetime
from gi.repository import Adw, Gtk, Gio, GLib, Gdk
from .managers import PackageManager
from .app_info import AppInfoProvider

# Setup localization
_ = gettext.gettext

@Gtk.Template(resource_path='/tte/nemas/Epola/epola/window.ui')
class EpolaWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'EpolaWindow'

    main_stack = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    apps_flowbox = Gtk.Template.Child()

    # Setup
    setup_carousel = Gtk.Template.Child()
    setup_managers_list = Gtk.Template.Child()
    setup_dark_switch = Gtk.Template.Child()
    setup_lang_dropdown = Gtk.Template.Child()

    # Updates
    updates_stack = Gtk.Template.Child()
    updates_list = Gtk.Template.Child()
    updates_status_page = Gtk.Template.Child()
    update_all_button = Gtk.Template.Child()
    last_updated_label = Gtk.Template.Child()

    # Settings
    settings_dark_switch = Gtk.Template.Child()
    settings_lang_dropdown = Gtk.Template.Child()
    auto_update_switch = Gtk.Template.Child()
    settings_managers_group = Gtk.Template.Child()

    # Details
    detail_icon = Gtk.Template.Child()
    detail_name = Gtk.Template.Child()
    detail_desc = Gtk.Template.Child()
    detail_action_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_css()
        self.settings = Gio.Settings.new("tte.nemas.Epola")
        self.pkg_manager = PackageManager()
        self.pkg_manager.enabled_managers = list(self.settings.get_strv("enabled-managers"))
        self.current_pkg = None
        self.available_updates = []

        # Bind Settings
        self.settings.bind("dark-mode", self.settings_dark_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("dark-mode", self.setup_dark_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("auto-updates", self.auto_update_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.connect("changed::dark-mode", self.on_dark_mode_changed)
        self.on_dark_mode_changed(self.settings, "dark-mode")

        # Initial Setup state
        self.populate_setup_managers()
        self.populate_settings_managers()

        if self.settings.get_boolean("first-run"):
            self.main_stack.set_visible_child_name("setup")
        else:
            self.main_stack.set_visible_child_name("main")
            self.load_home()
            self.on_refresh_updates_clicked(None)

    def load_css(self):
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_resource("/tte/nemas/Epola/epola/style.css")
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_dark_mode_changed(self, settings, key):
        dark = settings.get_boolean(key)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK if dark else Adw.ColorScheme.PREFER_LIGHT)

    # SETUP WIZARD LOGIC
    def populate_setup_managers(self):
        while child := self.setup_managers_list.get_first_child():
            self.setup_managers_list.remove(child)
        for name, manager in self.pkg_manager.all_managers.items():
            if manager.is_available():
                row = Adw.ActionRow(title=manager.name, subtitle=manager.command)
                switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=True)
                switch.connect("state-set", self.on_setup_manager_toggled, name)
                row.add_suffix(switch)
                self.setup_managers_list.append(row)

    def on_setup_manager_toggled(self, switch, state, name):
        enabled = list(self.settings.get_strv("enabled-managers"))
        if state and name not in enabled: enabled.append(name)
        elif not state and name in enabled: enabled.remove(name)
        self.settings.set_strv("enabled-managers", enabled)
        self.pkg_manager.enabled_managers = enabled
        return False

    @Gtk.Template.Callback()
    def on_setup_next_clicked(self, button):
        self.setup_carousel.scroll_to(self.setup_carousel.get_nth_page(self.setup_carousel.get_position() + 1), True)

    @Gtk.Template.Callback()
    def on_setup_finish_clicked(self, button):
        self.settings.set_boolean("first-run", False)
        idx = self.setup_lang_dropdown.get_selected()
        self.settings.set_string("language", "es" if idx == 0 else "en")
        self.main_stack.set_visible_child_name("main")
        self.load_home()
        self.on_refresh_updates_clicked(None)

    # SETTINGS LOGIC
    def populate_settings_managers(self):
        enabled = self.settings.get_strv("enabled-managers")
        for name, manager in self.pkg_manager.all_managers.items():
            if manager.is_available():
                row = Adw.ActionRow(title=manager.name)
                switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=(name in enabled))
                switch.connect("state-set", self.on_setup_manager_toggled, name)
                row.add_suffix(switch)
                self.settings_managers_group.add(row)

    # HOME LOGIC
    def load_home(self):
        while child := self.apps_flowbox.get_first_child():
            self.apps_flowbox.remove(child)
        threading.Thread(target=self.fetch_discovery, daemon=True).start()

    def fetch_discovery(self):
        apps = AppInfoProvider.get_random_apps(20)
        GLib.idle_add(self.display_apps, apps)

    def display_apps(self, apps):
        for app in apps:
            button = Gtk.Button(can_shrink=True)
            button.set_has_frame(False)
            button.add_css_class("app-tile")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_margin_all(12)

            icon = Gtk.Image.new_from_icon_name(app.get('icon', 'package-x-generic-symbolic'))
            icon.set_pixel_size(80)
            icon.add_css_class("app-icon-shadow")

            label = Gtk.Label(label=app['name'])
            label.add_css_class("caption-heading")
            label.set_ellipsize(3)

            box.append(icon)
            box.append(label)
            button.set_child(box)
            button.connect("clicked", self.on_app_clicked, app)
            self.apps_flowbox.append(button)

    def on_app_clicked(self, button, pkg_data):
        self.current_pkg = pkg_data
        self.detail_name.set_label(pkg_data['name'])
        self.detail_desc.set_label(pkg_data.get('description', _('No description available.')))
        self.detail_icon.set_from_icon_name(pkg_data.get('icon', 'package-x-generic-symbolic'))
        self.update_detail_button()
        self.main_stack.set_visible_child_name("details")

    def update_detail_button(self):
        pkg = self.current_pkg
        self.detail_action_button.remove_css_class("suggested-action")
        self.detail_action_button.remove_css_class("destructive-action")

        if pkg.get('can_update'):
             self.detail_action_button.set_label(_("Update"))
             self.detail_action_button.add_css_class("suggested-action")
        elif pkg.get('installed'):
            self.detail_action_button.set_label(_("Uninstall"))
            self.detail_action_button.add_css_class("destructive-action")
        else:
            self.detail_action_button.set_label(_("Install"))
            self.detail_action_button.add_css_class("suggested-action")

    @Gtk.Template.Callback()
    def on_back_clicked(self, button):
        self.main_stack.set_visible_child_name("main")

    # SEARCH LOGIC
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
        results = AppInfoProvider.search_system_apps(query)
        mgr_results = self.pkg_manager.search_all(query)
        seen_ids = {r['id'] for r in results}
        for r in mgr_results:
            if r['id'] not in seen_ids:
                results.append(r)
                seen_ids.add(r['id'])
        GLib.idle_add(self.display_apps, results)

    # UPDATES LOGIC
    @Gtk.Template.Callback()
    def on_refresh_updates_clicked(self, button):
        self.updates_stack.set_visible_child_name("loading")
        threading.Thread(target=self.do_check_updates, daemon=True).start()

    def do_check_updates(self):
        updates = self.pkg_manager.get_all_updates()
        GLib.idle_add(self.show_updates, updates)

    def show_updates(self, updates):
        self.available_updates = updates
        while child := self.updates_list.get_first_child():
            self.updates_list.remove(child)

        self.updates_stack.set_visible_child_name("results")
        self.last_updated_label.set_label(_("Last checked: ") + datetime.now().strftime("%H:%M:%S"))

        if not updates:
            self.updates_status_page.set_title(_("All up to date"))
            self.updates_status_page.set_description(_("No updates available."))
            self.update_all_button.set_visible(False)
        else:
            self.updates_status_page.set_title(f"{len(updates)} " + _("updates available"))
            self.updates_status_page.set_description("")
            self.update_all_button.set_visible(True)
            for up in updates:
                row = Adw.ActionRow(title=up['name'], subtitle=up['manager'])
                btn = Gtk.Button(label=_("Update"), valign=Gtk.Align.CENTER)
                btn.add_css_class("pill")
                btn.connect("clicked", self.on_single_update_clicked, up)
                row.add_suffix(btn)
                self.updates_list.append(row)

    def on_single_update_clicked(self, button, pkg_up):
        button.set_sensitive(False)
        manager = self.pkg_manager.all_managers[pkg_up['manager']]
        threading.Thread(target=self.run_op, args=(manager.update, pkg_up, "update"), daemon=True).start()

    @Gtk.Template.Callback()
    def on_update_all_clicked(self, button):
        button.set_sensitive(False)
        threading.Thread(target=self.do_update_all, daemon=True).start()

    def do_update_all(self):
        for up in self.available_updates:
            manager = self.pkg_manager.all_managers[up['manager']]
            manager.update(up['id'])
        GLib.idle_add(self.on_refresh_updates_clicked, None)

    # ACTIONS
    @Gtk.Template.Callback()
    def on_detail_action_clicked(self, button):
        pkg = self.current_pkg
        manager = self.pkg_manager.all_managers[pkg['manager']]
        button.set_sensitive(False)
        if pkg.get('can_update'): op = "update"
        elif pkg.get('installed'): op = "uninstall"
        else: op = "install"

        func = getattr(manager, op)
        threading.Thread(target=self.run_op, args=(func, pkg, op), daemon=True).start()

    def run_op(self, func, pkg, op_type):
        res = func(pkg['id'])
        GLib.idle_add(self.on_op_complete, res.returncode == 0, op_type, pkg)

    def on_op_complete(self, success, op_type, pkg):
        self.detail_action_button.set_sensitive(True)
        if success:
            if op_type == "install": pkg['installed'] = True
            elif op_type == "uninstall": pkg['installed'] = False
            elif op_type == "update": pkg['can_update'] = False
            self.update_detail_button()
            if pkg in self.available_updates:
                self.available_updates.remove(pkg)
                self.show_updates(self.available_updates)
