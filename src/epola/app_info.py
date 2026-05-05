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
                try:
                    for f in os.listdir(path):
                        if f.endswith('.desktop'):
                            desktop_files.append(os.path.join(path, f))
                except: pass
        return desktop_files

    @staticmethod
    def parse_desktop_file(filepath):
        info = {'name': '', 'icon': '', 'comment': '', 'exec': ''}
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Use a more robust regex to find the [Desktop Entry] section and its keys
                if '[Desktop Entry]' not in content:
                    return info

                entry_section = content.split('[Desktop Action')[0] # Only take main entry

                name_match = re.search(r'^Name=(.*)$', entry_section, re.MULTILINE)
                icon_match = re.search(r'^Icon=(.*)$', entry_section, re.MULTILINE)
                comment_match = re.search(r'^Comment=(.*)$', entry_section, re.MULTILINE)
                exec_match = re.search(r'^Exec=(.*)$', entry_section, re.MULTILINE)

                if name_match: info['name'] = name_match.group(1).strip()
                if icon_match: info['icon'] = icon_match.group(1).strip()
                if comment_match: info['comment'] = comment_match.group(1).strip()
                if exec_match: info['exec'] = exec_match.group(1).strip()
        except: pass
        return info

    @staticmethod
    def get_package_owner(filepath):
        if 'flatpak' in filepath:
            filename = os.path.basename(filepath)
            pkg_id = filename.replace('.desktop', '')
            return pkg_id, 'flatpak'
        if '/snapd/' in filepath:
             filename = os.path.basename(filepath)
             pkg_id = filename.split('_')[0]
             return pkg_id, 'snap'

        try:
            res = subprocess.run(["dpkg", "-S", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.split(':')[0], 'apt'
        except: pass

        try:
            res = subprocess.run(["rpm", "-qf", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.strip(), 'dnf'
        except: pass

        try:
            res = subprocess.run(["pacman", "-Qo", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                # Handle cases where pacman output varies
                match = re.search(r'is owned by (\S+)', res.stdout)
                if match: return match.group(1), 'pacman'
        except: pass

        return None, None

    @staticmethod
    def get_random_apps(count=20):
        files = AppInfoProvider.get_desktop_files()
        if not files: return []

        random.shuffle(files)
        apps = []
        for f in files:
            if len(apps) >= count: break

            info = AppInfoProvider.parse_desktop_file(f)
            # Filter for GUI apps and ignore internal/tools
            if not info['name'] or not info['icon'] or 'NoDisplay=true' in open(f, errors='ignore').read():
                continue

            pkg_id, manager = AppInfoProvider.get_package_owner(f)
            if not pkg_id:
                # If we can't find an owner, it might be a standalone or we use basename
                pkg_id = os.path.basename(f).replace('.desktop', '')
                manager = 'apt' # Default fallback

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
                if not pkg_id:
                    pkg_id = os.path.basename(f).replace('.desktop', '')
                    manager = 'apt'

                results.append({
                    'id': pkg_id,
                    'name': info['name'],
                    'description': info['comment'],
                    'icon': info['icon'],
                    'manager': manager,
                    'installed': True
                })
        return results
