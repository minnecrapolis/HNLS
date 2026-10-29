"""Explicitly paired LAN Pi nodes with preloaded assets and clock correction."""
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from libs.studio_project import ID, LOCK


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def node_url(url):
    parsed = urllib.parse.urlsplit(url.rstrip('/'))
    if parsed.scheme != 'http' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Enter the Pi LAN URL, for example http://192.168.1.50:8080')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 80, type=socket.SOCK_STREAM)
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not (ip.is_private or ip.is_loopback) or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise ValueError('Pi nodes must be on your trusted local network')
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))


def request_node(node, route, data=None, timeout=4):
    url = node_url(node['url'])+route
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers={
        'X-MLSC-Node-Key': node['key'], 'Content-Type': 'application/json'},
        method='POST' if body is not None else 'GET')
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            return json.loads(response.read(16*1024*1024))
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode('utf-8', 'replace')
        raise ValueError(f"Pi {node.get('name',node['url'])}: HTTP {exc.code}: {detail}") from exc


class StudioCoordinator:
    def __init__(self, store, engine):
        self.store, self.engine = store, engine
        self.thread, self.remote_nodes = None, []
        self.cancel = threading.Event()
        self.preparing, self.error, self.message = False, '', ''

    def pair(self, url, key):
        if not isinstance(key, str) or not 20 <= len(key) <= 200:
            raise ValueError('Copy the pairing key from the other Pi Advanced Users page')
        node = {'url': node_url(url), 'key': key}
        info = request_node(node, '/api/studio/node/info')
        own = self.store.node_settings()
        if info['id'] == own['id'] or not ID.fullmatch(info['id']):
            raise ValueError('This is the current Pi; choose another Pi')
        node.update(id=info['id'], name=info['name'])
        with LOCK:
            own['nodes'] = [n for n in own['nodes'] if n['id'] != node['id']]+[node]
            self.store.atomic(self.store.root/'nodes.json', own)
        return {'id': node['id'], 'name': node['name'], 'url': node['url']}

    def remove(self, node_id):
        if self.preparing or self.engine.state in ('starting','playing','paused'):
            raise ValueError('Stop the advanced show before removing a Pi')
        with LOCK:
            own = self.store.node_settings()
            own['nodes'] = [n for n in own['nodes'] if n['id'] != node_id]
            self.store.atomic(self.store.root/'nodes.json', own)

    def _prepare(self, node, project):
        remote = copy.deepcopy(project)
        remote['outputs'] = [dict(o, node='local') for o in project['outputs'] if o['node'] == node['id'] and o['enabled']]
        remote['media'], remote['audio_device'] = '', 'none'
        if project['asset']:
            asset = project['asset']
            exists = request_node(node, '/api/studio/node/asset/'+asset).get('exists')
            if not exists:
                offset = 0
                with self.store.asset_path(asset).open('rb') as source:
                    while True:
                        chunk = source.read(512*1024)
                        if self.cancel.is_set():
                            raise ValueError('Preparation canceled')
                        result = request_node(node, '/api/studio/node/asset/'+asset,
                            {'offset': offset, 'data': base64.b64encode(chunk).decode(), 'final': not chunk},
                            timeout=60 if not chunk else 10)
                        offset += len(chunk)
                        self.message = f"Transferring sequence to {node['name']}: {offset/1048576:.1f} MiB"
                        if not chunk:
                            break
        request_node(node, '/api/studio/node/prepare', {'project': remote})
        samples = []
        for _ in range(3):
            before = time.time()
            info = request_node(node, '/api/studio/node/info')
            after = time.time()
            samples.append((after-before, info['time']-(before+after)/2))
        latency, offset = min(samples)
        return {**node, 'clock_offset': offset, 'latency': latency}

    def start(self, project):
        self.stop()
        self.cancel = threading.Event()
        self.error, self.message, self.preparing = '', 'Preparing project and Pi nodes…', True
        self.thread = threading.Thread(target=self._play, args=(project,), daemon=True)
        self.thread.start()
        return self.status()

    def _play(self, project):
        started = []
        try:
            nodes = {n['id']: n for n in self.store.node_settings()['nodes']}
            required = sorted({o['node'] for o in project['outputs'] if o['enabled'] and o['node'] != 'local'})
            prepared = []
            for key in required:
                if key not in nodes:
                    raise ValueError('A project output references an unpaired Pi')
                self.message = 'Preparing '+nodes[key]['name']
                prepared.append(self._prepare(nodes[key], project))
            if self.cancel.is_set():
                return
            # A remote may need time to release its automatic GPIO owner.
            lead = max([0,-project['audio_offset_ms']]+[-o['offset_ms'] for o in project['outputs']])/1000
            epoch = time.time()+5+8*((len(prepared)+7)//8)+lead
            def start_node(node):
                request_node(node, '/api/studio/node/start', {'project': project['id'], 'epoch': epoch+node['clock_offset']}, timeout=8)
                return node
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(start_node, node) for node in prepared]
                failures = []
                for future in futures:
                    try: started.append(future.result())
                    except Exception as exc: failures.append(exc)
                if failures:
                    raise failures[0]
            self.remote_nodes = started
            if self.cancel.is_set():
                return
            self.engine.start(project, epoch=epoch)
            self.preparing = False
            self.message = ''
            while not self.cancel.wait(1):
                status = self.engine.status()
                if status['state'] in ('idle','error'):
                    break
                for node in started:
                    try:
                        request_node(node, '/api/studio/node/heartbeat',
                            {'position_ms': status['position_ms']+node['latency']*500,
                             'paused': status['paused']}, timeout=2)
                    except Exception as exc:
                        self.message = str(exc)
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.preparing = False
            for node in started:
                try:
                    request_node(node, '/api/studio/node/stop', {}, timeout=2)
                except Exception:
                    pass
            self.remote_nodes = []

    def status(self):
        return {**self.engine.status(), 'preparing': self.preparing,
                'error': self.error or self.engine.error, 'message': self.message,
                'remote_count': len(self.remote_nodes)}

    def pause(self, paused):
        self.engine.set_paused(paused)
        status = self.engine.status()
        for node in self.remote_nodes:
            request_node(node, '/api/studio/node/heartbeat', {'position_ms': status['position_ms'], 'paused': paused})

    def stop(self):
        self.cancel.set()
        self.engine.stop()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=12)
            if self.thread.is_alive():
                raise ValueError('Remote requests are still stopping; wait a moment and retry')
        self.thread = None
