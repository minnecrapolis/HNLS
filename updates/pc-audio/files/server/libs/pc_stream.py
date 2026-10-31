"""Authenticated, bounded LAN PCM input. Windows sends native-rate stereo s16le.

No service login, cloud relay, recording or media-service API is involved.
"""
import hashlib
import hmac
import io
import json
import os
import secrets
import socket
import struct
import time
import zipfile
from collections import deque
from pathlib import Path

PORT = 8950
HEADER = struct.Struct('<4s16sIIHH')
MAX_FRAMES = 256
MAX_PACKET = HEADER.size + 32 + MAX_FRAMES * 4
RATES = {44100, 48000, 88200, 96000, 192000}


def settings_path():
    return Path(os.environ.get('HNLS_SETTINGS_DIR', '/share/.mlsc')) / 'pc_stream.json'


def credentials():
    path = settings_path()
    try:
        try:
            value = json.loads(path.read_text())
            key = bytes.fromhex(value['key'])
            if len(key) != 32:
                raise ValueError('Wrong key length')
        except (KeyError, TypeError, ValueError):
            raise ValueError('Invalid Windows sender key; restore pc_stream.json from backup or revoke it as described in PC_AUDIO.md.') from None
        return key
    except FileNotFoundError:
        key = secrets.token_bytes(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create also handles two browser requests on first use.
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return credentials()
        with os.fdopen(fd, 'w') as f:
            json.dump({'version': 1, 'key': key.hex()}, f)
        return key


def sender_bundle(host):
    # Host is data in JSON, never interpolated into a shell command/source.
    if not isinstance(host, str) or not host or len(host) > 253 or any(c in host for c in '/\\\r\n\x00'):
        raise ValueError('Open HNLS using the main Pi LAN address before downloading.')
    directory = Path(__file__).with_name('windows_pc_audio')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ('Start-HNLS-Audio.cmd', 'Send-HNLS-Audio.ps1', 'LoopbackSender.cs', 'README.txt'):
            archive.writestr('HNLS-PC-Audio/' + name, (directory / name).read_bytes())
        archive.writestr('HNLS-PC-Audio/connection.json', json.dumps({'host': host, 'port': PORT, 'key': credentials().hex()}))
    output.seek(0)
    return output


def encode_packet(key, stream, sequence, rate, pcm):
    """Reference encoder for interoperability tests; the sender implements this layout."""
    frames = len(pcm) // 4
    if rate not in RATES or len(pcm) % 4 or not 1 <= frames <= MAX_FRAMES:
        raise ValueError('Invalid PCM')
    body = HEADER.pack(b'HNA1', stream, sequence, rate, frames, 2) + pcm
    return body[:HEADER.size] + hmac.digest(key, body, 'sha256') + pcm


class PacketBuffer:
    """One active sender, sequence reordering and a small bounded jitter buffer."""
    def __init__(self, key, block_size):
        self.key, self.block_size = key, block_size
        self.stream = None
        self.retired = deque(maxlen=64)
        self.last_seen = -1e9
        self.rate = None
        self.expected = 0
        self.pending = {}
        self.pcm = bytearray()
        self.started = False
        self.dropped = 0

    def feed(self, packet, now):
        if not HEADER.size + 36 <= len(packet) <= MAX_PACKET:
            return False
        header, tag, pcm = packet[:HEADER.size], packet[HEADER.size:HEADER.size+32], packet[HEADER.size+32:]
        magic, stream, seq, rate, frames, channels = HEADER.unpack(header)
        if magic != b'HNA1' or rate not in RATES or channels != 2 or not 1 <= frames <= MAX_FRAMES or len(pcm) != frames * 4:
            return False
        if not hmac.compare_digest(tag, hmac.digest(self.key, header + pcm, 'sha256')):
            return False
        if stream != self.stream:
            if stream in self.retired or (self.stream is not None and now - self.last_seen < 1.):
                return False
            if self.stream is not None:
                self.retired.append(self.stream)
            self.stream, self.rate, self.expected = stream, rate, seq
            self.pending.clear()
            self.pcm.clear()
            self.started = False
        if rate != self.rate or seq < self.expected or seq in self.pending:
            return False
        # A sender restart uses a new random stream ID, not a wrapping sequence.
        self.last_seen = now
        self.pending[seq] = (now, pcm)
        self.drain(now)
        return True

    def drain(self, now):
        for _ in range(128):
            if self.expected in self.pending:
                _, pcm = self.pending.pop(self.expected)
                self.pcm.extend(pcm)
                self.expected += 1
            elif self.pending:
                seq = min(self.pending)
                arrival = min(v[0] for v in self.pending.values())
                if len(self.pending) > 8 or now-arrival > .03:
                    self.dropped += seq-self.expected
                    self.expected = seq
                    continue
                break
            else:
                break
        # Discard old audio rather than letting Wi-Fi hiccups create seconds of lag.
        limit = max(self.block_size * 4 * 3, int((self.rate or 48000)*.16)*4)
        if len(self.pcm) > limit:
            excess = (len(self.pcm)-limit+3)//4*4
            del self.pcm[:excess]
            self.dropped += 1

    def read(self, now):
        self.drain(now)
        size = self.block_size * 4
        if now-self.last_seen > .35:
            self.pcm.clear()
            self.pending.clear()
            self.started = False
            return None
        if not self.started:
            if len(self.pcm) < size * 2:
                return None
            self.started = True
        if len(self.pcm) < size:
            return None
        result = bytes(self.pcm[:size])
        del self.pcm[:size]
        return result


class Receiver:
    def __init__(self, key, block_size, port=PORT):
        self.buffer = PacketBuffer(key, block_size)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)
            self.socket.bind(('0.0.0.0', port))
            self.socket.setblocking(False)
        except BaseException:
            self.socket.close()
            raise

    def read(self):
        for _ in range(128):
            try:
                packet, _ = self.socket.recvfrom(MAX_PACKET+1)
            except BlockingIOError:
                break
            self.buffer.feed(packet, time.monotonic())
        return self.buffer.read(time.monotonic())

    def close(self):
        self.socket.close()
