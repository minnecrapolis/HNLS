"""Persistent local audio routing and bounded BlueZ/BlueALSA operations."""
import json
import os
from pathlib import Path
import re
import pwd
import shutil
import subprocess
import threading
import time

LOCK = threading.RLock()
JOB = {'running': False, 'action': '', 'message': '', 'error': ''}
MAC = re.compile(r'^[0-9A-F]{2}(?::[0-9A-F]{2}){5}$')
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def settings_path():
    return Path(os.environ.get('MLSC_AUDIO_SETTINGS', str(Path(__file__).resolve().parents[3]/'.mlsc/audio_output.json')))


def address(value):
    value = str(value or '').upper()
    if not MAC.fullmatch(value):
        raise ValueError('Select a Bluetooth device address')
    return value


def load_settings():
    try:
        result = json.loads(settings_path().read_text())
        if result.get('mode') not in ('headphones', 'bluetooth'):
            raise ValueError('Invalid audio output')
        if result['mode'] == 'bluetooth':
            result['address'] = address(result.get('address'))
        return {'mode': result['mode'], 'address': result.get('address', '')}
    except FileNotFoundError:
        return {'mode': 'headphones', 'address': ''}


def save_settings(data):
    if not isinstance(data, dict) or data.get('mode') not in ('headphones', 'bluetooth'):
        raise ValueError('Choose the 3.5 mm jack or Bluetooth')
    result = {'mode': data['mode'], 'address': address(data.get('address')) if data['mode'] == 'bluetooth' else ''}
    path = settings_path();path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(result)+'\n');temporary.chmod(0o600);temporary.replace(path)
    return result


def run(argv, timeout=12, check=True):
    try:
        environment = dict(os.environ)
        if Path(argv[0]).name == 'apt-get':environment['DEBIAN_FRONTEND']='noninteractive'
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False, env=environment)
    except FileNotFoundError as exc:
        raise ValueError('Missing system tool: '+argv[0]) from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Timed out: '+Path(argv[0]).name) from exc
    output = ANSI.sub('', (result.stdout or '')+'\n'+(result.stderr or '')).strip()
    if check and (result.returncode or any(word in output for word in ('Failed to ', 'No default controller', 'not available', 'org.bluez.Error'))):
        raise ValueError(output[-1000:] or 'Command failed: '+Path(argv[0]).name)
    return output


def info(mac):
    return run(['bluetoothctl','info',address(mac)], timeout=5)


def connected(mac):
    return 'Connected: yes' in info(mac)


def connect(mac):
    mac = address(mac)
    if not connected(mac):
        run(['bluetoothctl','--timeout','15','connect',mac],timeout=20)
    if not connected(mac):
        raise ValueError('Bluetooth speaker did not connect. Turn it on and disconnect it from other devices.')


def daemon_path():
    return shutil.which('bluealsad') or shutil.which('bluealsa')


def active_unit():
    for unit in ('bluealsa.service','bluealsad.service','mlsc-bluealsa.service'):
        if run(['systemctl','is-active',unit],timeout=3,check=False)=='active':
            return unit
    return ''


def plugin_available():
    return any(Path('/usr/lib').glob('*/alsa-lib/libasound_module_pcm_bluealsa.so')) or Path('/usr/lib/alsa-lib/libasound_module_pcm_bluealsa.so').is_file()


def pulse_sessions():
    sessions=[]
    for sock in Path('/run/user').glob('*/pulse/native'):
        try:
            runtime=sock.parent.parent;uid=int(runtime.name);user=pwd.getpwuid(uid).pw_name
            if uid == 0:continue
            sessions.append(['runuser','-u',user,'--','env','XDG_RUNTIME_DIR='+str(runtime),
                'PULSE_SERVER=unix:'+str(sock),'DBUS_SESSION_BUS_ADDRESS=unix:'+str(runtime/'bus')])
        except (ValueError,KeyError):continue
    return sessions


