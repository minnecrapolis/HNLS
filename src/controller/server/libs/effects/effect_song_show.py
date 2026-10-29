"""Sparse, full-length music choreography with bass-only full-strip impacts."""
import time
import zlib

import numpy as np
from libs.section_sync import SectionSynchronizer


class SongShowRenderer:
    def __init__(self, led_count, section_size=50, settings=None):
        self.physical_count = max(1, int(led_count))
        self.sync = SectionSynchronizer(self.physical_count, {"section_size": section_size, **(settings or {})})
        self.section_size = self.sync.size
        self.count = self.sync.logical_count
        self.section_map = self.sync.mapping
        self.x = np.linspace(0.0, 1.0, self.count, endpoint=False)
        self.trails = np.zeros((3, self.count), dtype=np.float32)
        self.song_id = None
        self.last_time = None
        self.last_input_time = 0.0
        self.features = None
        self.pulses = []
        self.beat = 0
        self.scene = 0
        self.last_scene = 0.0
        self.rng = np.random.default_rng(42)
        self.colors = {
            key: np.array([int(value[i:i+2], 16) / 255 for i in (1, 3, 5)])[:, None]
            for key, value in self.sync.settings.items() if key.endswith("_color")
        }

    def render(self, features=None, now=None):
        if self.sync.update(features):
            self.count = self.sync.logical_count
            self.section_map = self.sync.mapping
            self.x = np.linspace(0.0, 1.0, self.count, endpoint=False)
            self.trails = np.zeros((3, self.count), dtype=np.float32)
            self.pulses.clear()
        unique = self._render_unique(features, now)
        # Uneven custom groups can repeat some pixels much more than others.
        # Enforce the coverage limit in PHYSICAL pixels while retaining exact sync.
        f = self.features
        clock = time.monotonic() if now is None else now
        age = (f["position"] + clock - self.last_input_time - f["last_heavy"]) if f else 10
        heavy = f and f["audible"] and f["heavy_count"] > 0 and 0 <= age < .12
        if not heavy:
            energy = min(1.0, f["energy"]) if f else 0.0
            configured = self.sync.settings["max_lit_leds"]
            budget = (min(self.physical_count, configured) if configured else
                      max(1, int(self.physical_count * (.20 + .20 * energy))))
            strength = np.max(unique, axis=0)
            order = np.argsort(-strength.astype(float), kind="stable")
            order = order[strength[order] > 0]
            keep = order[np.cumsum(self.sync.weights[order]) <= budget]
            mask = np.ones(self.count, dtype=bool)
            mask[keep] = False
            unique[:, mask] = 0
        return unique[:, self.section_map]

    def _render_unique(self, features=None, now=None):
        now = time.monotonic() if now is None else now
        dt = 0.04 if self.last_time is None else float(np.clip(now - self.last_time, 0.001, 0.2))
        self.last_time = now
        if features is not None:
            if features["song_id"] != self.song_id:
                self.song_id = features["song_id"]
                # Stable palette/movement seed per filename, independent of Python hash randomization.
                name = self.song_id.rsplit(":", 1)[0]
                self.rng = np.random.default_rng(zlib.crc32(name.encode()))
                self.trails.fill(0)
                self.pulses.clear()
                self.beat = features["beat_count"]
                self.scene = int(self.rng.integers(0, 3))
                self.last_scene = features["position"]
                self._section_kind = None
            self.features = features
            self.last_input_time = now

        self.trails *= np.exp(-dt / 0.22)
        f = self.features
        stale = now - self.last_input_time
        if f is None or stale > 0.18 or not f["audible"]:
            self.trails[self.trails < 2] = 0
            return np.clip(self.trails, 0, 200).astype(np.uint8)

        position = f["position"] + stale
        bass = min(1.0, f["bass"])
        mid = min(1.0, f["mid"])
        treble = min(1.0, f["treble"])
        energy = min(1.0, f["energy"])
        new_beat = f["beat_count"] != self.beat
        if new_beat:
            self.beat = f["beat_count"]
            self.pulses.append([float(self.rng.uniform(0.12, 0.88)), position, bass])
            self.pulses = self.pulses[-10:]
            if self.beat % 8 == 0 and position - self.last_scene > 6:
                self.scene = (self.scene + 1) % 3
                self.last_scene = position

        # Warm bass, teal mids, violet highs. Motion reaches every region of the strip.
        warm = self.colors["bass_color"]
        cool = self.colors["mid_color"]
        violet = self.colors["treble_color"]
        fresh = np.zeros_like(self.trails)
        speed = 0.045 + energy * 0.10
        tempo = float(f.get('tempo') or 120)
        speed *= float(np.clip(tempo/120, .7, 1.4))
        kind = f.get('section_kind', 'live')
        if kind != 'live' and kind != getattr(self, '_section_kind', None):
            self.scene = {'quiet':0, 'steady':1, 'intense':2}.get(kind,self.scene)
            self._section_kind = kind
        phase = position * speed
        bass_shape = np.maximum(0.0, 1.0 - np.abs(np.sin(
            2 * np.pi * (self.x * 2 - phase))) / (0.08 + bass * 0.15)) ** 2
        fresh += warm * bass_shape * (15 + 80 * bass) * bass

        if self.scene == 0:
            # Three short comets sweep the full strip with different velocities.
            for offset, velocity in ((0.0, 1.0), (0.37, -0.73), (0.73, 0.57)):
                distance = (self.x - (phase * velocity + offset)) % 1.0
                shape = np.maximum(0.0, 1.0 - distance / (0.025 + mid * 0.055)) ** 2
                fresh += cool * shape * (30 + 110 * mid) * mid
        elif self.scene == 1:
            # Moving islands expand with vocals and midrange energy.
            wave = 0.5 + 0.5 * np.cos(2 * np.pi * (self.x * 5 - phase * 3))
            shape = np.maximum(0.0, (wave - 0.90 + mid * 0.10) / 0.20) ** 2
            fresh += cool * shape * (25 + 95 * mid) * mid
        else:
            # Alternating ribbons, separated by dark space.
            wave = np.sin(2 * np.pi * (self.x * 4 + phase * 2))
            shape = np.maximum(0.0, 1.0 - np.abs(wave) / (0.12 + mid * 0.16))
            fresh += cool * shape * (30 + 100 * mid) * mid

        alive = []
        for origin, start, strength in self.pulses:
            age = position - start
            if 0 <= age < 1.6:
                alive.append([origin, start, strength])
                radius = age * (0.24 + energy * 0.18)
                width = 0.008 + strength * 0.015
                shape = np.maximum(0.0, 1.0 - np.abs(np.abs(self.x - origin) - radius) / width)
                fresh += self.colors["beat_color"] * shape * (90 + 105 * strength) * np.exp(-age / 0.8)
        self.pulses = alive

        # Treble produces sparse accents, with density scaled to the strip length.
        if treble > 0.10:
            amount = min(self.count, max(1, int(self.count * 0.010 * treble * dt / 0.04)))
            indexes = self.rng.choice(self.count, size=amount, replace=False)
            fresh[:, indexes] += violet * (45 + 125 * treble)

        # Quiet sections occupy less space and carry lower intensity.
        fresh *= 0.25 + 0.75 * energy
        self.trails = np.maximum(self.trails, fresh)
        maximum = np.max(self.trails, axis=0)
        self.trails *= np.minimum(1, 200 / np.maximum(maximum, 1))[None, :]

        # Enforce dark space: no ordinary frame can illuminate the whole chain.
        configured = self.sync.settings["max_lit_leds"]
        ratio = min(1.0, configured / self.physical_count) if configured else .20 + .20 * energy
        limit = max(1, int(self.count * ratio))
        strength = np.max(self.trails, axis=0)
        if np.count_nonzero(strength >= 3) > limit:
            keep = np.argpartition(strength, -limit)[-limit:]
            mask = np.ones(self.count, dtype=bool)
            mask[keep] = False
            self.trails[:, mask] = 0
        self.trails[self.trails < 3] = 0

        # Only confirmed heavy bass onsets can light every pixel, for at most 120 ms.
        age = position - f["last_heavy"]
        if f["heavy_count"] > 0 and 0 <= age < 0.12:
            sweep = 0.5 + 0.5 * np.sin(2 * np.pi * (self.x * 2 + phase))
            impact = self.colors["power_color"] * (0.6 + 0.4 * sweep)
            impact *= (1 - age / 0.12) * 190
            # Do not retain the full-strip impact in the trail buffer.
            return np.clip(np.maximum(self.trails, impact), 0, 220).astype(np.uint8)
        return np.clip(self.trails, 0, 200).astype(np.uint8)


class EffectSongShow:
    """EffectService adapter; avoids initializing unused legacy gradient arrays."""
    def __init__(self, device):
        self.device = device
        settings = device.device_config["effects"].get("effect_song_show", {})
        self.renderer = SongShowRenderer(device.device_config["led_count"], settings=settings)

    def run(self):
        features = None
        # Discard older packets so a 25 FPS renderer follows current audio.
        for _ in range(4):
            if self.device.audio_queue.empty():
                break
            packet = self.device.audio_queue.get_blocking()
            if packet is not None:
                features = packet.get("show")
        output = self.renderer.render(features)
        self.device.output_queue.put_none_blocking(output)
