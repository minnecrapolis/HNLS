"""Cached song statistics and lightweight, audio-clocked light-show features.

Full-file scanning runs in a separate low-priority process. Playback never waits
for it; live adaptation works until a profile is available. No new dependencies.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import deque

import numpy as np

VERSION = 2
BANDS = ((30, 250), (250, 2000), (2000, 8000))
MUSICAL_BANDS = ((20,60),(60,250),(250,500),(500,2000),(2000,4000),(4000,6000),(6000,10000),(10000,16000))


def spectrum_levels(magnitude, sample_rate, n_samples, window_power, bands=BANDS):
    frequencies = np.fft.rfftfreq(n_samples, 1.0 / sample_rate)
    power = np.square(magnitude)
    denominator = max(n_samples * window_power, 1e-12)
    return np.array([
        np.sqrt(2 * np.sum(power[(frequencies >= lo) & (frequencies < hi)]) / denominator)
        for lo, hi in bands
    ])


def cache_path(path):
    path = Path(path)
    stat = path.stat()
    identity = f"{VERSION}:{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
    key = hashlib.sha256(identity.encode()).hexdigest()
    directory = Path(os.environ.get("MLSC_ANALYSIS_DIR", "/share/.mlsc/song_analysis"))
    return directory / (key + ".json")


def _analyze_file_unlocked(path, destination=None):
    """Scan bounded batches of 64 ms windows, retaining only compact statistics."""
    path = Path(path)
    destination = Path(destination) if destination else cache_path(path)
    original_stat = (path.stat().st_size, path.stat().st_mtime_ns)
    rate, size = 16000, 1024
    window = np.hamming(size)
    window_power = float(np.sum(window ** 2))
    process = subprocess.Popen([
        "/usr/bin/ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-threads", "1", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
        "-f", "s16le", "pipe:1",
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    rows = []
    remainder = b""
    frames = 0
    started = time.monotonic()
    try:
        while True:
            data = process.stdout.read(size * 2 * 64)
            if not data:
                break
            remainder += data
            count = len(remainder) // (size * 2)
            if not count:
                continue
            end = count * size * 2
            samples = np.frombuffer(remainder[:end], dtype=np.int16).astype(np.float64)
            remainder = remainder[end:]
            samples = samples.reshape(count, size) / 32768.0
            rms = np.sqrt(np.mean(samples ** 2, axis=1))
            magnitudes = np.abs(np.fft.rfft(samples * window, axis=1))
            frequencies = np.fft.rfftfreq(size, 1.0 / rate)
            bands = [np.sqrt(2 * np.sum(magnitudes[:, (frequencies >= lo) &
                       (frequencies < hi)] ** 2, axis=1) / (size * window_power))
                     for lo, hi in BANDS]
            rows.extend(np.column_stack((rms, *bands)).tolist())
            frames += count
            # At most four times real time, with bounded CPU and memory use.
            delay = frames * size / rate / 4 - (time.monotonic() - started)
            if delay > 0:
                time.sleep(min(delay, 1.1))
            if frames * size / rate >= 4 * 60 * 60:
                raise ValueError("Analysis is limited to four-hour files")
        returncode = process.wait(timeout=5)
        if returncode != 0 or not rows:
            raise ValueError("No decodable audio for song analysis")
        if (path.stat().st_size, path.stat().st_mtime_ns) != original_stat:
            raise ValueError("Song changed during analysis")
        values = np.asarray(rows)
        active = values[values[:, 0] > 0.0005]
        if not len(active):
            active = values
        percentiles = np.percentile(active, [25, 50, 75, 90, 95, 99], axis=0)
        profile = {
            "version": VERSION, "file": path.name,
            "duration": frames * size / rate,
            "percentiles": {str(p): v.tolist() for p, v in
                            zip((25, 50, 75, 90, 95, 99), percentiles)},
        }
        profile.update(timeline_profile(values, size/rate, percentiles))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f".{os.getpid()}.tmp")
        try:
            temporary.write_text(json.dumps(profile), encoding="utf-8")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return profile
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if process.stdout:
            process.stdout.close()


class SongShowAnalyzer:
    def __init__(self):
        self.worker = None
        self.attempted = set()
        self.start_song(None)

    def start_song(self, path):
        self.path = Path(path) if path else None
        self.profile = None
        self.profile_path = None
        self.next_profile_check = 0.0
        self.position = 0.0
        self.song_id = f"{self.path.name if self.path else 'microphone'}:{time.monotonic_ns()}"
        self.history = deque(maxlen=48)
        self.peaks = np.array([0.08, 0.04, 0.04, 0.02], dtype=float)
        self.band_peaks = np.full(8, .04, dtype=float)
        self.previous_bass = 0.0
        self.last_beat = -10.0
        self.last_heavy = -10.0
        self.beat_count = 0
        self.heavy_count = 0
        self.energy = 0.0
        if self.path:
            try:
                self.profile_path = cache_path(self.path)
                self._poll_profile()
            except OSError:
                pass

    def _poll_profile(self):
        if self.profile_path is None or self.profile is not None:
            return
        if time.monotonic() < self.next_profile_check:
            return
        self.next_profile_check = time.monotonic() + 2.0
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            stats = np.array([data["percentiles"][str(p)] for p in (25, 50, 75, 90, 95, 99)])
            if valid_profile(data) and stats.shape == (6, 4) and np.all(np.isfinite(stats)):
                self.profile = data
                return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if self.worker is not None and self.worker.poll() is None:
            return
        key = str(self.profile_path)
        if key in self.attempted:
            return
        self.attempted.add(key)
        try:
            self.worker = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), str(self.path), str(self.profile_path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
            )
        except OSError:
            self.worker = None

    def update(self, raw, elapsed, bands=None):
        self._poll_profile()
        dt = max(0.0001, float(elapsed))
        self.position += dt
        raw = np.maximum(0, np.nan_to_num(np.asarray(raw, dtype=float), nan=0, posinf=0, neginf=0))
        self.peaks = np.maximum(raw, self.peaks * np.exp(-dt / 35.0))
        if self.profile:
            p = self.profile["percentiles"]
            ceiling = np.maximum(np.array(p["95"]), [0.008, 0.005, 0.003, 0.002])
            heavy_bass = max(0.025, p["95"][1])
            heavy_rms = max(0.06, p["75"][0])
        else:
            ceiling = np.maximum(self.peaks, [0.008, 0.005, 0.003, 0.002])
            heavy_bass = max(0.025, ceiling[1] * 0.88)
            heavy_rms = max(0.06, ceiling[0] * 0.72)
        levels = np.clip(raw / ceiling, 0, 1.3)
        context = None
        if self.profile and self.profile.get('sections'):
            sections = self.profile['sections']
            context = sections[min(len(sections)-1, int(self.position / self.profile.get('section_seconds', 8)))]
            # Retain whole-song dynamics while gently adapting frequency balance locally.
            local = np.maximum(np.asarray(context['ceiling']), [0.008, 0.005, 0.003, 0.002])
            adjusted = np.maximum(ceiling * .65, ceiling * .75 + local * .25)
            levels = np.clip(raw / adjusted, 0, 1.3)
        audible = raw[0] > 0.0008
        baseline = np.mean(self.history) if self.history else raw[1]
        deviation = np.std(self.history) if len(self.history) > 8 else 0.0
        onset = raw[1] - self.previous_bass
        beat = (audible and len(self.history) >= 6 and
                raw[1] > max(0.008, baseline * 1.45, baseline + deviation * 1.4) and
                onset > max(0.003, baseline * 0.15) and levels[1] > 0.50 and
                self.position - self.last_beat > 0.24)
        heavy = (beat and raw[1] >= heavy_bass and raw[0] >= heavy_rms and
                 raw[1] / max(float(np.sum(raw[1:])), 1e-8) > 0.40 and
                 self.position - self.last_heavy > 0.75)
        if self.profile and 'beat_times' in self.profile:
            # Use decoded-song time, so pauses and seeks never use a wall-clock beat grid.
            beat = profile_event(self.profile['beat_times'], self.position, dt, self.last_beat)
            heavy = profile_event(self.profile.get('heavy_times', []), self.position, dt, self.last_heavy)
        if beat:
            self.beat_count += 1
            self.last_beat = self.position
        if heavy:
            self.heavy_count += 1
            self.last_heavy = self.position
        self.previous_bass = float(raw[1])
        self.history.append(float(raw[1]))
        band_levels = None
        if bands is not None:
            band_raw = np.nan_to_num(np.asarray(bands,dtype=float),nan=0,posinf=0,neginf=0)
            if band_raw.shape == (8,):
                band_raw = np.maximum(0,band_raw)
                self.band_peaks = np.maximum(band_raw,self.band_peaks*np.exp(-dt/35.))
                band_levels = np.where((band_raw>.0005)&audible,np.clip(band_raw/np.maximum(self.band_peaks,.003),0,1.3),0).tolist()
        self.energy += (min(1, levels[0]) - self.energy) * (1 - np.exp(-dt / 1.8))
        return {
            "song_id": self.song_id, "position": self.position, "bands": band_levels,
            "bass": float(levels[1]) if audible else 0.0,
            "mid": float(levels[2]) if audible else 0.0,
            "treble": float(levels[3]) if audible else 0.0,
            "energy": float(self.energy) if audible else 0.0,
            "audible": bool(audible), "beat_count": self.beat_count,
            "heavy_count": self.heavy_count, "last_beat": self.last_beat,
            "last_heavy": self.last_heavy, "profile_ready": self.profile is not None,
            "tempo": self.profile.get('tempo_bpm') if self.profile else None,
            "section_energy": context['energy'] if context else float(self.energy),
            "section_kind": context['kind'] if context else 'live',
        }

    def close(self):
        if self.worker is not None and self.worker.poll() is None:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.worker.kill()
                self.worker.wait()
        self.worker = None


def profile_event(times, position, dt, previous):
    if not times: return False
    index = int(np.searchsorted(times, position, side='right'))-1
    return index >= 0 and times[index] > previous and 0 <= position-times[index] <= min(.12, dt+.025)


def valid_profile(data):
    try:
        stats=np.array([data['percentiles'][str(p)] for p in (25,50,75,90,95,99)],dtype=float)
        if data.get('version')!=VERSION or stats.shape!=(6,4) or not np.all(np.isfinite(stats)):return False
        if not isinstance(data['sections'],list) or not data['sections'] or not 0<float(data['section_seconds'])<=60:return False
        for section in data['sections']:
            ceiling=np.asarray(section['ceiling'],dtype=float)
            if ceiling.shape!=(4,) or not np.all(np.isfinite(ceiling)) or not 0<=section['energy']<=1 or section['kind'] not in ('quiet','steady','intense'):return False
        for key in ('beat_times','heavy_times'):
            times=np.asarray(data[key],dtype=float)
            if times.ndim!=1 or not np.all(np.isfinite(times)) or np.any(times<0) or np.any(np.diff(times)<0):return False
        tempo=data.get('tempo_bpm')
        return tempo is None or (isinstance(tempo,(int,float)) and np.isfinite(tempo) and 30<=tempo<=240)
    except (TypeError,ValueError,KeyError,AttributeError):return False


def timeline_profile(values, step, percentiles):
    """Describe dynamics and musical attacks; no instrument-separation claims."""
    count = len(values)
    chunk = max(1, int(round(8/step)))
    ceiling = np.maximum(percentiles[4], [.008,.005,.003,.002])
    normalized = np.clip(values/ceiling,0,2)
    sections=[]
    for start in range(0,count,chunk):
        part=values[start:start+chunk]
        energy=float(np.clip(np.median(part[:,0])/ceiling[0],0,1))
        sections.append({'start':round(start*step,4), 'energy':energy,
                         'kind':'quiet' if energy<.25 else 'intense' if energy>.7 else 'steady',
                         'ceiling':np.percentile(part,95,axis=0).tolist()})
    # Positive bass/mid/high changes identify attacks across the spectrum.
    delta=np.maximum(0,np.diff(normalized[:,1:],axis=0,prepend=normalized[:1,1:]))
    attacks=delta@np.array([.65,.20,.15])
    threshold=max(.04,float(np.median(attacks)+2.5*np.median(np.abs(attacks-np.median(attacks)))))
    beats=[];heavy=[];last=-10.
    for i in range(1,count-1):
        t=i*step
        if (values[i,0]>.0008 and attacks[i]>threshold and attacks[i]>=attacks[i-1]
                and attacks[i]>attacks[i+1] and t-last>=.24):
            beats.append(round(t,4));last=t
            if values[i,1]>=max(.025,percentiles[4,1]) and values[i,0]>=max(.06,percentiles[2,0]) and (not heavy or t-heavy[-1]>.75):
                heavy.append(round(t,4))
    tempo=None
    if len(beats)>=8 and np.std(attacks)>.005:
        envelope=attacks-np.mean(attacks)
        # Bounded autocorrelation on an attack envelope sampled at ~16 Hz.
        low=max(1,int(60/190/step));high=min(count-2,int(60/60/step))
        lags=np.arange(low,high+1)
        if len(lags):
            scores=np.array([np.dot(envelope[:-lag],envelope[lag:])/max(1,count-lag) for lag in lags])
            best=int(np.argmax(scores))
            if scores[best]>np.var(envelope)*.12: tempo=round(60/(int(lags[best])*step),1)
    return {'section_seconds':chunk*step,'sections':sections,'beat_times':beats,
            'heavy_times':heavy,'tempo_bpm':tempo}


def analyze_file(path, destination=None):
    """Serialize workers across playback and bulk preparation on Linux."""
    import fcntl
    destination=Path(destination) if destination else cache_path(path)
    directory=cache_path(path).parent;directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.scan.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            cached=json.loads(destination.read_text())
            if valid_profile(cached):return cached
        except (OSError,ValueError,AttributeError):pass
        return _analyze_file_unlocked(path,destination)


if __name__ == "__main__":
    try:
        os.nice(10)
    except (AttributeError, OSError):
        pass
    analyze_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
