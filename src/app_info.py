import os
import random
import subprocess
import re

class AppInfoProvider:
    @staticmethod
    def get_desktop_files():
        paths = ['/usr/share/applications', '/usr/local/share/applications']
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
    def get_random_apps(count=12):
        files = AppInfoProvider.get_desktop_files()
        if not files:
            return []

        selected_files = random.sample(files, min(count, len(files)))
        apps = []
        for f in selected_files:
            info = AppInfoProvider.parse_desktop_file(f)
            if info['name'] and info['icon']:
                apps.append({
                    'id': os.path.basename(f).replace('.desktop', ''),
                    'name': info['name'],
                    'description': info['comment'],
                    'icon': info['icon'],
                    'manager': 'apt', # Default for system apps
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
                results.append({
                    'id': os.path.basename(f).replace('.desktop', ''),
                    'name': info['name'],
                    'description': info['comment'],
                    'icon': info['icon'],
                    'manager': 'apt',
                    'installed': True
                })
        return results
