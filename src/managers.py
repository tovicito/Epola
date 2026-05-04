import subprocess
import os

class BaseManager:
    def __init__(self, name, icon):
        self.name = name
        self.icon = icon

    def is_available(self):
        try:
            return subprocess.run(["which", self.command], capture_output=True).returncode == 0
        except:
            return False

    def search(self, query):
        raise NotImplementedError

    def get_updates(self):
        raise NotImplementedError

    def install(self, pkg_id):
        raise NotImplementedError

    def uninstall(self, pkg_id):
        raise NotImplementedError

    def update(self, pkg_id):
        raise NotImplementedError

class AptManager(BaseManager):
    command = "apt"

    def search(self, query):
        try:
            res = subprocess.run(["apt", "search", "--names-only", query], capture_output=True, text=True)
            lines = res.stdout.split('\n')
            results = []
            for i in range(0, len(lines)-1):
                line = lines[i].strip()
                if not line or line.startswith('Sorting...') or line.startswith('Full Text Search...'):
                    continue
                if '/' in line and not line.startswith(' '):
                    parts = line.split('/')
                    pkg_name = parts[0]
                    desc = ""
                    if i + 1 < len(lines):
                        desc = lines[i+1].strip()
                    results.append({
                        'id': pkg_name,
                        'name': pkg_name,
                        'description': desc,
                        'manager': 'apt',
                        'installed': self.is_installed(pkg_name)
                    })
            return results
        except Exception as e:
            print(f"Apt search error: {e}")
            return []

    def is_installed(self, pkg_name):
        res = subprocess.run(["dpkg", "-l", pkg_name], capture_output=True)
        return res.returncode == 0

    def get_updates(self):
        try:
            res = subprocess.run(["apt-get", "-s", "upgrade"], capture_output=True, text=True)
            updates = []
            for line in res.stdout.split('\n'):
                if line.startswith('Inst '):
                    parts = line.split(' ')
                    pkg_name = parts[1]
                    updates.append({
                        'id': pkg_name,
                        'name': pkg_name,
                        'manager': 'apt',
                        'description': 'Actualización disponible'
                    })
            return updates
        except:
            return []

    def run_with_pkexec(self, args):
        cmd = ["pkexec", "apt-get", "-y"] + args
        return subprocess.run(cmd)

    def install(self, pkg_id):
        return self.run_with_pkexec(["install", pkg_id])

    def uninstall(self, pkg_id):
        return self.run_with_pkexec(["remove", pkg_id])

    def update(self, pkg_id):
        return self.run_with_pkexec(["install", "--only-upgrade", pkg_id])

class FlatpakManager(BaseManager):
    command = "flatpak"

    def search(self, query):
        try:
            res = subprocess.run(["flatpak", "search", "--columns=application,name,description", query], capture_output=True, text=True)
            results = []
            for line in res.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    results.append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'description': parts[2].strip() if len(parts) > 2 else "",
                        'manager': 'flatpak',
                        'installed': self.is_installed(parts[0].strip())
                    })
            return results
        except:
            return []

    def is_installed(self, pkg_id):
        res = subprocess.run(["flatpak", "info", pkg_id], capture_output=True)
        return res.returncode == 0

    def get_updates(self):
        try:
            res = subprocess.run(["flatpak", "update", "--no-deploy"], capture_output=True, text=True)
            # This is complex to parse without actual output, but flatpak has a better way
            res = subprocess.run(["flatpak", "remote-ls", "--updates", "--columns=application,name"], capture_output=True, text=True)
            updates = []
            for line in res.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    updates.append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'manager': 'flatpak',
                        'description': 'Actualización disponible (Flatpak)'
                    })
            return updates
        except:
            return []

    def install(self, pkg_id):
        return subprocess.run(["pkexec", "flatpak", "install", "-y", "flathub", pkg_id])

    def uninstall(self, pkg_id):
        return subprocess.run(["pkexec", "flatpak", "uninstall", "-y", pkg_id])

    def update(self, pkg_id):
        return subprocess.run(["pkexec", "flatpak", "update", "-y", pkg_id])

