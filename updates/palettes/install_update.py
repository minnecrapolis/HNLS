#!/usr/bin/env python3
"""Scoped HNLS holiday palette / analysis-directed Song Show update for an existing controller."""
import argparse,ast,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
PACKAGE=Path(__file__).resolve().parent
FILES = {'server/libs/section_sync.py', 'server/libs/show_director.py', 'server/libs/webserver/blueprints/effect_settings_executer.py', 'server/libs/song_analysis.py', 'server/libs/show_palettes.py', 'server/libs/audio_process_service.py', 'server/libs/webserver/schemas/config_validator_service.py', 'server/libs/webserver/blueprints/effect_settings_api.py', 'server/libs/effects/effect_song_show.py', 'server/libs/dsp.py', 'server/libs/app/templates/home/effects/effect_song_show.html', 'server/libs/app/static/assets/js/song_show.js'}
def service(action):subprocess.run(['systemctl',action,'mlsc'],check=True,timeout=90)
def active():return subprocess.run(['systemctl','is-active','--quiet','mlsc'],check=False).returncode==0

def clean_rollback_settings(root,backup):
    additions={'subbass_color','lowmid_color','uppermid_color','presence_color','brilliance_color','expanded_bands','show_mode','palette_preset'}
    updates=[]
    for filename in ('config.json','config_backup.json'):
        p=root.parent/'.mlsc'/filename
        if not p.exists():continue
        original=p.read_bytes();value=json.loads(original)
        devices=[value.get('default_device',{})]+list(value.get('device_configs',{}).values())
        changed=False
        for device in devices:
            settings=device.get('effects',{}).get('effect_song_show',{})
            for key in additions:
                if key in settings:settings.pop(key);changed=True
        if changed:updates.append((p,original,json.dumps(value,indent=2).encode()))
    if updates:
        archive=backup/('settings-before-rollback-'+str(time.time_ns()));archive.mkdir(mode=0o700)
        for p,original,data in updates:
            saved=archive/p.name;saved.write_bytes(original);saved.chmod(0o600)
            temp=p.with_name(p.name+'.hnls-rollback-tmp')
            try:
                temp.write_bytes(data);shutil.copystat(p,temp);temp.replace(p)
            finally:temp.unlink(missing_ok=True)

def restore(root,backup):
    manifest=json.loads((backup/'backup.json').read_text())
    if set(manifest)!=FILES:raise ValueError('Unexpected rollback manifest')
    for name,digest in manifest.items():
        if digest is not None and hashlib.sha256((backup/name).read_bytes()).hexdigest()!=digest:raise ValueError('Incomplete or changed rollback backup')
    clean_rollback_settings(root,backup)
    for name,digest in manifest.items():
        target=root/name
        if digest is None:target.unlink(missing_ok=True)
        else:shutil.copy2(backup/name,target)
        for p in (target.parent/'__pycache__').glob(target.stem+'.*.pyc'):p.unlink()

def install(root,no_service=False):
    root=root.resolve();meta=json.loads((PACKAGE/'manifest.json').read_text())
    if set(meta)!=FILES:raise ValueError('Unexpected update file list')
    payload={}
    # Verify everything before interrupting playback.
    for name,item in meta.items():
        data=(PACKAGE/'files'/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Update checksum mismatch: '+name)
        target=root/name
        if target.is_symlink():raise ValueError('Unexpected symlink: '+name)
        current=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if current not in item['supported']+[item['sha256']]:raise ValueError('This installed file differs from the captured/release build; nothing changed: '+name)
        if name.endswith('.py'):compile(data.decode(),name,'exec')
        payload[name]=data
    if not no_service:
        from jinja2 import Environment
        from zoneinfo import ZoneInfo
        for name, data in payload.items():
            if name.endswith('.html'):
                Environment().parse(data.decode())
        ZoneInfo('America/Chicago')
    backup=root.parent/('hnls-palettes-backup-'+str(time.time_ns()));backup.mkdir(mode=0o700)
    originals={}
    for name in FILES:
        target=root/name
        if target.exists():
            p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,p)
            originals[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        else:originals[name]=None
    (backup/'backup.json').write_text(json.dumps(originals,indent=2))
    running=not no_service and active()
    if running:service('stop')
    try:
        for name,data in payload.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.hnls-update-tmp')
            try:
                temp.write_bytes(data)
                if target.exists():shutil.copystat(target,temp)
                temp.replace(target)
            finally:temp.unlink(missing_ok=True)
            for p in (target.parent/'__pycache__').glob(target.stem+'.*.pyc'):p.unlink()
        if running:service('start');service('is-active')
    except BaseException:
        if running:subprocess.run(['systemctl','stop','mlsc'],check=False)
        restore(root,backup)
        if running:subprocess.run(['systemctl','start','mlsc'],check=False)
        raise
    print('HNLS holiday palettes and analysis-directed shows installed. Refresh Automatic show with Ctrl+F5.')
    print('Your existing config_template.json is left untouched. New palette settings use optional defaults.')
    print('Existing song moments, LED settings, audio routing, schedules and pairing are retained.')
    print('Backup:',backup)
    print('Rollback: sudo /share/.venv/bin/python3',Path(__file__).resolve(),'--root',root,'--restore',backup)
    if not running and not no_service:print('Service was already stopped. Start it when ready: sudo systemctl start mlsc')
    return backup

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,default=Path('/share/music_led_strip_control'));a.add_argument('--no-service',action='store_true',help='Offline fixture verification only');a.add_argument('--restore',type=Path);x=a.parse_args()
    if not x.no_service and os.geteuid()!=0:raise SystemExit('Run with sudo /share/.venv/bin/python3')
    if x.restore:
        running=not x.no_service and active()
        # Verify the entire backup before stopping, without changing the install.
        manifest=json.loads((x.restore/'backup.json').read_text())
        if set(manifest)!=FILES:raise SystemExit('Unexpected backup')
        for n,d in manifest.items():
            if d is not None and hashlib.sha256((x.restore/n).read_bytes()).hexdigest()!=d:raise SystemExit('Changed backup')
        if running:service('stop')
        try:restore(x.root,x.restore)
        finally:
            if running:service('start')
        print('Previous code restored. Palette-only settings were archived and removed; existing colors and other settings are retained.')
    else:install(x.root,x.no_service)
if __name__=='__main__':main()