def desktop_a2dp(mac):
    if not shutil.which('pactl'):return
    needle=address(mac).replace(':','_').lower()
    for prefix in pulse_sessions():
        try:
            cards=json.loads(run(prefix+['pactl','--format=json','list','cards'],timeout=2))
            for card in cards:
                name=str(card.get('name',''))
                if not name.startswith('bluez_card.') or needle not in name.lower():continue
                profiles=card.get('profiles',{})
                if isinstance(profiles,list):profiles={p.get('name',''):p for p in profiles}
                choices=[n for n,p in profiles.items() if n.startswith(('a2dp-sink','a2dp_sink')) and p.get('available')!='no']
                if choices:
                    active=card.get('active_profile','')
                    if isinstance(active,dict):active=active.get('name','')
                    if active not in choices:run(prefix+['pactl','set-card-profile',name,choices[0]],timeout=8)
        except (ValueError,json.JSONDecodeError):continue


def desktop_sink(mac):
    if not shutil.which('pactl') or not shutil.which('paplay'):return None
    needle=address(mac).replace(':','_').lower()
    for prefix in pulse_sessions():
        try:
            sinks=json.loads(run(prefix+['pactl','--format=json','list','sinks'],timeout=2))
            for sink in sinks:
                name=str(sink.get('name',''))
                if name.startswith(('bluez_output.','bluez_sink.')) and needle in name.lower():
                    profile=str(sink.get('properties',{}).get('api.bluez5.profile',''))+' '+name
                    if any(word in profile.lower() for word in ('headset','handsfree','head_unit','hfp','hsp')):continue
                    return prefix,name
        except (ValueError,json.JSONDecodeError):continue
    return None


def aplay_command(device,rate,channels):
    return ['/usr/bin/aplay','-q','-D',device,'-t','raw','-f','S16_LE','-r',str(int(rate)),
        '-c',str(int(channels)),'--buffer-time=100000','--period-time=25000']


def playback_command(rate,channels):
    selected=load_settings()
    if selected['mode']=='headphones':
        return aplay_command('plughw:CARD=Headphones,DEV=0',rate,channels)
    connect(selected['address'])
    desktop_a2dp(selected['address'])
    sink=desktop_sink(selected['address'])
    if not sink and pulse_sessions():
        for _ in range(2):
            time.sleep(.2)
            sink=desktop_sink(selected['address'])
            if sink:break
    if sink:
        prefix,name=sink
        return prefix+['paplay','--playback','--raw','--format=s16le','--rate='+str(int(rate)),
            '--channels='+str(int(channels)),'--device='+name,'--latency-msec=100']
    if daemon_path() and plugin_available() and active_unit():
        return aplay_command('bluealsa:DEV='+selected['address']+',PROFILE=a2dp',rate,channels)
    raise ValueError('No Bluetooth audio output is ready for the selected speaker. Enable Bluetooth support, pair/connect the speaker, then select it again.')


def state():
    devices=[];error=''
    if shutil.which('bluetoothctl'):
        try:
            for line in run(['bluetoothctl','devices'],timeout=5).splitlines():
                found=re.fullmatch(r'Device ([0-9A-Fa-f:]{17}) (.*)',line.strip())
                if found:devices.append({'address':address(found[1]),'name':found[2]})
        except ValueError as exc:error=str(exc)
    else:error='Bluetooth tools are not installed.'
    try:selected=load_settings()
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        selected={'mode':'headphones','address':''};error='Audio-output preferences could not be read: '+str(exc)
    with LOCK:job=dict(JOB)
    desktop=bool(pulse_sessions() and shutil.which('pactl') and shutil.which('paplay'))
    ready=bool(desktop or (daemon_path() and plugin_available() and active_unit()))
    return {'settings':selected,'devices':devices,'ready':ready,'backend':'Desktop audio' if desktop else 'BlueALSA' if ready else 'Not configured','error':error,'job':job}