class SnapManager(BaseManager):
    command = "snap"

    def search(self, query):
        try:
            res = subprocess.run(["snap", "find", query], capture_output=True, text=True)
            results = []
            lines = res.stdout.strip().split('\n')
            if len(lines) > 1: # Skip header
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 1:
                        results.append({
                            'id': parts[0],
                            'name': parts[0],
                            'description': " ".join(parts[3:]) if len(parts) > 3 else "",
                            'manager': 'snap',
                            'installed': self.is_installed(parts[0])
                        })
            return results
        except:
            return []

    def is_installed(self, pkg_id):
        res = subprocess.run(["snap", "list", pkg_id], capture_output=True)
        return res.returncode == 0

    def get_updates(self):
        try:
            res = subprocess.run(["snap", "refresh", "--list"], capture_output=True, text=True)
            updates = []
            lines = res.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 1:
                        updates.append({
                            'id': parts[0],
                            'name': parts[0],
                            'manager': 'snap',
                            'description': 'Actualización disponible (Snap)'
                        })
            return updates
        except:
            return []

    def install(self, pkg_id):
        return subprocess.run(["pkexec", "snap", "install", pkg_id])

    def uninstall(self, pkg_id):
        return subprocess.run(["pkexec", "snap", "remove", pkg_id])

    def update(self, pkg_id):
        return subprocess.run(["pkexec", "snap", "refresh", pkg_id])

class DnfManager(BaseManager):
    command = "dnf"
    def search(self, query):
        try:
            res = subprocess.run(["dnf", "search", query], capture_output=True, text=True)
            results = []
            for line in res.stdout.strip().split('\n'):
                if ' : ' in line:
                    parts = line.split(' : ')
                    pkg_full = parts[0].strip()
                    pkg_name = pkg_full.split('.')[0]
                    results.append({
                        'id': pkg_name,
                        'name': pkg_name,
                        'description': parts[1].strip(),
                        'manager': 'dnf',
                        'installed': self.is_installed(pkg_name)
                    })
            return results
        except: return []

    def is_installed(self, pkg_name):
        res = subprocess.run(["rpm", "-q", pkg_name], capture_output=True)
        return res.returncode == 0

    def get_updates(self):
        try:
            res = subprocess.run(["dnf", "check-update"], capture_output=True, text=True)
            updates = []
            for line in res.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 1 and '.' in parts[0]:
                    pkg_name = parts[0].split('.')[0]
                    updates.append({'id': pkg_name, 'name': pkg_name, 'manager': 'dnf'})
            return updates
        except: return []

    def install(self, pkg_id): return subprocess.run(["pkexec", "dnf", "install", "-y", pkg_id])
    def uninstall(self, pkg_id): return subprocess.run(["pkexec", "dnf", "remove", "-y", pkg_id])
    def update(self, pkg_id): return subprocess.run(["pkexec", "dnf", "upgrade", "-y", pkg_id])

class PacmanManager(BaseManager):
    command = "pacman"
    def search(self, query):
        try:
            res = subprocess.run(["pacman", "-Ss", query], capture_output=True, text=True)
            results = []
            lines = res.stdout.strip().split('\n')
            for i in range(0, len(lines), 2):
                header = lines[i]
                if '/' in header:
                    pkg_name = header.split('/')[1].split(' ')[0]
                    desc = lines[i+1].strip() if i+1 < len(lines) else ""
                    results.append({
                        'id': pkg_name,
                        'name': pkg_name,
                        'description': desc,
                        'manager': 'pacman',
                        'installed': self.is_installed(pkg_name)
                    })
            return results
        except: return []

    def is_installed(self, pkg_name):
        res = subprocess.run(["pacman", "-Qi", pkg_name], capture_output=True)
        return res.returncode == 0

    def get_updates(self):
        try:
            res = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True)
            updates = []
            for line in res.stdout.strip().split('\n'):
                if line:
                    pkg_name = line.split(' ')[0]
                    updates.append({'id': pkg_name, 'name': pkg_name, 'manager': 'pacman'})
            return updates
        except: return []

    def install(self, pkg_id): return subprocess.run(["pkexec", "pacman", "-S", "--noconfirm", pkg_id])
    def uninstall(self, pkg_id): return subprocess.run(["pkexec", "pacman", "-R", "--noconfirm", pkg_id])
    def update(self, pkg_id): return subprocess.run(["pkexec", "pacman", "-S", "--noconfirm", pkg_id])

class PackageManager:
    def __init__(self):
        self.all_managers = {
            'apt': AptManager('APT', 'package-x-generic-symbolic'),
            'flatpak': FlatpakManager('Flatpak', 'package-x-generic-symbolic'),
            'snap': SnapManager('Snap', 'package-x-generic-symbolic'),
            'dnf': DnfManager('DNF', 'package-x-generic-symbolic'),
            'pacman': PacmanManager('Pacman', 'package-x-generic-symbolic'),
        }
        self.enabled_managers = ['apt', 'flatpak', 'snap', 'dnf', 'pacman']

    def get_active_managers(self):
        return [self.all_managers[m] for m in self.enabled_managers if m in self.all_managers and self.all_managers[m].is_available()]

    def search_all(self, query):
        results = []
        for manager in self.get_active_managers():
            results.extend(manager.search(query))
        return results

    def get_all_updates(self):
        updates = []
        for manager in self.get_active_managers():
            updates.extend(manager.get_updates())
        return updates
