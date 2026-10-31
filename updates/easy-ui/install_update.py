#!/usr/bin/env python3
"""Install the HNLS task-based interface without restarting audio or services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

PACKAGE = Path(__file__).resolve().parent
FILES = {'server/libs/app/templates/layouts/base.html', 'server/libs/app/templates/includes/sidebar.html', 'server/libs/app/templates/home/settings/device_settings.html', 'server/libs/app/templates/home/song_designer.html', 'server/libs/app/static/assets/js/hnls-tools.js', 'server/libs/app/templates/includes/song_moments.html', 'server/libs/app/templates/includes/hournerd_start.html', 'server/libs/app/templates/home/music.html', 'server/libs/app/static/assets/js/hnls-guide.js', 'server/libs/app/templates/home/effects/effect_song_show.html', 'server/libs/app/static/assets/js/song_show.js', 'server/libs/app/static/assets/css/hnls-guide.css', 'server/libs/app/templates/home/dashboard.html'}


def verified_payload(root, offline=False):
    meta = json.loads((PACKAGE/'manifest.json').read_text())
    if set(meta) != FILES:
        raise ValueError('Unexpected UI update file list')
    payload = {}
    for name,item in meta.items():
        if not name.startswith('server/libs/app/') or Path(name).suffix not in ('.html','.css','.js'):
            raise ValueError('UI updates must contain only templates and browser assets')
        target = root/name
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError('Unexpected path: '+name)
        data = (PACKAGE/'files'/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Update checksum mismatch: '+name)
        current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if current not in item['supported']+[item['sha256']]:
            raise ValueError('Installed UI file differs; nothing changed: '+name)
        payload[name] = data
    if not offline:
        from jinja2 import Environment
        environment = Environment()
        for name,data in payload.items():
            if name.endswith('.html'):
                environment.parse(data.decode())
    return payload


def restore(root,backup):
    meta = json.loads((backup/'backup.json').read_text())
    if set(meta) != FILES:
        raise ValueError('Unexpected rollback manifest')
    for name,digest in meta.items():
        if digest is not None and hashlib.sha256((backup/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Incomplete or changed UI backup')
        if (root/name).is_symlink() or not (root/name).resolve().is_relative_to(root):
            raise ValueError('Unexpected restore path')
    for name,digest in meta.items():
        p = root/name
        if digest is None:
            p.unlink(missing_ok=True)
        else:
            temporary = p.with_name(p.name+'.hnls-ui-restore-tmp')
            try:
                shutil.copy2(backup/name,temporary)
                temporary.replace(p)
            finally:
                temporary.unlink(missing_ok=True)


def install(root,offline=False):
    root = root.resolve()
    payload = verified_payload(root,offline)
    backup = root.parent/('hnls-easy-ui-backup-'+str(time.time_ns()))
    backup.mkdir(mode=0o700)
    originals = {}
    for name in FILES:
        p = root/name
        if p.exists():
            saved = backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,saved)
            originals[name] = hashlib.sha256(saved.read_bytes()).hexdigest()
        else:
            originals[name] = None
    (backup/'backup.json').write_text(json.dumps(originals,indent=2))
    try:
        # New dependencies are listed first; base.html is written last.
        for name,data in payload.items():
            p = root/name;p.parent.mkdir(parents=True,exist_ok=True)
            temporary = p.with_name(p.name+'.hnls-ui-tmp')
            try:
                temporary.write_bytes(data)
                if p.exists():shutil.copystat(p,temporary)
                temporary.replace(p)
            finally:
                temporary.unlink(missing_ok=True)
    except BaseException:
        restore(root,backup)
        raise
    print('HNLS easy navigation installed. Refresh the browser with Ctrl+F5.')
    print('Music and services continue running. Open Home to see the new task menu.')
    print('Backup:',backup)
    print('Rollback: sudo /share/.venv/bin/python3',Path(__file__).resolve(),'--root',root,'--restore',backup)
    return backup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/share/music_led_strip_control'))
    parser.add_argument('--offline-checks',action='store_true',help='Skip Jinja only for offline fixtures')
    parser.add_argument('--restore',type=Path)
    args=parser.parse_args()
    if not args.offline_checks and os.geteuid()!=0:
        raise SystemExit('Run with sudo /share/.venv/bin/python3')
    if args.restore:
        restore(args.root.resolve(),args.restore)
        print('Previous interface restored. Refresh with Ctrl+F5.')
    else:
        install(args.root,args.offline_checks)


if __name__=='__main__':
    main()