def setup_support():
    # Reuse a desktop sound server instead of registering competing BlueALSA profiles.
    desktop=bool(pulse_sessions())
    pipewire=bool(run(['pgrep','-x','pipewire'],timeout=3,check=False))
    pulseaudio=bool(run(['pgrep','-x','pulseaudio'],timeout=3,check=False))
    if desktop or pipewire or pulseaudio:
        if not desktop:
            raise ValueError('A desktop audio stack is running without an accessible user audio session. Log into its desktop session before enabling Bluetooth.')
        run(['apt-get','update'],timeout=300)
        packages=['bluez','pulseaudio-utils']+(['libspa-0.2-bluetooth'] if pipewire else ['pulseaudio-module-bluetooth'])
        run(['apt-get','install','-y',*packages],timeout=600)
        run(['systemctl','enable','--now','bluetooth.service'],timeout=30)
        for prefix in pulse_sessions():
            if pipewire:run(prefix+['systemctl','--user','restart','wireplumber.service'],timeout=30)
            else:run(prefix+['pactl','load-module','module-bluetooth-discover'],check=False)
        if shutil.which('rfkill'):run(['rfkill','unblock','bluetooth'])
        run(['bluetoothctl','power','on'])
        return
    run(['apt-get','update'],timeout=300)
    run(['apt-get','install','-y','bluez','bluez-alsa-utils','libasound2-plugin-bluez'],timeout=600)
    run(['systemctl','enable','--now','bluetooth.service'],timeout=30)
    daemon=daemon_path()
    if not daemon or not plugin_available():
        raise ValueError('The distribution did not provide the required BlueALSA daemon and ALSA plugin.')
    if not active_unit():
        existing=''
        for unit in ('bluealsa.service','bluealsad.service'):
            if run(['systemctl','show','-p','LoadState','--value',unit],check=False)=='loaded':
                existing=unit;break
        if existing:
            run(['systemctl','enable','--now',existing],timeout=30)
        else:
            unit=Path('/etc/systemd/system/mlsc-bluealsa.service')
            text='[Unit]\nDescription=MLSC Bluetooth audio\nAfter=bluetooth.service\nRequires=bluetooth.service\n\n[Service]\nType=simple\nExecStart='+daemon+' -p a2dp-source\nRestart=on-failure\n\n[Install]\nWantedBy=multi-user.target\n'
            if unit.exists() and unit.read_text()!=text:
                raise ValueError('An existing custom MLSC BlueALSA unit differs; it was not overwritten.')
            unit.write_text(text)
            run(['systemctl','daemon-reload'])
            run(['systemctl','enable','--now','mlsc-bluealsa.service'],timeout=30)
    if not active_unit():raise ValueError('BlueALSA did not start. Check its system journal.')
    if shutil.which('rfkill'):run(['rfkill','unblock','bluetooth'])
    run(['bluetoothctl','power','on'])


def start_job(data):
    if not isinstance(data,dict):raise ValueError('Expected a Bluetooth action')
    action=data.get('action')
    if action not in ('setup','scan','pair','connect','disconnect'):
        raise ValueError('Unknown Bluetooth action')
    mac=address(data.get('address')) if action in ('pair','connect','disconnect') else ''
    with LOCK:
        if JOB['running']:raise ValueError('A Bluetooth operation is already running')
        JOB.update(running=True,action=action,message='Starting '+action+'…',error='')
    def work():
        try:
            if action=='setup':setup_support()
            else:
                run(['bluetoothctl','power','on'])
                if action=='scan':
                    run(['bluetoothctl','--timeout','8','scan','on'],timeout=12)
                elif action=='pair':
                    if 'Paired: yes' not in info(mac):
                        run(['bluetoothctl','--agent','NoInputNoOutput','--timeout','30','pair',mac],timeout=35)
                    run(['bluetoothctl','trust',mac]);connect(mac)
                elif action=='connect':connect(mac)
                elif action=='disconnect':run(['bluetoothctl','disconnect',mac])
            with LOCK:JOB.update(message=action.capitalize()+' completed.',error='')
        except Exception as exc:
            with LOCK:JOB.update(message='Bluetooth operation failed.',error=str(exc)[-1500:])
        finally:
            with LOCK:JOB['running']=False
    threading.Thread(target=work,daemon=True,name='mlsc-bluetooth').start()
    return {'ok':True,'queued':True}
