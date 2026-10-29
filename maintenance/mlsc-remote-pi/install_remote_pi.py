#!/usr/bin/env python3
"""Install the light receiver on LED-SLAVE, or its controls on LED03."""
import argparse
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
MASTER_NAMES = ['server/libs/remote_protocol.py', 'server/libs/remote_pixels.py',
                'server/libs/outputs/output_udp.py', 'server/libs/gpio_outputs.py',
                'server/libs/webserver/blueprints/device_api.py',
                'server/libs/webserver/blueprints/device_executer.py',
                'server/libs/app/templates/home/settings/device_settings.html',
                'server/libs/app/static/assets/js/remote_pis.js']
UNIT = '''[Unit]
Description=MLSC remote LED receiver
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mlsc-receiver
ExecStart=/opt/mlsc-receiver/venv/bin/python3 /opt/mlsc-receiver/receiver.py
Restart=on-failure
RestartSec=2
TimeoutStopSec=8
UMask=0077

[Install]
WantedBy=multi-user.target
'''


def run(args):
    subprocess.run(args, check=True)


def clear_cache(path):
    if path.suffix == '.py':
        for cached in (path.parent/'__pycache__').glob(path.stem+'.*.pyc'):
            cached.unlink()


def atomic(path, text, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.mlsc-remote.tmp')
    if path.exists():
        shutil.copy2(path, temporary)
    temporary.write_text(text)
    if mode is not None:
        temporary.chmod(mode)
    temporary.replace(path)
    clear_cache(path)


def backup_files(root, names, prefix):
    backup = root.parent/(prefix+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    manifest = {}
    for name in names:
        target = root/name
        manifest[name] = target.is_file()
        if target.is_file():
            saved = backup/name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    (backup/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return backup


def restore_files(root, backup):
    manifest = json.loads((backup/'manifest.json').read_text())
    if not isinstance(manifest, dict) or set(manifest)-set(MASTER_NAMES):
        raise ValueError('Invalid master backup')
    for name, existed in manifest.items():
        if type(existed) is not bool or (existed and not (backup/name).is_file()):
            raise ValueError('Incomplete backup')
    for name, existed in manifest.items():
        target = root/name
        if existed:
            shutil.copy2(backup/name, target)
        else:
            target.unlink(missing_ok=True)
        clear_cache(target)


def replace_method(original, reference, class_name, method_name):
    def method(text):
        cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == class_name)
        return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
    old, new = method(original), method(reference)
    lines = original.splitlines(keepends=True)
    lines[old.lineno-1:old.end_lineno] = reference.splitlines(keepends=True)[new.lineno-1:new.end_lineno]
    return ''.join(lines)


def prepare_master(root):
    reference = PACKAGE/'master/files'
    if not (root/'server/libs/gpio_outputs.py').is_file():
        raise ValueError('Install the working second-string update first; no files changed')
    if '_sync_gpio_devices()' not in (root/'server/libs/device_manager.py').read_text():
        raise ValueError('Requires the working second-string device manager; no files changed')
    updates = {}
    for name in MASTER_NAMES:
        payload = (reference/name).read_text()
        target = root/name
        if name.endswith('output_udp.py'):
            # Preserve other UDP color mappings; only update remote delegation methods.
            text = target.read_text()
            for method in ('__init__', 'show'):
                text = replace_method(text, payload, 'OutputUDP', method)
            if '    def close(self):' not in text:
                close = '''    def close(self):
        if getattr(self, '_remote', None):
            self._remote.close()
        elif hasattr(self, '_sock'):
            self._sock.close()

'''
                text = text.replace('    def show(self, output_array):', close+'    def show(self, output_array):', 1)
            updates[name] = text
        elif name.endswith('gpio_outputs.py'):
            text = target.read_text()
            marker = '    from libs.remote_pixels import validate_devices\n    validate_devices(config)'
            if marker not in text:
                if text.count('def validate_layout(config):') != 1:
                    raise ValueError('Unexpected GPIO validation version')
                text = text.replace('def validate_layout(config):', 'def validate_layout(config):\n'+marker, 1)
            updates[name] = text
        elif name.endswith('device_api.py'):
            text = target.read_text()
            if "@device_api.get('/api/system/remote-pis')" not in text:
                text += payload[payload.index("\n\n@device_api.get('/api/system/remote-pis')"):]
            updates[name] = text
        elif name.endswith('device_executer.py'):
            text = target.read_text()
            old = '        self.save_config()\n        self.refresh_device(self.all_devices_id)\n        return {\n            "deleted_device": device'
            new = '        self.save_config()\n        from libs.remote_pixels import forget\n        forget(device)\n        self.refresh_device(self.all_devices_id)\n        return {\n            "deleted_device": device'
            if '        forget(device)' not in text:
                if text.count(old) != 1:
                    raise ValueError('Unexpected device deletion version')
                text = text.replace(old, new, 1)
            updates[name] = text
        elif name.endswith('device_settings.html'):
            text = target.read_text()
            if 'id="remotePiPanel"' not in text:
                start = payload.index('                    <section class="card" id="remotePiPanel">')
                end = payload.index('                    <input type="hidden" id="settingsIdentifier"', start)
                marker = '                    <input type="hidden" id="settingsIdentifier"'
                if text.count(marker) != 1:
                    raise ValueError('Unexpected Device Settings template')
                text = text.replace(marker, payload[start:end]+marker, 1)
                text = text.replace('{% endblock javascripts %}', '<script src="{{ url_for(\'static\', filename=\'assets/js/remote_pis.js\') }}?v=1"></script>\n{% endblock javascripts %}', 1)
            updates[name] = text
        else:
            updates[name] = payload
    for name, text in updates.items():
        if name.endswith('.py'):
            compile(text, name, 'exec')
    return updates


def install_master(args):
    root = args.root.resolve()
    if args.restore:
        # Paired devices must be removed first; legacy UDP is a different protocol.
        store = root.parent/'.mlsc/remote_pis.json'
        config_path = root.parent/'.mlsc/config.json'
        if store.is_file() and config_path.is_file():
            nodes = json.loads(store.read_text())
            devices = json.loads(config_path.read_text()).get('device_configs', {})
            if set(nodes) & set(devices):
                raise ValueError('Delete remote Pi devices in the web interface before restoring older code. No files changed.')
        # Validate backup before service stop.
        manifest = json.loads((args.restore/'manifest.json').read_text())
        if set(manifest)-set(MASTER_NAMES) or any(type(v) is not bool or (v and not (args.restore/n).is_file()) for n,v in manifest.items()):
            raise ValueError('Invalid backup')
        if not args.no_service:
            run(['systemctl', 'stop', 'mlsc'])
        restore_files(root, args.restore)
        if not args.no_service:
            run(['systemctl', 'start', 'mlsc'])
        print('Previous master code restored. Audio and local GPIO configuration retained.')
        return
    updates = prepare_master(root)
    backup = backup_files(root, updates, 'mlsc-remote-pi-backup-')
    if not args.no_service:
        run(['systemctl', 'stop', 'mlsc'])
    try:
        for name, text in updates.items():
            atomic(root/name, text)
        if not args.no_service:
            run(['systemctl', 'start', 'mlsc'])
    except Exception:
        restore_files(root, backup)
        if not args.no_service:
            subprocess.run(['systemctl', 'start', 'mlsc'], check=False)
        raise
    print('Remote Pi controls installed on LED03. Refresh Device Settings with Ctrl+F5.')
    print('Use Add remote Pi, enter receiver address/key/count and pair.')
    print('Local LED driver, audio, music and current configuration were retained.')
    print('Rollback: sudo python3', Path(__file__).resolve(), '--master --restore', backup)


def install_receiver(args):
    if args.no_service:
        raise ValueError('--no-service is only for offline master verification')
    hardware = Path('/proc/device-tree/model')
    if not hardware.is_file() or 'Raspberry Pi 5' in hardware.read_text():
        raise ValueError('Install the receiver on LED-SLAVE (Pi 3 A+), not this machine')
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'mlsc'], check=False).returncode == 0:
        raise ValueError('MLSC is already active here. Run --receiver only on the dedicated LED-SLAVE, not LED03.')
    destination = Path('/opt/mlsc-receiver')
    keypath = Path('/etc/mlsc-receiver/key')
    unit = Path('/etc/systemd/system/mlsc-receiver.service')
    # Dependencies go into their own venv; the main Pi MLSC environment is untouched.
    run(['apt-get', 'update'])
    run(['apt-get', 'install', '-y', 'python3-venv', 'python3-dev', 'build-essential'])
    destination.mkdir(parents=True, exist_ok=True)
    if not (destination/'venv/bin/python3').exists():
        run([sys.executable, '-m', 'venv', str(destination/'venv')])
    run([str(destination/'venv/bin/python3'), '-m', 'pip', 'install', 'rpi_ws281x==5.0.0'])
    run([str(destination/'venv/bin/python3'), '-c', 'from rpi_ws281x import PixelStrip, WS2811_STRIP_GRB'])
    names = ('receiver.py', 'remote_protocol.py')
    for name in names:
        compile((PACKAGE/'receiver'/name).read_text(), name, 'exec')
    backup = destination/('backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir()
    for name in names:
        if (destination/name).is_file():
            shutil.copy2(destination/name, backup/name)
    if unit.is_file():
        shutil.copy2(unit, backup/'mlsc-receiver.service')
    previously_active = subprocess.run(['systemctl', 'is-active', '--quiet', 'mlsc-receiver'], check=False).returncode == 0
    run(['systemctl', 'stop', 'mlsc-receiver']) if unit.is_file() else None
    try:
        for name in names:
            atomic(destination/name, (PACKAGE/'receiver'/name).read_text(), 0o644)
        keypath.parent.mkdir(parents=True, exist_ok=True)
        keypath.parent.chmod(0o700)
        if not keypath.exists():
            atomic(keypath, secrets.token_hex(32)+'\n', 0o600)
        keypath.chmod(0o600)
        atomic(unit, UNIT, 0o644)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'enable', '--now', 'mlsc-receiver'])
        run(['systemctl', 'is-active', '--quiet', 'mlsc-receiver'])
    except Exception:
        subprocess.run(['systemctl', 'stop', 'mlsc-receiver'], check=False)
        for name in names:
            if (backup/name).is_file():
                shutil.copy2(backup/name, destination/name)
            else:
                (destination/name).unlink(missing_ok=True)
            clear_cache(destination/name)
        if (backup/'mlsc-receiver.service').is_file():
            shutil.copy2(backup/'mlsc-receiver.service', unit)
        else:
            subprocess.run(['systemctl', 'disable', 'mlsc-receiver'], check=False)
            unit.unlink(missing_ok=True)
        subprocess.run(['systemctl', 'daemon-reload'], check=False)
        if previously_active:
            subprocess.run(['systemctl', 'start', 'mlsc-receiver'], check=False)
        raise
    print('\nLED-SLAVE receiver installed. No reboot needed for GPIO21.')
    print('Pairing key (paste into LED03 Device Settings → Add remote Pi):')
    print(keypath.read_text().strip())
    print('Receiver uses GPIO21 / physical pin40. LED count and order are set from LED03.')
    print('Status: sudo systemctl status mlsc-receiver --no-pager -l')
    print('Stop receiver: sudo systemctl stop mlsc-receiver')
    print('Disable receiver: sudo systemctl disable --now mlsc-receiver')
    print('Code backup:', backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--receiver', action='store_true')
    choice.add_argument('--master', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/share/music_led_strip_control'))
    parser.add_argument('--restore', type=Path)
    parser.add_argument('--no-service', action='store_true', help='Offline master verification only')
    args = parser.parse_args()
    if not args.no_service and os.geteuid() != 0:
        parser.error('Run this installer with sudo')
    hashes = json.loads((PACKAGE/'sha256.json').read_text())
    for name, digest in hashes.items():
        if hashlib.sha256((PACKAGE/name).read_bytes()).hexdigest() != digest:
            raise SystemExit('Package checksum mismatch; no files changed: '+name)
    try:
        if args.receiver:
            if args.restore:
                raise ValueError('--restore applies to the master. To stop a receiver: sudo systemctl disable --now mlsc-receiver')
            install_receiver(args)
        else:
            install_master(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
