"""Web-managed advanced show projects and bounded frame rendering."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading
import uuid

import numpy as np
from libs.studio_fseq import FSEQReader

LOCK = threading.RLock()
ID = re.compile(r'^[a-f0-9]{32}$')
COLORS = re.compile(r'^#[a-fA-F0-9]{6}$')
PINS = {21: ('pcm', 0), 10: ('spi', 0), 18: ('pwm', 0), 12: ('pwm', 0), 13: ('pwm', 1), 19: ('pwm', 1)}


def number(value, low, high, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}')
    if integer and int(value) != value:
        raise ValueError(f'{name} must be an integer')
    return int(value) if integer else float(value)


def ranges(text, maximum=10_000_000):
    result = []
    for token in str(text).replace(' ', '').split(','):
        if not token:
            continue
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', token)
        if not match:
            raise ValueError('Pixel targets use numbers and ranges, for example 1,5,20-50')
        first, last = int(match[1]), int(match[2] or match[1])
        if not 1 <= first <= last <= maximum:
            raise ValueError('Invalid pixel range')
        result.append((first, last))
    if len(result) > 2048:
        raise ValueError('Too many target ranges; combine adjacent pixels')
    return result


def validate_project(data):
    if not isinstance(data, dict):
        raise ValueError('Project must be an object')
    p = {'id': str(data.get('id') or uuid.uuid4().hex), 'name': str(data.get('name', 'New show'))[:120],
         'media': str(data.get('media', '')), 'asset': str(data.get('asset', '')),
         'audio_device': data.get('audio_device', 'headphones'),
         'audio_offset_ms': number(data.get('audio_offset_ms', 0), -10000, 10000, 'Audio offset'),
         'duration_ms': number(data.get('duration_ms', 180000), 1, 14_400_000, 'Duration', True),
         'frame_ms': number(data.get('frame_ms', 40), 1, 255, 'Frame interval', True),
         'groups': {}, 'outputs': [], 'cues': [], 'loop': bool(data.get('loop', False))}
    if not ID.fullmatch(p['id']):
        raise ValueError('Invalid project ID')
    if p['asset'] and re.fullmatch(r'[a-f0-9]{64}\.fseq', p['asset']) is None:
        raise ValueError('Invalid sequence asset')
    if p['media'] and (Path(p['media']).name != p['media'] or '\\' in p['media']):
        raise ValueError('Choose a music-library filename')
    if p['audio_device'] not in ('headphones', 'none'):
        raise ValueError('Choose built-in headphones or no audio')
    groups = data.get('groups', {})
    if not isinstance(groups, dict) or len(groups) > 1000:
        raise ValueError('Invalid groups')
    for name, targets in groups.items():
        if not re.fullmatch(r'[\w -]{1,80}', name):
            raise ValueError('Group names use letters, numbers, spaces, underscores or hyphens')
        ranges(targets)
        p['groups'][name] = str(targets)
    outputs = data.get('outputs', [])
    if not isinstance(outputs, list) or len(outputs) > 512:
        raise ValueError('Too many output lines')
    occupied = set()
    for index, out in enumerate(outputs):
        pin = number(out.get('gpio', 21), 0, 53, 'GPIO', True)
        if pin not in PINS:
            raise ValueError('Supported data pins: GPIO21 PCM, GPIO10 SPI, GPIO18/12 PWM0, GPIO13/19 PWM1')
        node = str(out.get('node', 'local'))
        if node != 'local' and not ID.fullmatch(node):
            raise ValueError('Choose a paired Pi for this output')
        backend, channel = PINS[pin]
        count = number(out.get('count', 300), 1, 5400 if backend == 'pcm' else 2700 if backend == 'pwm' else 10000, 'LED count', True)
        fps = number(out.get('fps', 25), 1, 100, 'Output FPS')
        if fps > 1 / (count*30e-6 + .004) + .001:
            raise ValueError(f'Output {index+1}: requested FPS is too high for {count} RGB LEDs; use at most {1/(count*30e-6+.004):.1f} FPS')
        enabled = bool(out.get('enabled', True))
        if enabled and (node, backend, channel) in occupied:
            raise ValueError('Two enabled outputs use the same hardware channel on the same Pi')
        if enabled:
            occupied.add((node, backend, channel))
        if enabled and node == 'local' and backend == 'pwm' and p['audio_device'] == 'headphones':
            raise ValueError('PWM outputs conflict with built-in headphone audio. Use GPIO21/10 or a remote Pi with audio set to none.')
        order = out.get('order', 'GRB')
        if order not in ('RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR'):
            raise ValueError('Invalid RGB channel order')
        p['outputs'].append({'name': str(out.get('name', f'Line {index+1}'))[:80], 'node': node,
            'gpio': pin, 'count': count, 'first_pixel': number(out.get('first_pixel', 1), 1, 10_000_000, 'First pixel', True),
            'fps': fps, 'offset_ms': number(out.get('offset_ms', 0), -10000, 10000, 'Line offset'),
            'brightness': number(out.get('brightness', 40), 0, 100, 'Brightness'), 'order': order,
            'max_lit': number(out.get('max_lit', 0), 0, count, 'Maximum lit LEDs', True), 'enabled': enabled})
    for node in {o['node'] for o in p['outputs']}:
        pwm = [o for o in p['outputs'] if o['enabled'] and o['node'] == node and PINS[o['gpio']][0] == 'pwm']
        if pwm:
            common_limit = 1/(max(o['count'] for o in pwm)*30e-6+.004)
            if any(o['fps'] > common_limit+.001 for o in pwm):
                raise ValueError(f'The PWM lines share a refresh context; use at most {common_limit:.1f} FPS on both')
    cues = data.get('cues', [])
    if not isinstance(cues, list) or len(cues) > 20000:
        raise ValueError('Too many cues')
    for c in cues:
        target = str(c.get('target', '1-50'))
        if target.startswith('@'):
            if target[1:] not in p['groups']:
                raise ValueError('Cue refers to an unknown group')
        else:
            ranges(target)
        color = str(c.get('color', '#ff0000'))
        effect = c.get('effect', 'solid')
        if not COLORS.fullmatch(color) or effect not in ('solid', 'fade', 'pulse', 'chase', 'sparkle', 'blackout'):
            raise ValueError('Invalid cue color or effect')
        start = number(c.get('start_ms', 0), 0, p['duration_ms'], 'Cue start', True)
        duration = number(c.get('duration_ms', 1000), 1, p['duration_ms'], 'Cue duration', True)
        if start + duration > p['duration_ms']:
            raise ValueError('A cue extends beyond the show duration')
        p['cues'].append({'id': str(c.get('id') or uuid.uuid4().hex)[:80], 'target': target,
            'start_ms': start, 'duration_ms': duration, 'effect': effect, 'color': color,
            'intensity': number(c.get('intensity', 100), 0, 100, 'Cue intensity'),
            'period_ms': number(c.get('period_ms', 500), 40, 60000, 'Effect period'),
            'power': bool(c.get('power', False))})
    return p


class StudioStore:
    def __init__(self, root):
        self.root = Path(root)
        for name in ('projects', 'assets'):
            (self.root/name).mkdir(parents=True, exist_ok=True)

    def atomic(self, path, value):
        path = Path(path)
        with LOCK:
            temp = path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
            try:
                temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
                temp.chmod(0o600)
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)

    def project_path(self, project_id):
        if not ID.fullmatch(project_id):
            raise ValueError('Invalid project ID')
        return self.root/'projects'/(project_id+'.json')

    def save(self, data):
        p = validate_project(data)
        self.atomic(self.project_path(p['id']), p)
        return p

    def load(self, project_id):
        return validate_project(json.loads(self.project_path(project_id).read_text()))

    def list(self):
        return [{'id': p.stem, 'name': json.loads(p.read_text()).get('name', p.stem)} for p in sorted((self.root/'projects').glob('*.json'))]

    def asset_path(self, name):
        if re.fullmatch(r'[a-f0-9]{64}\.fseq', name) is None:
            raise ValueError('Invalid asset name')
        return self.root/'assets'/name

    def import_fseq(self, path):
        reader = FSEQReader(path)
        # Validate the first decoded block before accepting an upload.
        reader.pixels(0, 1, min(100, (reader.total_channels+2)//3))
        digest = hashlib.sha256()
        with Path(path).open('rb') as source:
            for chunk in iter(lambda: source.read(1024*1024), b''):
                digest.update(chunk)
        name = digest.hexdigest()+'.fseq'
        destination = self.asset_path(name)
        if Path(path).resolve() != destination.resolve():
            os.replace(path, destination)
        return {'asset': name, **reader.info()}

    def node_settings(self):
        path = self.root/'nodes.json'
        with LOCK:
            if not path.exists():
                self.atomic(path, {'id': uuid.uuid4().hex, 'name': os.uname().nodename,
                                   'key': secrets.token_urlsafe(32), 'nodes': []})
            return json.loads(path.read_text())


class ProjectRenderer:
    def __init__(self, project, store):
        self.project = validate_project(project)
        self.sequence = FSEQReader(store.asset_path(project['asset'])) if project.get('asset') else None
        self.compiled = []
        for cue in self.project['cues']:
            targets = self.project['groups'][cue['target'][1:]] if cue['target'].startswith('@') else cue['target']
            color = np.array([int(cue['color'][i:i+2], 16) for i in (1, 3, 5)], dtype=float)[:, None] * cue['intensity']/100
            self.compiled.append((cue, ranges(targets), color))

    def frame(self, milliseconds, output):
        t = milliseconds - output.get('offset_ms', 0)
        first, count = output['first_pixel'], output['count']
        frame = self.sequence.pixels(t, first, count).astype(float) if self.sequence else np.zeros((3, count))
        power = False
        if t < 0 or t >= self.project['duration_ms']:
            return np.zeros((3, count), dtype=np.uint8)
        for cue, targets, color in self.compiled:
            elapsed = t-cue['start_ms']
            if not 0 <= elapsed < cue['duration_ms']:
                continue
            for low, high in targets:
                left, right = max(low, first), min(high, first+count-1)
                if left > right:
                    continue
                x = np.arange(left, right+1)
                amplitude = np.ones(len(x))
                if cue['effect'] == 'fade':
                    amplitude *= elapsed/cue['duration_ms']
                elif cue['effect'] == 'pulse':
                    amplitude *= .5-.5*np.cos(2*np.pi*elapsed/cue['period_ms'])
                elif cue['effect'] == 'chase':
                    phase = ((x-low)/max(1, high-low+1)-elapsed/cue['period_ms']) % 1
                    amplitude *= np.maximum(0, 1-phase/.15)
                elif cue['effect'] == 'sparkle':
                    tick = int(elapsed/cue['period_ms'])
                    amplitude *= ((x*1103515245 + tick*12345) % 101) < 12
                elif cue['effect'] == 'blackout':
                    amplitude *= 0
                frame[:, left-first:right-first+1] = color*amplitude
                power = power or cue['power']
        cap = output.get('max_lit', 0)
        if cap and not power:
            strength = np.max(frame, axis=0)
            if np.count_nonzero(strength) > cap:
                keep = np.argpartition(strength, -cap)[-cap:]
                mask = np.ones(count, dtype=bool); mask[keep] = False
                frame[:, mask] = 0
        return np.clip(frame*output.get('brightness', 100)/100, 0, 255).astype(np.uint8)
