import base64
import copy
from functools import wraps
import hmac
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
from libs.music_library import list_music_files, safe_music_path
from libs.notification_enum import NotificationEnum
from libs.notification_item import NotificationItem
from libs.studio_engine import StudioEngine
from libs.studio_fseq import write_fseq
from libs.studio_network import StudioCoordinator
from libs.studio_project import LOCK, ProjectRenderer, StudioStore, validate_project
from libs.webserver.executer import Executer

studio_api = Blueprint('studio_api', __name__)
_runtime = None
_preview_cache = {'key': None, 'renderer': None}


def services():
    global _runtime
    with LOCK:
        if _runtime is None:
            executer = Executer.instance.general_settings_executer
            store = StudioStore(executer.export_config_path.parent/'studio')
            def notify(kind, payload=None):
                executer.notification_queue_out.put(NotificationItem(kind, 'all_devices', payload))
            def acquire():
                token = secrets.token_hex(16)
                notify(NotificationEnum.studio_takeover, {'token': token})
                limit = time.monotonic()+5
                while time.monotonic() < limit:
                    try:
                        if json.loads((store.root/'ownership.json').read_text()).get('token') == token:
                            return
                    except (OSError, ValueError):
                        pass
                    time.sleep(.02)
                notify(NotificationEnum.studio_release)
                raise ValueError('Automatic player did not release the GPIO outputs; advanced playback was not started')
            engine = StudioEngine(store, acquire, lambda: notify(NotificationEnum.studio_release))
            _runtime = (store, engine, StudioCoordinator(store, engine))
        return _runtime


def checked(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, TypeError, KeyError, IndexError, OSError) as exc:
            return jsonify(error=str(exc)), 400
    return wrapper


