"""Section grouping shared by the renderer and settings validation."""
import zlib
import re
import numpy as np
from libs.show_palettes import COLOR_KEYS, EXTRA_COLORS, SHOW_MODES, PALETTE_IDS

DEFAULT_SYNC = {
    "section_size": 50, "sync_mode": "paired", "sync_groups": [],
    **EXTRA_COLORS, "expanded_bands": False, "show_mode": "classic", "palette_preset": "custom",
    "max_lit_leds": 0, "bass_color": "#ff2106", "mid_color": "#05adff",
    "treble_color": "#991fff", "beat_color": "#ff8500", "power_color": "#ff3300",
}
MODES = ("paired", "independent", "all", "custom", "auto")


def validate_sync_settings(led_count, settings):
    if set(settings) - set(DEFAULT_SYNC):
        raise ValueError("Unknown synchronization setting")
    size = settings.get("section_size", 50)
    mode = settings.get("sync_mode", "paired")
    groups = settings.get("sync_groups", [])
    if type(size) is not int or not 1 <= size <= 5000:
        raise ValueError("Section size must be between 1 and 5000")
    if mode not in MODES:
        raise ValueError("Unknown synchronization mode")
    if not isinstance(groups, list) or len(groups) > 5000 or any(
            type(g) is not int or not 1 <= g <= 5000 for g in groups):
        raise ValueError("Groups must be a list of positive group numbers")
    count = (led_count + size - 1) // size
    if mode == "custom" and len(groups) != count:
        raise ValueError("Assign a group to every section")
    maximum = settings.get("max_lit_leds", 0)
    if type(maximum) is not int or not 0 <= maximum <= 5000:
        raise ValueError("Maximum lit LEDs must be 0 (automatic) or between 1 and 5000")
    result = {**DEFAULT_SYNC, **settings, "sync_groups": list(groups)}
    if type(result["expanded_bands"]) is not bool:
        raise ValueError("Choose expanded bands on or off")
    if result["show_mode"] not in SHOW_MODES:
        raise ValueError("Choose a supported Song Show mode")
    if result["palette_preset"] not in PALETTE_IDS:
        raise ValueError("Choose a known holiday palette or Custom")
    for key in COLOR_KEYS:
        value = result[key]
        if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
            raise ValueError("Colors must be six-digit hex colors")
    return result


def preset_groups(mode, count):
    if mode == "paired":
        return [min(i, count - 1 - i) + 1 for i in range(count)]
    if mode == "all":
        return [1] * count
    if mode == "adjacent":
        return [i // 2 + 1 for i in range(count)]
    if mode == "alternating":
        return [i % 2 + 1 for i in range(count)]
    return list(range(1, count + 1))


def section_mapping(led_count, size, groups):
    # Compact arbitrary user group labels without changing the saved labels.
    labels = {}
    compact = [labels.setdefault(g, len(labels)) for g in groups]
    physical = np.arange(led_count)
    mapping = np.asarray(compact)[physical // size] * size + physical % size
    return mapping, int(mapping.max()) + 1


class SectionSynchronizer:
    def __init__(self, led_count, settings=None):
        self.led_count = int(led_count)
        self.settings = validate_sync_settings(self.led_count, {**DEFAULT_SYNC, **(settings or {})})
        self.size = self.settings["section_size"]
        self.sections = (self.led_count + self.size - 1) // self.size
        self.auto_mode = "paired"
        self.song_id = None
        self.last_change = 0.0
        self.last_change_beat = 0
        self.rng = np.random.default_rng(42)
        self._rebuild()

    def _rebuild(self):
        mode = self.settings["sync_mode"]
        self.groups = (self.settings["sync_groups"] if mode == "custom" else
                       preset_groups(self.auto_mode if mode == "auto" else mode, self.sections))
        self.mapping, self.logical_count = section_mapping(self.led_count, self.size, self.groups)
        self.weights = np.bincount(self.mapping, minlength=self.logical_count)

    def update(self, features):
        if self.settings["sync_mode"] != "auto" or not features or not features.get("audible"):
            return False
        changed = False
        position, beats = features["position"], features["beat_count"]
        if features["song_id"] != self.song_id:
            self.song_id = features["song_id"]
            name = self.song_id.rsplit(":", 1)[0]
            self.rng = np.random.default_rng(zlib.crc32(name.encode()))
            self.last_change, self.last_change_beat = position, beats
            changed = self.auto_mode != "paired"
            self.auto_mode = "paired"
        age = position - self.last_change
        phrase = beats - self.last_change_beat >= 16 and age >= 8
        fallback = age >= 20 and features["energy"] > 0.2
        if phrase or fallback:
            energy = features["energy"]
            choices = (["paired", "alternating"] if energy < .3 else
                       ["paired", "adjacent", "alternating"] if energy < .7 else
                       ["independent", "paired", "adjacent", "all"])
            choices = [mode for mode in choices if mode != self.auto_mode]
            self.auto_mode = str(self.rng.choice(choices))
            self.last_change, self.last_change_beat = position, beats
            changed = True
        if changed:
            self._rebuild()
        return changed
