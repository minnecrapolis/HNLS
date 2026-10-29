"""Validated GPIO21 + GPIO10 expansion for the normal music-reactive player."""
from copy import deepcopy
import math
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time

LOCK=threading.RLock()
ORDERS={'ws2811_strip_'+order.lower() for order in ('RGB','RBG','GRB','GBR','BRG','BGR')}
MARKER=re.compile(r'\n# BEGIN MLSC GPIO10 SPI\n.*?# END MLSC GPIO10 SPI\n?',re.S)


def model():
    path=Path('/proc/device-tree/model')
    return path.read_text(errors='ignore').strip('\x00') if path.is_file() else ''


def boot_path():
    return Path('/boot/firmware') if Path('/boot/firmware/config.txt').is_file() else Path('/boot')


def spi_state():
    path=Path('/sys/module/spidev/parameters/bufsiz')
    try:buffer=int(path.read_text()) if path.is_file() else 0
    except (ValueError,OSError):buffer=0
    hardware=model();clock_fixed=True
    if 'Raspberry Pi 4' in hardware:
        clock_fixed=False
        try:
            clocks=[subprocess.run(['vcgencmd','get_config',field],capture_output=True,text=True,timeout=3,check=False) for field in ('core_freq','core_freq_min')]
            clock_fixed=all(result.returncode==0 and result.stdout.strip()==field+'=500' for field,result in zip(('core_freq','core_freq_min'),clocks))
        except (OSError,subprocess.SubprocessError):pass
    available=Path('/dev/spidev0.0').exists()
    return {'available':available,'buffer_bytes':buffer,'clock_fixed':clock_fixed,'model':hardware,
        'ready':available and buffer>=131072 and clock_fixed and 'Raspberry Pi 5' not in hardware}


def native_devices(config):
    return [(key,d) for key,d in config['device_configs'].items() if d.get('output_type')=='output_raspi']


def validate_layout(config):
    from libs.remote_pixels import validate_devices
    validate_devices(config)
    devices=native_devices(config)
    pins=[d['output']['output_raspi']['led_pin'] for _,d in devices]
    if len(pins)!=len(set(pins)):raise ValueError('Two devices cannot drive the same GPIO. Choose a different output pin.')
    if len(devices)>1 and (len(devices)!=2 or set(pins)!={21,10}):
        raise ValueError('The normal player supports GPIO21 plus GPIO10 together. Use Advanced Users for other hardware combinations.')
    for _,device in devices:
        pin=device['output']['output_raspi']['led_pin']
        if pin==10:
            state=spi_state()
            if not state['ready']:raise ValueError('Prepare GPIO10 SPI and reboot this Pi before enabling the second string.')
            if device['output']['output_raspi']['led_channel']!=0:raise ValueError('GPIO10 SPI uses channel 0')
            bits=4 if str(device.get('led_strip','')).startswith('sk6812') else 3
            if device['led_count']*bits*3+64>state['buffer_bytes']:raise ValueError('The SPI transfer buffer is too small for this LED count.')
        if pin==21 and device['output']['output_raspi']['led_channel']!=0:raise ValueError('GPIO21 PCM uses channel 0')


def add_string(executer,data):
    if not isinstance(data,dict):raise ValueError('Expected new LED string settings')
    source=data.get('source');count=data.get('count');name=data.get('name','GPIO10 string');order=data.get('strip','ws2811_strip_grb');brightness=data.get('brightness',10)
    if type(count) is not int or not 7<=count<=10000:raise ValueError('LED count must be a whole number between 7 and 10000 for this SPI line')
    if isinstance(name,str):name=name.strip()
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_ ()-]{1,80}',name):raise ValueError('Use a short name with letters, numbers, spaces, parentheses or hyphens')
    if order not in ORDERS:raise ValueError('Choose the RGB channel order of the second string')
    if type(brightness) is not int or not 0<=brightness<=100:raise ValueError('Brightness must be between 0 and 100')
    with LOCK:
        config=executer._config
        if source not in config['device_configs']:raise ValueError('Choose an existing source device')
        if any(d['device_name']==name for d in config['device_configs'].values()):raise ValueError('Choose a unique device name')
        original=config['device_configs'][source]
        if original.get('output_type')!='output_raspi' or original['output']['output_raspi']['led_pin']!=21:
            raise ValueError('Choose the working GPIO21 device as the source')
        device=deepcopy(original);device.update(device_name=name,led_count=count,led_mid=max(1,count//2),led_brightness=brightness,led_strip=order,output_type='output_raspi')
        device['device_groups']=[]
        device['fps']=max(1,min(25,int(original['fps']),int(1/(count*30e-6+.004))))
        device['output']['output_raspi'].update(led_pin=10,led_channel=0,led_freq_hz=800000,led_invert=False)
        show=device['effects']['effect_song_show']
        if show.get('sync_mode')=='custom' and len(show.get('sync_groups',[]))!=math.ceil(count/show.get('section_size',50)):
            show.update(sync_mode='paired',sync_groups=[])
        if show.get('max_lit_leds',0)>count:show['max_lit_leds']=count
        device['effects']['last_effect']='effect_song_show'
        key=next(('device_'+str(i) for i in range(100) if 'device_'+str(i) not in config['device_configs']),None)
        if not key:raise ValueError('Device limit reached')
        proposed=deepcopy(config);proposed['device_configs'][key]=device
        validate_layout(proposed)
        config['device_configs'][key]=device
        try:executer.save_config()
        except Exception:
            config['device_configs'].pop(key,None);raise
        # Only the new output needs to start; the working GPIO21 output stays running.
        from libs.notification_enum import NotificationEnum
        executer.put_into_notification_queue(NotificationEnum.song_show_refresh,key)
        return {'ok':True,'device':key,'name':name,'gpio':10,'physical_pin':19,'count':count}


def prepare_spi():
    hardware=model()
    if not hardware or 'Raspberry Pi 5' in hardware:raise ValueError('This GPIO10 preparation supports the existing Raspberry Pi 4 / earlier ws281x backend, not Pi 5.')
    boot=boot_path();config=boot/'config.txt';command=boot/'cmdline.txt'
    if not config.is_file() or not command.is_file():raise ValueError('Pi boot configuration files were not found')
    with LOCK:
        old_config=config.read_text();old_command=command.read_text()
        if len([line for line in old_command.splitlines() if line.strip()])!=1:raise ValueError('Kernel command line must contain one nonempty line; no files changed')
        clock=500 if 'Raspberry Pi 4' in hardware else 250
        new_config=MARKER.sub('\n',old_config).rstrip()+f'\n# BEGIN MLSC GPIO10 SPI\n[all]\ndtparam=spi=on\ncore_freq={clock}\ncore_freq_min={clock}\n# END MLSC GPIO10 SPI\n'
        words=[word for word in old_command.split() if not word.startswith('spidev.bufsiz=')]
        new_command=' '.join(words+['spidev.bufsiz=131072'])+'\n'
        stamp=str(time.time_ns());backups=[]
        for path in (config,command):
            backup=path.with_name(path.name+'.mlsc-spi-'+stamp+'.bak');shutil.copy2(path,backup);backups.append((path,backup))
        try:
            for path,text in ((config,new_config),(command,new_command)):
                temporary=path.with_name(path.name+'.mlsc-spi.tmp');shutil.copy2(path,temporary);temporary.write_text(text);temporary.replace(path)
        except Exception:
            for path,backup in backups:shutil.copy2(backup,path)
            raise
    return {'ok':True,'reboot_required':True,'message':'SPI prepared and boot files backed up. Reboot this Pi, then add the GPIO10 string.'}