def node_auth(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        key = request.headers.get('X-MLSC-Node-Key', '')
        if not hmac.compare_digest(key.encode('utf-8'), services()[0].node_settings()['key'].encode('utf-8')):
            return jsonify(error='Invalid Pi pairing key'), 403
        if request.content_length and request.content_length > 16*1024*1024:
            return jsonify(error='Node request too large'), 413
        return function(*args, **kwargs)
    return wrapper


@studio_api.get('/api/studio/config')
@login_required
@checked
def config():
    store, engine, coordinator = services()
    own = store.node_settings()
    config = Executer.instance.general_settings_executer._config
    candidates = list(config['device_configs'].values())
    device = candidates[0] if candidates else config['default_device']
    default_line = {'name': 'Main line', 'node': 'local', 'gpio': 21, 'count': device['led_count'],
        'first_pixel': 1, 'fps': min(25, device['fps']), 'offset_ms': 0,
        'brightness': device['led_brightness'], 'order': 'GRB', 'max_lit': 0, 'enabled': True}
    return jsonify(projects=store.list(), music=list_music_files(),
        local={'id': own['id'], 'name': own['name'], 'pairing_key': own['key']},
        nodes=[{k:n[k] for k in ('id','name','url')} for n in own['nodes']], default_output=default_line,
        status=coordinator.status(), spi_enabled=Path('/dev/spidev0.0').exists())


@studio_api.post('/api/studio/projects')
@login_required
@checked
def save_project():
    store = services()[0]
    project = validate_project(request.get_json())
    if project['asset'] and not store.asset_path(project['asset']).is_file():
        raise ValueError('Upload the associated FSEQ file first')
    return jsonify(project=store.save(project))


@studio_api.get('/api/studio/projects/<project_id>')
@login_required
@checked
def get_project(project_id):
    return jsonify(project=services()[0].load(project_id))


@studio_api.delete('/api/studio/projects/<project_id>')
@login_required
@checked
def delete_project(project_id):
    store, engine, coordinator = services()
    if engine.project and engine.project['id'] == project_id and engine.state not in ('idle','error'):
        raise ValueError('Stop this show before deleting it')
    store.project_path(project_id).unlink()
    return jsonify(ok=True)


@studio_api.post('/api/studio/import')
@login_required
@checked
def import_sequence():
    store = services()[0]
    if request.content_length and request.content_length > 1024*1024*1024:
        raise ValueError('FSEQ upload exceeds 1 GiB')
    upload = request.files.get('file')
    if not upload or not upload.filename.lower().endswith('.fseq'):
        raise ValueError('Choose a rendered .fseq sequence from xLights or Falcon Player')
    with tempfile.NamedTemporaryFile(dir=store.root/'assets', suffix='.upload', delete=False) as f:
        temporary = Path(f.name)
    try:
        upload.save(temporary)
        return jsonify(sequence=store.import_fseq(temporary))
    finally:
        temporary.unlink(missing_ok=True)


@studio_api.post('/api/studio/preview')
@login_required
@checked
def preview():
    store = services()[0]
    data = request.get_json()
    project = validate_project(data['project'])
    output = project['outputs'][int(data.get('output', 0))]
    signature = hashlib.sha256(json.dumps(project, sort_keys=True).encode()).hexdigest()
    with LOCK:
        if _preview_cache['key'] != signature:
            _preview_cache.update(key=signature, renderer=ProjectRenderer(project, store))
        frame = _preview_cache['renderer'].frame(float(data.get('time_ms', 0)), output)
    return jsonify(rgb=base64.b64encode(frame.T.tobytes()).decode(), count=output['count'])


@studio_api.get('/api/studio/export/<project_id>')
@login_required
@checked
def export_sequence(project_id):
    store = services()[0]
    project = store.load(project_id)
    renderer = ProjectRenderer(project, store)
    count = max((o['first_pixel']+o['count']-1 for o in project['outputs']), default=1)
    frames = (project['duration_ms']+project['frame_ms']-1)//project['frame_ms']
    if frames*count*3 > 256*1024*1024:
        raise ValueError('Web export exceeds 256 MiB. Split the show or use xLights/FPP for the large export.')
    line = {'first_pixel': 1, 'count': count, 'offset_ms': 0, 'brightness': 100, 'max_lit': 0}
    result = tempfile.TemporaryFile()
    write_fseq(Path('/proc/self/fd')/str(result.fileno()), frames, count*3, project['frame_ms'],
               (renderer.frame(i*project['frame_ms'], line).T.tobytes() for i in range(frames)))
    result.seek(0)
    return send_file(result, mimetype='application/octet-stream', as_attachment=True, download_name=project_id+'.fseq')


@studio_api.get('/api/studio/project-download/<project_id>')
@login_required
@checked
def download_project(project_id):
    project = services()[0].load(project_id)
    response = jsonify(project)
    response.headers['Content-Disposition'] = f'attachment; filename="{project_id}.json"'
    return response


@studio_api.post('/api/studio/play')
@login_required
@checked
def play():
    store, engine, coordinator = services()
    data = request.get_json()
    project = store.load(data['project'])
    if not any(o['enabled'] for o in project['outputs']):
        raise ValueError('Enable at least one output line')
    if 'test_output' in data:
        line = project['outputs'][int(data['test_output'])]
        project = {**project, 'outputs':[line], 'media':'', 'loop':False, 'duration_ms':3000, 'asset':'',
            'cues':[{'target':f"{line['first_pixel']}-{line['first_pixel']+line['count']-1}",
                     'start_ms':0,'duration_ms':3000,'effect':'chase','color':'#0080ff','period_ms':1000,'intensity':25}]}
        project = validate_project(project)
    return jsonify(coordinator.start(project)), 202


@studio_api.post('/api/studio/control')
@login_required
@checked
def control():
    coordinator = services()[2]
    command = request.get_json()['command']
    if command == 'stop': coordinator.stop()
    elif command == 'pause': coordinator.pause(True)
    elif command == 'resume': coordinator.pause(False)
    else: raise ValueError('Unknown command')
    return jsonify(coordinator.status())


@studio_api.get('/api/studio/status')
@login_required
def status():
    return jsonify(services()[2].status())


@studio_api.get('/api/studio/media/<filename>')
@login_required
@checked
def media_file(filename):
    return send_file(safe_music_path(filename), conditional=True)


@studio_api.post('/api/studio/nodes')
@login_required
@checked
def pair_node():
    data = request.get_json()
    return jsonify(node=services()[2].pair(data['url'], data['key']))


@studio_api.delete('/api/studio/nodes/<node_id>')
@login_required
@checked
def remove_node(node_id):
    services()[2].remove(node_id)
    return jsonify(ok=True)


@studio_api.get('/api/studio/node/info')
@node_auth
def node_info():
    own = services()[0].node_settings()
    return jsonify(id=own['id'], name=own['name'], time=time.time(), protocol=1, status=services()[1].status())


@studio_api.route('/api/studio/node/asset/<asset>', methods=['GET','POST'])
@node_auth
@checked
def node_asset(asset):
    store = services()[0]
    path = store.asset_path(asset)
    if request.method == 'GET':
        return jsonify(exists=path.is_file())
    data = request.get_json()
    chunk = base64.b64decode(data['data'], validate=True)
    if len(chunk) > 512*1024:
        raise ValueError('Transfer chunk too large')
    partial = path.with_suffix('.partial')
    with LOCK:
        offset = data['offset']
        if type(offset) is not int or not 0 <= offset <= 1024*1024*1024:
            raise ValueError('Invalid transfer offset')
        if offset == 0:
            partial.write_bytes(b'')
        if not partial.exists() or partial.stat().st_size != offset:
            raise ValueError('Transfer offset mismatch')
        with partial.open('ab') as f:
            f.write(chunk)
        if data.get('final'):
            result = store.import_fseq(partial)
            if result['asset'] != asset:
                raise ValueError('Transferred sequence checksum mismatch')
    return jsonify(received=offset+len(chunk))


@studio_api.post('/api/studio/node/<command>')
@node_auth
@checked
def node_command(command):
    store, engine, coordinator = services()
    data = request.get_json() or {}
    if command == 'prepare':
        project = validate_project(data['project'])
        if project['media'] or project['audio_device'] != 'none' or any(o['node'] != 'local' for o in project['outputs']):
            raise ValueError('Remote bundles must contain local outputs and no audio')
        store.save(project)
    elif command == 'start':
        epoch = float(data['epoch'])
        if not time.time()-1 <= epoch <= time.time()+600:
            raise ValueError('Remote start time is outside the scheduling window')
        engine.start(store.load(data['project']), epoch, remote=True)
    elif command == 'heartbeat':
        engine.heartbeat(float(data['position_ms']), bool(data.get('paused')))
    elif command == 'stop': engine.stop()
    else: raise ValueError('Unknown node command')
    return jsonify(ok=True, status=engine.status())


@studio_api.post('/api/studio/platform')
@login_required
@checked
def platform_setup():
    kind = request.get_json()['action']
    if kind == 'reboot':
        subprocess.Popen(['/usr/bin/systemctl','reboot'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify(message='Pi reboot requested')
    if kind not in ('spi','pwm'):
        raise ValueError('Choose SPI or remote PWM preparation')
    boot = Path('/boot/firmware') if Path('/boot/firmware/config.txt').exists() else Path('/boot')
    config = boot/'config.txt'
    if not config.is_file():
        raise ValueError('Pi boot configuration was not found')
    backup = config.with_name('config.txt.mlsc-'+str(time.time_ns())+'.bak')
    shutil.copy2(config, backup)
    text = config.read_text()
    if kind == 'spi':
        model = Path('/proc/device-tree/model').read_text(errors='ignore') if Path('/proc/device-tree/model').exists() else ''
        clock = 500 if 'Pi 4' in model else 250
        text += f'\n[all]\n# MLSC Advanced SPI output\ndtparam=spi=on\ncore_freq={clock}\ncore_freq_min={clock}\n'
        command = boot/'cmdline.txt'
        if not command.is_file():
            raise ValueError('Pi command-line configuration was not found')
        shutil.copy2(command, command.with_name('cmdline.txt.mlsc-'+str(time.time_ns())+'.bak'))
        words = [w for w in command.read_text().split() if not w.startswith('spidev.bufsiz=')]
        command.write_text(' '.join(words+['spidev.bufsiz=131072'])+'\n')
    else:
        text += '\n[all]\n# MLSC remote PWM output: disables built-in headphone audio\ndtparam=audio=off\n'
        Path('/etc/modprobe.d/mlsc-studio-pwm.conf').write_text('blacklist snd_bcm2835\n')
    config.write_text(text)
    return jsonify(message='Hardware preparation saved. Reboot this Pi to apply.', reboot_required=True, backup=str(backup))
