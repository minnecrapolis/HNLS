"""Web pairing and asynchronous authenticated UDP output for remote RGB Pis."""
from copy import deepcopy
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener

from libs.remote_protocol import HTTP_PORT, UDP_PORT, MAX_LEDS, packets

LOCK = threading.RLock()
ORDERS = ('RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR')


def store_path():
    return Path(__file__).resolve().parents[3]/'.mlsc/remote_pis.json'


def load():
    path = store_path()
    return json.loads(path.read_text()) if path.is_file() else {}


def save(nodes):
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(nodes, output, indent=2)
    temporary.chmod(0o600)
    temporary.replace(path)


def validate_host(host):
    try:
        address = ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, TypeError):
        raise ValueError('Enter the other Pi’s private IPv4 address, for example 192.168.1.34') from None
    # Explicit RFC1918 LAN destinations; never proxy pairing keys to public servers.
    if not any(address in ipaddress.IPv4Network(network) for network in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise ValueError('Use a private LAN IPv4 address')
    return str(address)


def call(node, endpoint='/status', data=None, timeout=2):
    host = validate_host(node['host'])
    request = Request('http://'+host+':'+str(HTTP_PORT)+endpoint,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Authorization': 'Bearer '+node['key'], 'Content-Type': 'application/json'})
    # Private LAN traffic never uses environment HTTP proxies or follows redirects.
    from urllib.request import HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=timeout) as response:
            body = response.read(8193)
            if len(body) > 8192:
                raise ValueError('Invalid receiver response')
            result = json.loads(body)
    except HTTPError as exc:
        if exc.code == 401:
            raise ValueError('Pairing key was rejected by the remote Pi') from None
        raise ValueError('Receiver request failed (HTTP '+str(exc.code)+'). Check its service log.') from None
    except (OSError, URLError, ValueError) as exc:
        raise ValueError('Cannot reach the receiver at '+host+': '+str(exc)) from None
    if not isinstance(result, dict) or result.get('protocol') != 'mlsc-remote-1':
        raise ValueError('This address is not an MLSC remote receiver')
    return result


def node_for(device):
    config = device.device_config
    if config.get('output_type') != 'output_udp':
        return None
    output = config['output']['output_udp']
    for key, value in device.config['device_configs'].items():
        if value is config or value == config:
            node = load().get(key)
            if (node and node['host'] == output['udp_client_ip']
                    and int(output['udp_client_port']) == UDP_PORT):
                return node
    return None


def add_remote(executer, data):
    if not isinstance(data, dict):
        raise ValueError('Expected remote Pi settings')
    key_text = data.get('key', '')
    if not isinstance(key_text, str):
        raise ValueError('Paste the receiver pairing key')
    node = {'host': validate_host(data.get('host')), 'key': key_text.strip()}
    if not re.fullmatch('[0-9a-f]{64}', node['key']):
        raise ValueError('Paste the complete 64-character receiver pairing key')
    count, brightness = data.get('count'), data.get('brightness', 10)
    order, name = data.get('order', 'GRB'), data.get('name', 'LED-SLAVE')
    if type(count) is not int or not 7 <= count <= MAX_LEDS:
        raise ValueError('Choose 7–2500 RGB LEDs for this GPIO21 receiver')
    if type(brightness) is not int or not 0 <= brightness <= 100:
        raise ValueError('Brightness must be between 0 and 100')
    if order not in ORDERS:
        raise ValueError('Choose the physical RGB color order')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_ ()-]{1,80}', name.strip()):
        raise ValueError('Use a short name with letters, numbers, spaces, parentheses or hyphens')
    name = name.strip()
    with LOCK:
        config, nodes = executer._config, load()
        devices = config['device_configs']
        source = data.get('source')
        if not isinstance(source, str) or source not in devices:
            raise ValueError('Choose an existing source device')
        if any(device['device_name'] == name for device in devices.values()):
            raise ValueError('Choose a unique device name')
        if any(n['host'] == node['host'] and key in devices for key, n in nodes.items()):
            raise ValueError('This Pi already has a device entry. Select it below to adjust its settings.')
        key = next(('device_'+str(i) for i in range(100) if 'device_'+str(i) not in devices), None)
        if key is None:
            raise ValueError('Device limit reached')
        # Verify key, protocol and reachability before making any local changes.
        status = call(node)
        if status.get('hostname') == socket.gethostname():
            raise ValueError('Choose a different Pi')
        device = deepcopy(devices[source])
        device.update(device_name=name, led_count=count, led_mid=max(1, count//2),
                      led_brightness=brightness, led_strip='ws2811_strip_'+order.lower(),
                      output_type='output_udp', device_groups={})
        device['fps'] = max(1, min(25, int(device['fps']), int(1/(count*30e-6+.004))))
        device['output']['output_udp'].update(udp_client_ip=node['host'], udp_client_port=UDP_PORT)
        show = device['effects']['effect_song_show']
        if show.get('sync_mode') == 'custom' and len(show.get('sync_groups', [])) != math.ceil(count/show.get('section_size', 50)):
            show.update(sync_mode='paired', sync_groups=[])
        if show.get('max_lit_leds', 0) > count:
            show['max_lit_leds'] = count
        device['effects']['last_effect'] = 'effect_song_show'
        old_nodes = deepcopy(nodes)
        nodes[key] = node
        save(nodes)
        devices[key] = device
        try:
            executer.save_config()
        except Exception:
            devices.pop(key, None)
            save(old_nodes)
            raise
        from libs.notification_enum import NotificationEnum
        executer.put_into_notification_queue(NotificationEnum.song_show_refresh, key)
        return {'ok': True, 'device': key, 'name': name, 'hostname': status['hostname']}


def list_remote(executer):
    devices = executer._config['device_configs']
    nodes = load()
    return {'sources': [{'id': key, 'name': d['device_name']} for key, d in devices.items()],
            'nodes': [{'device': key, 'name': devices[key]['device_name'], 'host': node['host']}
                      for key, node in nodes.items() if key in devices]}


class RemoteSender:
    """Output process only enqueues the newest frame; network work cannot block it."""
    def __init__(self, node, config):
        self.node, self.config = node, config
        self.lock, self.event, self.stop = threading.Lock(), threading.Event(), threading.Event()
        self.latest, self.session, self.sequence = None, None, 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(.05)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def show(self, array):
        frame = (array[:3] * (float(self.config['led_brightness'])/100.)).clip(0, 255).astype('uint8').tobytes('F')
        if len(frame) != self.config['led_count']*3:
            return
        with self.lock:
            self.latest = (frame, time.monotonic())
        self.event.set()

    def run(self):
        retry, poll, errors = 0., 0., 0
        settings = {'count': self.config['led_count'], 'order': self.config['led_strip'].rsplit('_', 1)[-1].upper()}
        try:
            while not self.stop.is_set():
                self.event.wait(.1)
                self.event.clear()
                now = time.monotonic()
                try:
                    if self.session is None:
                        if now < retry:
                            continue
                        result = call(self.node, '/session', settings, timeout=5)
                        self.session = bytes.fromhex(result['session'])
                        self.sequence, poll, errors = 0, time.monotonic()+2., 0
                    elif now >= poll:
                        state = call(self.node, timeout=1)
                        poll = time.monotonic()+2.
                        if state['session'] != self.session.hex():
                            self.session = None
                            continue
                    with self.lock:
                        latest, self.latest = self.latest, None
                    # Drop old frames after reconnection; don't replay queued history.
                    if latest is not None and time.monotonic()-latest[1] <= .2:
                        self.sequence += 1
                        for packet in packets(latest[0], self.node['key'].encode(), self.session, self.sequence):
                            self.socket.sendto(packet, (self.node['host'], UDP_PORT))
                except Exception as exc:
                    self.session, retry = None, time.monotonic()+2.
                    if errors == 0:
                        from loguru import logger
                        logger.warning('Remote Pi {} unavailable: {}', self.node['host'], exc)
                    errors += 1
        finally:
            if self.session:
                try:
                    self.sequence += 1
                    for packet in packets(bytes(self.config['led_count']*3), self.node['key'].encode(), self.session, self.sequence):
                        self.socket.sendto(packet, (self.node['host'], UDP_PORT))
                except OSError:
                    pass
            self.socket.close()

    def close(self):
        self.stop.set()
        self.event.set()
        self.thread.join(timeout=.5)
        # Receiver watchdog also blanks the output if a network call is in flight.


def validate_devices(config):
    nodes = load()
    for key, device in config['device_configs'].items():
        if key not in nodes:
            continue
        node = nodes[key]
        if device['output_type'] != 'output_udp':
            raise ValueError('Remote Pi devices use network output. Delete and re-add this device to change its controller.')
        output = device['output']['output_udp']
        if output['udp_client_ip'] != node['host'] or int(output['udp_client_port']) != UDP_PORT:
            raise ValueError('Remote Pi network settings are paired. Delete and re-add the device to change its address.')
        if type(device['led_count']) is not int or not 7 <= device['led_count'] <= MAX_LEDS:
            raise ValueError('This GPIO21 receiver supports 7–2500 RGB LEDs per line')
        if device['led_strip'] not in ['ws2811_strip_'+order.lower() for order in ORDERS]:
            raise ValueError('Remote receiver requires a physical RGB color order, such as ws2811_strip_grb')
        maximum = max(1, int(1/(device['led_count']*30e-6+.004)))
        if device['fps'] > min(25, maximum):
            raise ValueError('Lower Maximum FPS to '+str(min(25, maximum))+' or less for this remote LED count')


def forget(device):
    with LOCK:
        nodes = load()
        if device in nodes:
            nodes.pop(device)
            save(nodes)
