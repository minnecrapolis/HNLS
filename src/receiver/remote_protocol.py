"""MLSC LAN RGB frames: bounded MTU-sized chunks, session/sequence and HMAC."""
import hashlib
import hmac
import struct

HEADER = struct.Struct('!4s8sQHHH')
MAGIC = b'MLR1'
CHUNK = 1020
MAX_LEDS = 2500
HTTP_PORT = 8943
UDP_PORT = 8944


def packets(frame, key, session, sequence):
    if not 21 <= len(frame) <= MAX_LEDS * 3 or len(frame) % 3:
        raise ValueError('RGB frame size is invalid')
    total = (len(frame) + CHUNK - 1) // CHUNK
    for index in range(total):
        body = HEADER.pack(MAGIC, session, sequence, index, total, len(frame)) + frame[index*CHUNK:(index+1)*CHUNK]
        yield body + hmac.new(key, body, hashlib.sha256).digest()


class Assembler:
    def __init__(self, key, session, count):
        self.key, self.session, self.size = key, session, count * 3
        self.sequence, self.parts, self.started, self.finished = -1, {}, 0., False

    def feed(self, packet, now):
        if len(packet) < HEADER.size + 33 or len(packet) > HEADER.size + CHUNK + 32:
            return None
        body, signature = packet[:-32], packet[-32:]
        if not hmac.compare_digest(signature, hmac.new(self.key, body, hashlib.sha256).digest()):
            return None
        magic, session, sequence, index, total, size = HEADER.unpack(body[:HEADER.size])
        expected = (self.size + CHUNK - 1) // CHUNK
        payload = body[HEADER.size:]
        if (magic != MAGIC or session != self.session or size != self.size or total != expected
                or index >= total or len(payload) != min(CHUNK, size-index*CHUNK)
                or sequence < self.sequence):
            return None
        if sequence > self.sequence:
            self.sequence, self.parts, self.started, self.finished = sequence, {}, now, False
        if self.finished or now-self.started > .15:
            return None
        self.parts[index] = payload
        if len(self.parts) == total:
            self.finished = True
            return b''.join(self.parts[i] for i in range(total))
        return None
