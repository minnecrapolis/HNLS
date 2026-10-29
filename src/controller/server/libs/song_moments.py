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
EFFECTS = ('solid', 'flash', 'color_scroll', 'blackout')


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
    return {'id': cue_id, 'region': region_id or None, 'file': filename, 'start': start, 'end': end,
            'effect': effect, 'targets': targets, 'first': first, 'last': last,
            'color': colors[0].lower(), 'color2': colors[1].lower(),
            'speed': number(data.get('speed', 1), .1, 5, 'Effect speed'),
            'brightness': number(data.get('brightness', 100), 0, 100, 'Moment brightness'),
            'reserve': data.get('reserve', False)}


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
                cues = read()['cues'] if stamp else []
                _CACHE.update(stamp=stamp, cues=cues)
        except (OSError, ValueError, KeyError):
            _CACHE.update(stamp=None, cues=[])
    return _CACHE['cues']


def overlay(frame, device, now=None):
    """Return (frame, applied): half-open times, RGB logic, last saved row wins."""
    now = time.monotonic() if now is None else now
    if getattr(getattr(device, 'song_moment_off', None), 'value', False):
        return frame, False
    clock = getattr(device, 'song_moment_clock', None)
    if clock is None:
        return frame, False
    with clock.get_lock():
        age = now-clock.value
        token = device.song_moment_token.value
        position = device.song_moment_position.value+age
    if not token or age < 0:
        return frame, False
    fresh = age <= .18
    key = next((k for k, d in device.config['device_configs'].items() if d is device.device_config or d == device.device_config), None)
    matching = [c for c in cached_cues(now) if song_token(c['file']) == token and ('*' in c['targets'] or key in c['targets'])]
    active = [c for c in matching if fresh and c['start'] <= position < c['end']]
    reserved = [c for c in matching if c['reserve']]
    if not active and not reserved:
        return frame, False
    result = np.array(frame, copy=True)
    count = result.shape[1]
    def bounds(c):
        return max(0, min(count, c['first']-1)), max(0, min(count, c['last'] if c['last'] is not None else count))
    for cue in reserved:
        lo, hi = bounds(cue)
        result[:, lo:hi] = 0
    for cue in active:
        lo, hi = bounds(cue)
        if hi <= lo:
            continue
        elapsed = position-cue['start']
        color = np.array([int(cue['color'][n:n+2], 16) for n in (1, 3, 5)])[:, None].astype(float)
        factor = cue['brightness']/100.
        effect = cue['effect']
        if effect == 'blackout' or (effect == 'flash' and (elapsed*2*cue['speed']) % 1 >= .5):
            color = np.zeros((3, 1))
        elif effect == 'color_scroll':
            second = np.array([int(cue['color2'][n:n+2], 16) for n in (1, 3, 5)])[:, None]
            phase = (np.arange(hi-lo)/32. - elapsed*cue['speed']) % 1.
            blend = (1-np.cos(2*np.pi*phase))[None, :]/2.
            color = color*(1-blend)+second*blend
        result[:3, lo:hi] = (color*factor).clip(0, 255).astype(result.dtype)
        if result.shape[0] > 3:
            result[3:, lo:hi] = 0
    return result, True



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
