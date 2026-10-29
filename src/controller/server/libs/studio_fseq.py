"""Random-access FSEQ v1/v2 reader, including zlib/zstd and sparse channels.

Format reference: FalconChristmas/fpp/docs/FSEQ_Sequence_File_Format.txt.
Reads rendered frames; xLights' editable effect layers are not in FSEQ files.
"""
import ctypes
import ctypes.util
from pathlib import Path
import struct
import zlib
import numpy as np

MAX_BLOCK = 128 * 1024 * 1024


def zstd_decode(data, expected):
    library = ctypes.util.find_library('zstd')
    if not library:
        raise ValueError('This Pi needs libzstd for compressed FSEQ. Export uncompressed or zlib FSEQ instead.')
    lib = ctypes.CDLL(library)
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    out = ctypes.create_string_buffer(expected)
    source = ctypes.create_string_buffer(data)
    result = lib.ZSTD_decompress(out, expected, source, len(data))
    if lib.ZSTD_isError(result) or result != expected:
        raise ValueError('Invalid zstd FSEQ block')
    return out.raw


class FSEQReader:
    def __init__(self, path):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        self.cache = (-1, b'')
        with self.path.open('rb') as source:
            header = source.read(32)
            if len(header) < 28 or header[:4] != b'PSEQ':
                raise ValueError('Not an FSEQ file')
            self.offset, self.minor, self.major, fixed, self.channels, self.frames, self.step = struct.unpack_from('<HBBHIIB', header, 4)
            if self.major not in (1, 2) or not self.channels or not self.frames or not self.step:
                raise ValueError('Unsupported or empty FSEQ')
            if not 28 <= fixed <= self.offset <= self.size:
                raise ValueError('Invalid FSEQ header bounds')
            self.compression = 0
            self.blocks, self.ranges, self.media = [], [], ''
            header = header[:self.offset] + source.read(max(0, self.offset - len(header)))
            if self.major == 2:
                if fixed < 32:
                    raise ValueError('Invalid v2 header')
                self.compression = header[20] & 15
                count = header[21] | ((header[20] >> 4) << 8)
                ranges = header[22]
                if self.compression not in (0, 1, 2):
                    raise ValueError('Unknown FSEQ compression')
                cursor = 32
                data_offset = self.offset
                for _ in range(count):
                    if cursor + 8 > fixed:
                        raise ValueError('Invalid compressed block table')
                    first, length = struct.unpack_from('<II', header, cursor)
                    self.blocks.append((first, data_offset, length))
                    data_offset += length
                    cursor += 8
                for _ in range(ranges):
                    if cursor + 6 > fixed:
                        raise ValueError('Invalid sparse table')
                    self.ranges.append((int.from_bytes(header[cursor:cursor+3], 'little'),
                                        int.from_bytes(header[cursor+3:cursor+6], 'little')))
                    cursor += 6
                if self.compression and (not self.blocks or self.blocks[0][0] != 0 or data_offset > self.size):
                    raise ValueError('Invalid compressed FSEQ layout')
                if any(a[0] >= b[0] for a, b in zip(self.blocks, self.blocks[1:])):
                    raise ValueError('Unordered FSEQ blocks')
                if any(first >= self.frames or length <= 0 for first, _, length in self.blocks):
                    raise ValueError('Invalid FSEQ compression block bounds')
            cursor = fixed
            while cursor + 4 <= self.offset:
                length = int.from_bytes(header[cursor:cursor+2], 'little')
                code = header[cursor+2:cursor+4]
                if length < 4 or cursor + length > self.offset:
                    break
                value = header[cursor+4:cursor+length]
                if code == b'ED' and len(value) == 14:
                    code, address, size = value[:2], int.from_bytes(value[2:10], 'little'), int.from_bytes(value[10:14], 'little')
                    if size > MAX_BLOCK or address + size > self.size:
                        raise ValueError('Invalid extended FSEQ header')
                    source.seek(address)
                    value = source.read(size)
                if code == b'SR':
                    if len(value) % 6:
                        raise ValueError('Invalid extended sparse table')
                    self.ranges = [(int.from_bytes(value[i:i+3], 'little'), int.from_bytes(value[i+3:i+6], 'little')) for i in range(0, len(value), 6)]
                if code == b'mf':
                    self.media = Path(value.rstrip(b'\0').decode('utf-8', 'replace').replace('\\', '/')).name
                cursor += length
        if not self.compression and self.offset + self.frames * self.channels > self.size:
            raise ValueError('Truncated FSEQ frames')
        if self.ranges and sum(length for _, length in self.ranges) != self.channels:
            raise ValueError('Sparse channel lengths do not match frame size')
        self.total_channels = max((start + length for start, length in self.ranges), default=self.channels)
        if self.total_channels > 30_000_000:
            raise ValueError('FSEQ channel addressing exceeds this installation limit')

    def info(self):
        return {'version': f'{self.major}.{self.minor}', 'frames': self.frames,
                'channels': self.total_channels, 'stored_channels': self.channels,
                'frame_ms': self.step, 'duration_ms': self.frames*self.step,
                'media': self.media, 'compression': self.compression, 'sparse': bool(self.ranges)}

    def _frame(self, index):
        if not self.compression:
            with self.path.open('rb') as f:
                f.seek(self.offset + index * self.channels)
                return f.read(self.channels)
        block = next(i for i in range(len(self.blocks)-1, -1, -1) if self.blocks[i][0] <= index)
        first, address, size = self.blocks[block]
        last = self.blocks[block+1][0] if block+1 < len(self.blocks) else self.frames
        expected = (last-first)*self.channels
        if expected <= 0 or expected > MAX_BLOCK:
            raise ValueError('FSEQ block exceeds the 128 MiB decode buffer; export smaller blocks')
        if self.cache[0] != block:
            if size > MAX_BLOCK:
                raise ValueError('Compressed FSEQ block is too large')
            with self.path.open('rb') as f:
                f.seek(address)
                compressed = f.read(size)
            if self.compression == 1:
                raw = zstd_decode(compressed, expected)
            else:
                decoder = zlib.decompressobj(47)
                raw = decoder.decompress(compressed, expected+1)
                if len(raw) != expected or not decoder.eof:
                    raise ValueError('Invalid zlib FSEQ block')
            self.cache = (block, raw)
        offset = (index-first)*self.channels
        return self.cache[1][offset:offset+self.channels]

    def pixels(self, milliseconds, first_pixel, count):
        result = np.zeros(count*3, dtype=np.uint8)
        if milliseconds < 0 or milliseconds >= self.frames*self.step:
            return result.reshape(count, 3).T
        frame = np.frombuffer(self._frame(int(milliseconds // self.step)), dtype=np.uint8)
        low, high = (first_pixel-1)*3, (first_pixel-1+count)*3
        if not self.ranges:
            end = min(high, len(frame))
            if end > low:
                result[:end-low] = frame[low:end]
        else:
            packed = 0
            for start, size in self.ranges:
                left, right = max(low, start), min(high, start+size)
                if right > left:
                    result[left-low:right-low] = frame[packed+left-start:packed+right-start]
                packed += size
        return result.reshape(count, 3).T


def write_fseq(path, frame_count, channels, step_ms, frames):
    if not 1 <= step_ms <= 255:
        raise ValueError('FSEQ frame interval must be between 1 and 255 ms')
    header = bytearray(28)
    header[:4] = b'PSEQ'
    struct.pack_into('<HBBHIIB', header, 4, 28, 0, 1, 28, channels, frame_count, step_ms)
    header[24:26] = b'\x01\x02'
    with Path(path).open('wb') as f:
        f.write(header)
        written = 0
        for frame in frames:
            if len(frame) != channels or written >= frame_count:
                raise ValueError('Incorrect exported FSEQ frame size/count')
            f.write(frame)
            written += 1
        if written != frame_count:
            raise ValueError('Incorrect exported FSEQ frame count')
