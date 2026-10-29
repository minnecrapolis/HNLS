#!/usr/bin/env python3
"""Small Python 3.9-compatible receiver. GPIO access stays on the main thread."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import secrets
import signal
import socket
import threading
import time

from remote_protocol import Assembler, MAX_LEDS, HTTP_PORT, UDP_PORT

ORDERS = ('RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR')


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Expected LED settings')
    count, order = data.get('count'), data.get('order')
    if type(count) is not int or not 7 <= count <= MAX_LEDS:
        raise ValueError('This receiver supports 7–2500 RGB LEDs on GPIO21')
    if order not in ORDERS:
        raise ValueError('Choose a valid physical RGB color order')
    return {'count': count, 'order': order}


class Pixels:
    def __init__(self, settings):
        import rpi_ws281x as ws
        self.ws = ws
        self.strip = ws.PixelStrip(settings['count'], 21, freq_hz=800000, dma=10,
                                   invert=False, brightness=255, channel=0,
                                   strip_type=getattr(ws, 'WS2811_STRIP_'+settings['order']))
        self.strip.begin()
        self.count = settings['count']
        self.show(bytes(self.count*3))

    def show(self, frame):
        for i in range(self.count):
            r, g, b = frame[i*3:i*3+3]
            self.strip.setPixelColor(i, (r << 16) | (g << 8) | b)
        self.strip.show()

    def close(self):
        self.show(bytes(self.count*3))
        self.strip._cleanup()


class Receiver:
    def __init__(self, key, pixels_factory=Pixels, clock=time.monotonic, settings_file=None):
        self.key, self.factory, self.clock = key.encode(), pixels_factory, clock
        self.commands = queue.Queue(maxsize=4)
        self.lock = threading.RLock()
        self.settings, self.pixels, self.assembler = None, None, None
        self.peer, self.session = None, None
        self.last_frame, self.frames, self.blackout, self.error = 0., 0, True, ''
        self.running = True
        self.settings_file = settings_file

    def status(self):
        with self.lock:
            return {'protocol': 'mlsc-remote-1', 'hostname': socket.gethostname(), 'gpio': 21,
                    'physical_pin': 40, 'max_leds': MAX_LEDS, 'settings': self.settings,
                    'session': self.session.hex() if self.session else None,
                    'receiving': bool(self.assembler and not self.blackout), 'frames': self.frames,
                    'last_frame_age': round(self.clock()-self.last_frame, 2) if self.frames else None,
                    'error': self.error}

    def start_session(self, data, peer):
        settings = validate(data)
        with self.lock:
            # Invalidate the previous owner before reconfiguring the native output.
            self.assembler = None
            self.blackout = True
            try:
                if self.settings != settings or self.pixels is None:
                    if self.pixels:
                        self.pixels.close()
                        self.pixels = None
                    self.pixels = self.factory(settings)
                    self.settings = settings
                else:
                    self.pixels.show(bytes(settings['count']*3))
                if self.settings_file:
                    temporary = self.settings_file.with_suffix('.tmp')
                    temporary.write_text(json.dumps(settings))
                    temporary.chmod(0o600)
                    temporary.replace(self.settings_file)
                self.error = ''
            except Exception as exc:
                self.error = 'GPIO21 initialization failed: '+str(exc)
                raise ValueError(self.error) from exc
            self.session, self.peer = secrets.token_bytes(8), peer
            self.assembler = Assembler(self.key, self.session, settings['count'])
            self.last_frame = self.clock()
            return self.status()

    def process_commands(self):
        try:
            data, peer, done, result, cancelled = self.commands.get_nowait()
        except queue.Empty:
            return
        if cancelled.is_set():
            done.set()
            return
        try:
            result.update(self.start_session(data, peer))
        except Exception as exc:
            result['error'] = str(exc)
        finally:
            done.set()

    def feed(self, packet, peer):
        now = self.clock()
        with self.lock:
            if self.assembler is None or peer != self.peer:
                return False
            frame = self.assembler.feed(packet, now)
            if frame is None:
                return False
            self.pixels.show(frame)
            self.last_frame, self.blackout = now, False
            self.frames += 1
            return True

    def tick(self):
        with self.lock:
            if self.pixels and not self.blackout and self.clock()-self.last_frame > 1.:
                self.pixels.show(bytes(self.settings['count']*3))
                self.blackout = True

    def close(self):
        if self.pixels:
            self.pixels.close()
            self.pixels = None


def handler_for(receiver):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *args):
            pass  # Never log request credentials.

        def reply(self, code, data):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authenticated(self):
            provided = self.headers.get('Authorization', '').encode()
            return hmac.compare_digest(provided, b'Bearer '+receiver.key)

        def do_GET(self):
            if not self.authenticated():
                return self.reply(401, {'error': 'Pairing key required'})
            if self.path != '/status':
                return self.reply(404, {'error': 'Unknown endpoint'})
            self.reply(200, receiver.status())

        def do_POST(self):
            if not self.authenticated():
                return self.reply(401, {'error': 'Pairing key required'})
            if self.path != '/session':
                return self.reply(404, {'error': 'Unknown endpoint'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= 2048:
                    raise ValueError('Invalid request length')
                data = validate(json.loads(self.rfile.read(length)))
                done, cancelled, result = threading.Event(), threading.Event(), {}
                receiver.commands.put_nowait((data, self.client_address[0], done, result, cancelled))
                if not done.wait(4):
                    cancelled.set()
                    return self.reply(503, {'error': 'GPIO output is busy; try again'})
                self.reply(400 if result.get('error') else 200, result)
            except (ValueError, queue.Full) as exc:
                self.reply(400, {'error': str(exc)})
    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # Prevent slow clients from creating unbounded worker threads on the 512 MB Pi.
    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key-file', type=Path, default=Path('/etc/mlsc-receiver/key'))
    args = parser.parse_args()
    key = args.key_file.read_text().strip()
    if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise SystemExit('Receiver key must be 64 hexadecimal characters')
    settings_file = args.key_file.parent/'settings.json'
    receiver = Receiver(key, settings_file=settings_file)
    if settings_file.is_file():
        # Reinitialize to black after a service restart; wait for a fresh sender session.
        settings = validate(json.loads(settings_file.read_text()))
        receiver.settings = settings
        try:
            receiver.pixels = Pixels(settings)
        except Exception as exc:
            receiver.error = 'GPIO21 startup failed: '+str(exc)
    http = Server(('0.0.0.0', HTTP_PORT), handler_for(receiver))
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    udp.bind(('0.0.0.0', UDP_PORT))
    udp.settimeout(.01)
    def stop(*_):
        receiver.running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    print('MLSC receiver ready: GPIO21 / pin40; waiting for pairing', flush=True)
    try:
        while receiver.running:
            receiver.process_commands()
            try:
                packet, address = udp.recvfrom(2048)
                receiver.feed(packet, address[0])
            except socket.timeout:
                pass
            receiver.tick()
    finally:
        receiver.close()
        udp.close()
        http.shutdown()
        http.server_close()


if __name__ == '__main__':
    main()
