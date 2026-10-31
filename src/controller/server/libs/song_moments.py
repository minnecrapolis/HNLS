"""Song-clocked, per-line RGB cue overlays for normal playlist playback."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid

import numpy as np

LOCK = threading.RLock()
_CACHE = {'checked': -1., 'stamp': None, 'cues': []}
EFFECTS = ('solid', 'flash', 'color_scroll', 'color_blocks', 'chase', 'comet', 'bounce', 'pulse', 'twinkle', 'rainbow', 'wipe', 'blackout')


def store_path():
    return Path(__file__).resolve().parents[3]/'.mlsc/song_moments.json'


def song_token(filename):
    return int.from_bytes(hashlib.blake2b(filename.encode(), digest_size=8).digest(), 'big') if filename else 0


def read():
    path = store_path()
    data = json.loads(path.read_text()) if path.is_file() else {'version': 1, 'cues': []}
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('cues'), list):
        raise ValueError('Unsupported song-moment file')
    return data


def write(data):
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(data, stream, indent=2)
    temporary.chmod(0o600)
    temporary.replace(path)
    _CACHE['checked'] = -1.


def number(value, minimum, maximum, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(name+' is outside its supported range')
    return float(value)


def validate(data, config):
    from libs.music_library import safe_music_path
    if not isinstance(data, dict):
        raise ValueError('Expected a song moment')
    data = dict(data)
    region_id = data.get('region')
    if region_id:
        region = next((r for r in read().get('regions', []) if r['id'] == region_id), None)
        if region is None:
            raise ValueError('That named light group no longer exists')
        data.update(targets=[region['device']], first=region['first'], last=region['last'])
    filename = data.get('file')
    if not isinstance(filename, str) or not safe_music_path(filename).is_file():
        raise ValueError('Choose an uploaded song')
    start = number(data.get('start'), 0, 86400, 'Start time')
    end = number(data.get('end'), 0, 86400, 'End time')
    if end-start < .1 or end-start > 3600:
        raise ValueError('Select a span between 0.1 seconds and one hour')
    effect = data.get('effect')
    if effect not in EFFECTS:
        raise ValueError('Choose a supported effect')
    targets = data.get('targets')
    devices = config['device_configs']
    if not isinstance(targets, list) or not targets or len(targets) > 100 or any(not isinstance(t, str) for t in targets):
        raise ValueError('Choose the light strings for this moment')
    if len(targets) != len(set(targets)) or ('*' in targets and targets != ['*']):
        raise ValueError('Choose all strings or individual strings')
    selected = list(devices) if targets == ['*'] else targets
    if not selected or any(t not in devices for t in selected):
        raise ValueError('A selected string no longer exists')
    first, last = data.get('first', 1), data.get('last')
    if type(first) is not int or first < 1 or (last is not None and (type(last) is not int or last < first)):
        raise ValueError('LED numbers start at 1; the end must follow the start')
    if any(first > devices[t]['led_count'] or (last is not None and last > devices[t]['led_count']) for t in selected):
        raise ValueError('That LED range extends past a selected string')
    colors = [data.get('color', '#ffffff'), data.get('color2', '#ff8000')]
    if any(not isinstance(c, str) or not re.fullmatch('#[0-9a-fA-F]{6}', c) for c in colors):
        raise ValueError('Choose valid RGB colors')
    if type(data.get('reserve', False)) is not bool:
        raise ValueError('Invalid outside-time setting')
    cue_id = data.get('id') or uuid.uuid4().hex
    if not isinstance(cue_id, str) or not re.fullmatch('[0-9a-f]{32}', cue_id):
        raise ValueError('Invalid moment identifier')
    extra = motion_settings(data)
    return {**extra, 'id': cue_id, 'region': region_id or None, 'file': filename, 'start': start, 'end': end,
            'effect': effect, 'targets': targets, 'first': first, 'last': last,
            'color': colors[0].lower(), 'color2': colors[1].lower(),
            'speed': number(data.get('speed', 1), .1, 5, 'Effect speed'),
            'brightness': number(data.get('brightness', 100), 0, 100, 'Moment brightness'),
            'reserve': data.get('reserve', False)}



def motion_settings(data):
    extra = {}
    if 'use_color2' in data:
        if type(data['use_color2']) is not bool:
            raise ValueError('Use second color must be on or off')
        extra['use_color2'] = data['use_color2']
    if 'cycle_seconds' in data:
        extra['cycle_seconds'] = number(data['cycle_seconds'], .1, 600, 'Seconds per cycle')
    if 'band_width' in data:
        width = data['band_width']
        if type(width) is not int or not 1 <= width <= 5000:
            raise ValueError('Band / trail width must be 1–5000 LEDs')
        extra['band_width'] = width
    if 'direction' in data:
        if data['direction'] not in ('forward', 'reverse'):
            raise ValueError('Choose forward or reverse')
        extra['direction'] = data['direction']
    return extra


def safe_runtime_cue(raw):
    """Defensive loading: a damaged saved row must not kill an output worker."""
    if not isinstance(raw, dict):raise ValueError('Invalid saved moment')
    cue=dict(raw)
    if not isinstance(cue.get('file'), str):raise ValueError('Invalid song')
    if cue.get('effect') not in EFFECTS:raise ValueError('Invalid effect')
    targets=cue.get('targets')
    if not isinstance(targets,list) or not targets or any(not isinstance(x,str) for x in targets):raise ValueError('Invalid targets')
    if type(cue.get('first')) is not int or not 1<=cue['first']<=5000:raise ValueError('Invalid range')
    if cue.get('last') is not None and (type(cue['last']) is not int or not cue['first']<=cue['last']<=5000):raise ValueError('Invalid range')
    cue['start']=number(cue.get('start'),0,86400,'Start');cue['end']=number(cue.get('end'),0,86400,'End')
    if cue['end']<=cue['start']:raise ValueError('Invalid duration')
    for key,default in [('color','#ffffff'),('color2','#ff8000')]:
        value=cue.get(key,default)
        if not isinstance(value,str) or not re.fullmatch('#[0-9a-fA-F]{6}',value):raise ValueError('Invalid color')
        cue[key]=value
    cue['speed']=number(cue.get('speed',1),.1,5,'Speed')
    cue['brightness']=number(cue.get('brightness',100),0,100,'Brightness')
    if type(cue.get('reserve',False)) is not bool:raise ValueError('Invalid reservation')
    cue['reserve']=cue.get('reserve',False);cue.update(motion_settings(cue));cue['_token']=song_token(cue['file'])
    return cue


def render_cue(cue, count, elapsed):
    """Return a complete RGB range; the background is explicit, never automatic."""
    rgb=np.array([int(cue['color'][n:n+2],16) for n in (1,3,5)],dtype=float)[:,None]
    second=np.array([int(cue['color2'][n:n+2],16) for n in (1,3,5)],dtype=float)[:,None]
    effect=cue['effect'];speed=cue['speed'];period=cue.get('cycle_seconds')
    two=cue.get('use_color2',effect in ('color_scroll','color_blocks','twinkle'))
    background=second if two else np.zeros((3,1))
    # Legacy saved scroll and flash timing remains intact until the cue is edited.
    if period is None:period=.5/speed if effect=='flash' else 1./speed if effect=='color_scroll' else 6./speed
    phase=(elapsed/period)%1.;width=max(1,min(count,cue.get('band_width',8)))
    x=np.arange(count,dtype=float);result=np.zeros((3,count),dtype=float)
    if effect=='solid':result[:]=rgb
    elif effect=='flash':result[:]=rgb if phase<.5 else background
    elif effect=='color_scroll':
        wavelength=32. if 'cycle_seconds' not in cue and 'band_width' not in cue else 2.*width
        blend=(1-np.cos(2*np.pi*((x/wavelength-phase)%1.)))[None,:]/2.
        result=rgb*(1-blend)+background*blend
    elif effect=='color_blocks':result=np.where(((x/(2.*width)-phase)%1.)[None,:]<.5,rgb,background)
    elif effect=='chase':
        weight=(((x-phase*count)%count)<width)[None,:]
        result=rgb*weight+background*(1-weight)
    elif effect=='comet':
        weight=np.maximum(0,1-((phase*count-x)%count)/width)[None,:]**2
        result=rgb*weight+background*(1-weight)
    elif effect=='bounce':
        head=(1-abs(2*phase-1))*(count-1)
        weight=np.maximum(0,1-np.abs(x-head)/width)[None,:]
        result=rgb*weight+background*(1-weight)
    elif effect=='pulse':
        weight=(1-np.cos(2*np.pi*phase))/2.
        result[:]=rgb*weight+background*(1-weight)
    elif effect=='twinkle':
        step=math.floor(elapsed/period);noise=np.sin((x+1)*12.9898+step*78.233)*43758.5453;noise-=np.floor(noise)
        result=np.where((noise>.1)[None,:],rgb,second if two else rgb)*(noise<.2)[None,:]*(1-phase)
    elif effect=='rainbow':
        hue=(x/(2.*width)-phase)%1.
        if two:
            blend=(1-np.cos(2*np.pi*hue))[None,:]/2.
            result=rgb*(1-blend)+second*blend
        else:
            k=np.array([0.,4.,2.])[:,None]
            result=255*np.clip(np.abs((hue[None,:]*6+k)%6-3)-1,0,1)
    elif effect=='wipe':
        weight=(x<math.ceil(phase*count))[None,:]
        result=rgb*weight+background*(1-weight)
    # Blackout intentionally remains zero.
    if cue.get('direction')=='reverse':result=result[:,::-1]
    return (result*(cue['brightness']/100.)).clip(0,255)


def clock_snapshot(device, now):
    clock=getattr(device,'song_moment_clock',None)
    if clock is None:return None
    lock=clock.get_lock()
    if lock.acquire(False):
        try:
            snapshot=(clock.value,device.song_moment_token.value,device.song_moment_position.value,
                      bool(getattr(getattr(device,'song_moment_paused',None),'value',False)))
            device._moment_clock_snapshot=snapshot
        finally:lock.release()
    else:snapshot=getattr(device,'_moment_clock_snapshot',None)
    return snapshot

def save_moment(data, config):
    cue = validate(data, config)
    with LOCK:
        document = read()
        existing = next((i for i, c in enumerate(document['cues']) if c['id'] == cue['id']), None)
        if existing is not None:
            if document['cues'][existing]['file'] != cue['file']:
                raise ValueError('A moment belongs to one song; create a new moment instead')
            document['cues'][existing] = cue
        else:
            if len(document['cues']) >= 500:
                raise ValueError('This editor currently supports 500 saved moments')
            document['cues'].append(cue)
        write(document)
    return cue


def delete_moment(cue_id):
    if not isinstance(cue_id, str):
        raise ValueError('Choose a saved moment')
    with LOCK:
        document = read()
        remaining = [c for c in document['cues'] if c['id'] != cue_id]
        if len(remaining) == len(document['cues']):
            raise ValueError('Moment not found')
        document['cues'] = remaining
        write(document)
    return {'ok': True}


def cached_cues(now):
    if now-_CACHE['checked'] >= .25 or _CACHE['checked'] < 0:
        _CACHE['checked'] = now
        path = store_path()
        try:
            stamp = (path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None
            if stamp != _CACHE['stamp']:
                rows = read()['cues'] if stamp else []
                cues=[]
                for raw in rows:
                    try:cues.append(safe_runtime_cue(raw))
                    except (ValueError,TypeError,KeyError,OverflowError):continue
                _CACHE.update(stamp=stamp, cues=cues)
        except (OSError, ValueError, KeyError):
            pass  # Retain the last good snapshot if a read fails; retry next poll.
    return _CACHE['cues']


def overlay(frame, device, now=None):
    """Exclusive, half-open cue overlays; no blocking clock or rendering state mutation."""
    now=time.monotonic() if now is None else now
    if getattr(getattr(device,'song_moment_off',None),'value',False):return frame,False
    snapshot=clock_snapshot(device,now)
    if snapshot is None:
        # A busy/orphaned clock must never block output or flash a fallback full frame.
        if getattr(device,'song_moment_clock',None) is not None:return np.zeros_like(frame),True
        return frame,False
    stamp,token,position,paused=snapshot;age=now-stamp
    if not token or age<0:return frame,False
    stale=age>.75
    if not paused and not stale:position+=age
    key=next((k for k,d in device.config['device_configs'].items() if d is device.device_config or d==device.device_config),None)
    matching=[c for c in cached_cues(now) if c['_token']==token and ('*' in c['targets'] or key in c['targets'])]
    active=[c for c in matching if not stale and c['start']<=position<c['end']]
    reserved=matching if stale else [c for c in matching if c['reserve']]
    if not active and not reserved:return frame,False
    result=np.array(frame,copy=True);count=result.shape[1]
    def bounds(c):return max(0,min(count,c['first']-1)),max(0,min(count,c['last'] if c['last'] is not None else count))
    for cue in reserved:
        lo,hi=bounds(cue);result[:,lo:hi]=0
    for cue in active:
        lo,hi=bounds(cue)
        if hi<=lo:continue
        result[:,lo:hi]=0
        result[:3,lo:hi]=render_cue(cue,hi-lo,position-cue['start']).astype(result.dtype)
    return result,True



def save_region(data, config):
    if not isinstance(data, dict):raise ValueError('Expected a named LED range')
    name = data.get('name')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:raise ValueError('Give the light group a short name')
    name = name.strip()
    device = data.get('device')
    if not isinstance(device, str) or device not in config['device_configs']:raise ValueError('Choose one existing string for this light group')
    first, last = data.get('first'), data.get('last')
    if type(first) is not int or type(last) is not int or not 1 <= first <= last <= config['device_configs'][device]['led_count']:
        raise ValueError('Choose an LED range inside this string')
    region_id = data.get('id') or uuid.uuid4().hex
    if not isinstance(region_id, str) or not re.fullmatch('[0-9a-f]{32}', region_id):raise ValueError('Invalid light-group identifier')
    region = {'id': region_id, 'name': name, 'device': device, 'first': first, 'last': last}
    with LOCK:
        document = read()
        regions = document.setdefault('regions', [])
        if any(r['name'].casefold() == name.casefold() and r['id'] != region_id for r in regions):raise ValueError('Choose a unique light-group name')
        index = next((i for i, r in enumerate(regions) if r['id'] == region_id), None)
        if index is None:
            if len(regions) >= 100:raise ValueError('This editor currently supports 100 named light groups')
            regions.append(region)
        else:regions[index] = region
        # Update references in one atomic write; existing songs follow the new wiring map.
        for cue in document['cues']:
            if cue.get('region') == region_id:cue.update(targets=[device], first=first, last=last)
        write(document)
    return region


def delete_region(region_id):
    if not isinstance(region_id, str):raise ValueError('Choose a named light group')
    with LOCK:
        document = read()
        regions = document.get('regions', [])
        remaining = [r for r in regions if r['id'] != region_id]
        if len(remaining) == len(regions):raise ValueError('Light group not found')
        document['regions'] = remaining
        # Retain the actual saved LED ranges in existing song cues.
        for cue in document['cues']:
            if cue.get('region') == region_id:cue['region'] = None
        write(document)
    return {'ok': True}
