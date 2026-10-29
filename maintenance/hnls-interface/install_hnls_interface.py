#!/usr/bin/env python3
"""Install the HNLS lighting desk presentation on the main Pi only."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PREFIX = 'server/libs/app/'
TEMPLATES = (
    'templates/layouts/base.html', 'templates/layouts/base-fullscreen.html',
    'templates/includes/sidebar.html', 'templates/includes/navigation.html',
    'templates/includes/hournerd_footer.html', 'templates/includes/hournerd_start.html',
    'templates/includes/song_moments.html', 'templates/home/dashboard.html',
    'templates/home/music.html', 'templates/home/song_designer.html', 'templates/home/login.html',
)
ALLOWED = {PREFIX+n for n in TEMPLATES} | {PREFIX+'static/assets/css/hnls-desk.css', PREFIX+'static/assets/js/hnls-navigation.js', PREFIX+'static/assets/js/hnls-tools.js'}

def service(action):
    subprocess.run(['systemctl', action, 'mlsc'], check=True, timeout=90)

def restore(root, backup, check_only=False):
    manifest = json.loads((backup/'manifest.json').read_text())
    if not isinstance(manifest, dict) or set(manifest) != ALLOWED:
        raise ValueError('Unexpected backup manifest; nothing restored')
    for name, existed in manifest.items():
        if type(existed) is not bool or (existed and not (backup/name).is_file()):
            raise ValueError('Incomplete backup: '+name)
    if check_only: return
    for name, existed in manifest.items():
        target = root/name
        if existed:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup/name, target)
        else: target.unlink(missing_ok=True)

def install(root, package, no_service=False):
    hashes=json.loads((package/'sha256.json').read_text())
    if set(hashes) != ALLOWED: raise ValueError('Unexpected package file list')
    updates={}
    for name, digest in hashes.items():
        data=(package/'files'/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Checksum mismatch: '+name)
        updates[name]=data
    for name in TEMPLATES:
        if not (root/PREFIX/name).is_file():
            raise ValueError('Required installed interface is missing: '+name)
    for name in ('static/assets/js/song_moments.js', 'static/assets/js/music.js',
                 'static/assets/images/hournerd_logo.png'):
        if not (root/PREFIX/name).is_file(): raise ValueError('Missing dependency: '+name)
    # Parse templates with the Pi's installed Jinja before stopping playback.
    try:
        from jinja2 import Environment
    except ImportError:
        if not no_service: raise ValueError('Run using sudo /share/.venv/bin/python3')
    else:
        env=Environment()
        for name,data in updates.items():
            if name.endswith('.html'): env.parse(data.decode())
    backup=root.parent/('hnls-interface-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(mode=0o700)
    if not no_service: service('stop')
    manifest={}
    try:
        for name in sorted(updates):
            target=root/name
            manifest[name]=target.is_file()
            if target.is_file():
                saved=backup/name
                saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,saved)
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        for name,data in updates.items():
            target=root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.hnls-ui.tmp')
            try:
                if target.exists():
                    shutil.copy2(target,temp)
                    if os.geteuid()==0:
                        info=target.stat();os.chown(temp,info.st_uid,info.st_gid)
                temp.write_bytes(data)
                temp.chmod(target.stat().st_mode & 0o777 if target.exists() else 0o644)
                temp.replace(target)
            finally: temp.unlink(missing_ok=True)
        if not no_service:
            service('start')
            subprocess.run(['systemctl','is-active','--quiet','mlsc'],check=True,timeout=15)
    except Exception:
        if not no_service: subprocess.run(['systemctl','stop','mlsc'],check=False)
        if (backup/'manifest.json').is_file(): restore(root,backup)
        if not no_service: subprocess.run(['systemctl','start','mlsc'],check=False)
        raise
    return backup

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/share/music_led_strip_control'))
    parser.add_argument('--restore',type=Path)
    parser.add_argument('--no-service',action='store_true',help='For offline verification only')
    args=parser.parse_args()
    if not args.no_service and os.geteuid()!=0: parser.error('Run with sudo /share/.venv/bin/python3')
    root=args.root.resolve()
    if args.restore:
        restore(root,args.restore,True)
        if not args.no_service: service('stop')
        restore(root,args.restore)
        if not args.no_service: service('start')
        print('Previous HNLS interface restored.');return
    backup=install(root,Path(__file__).resolve().parent,args.no_service)
    print('HNLS lighting desk installed. Hard-refresh the browser with Ctrl+F5.')
    print('Playback was restarted. Saved songs, cues, colors and controller settings were retained.')
    print('No LED-SLAVE update needed. Backup:',backup)
    print('Rollback: sudo /share/.venv/bin/python3',Path(__file__).resolve(),'--restore',backup)

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.SubprocessError) as exc: raise SystemExit(str(exc)) from None
