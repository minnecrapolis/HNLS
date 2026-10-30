#!/usr/bin/env python3
"""HNLS fresh-Pi installer. Existing installations are deliberately refused."""
import argparse,hashlib,json,os,platform,secrets,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(argv,**kw):
    print('+ '+' '.join(map(str,argv)),flush=True)
    return subprocess.run(list(map(str,argv)),check=True,**kw)

def paths(role):
    if role=='controller':return Path('/share/music_led_strip_control'),Path('/share/.venv'),Path('/etc/systemd/system/mlsc.service'),'mlsc'
    return Path('/opt/mlsc-receiver'),Path('/opt/mlsc-receiver/venv'),Path('/etc/systemd/system/mlsc-receiver.service'),'mlsc-receiver'

def unit_text(role):
    target,venv,_,_=paths(role)
    working=target/'server' if role=='controller' else target
    command=str(venv/'bin/python3')+(' main.py' if role=='controller' else ' '+str(target/'receiver.py'))
    return f'''[Unit]
Description=HourNerd LightShow {role}
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
User=root
WorkingDirectory={working}
ExecStart={command}
Restart=on-failure
RestartSec=5
UMask=0077
[Install]
WantedBy=multi-user.target
'''

def check_payload():
    manifest=json.loads((ROOT/'release-manifest.json').read_text())
    for name,digest in manifest.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe manifest path')
        target=ROOT/p
        if target.is_symlink() or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            raise ValueError('Release file is missing or changed: '+name)
    actual = {p.relative_to(ROOT).as_posix() for folder in ('src','requirements') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    extras = actual-set(manifest)
    if extras:raise ValueError('Unexpected payload files: '+', '.join(sorted(extras)))
    return len(manifest)

def preflight(role):
    target,venv,unit,service=paths(role)
    conflicts=[p for p in [target,unit] if p.exists()]
    if role=='controller':conflicts += [p for p in [venv,Path('/share/.mlsc')] if p.exists()]
    else:conflicts += [p for p in [Path('/etc/mlsc-receiver')] if p.exists()]
    if conflicts:raise ValueError('Existing installation detected; nothing changed. Use a spare/fresh Pi. Found: '+', '.join(map(str,conflicts)))
    if platform.system()!='Linux' or platform.machine() not in ('aarch64','armv7l','armv6l'):
        raise ValueError('Install only on a supported Raspberry Pi Linux system.')
    model=Path('/proc/device-tree/model')
    if not model.exists() or 'Raspberry Pi' not in model.read_text(errors='replace'):
        raise ValueError('A Raspberry Pi model was not detected.')
    if role=='controller' and ('Raspberry Pi 5' in model.read_text(errors='replace')):
        raise ValueError('Native Pi 5 output is not validated by this release. Use the tested Pi 4 controller.')
    if role=='controller' and (sys.version_info<(3,11) or platform.machine()!='aarch64'):
        raise ValueError('Controller baseline requires 64-bit Raspberry Pi OS Bookworm and Python 3.11+.')
    if sys.version_info<(3,9):raise ValueError('Python 3.9+ required.')
    return target,venv,unit,service

def install(role):
    if os.geteuid()!=0:raise ValueError('Run installation with sudo.')
    target,venv,unit,service=preflight(role)
    count=check_payload();print('Verified',count,'release files.')
    source=ROOT/'src'/role
    packages=['python3-venv','python3-dev','build-essential']
    if role=='controller':packages += ['python3-pyaudio','portaudio19-dev','ffmpeg','alsa-utils']
    env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
    # Package operations occur before any service installation.
    run(['apt-get','update'],env=env);run(['apt-get','install','-y']+packages,env=env)
    target.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.hnls-stage-',dir=target.parent))
    installed=False;created_venv=False;created_key=False;unit_written=False
    was_enabled=False
    try:
        for p in source.iterdir():
            dst=staging/p.name
            if p.is_dir():shutil.copytree(p,dst)
            else:shutil.copy2(p,dst)
        if role=='controller':
            # Virtual environments cannot be relocated after creation.
            created_venv=True;run([sys.executable,'-m','venv','--system-site-packages',venv])
            python=venv/'bin/python3'
        else:
            # Place receiver code at its final path before creating its nested venv.
            staging.rename(target);installed=True
            created_venv=True;run([sys.executable,'-m','venv',venv]);python=venv/'bin/python3'
        run([python,'-m','pip','install','-r',ROOT/'requirements'/(role+'.txt')])
        if role=='controller':
            smoke='import json,pyaudio,numpy,scipy,flask,flask_login,flask_openapi,waitress,loguru,icmplib,psutil,apscheduler,_rpi_ws281x; from jsonschema import Draft202012Validator; from libs.webserver.schemas.config_validator_service import schema; Draft202012Validator(schema).validate(json.load(open("libs/config_template.json"))); print("Controller imports and default schema passed")'
            run([python,'-c',smoke],cwd=staging/'server')
            staging.rename(target);installed=True
            (target.parent/'music').mkdir(exist_ok=True)
        else:
            run([python,'-c','import rpi_ws281x,receiver; print("Receiver imports passed")'],cwd=target)
            keydir=Path('/etc/mlsc-receiver');keydir.mkdir(mode=0o700);created_key=True
            key=keydir/'key';key.write_text(secrets.token_hex(32)+'\n');key.chmod(0o600)
        unit.write_text(unit_text(role));unit_written=True
        run(['systemctl','daemon-reload']);run(['systemctl','enable',service]);was_enabled=True
        run(['systemctl','start',service]);run(['systemctl','is-active','--quiet',service])
        print('Installed HNLS',role,'and enabled startup at boot.')
        print('Controller UI: http://<this-Pi-LAN-address>:8080' if role=='controller' else 'Pair from the controller UI. Show the key locally with: sudo cat /etc/mlsc-receiver/key')
        print('A started service is not a hardware acceptance test. See docs/INSTALLATION.md.')
    except BaseException:
        if unit_written:
            subprocess.run(['systemctl','stop',service],check=False)
            if was_enabled:subprocess.run(['systemctl','disable',service],check=False)
            unit.unlink(missing_ok=True);subprocess.run(['systemctl','daemon-reload'],check=False)
        if installed:shutil.rmtree(target)
        if role=='controller' and created_venv and venv.exists():shutil.rmtree(venv)
        if created_key:shutil.rmtree('/etc/mlsc-receiver')
        print('Fresh application install rolled back. OS packages and any generated runtime data are retained.',file=sys.stderr)
        raise
    finally:
        if staging.exists():shutil.rmtree(staging)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--role',choices=['controller','receiver'],default='controller');a.add_argument('--check',action='store_true');x=a.parse_args()
    if x.check:
        print('PASS:',check_payload(),'release files verified; no system changes.');print('This does not validate Pi hardware or package availability.');return
    try:install(x.role)
    except (ValueError,OSError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
if __name__=='__main__':main()
