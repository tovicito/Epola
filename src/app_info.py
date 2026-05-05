import os
import random
import subprocess
import re

class AppInfoProvider:
    @staticmethod
    def get_desktop_files():
        paths = [
            '/usr/share/applications',
            '/usr/local/share/applications',
            os.path.expanduser('~/.local/share/applications'),
            '/var/lib/flatpak/exports/share/applications',
            os.path.expanduser('~/.local/share/flatpak/exports/share/applications'),
            '/var/lib/snapd/desktop/applications'
        ]
        desktop_files = []
        for path in paths:
            if os.path.exists(path):
                for f in os.listdir(path):
                    if f.endswith('.desktop'):
                        desktop_files.append(os.path.join(path, f))
        return desktop_files

    @staticmethod
    def parse_desktop_file(filepath):
        info = {'name': '', 'icon': '', 'comment': '', 'exec': ''}
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                name_match = re.search(r'^Name=(.*)$', content, re.MULTILINE)
                icon_match = re.search(r'^Icon=(.*)$', content, re.MULTILINE)
                comment_match = re.search(r'^Comment=(.*)$', content, re.MULTILINE)
                exec_match = re.search(r'^Exec=(.*)$', content, re.MULTILINE)

                if name_match: info['name'] = name_match.group(1).strip()
                if icon_match: info['icon'] = icon_match.group(1).strip()
                if comment_match: info['comment'] = comment_match.group(1).strip()
                if exec_match: info['exec'] = exec_match.group(1).strip()
        except:
            pass
        return info

    @staticmethod
    def get_package_owner(filepath):
        # Flatpak check
        if 'flatpak' in filepath:
            filename = os.path.basename(filepath)
            # Flatpak desktop files are usually named like com.example.App.desktop
            pkg_id = filename.replace('.desktop', '')
            return pkg_id, 'flatpak'

        # Snap check
        if '/snapd/' in filepath:
             filename = os.path.basename(filepath)
             # Snaps are often named like appname_appname.desktop
             pkg_id = filename.split('_')[0]
             return pkg_id, 'snap'

        # Try dpkg
        try:
            res = subprocess.run(["dpkg", "-S", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.split(':')[0], 'apt'
        except: pass

        # Try rpm
        try:
            res = subprocess.run(["rpm", "-qf", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.strip(), 'dnf'
        except: pass

        # Try pacman
        try:
            res = subprocess.run(["pacman", "-Qo", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.split(' is owned by ')[1].split(' ')[0], 'pacman'
        except: pass

        return None, None

    @staticmethod
    def get_random_apps(count=12):
        files = AppInfoProvider.get_desktop_files()
        if not files:
            return []

        selected_files = random.sample(files, min(count * 5, len(files)))
        apps = []
        for f in selected_files:
            if len(apps) >= count: break

            pkg_id, manager = AppInfoProvider.get_package_owner(f)
            if not pkg_id: continue

            info = AppInfoProvider.parse_desktop_file(f)
            if info['name'] and info['icon']:
                apps.append({
                    'id': pkg_id,
                    'name': info['name'],
                    'description': info['comment'],
                    'icon': info['icon'],
                    'manager': manager,
                    'installed': True
                })
        return apps

    @staticmethod
    def search_system_apps(query):
        files = AppInfoProvider.get_desktop_files()
        results = []
        query = query.lower()
        for f in files:
            info = AppInfoProvider.parse_desktop_file(f)
            if query in info['name'].lower() or query in info['comment'].lower():
                pkg_id, manager = AppInfoProvider.get_package_owner(f)
                if not pkg_id: continue

                results.append({
                    'id': pkg_id,
                    'name': info['name'],
                    'description': info['comment'],
                    'icon': info['icon'],
                    'manager': manager,
                    'installed': True
                })
        return results
