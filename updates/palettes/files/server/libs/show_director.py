"""Phrase-paced motion choices from analyzed dynamics; no LED/power control."""
import zlib


class ShowDirector:
    def __init__(self):
        self.song_id = None
        self.effect = 'comets'
        self.changed = -1e9
        self.beat = 0
        self.kind = None
        self.turn = 0

    def choose(self, f):
        position = float(f['position'])
        reset = f['song_id'] != self.song_id
        if reset:
            self.song_id = f['song_id']
            self.changed = -1e9
            self.turn = 0
            self.beat = int(f.get('beat_count',0))
        kind = f.get('section_kind','live')
        elapsed = position-self.changed
        phrase = int(f.get('beat_count',0))-self.beat >= 16
        boundary = kind != self.kind
        if not reset and (elapsed < 8 or not (phrase or boundary or elapsed >= 20)):
            return self.effect
        energy = float(f.get('section_energy', f.get('energy',0)))
        tempo = float(f.get('tempo') or 120)
        if kind == 'quiet' or energy < .30:
            choices = ['pulse','comets','bounce']
        elif kind == 'intense' or energy > .72:
            choices = ['ribbons','chase','bounce']
            if f.get('treble',0) > .5: choices += ['sparkle']
        else:
            choices = ['waves','comets','bounce']
            if tempo >= 120 or f.get('bass',0) > .6: choices += ['chase']
        if not reset and len(choices)>1:
            choices = [e for e in choices if e != self.effect]
        # A separate stable decision seed prevents render FPS/sparkle RNG from
        # changing the effect plan when the same song starts after another song.
        name = str(self.song_id).rsplit(':',1)[0]
        seed = zlib.crc32(f'{name}:{self.turn}:{kind}'.encode())
        self.effect = choices[seed%len(choices)]
        self.changed, self.beat, self.kind = position, int(f.get('beat_count',0)), kind
        self.turn += 1
        return self.effect
