"""Clocked local playback with explicit GPIO ownership and independent line FPS."""
import os
from pathlib import Path
import subprocess
import threading
import time

import numpy as np
from libs.alsa_music_output import HeadphoneOutput
from libs.music_library import safe_music_path
from libs.studio_project import PINS, ProjectRenderer, validate_project


class PiPixelBus:
    def __init__(self, outputs):
        import _rpi_ws281x as ws
        self.ws, self.contexts, self.channels = ws, {}, {}
        self.initialized = set()
        try:
            if any(o['gpio'] == 10 for o in outputs):
                if not Path('/dev/spidev0.0').exists():
                    raise ValueError('SPI is not enabled. Use Advanced Users → Pi setup → Enable SPI, then reboot.')
                path = Path('/sys/module/spidev/parameters/bufsiz')
                size = int(path.read_text()) if path.exists() else 4096
                if any(o['gpio'] == 10 and o['count']*12 > size for o in outputs):
                    raise ValueError('SPI transfer buffer is too small. Use Pi setup → Enable SPI, then reboot.')
            if any(PINS[o['gpio']][0] == 'pwm' for o in outputs):
                if Path('/sys/module/snd_bcm2835').exists():
                    raise ValueError('PWM requires built-in audio disabled. Use Pi setup on this remote Pi, then reboot, or choose GPIO21/10.')
            for index, out in enumerate(outputs):
                backend, channel_id = PINS[out['gpio']]
                if backend not in self.contexts:
                    self.contexts[backend] = ws.new_ws2811_t()
                context = self.contexts[backend]
                channel = ws.ws2811_channel_get(context, channel_id)
                ws.ws2811_channel_t_strip_type_set(channel, getattr(ws, 'WS2811_STRIP_'+out['order']))
                ws.ws2811_channel_t_count_set(channel, out['count'])
                ws.ws2811_channel_t_gpionum_set(channel, out['gpio'])
                ws.ws2811_channel_t_invert_set(channel, 0)
                # Brightness is applied once by ProjectRenderer.
                ws.ws2811_channel_t_brightness_set(channel, 255)
                self.channels[index] = (backend, channel)
            for backend, context in self.contexts.items():
                ws.ws2811_t_freq_set(context, 800000)
                ws.ws2811_t_dmanum_set(context, 11 if backend == 'pwm' else 10)
                code = ws.ws2811_init(context)
                if code != ws.WS2811_SUCCESS:
                    raise RuntimeError('Pixel driver initialization failed: '+str(ws.ws2811_get_return_t_str(code)))
                self.initialized.add(backend)
        except Exception:
            self.close()
            raise

    def show(self, updates):
        ws, dirty = self.ws, set()
        for index, frame in updates.items():
            backend, channel = self.channels[index]
            colors = frame.astype(np.uint32)
            packed = (colors[0] << 16) | (colors[1] << 8) | colors[2]
            for pixel, value in enumerate(packed):
                ws.ws2811_led_set(channel, pixel, int(value))
            dirty.add(backend)
        for backend in dirty:
            code = ws.ws2811_render(self.contexts[backend])
            if code != ws.WS2811_SUCCESS:
                raise RuntimeError('Pixel output failed: '+str(ws.ws2811_get_return_t_str(code)))

    def close(self):
        for backend, context in list(getattr(self, 'contexts', {}).items()):
            try:
                if backend in self.initialized:
                    self.ws.ws2811_fini(context)
                self.ws.delete_ws2811_t(context)
            except Exception:
                pass
        self.contexts = {}


class AudioTrack:
    def __init__(self, path, due, paused):
        self.path, self.due, self.paused = path, due, paused
        self.cancel = threading.Event()
        self.decoder, self.output, self.error = None, None, ''
        self.progress = (0, 0.0)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            while time.monotonic() < self.due:
                if self.cancel.wait(.01):
                    return
            self.decoder = subprocess.Popen(['/usr/bin/ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-i', str(self.path), '-vn', '-ac', '2', '-ar', '48000', '-f', 's16le', 'pipe:1'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            self.output = HeadphoneOutput(48000, 2)
            while not self.cancel.is_set():
                if self.paused():
                    self.cancel.wait(.01)
                    continue
                data = self.decoder.stdout.read(4096)
                if not data:
                    self.output.finish()
                    break
                self.output.write(data)
                self.progress = (self.progress[0]+len(data)//4, time.monotonic())
        except Exception as exc:
            if not self.cancel.is_set():
                self.error = str(exc)
        finally:
            self._close()

    def _close(self):
        if self.output:
            try:
                self.output.close()
            except Exception:
                pass
        if self.decoder:
            try:
                if self.decoder.poll() is None:
                    self.decoder.terminate()
                    self.decoder.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.decoder.kill(); self.decoder.wait()
            if self.decoder.stdout:
                self.decoder.stdout.close()

    def stop(self):
        self.cancel.set()
        self._close()
        if self.thread is not threading.current_thread():
            self.thread.join(timeout=3)


class StudioEngine:
    def __init__(self, store, acquire=lambda: None, release=lambda: None, bus_factory=PiPixelBus):
        self.store, self.acquire, self.release, self.bus_factory = store, acquire, release, bus_factory
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.thread, self.audio, self.project = None, None, None
        self.state, self.error = 'idle', ''
        self.anchor, self.pause_ms, self.paused = 0., 0., False
        self.remote, self.lease = False, 0.
        self.line_stats = []

    def position(self):
        return self.pause_ms if self.paused else (time.monotonic()-self.anchor)*1000

    def status(self):
        with self.lock:
            raw = self.position() if self.project else 0
            duration = self.project['duration_ms'] if self.project else 0
            position = raw % duration if self.project and self.project['loop'] and raw >= 0 else raw
            return {'state': self.state, 'error': self.error, 'position_ms': position,
                    'duration_ms': duration, 'project': self.project['id'] if self.project else None,
                    'paused': self.paused, 'audio_error': self.audio.error if self.audio else '',
                    'outputs': [dict(line) for line in self.line_stats]}

    def start(self, project, epoch=None, remote=False):
        project = validate_project(project)
        renderer = ProjectRenderer(project, self.store)
        media = safe_music_path(project['media']) if project['media'] and project['audio_device'] == 'headphones' else None
        if media and not media.is_file():
            raise ValueError('The selected audio file is missing')
        self.stop()
        self.acquire()
        try:
            outputs = [o for o in project['outputs'] if o['enabled'] and o['node'] == 'local']
            bus = self.bus_factory(outputs) if outputs else None
        except Exception:
            self.release()
            raise
        with self.lock:
            self.project, self.error, self.state = project, '', 'starting'
            self.line_stats = [{'name':o['name'],'requested_fps':o['fps'],'actual_fps':0.0,'late_frames':0} for o in outputs]
            lead = max([0, -project['audio_offset_ms']]+[-o['offset_ms'] for o in outputs])/1000
            epoch = epoch or time.time()+2+lead
            self.anchor = time.monotonic() + epoch-time.time()
            self.cancel = threading.Event()
            self.paused, self.pause_ms, self.remote = False, 0., remote
            self.lease = time.monotonic()+6
            self.thread = threading.Thread(target=self._run, args=(renderer, outputs, bus, media), daemon=True)
            self.thread.start()
        return self.status()

    def _run(self, renderer, outputs, bus, media):
        due = [float('-inf')]*len(outputs)
        totals, measured = [0]*len(outputs), time.monotonic()
        context_due = {}
        context_period = {}
        for output in outputs:
            backend = PINS[output['gpio']][0]
            context_period[backend] = max(context_period.get(backend,0), output['count']*30e-6+.004)
        cycle = -1
        audio_bias, last_audio_sync = None, time.monotonic()
        try:
            while not self.cancel.is_set():
                if self.remote and time.monotonic() > self.lease:
                    raise RuntimeError('Master heartbeat lost; remote output stopped')
                raw = self.position()
                if not renderer.project['loop'] and raw >= renderer.project['duration_ms']+max([0]+[o['offset_ms'] for o in outputs]):
                    break
                new_cycle = max(0, int(raw//renderer.project['duration_ms'])) if renderer.project['loop'] else 0
                if new_cycle != cycle:
                    if self.audio:
                        self.audio.stop()
                    cycle = new_cycle
                    audio_bias = None
                    if media:
                        audio_due = self.anchor+(cycle*renderer.project['duration_ms']+renderer.project['audio_offset_ms'])/1000
                        self.audio = AudioTrack(media, audio_due, lambda: self.paused)
                position = raw-cycle*renderer.project['duration_ms']
                self.state = 'paused' if self.paused else 'starting' if raw < 0 else 'playing'
                now = time.monotonic()
                # Follow the audio feed's long-term rate instead of letting an
                # independent sound-device clock drift over a lengthy sequence.
                # A stable startup bias retains the user's physical latency trim.
                if self.audio and not self.paused and now-last_audio_sync >= 1:
                    frames, stamp = self.audio.progress
                    if frames >= 4800 and now-stamp < .2:
                        audio_ms = frames/48 + (now-stamp)*1000
                        expected = cycle*renderer.project['duration_ms']+renderer.project['audio_offset_ms']+audio_ms
                        if audio_bias is None:
                            audio_bias = raw-expected
                        else:
                            drift = expected+audio_bias-raw
                            self.anchor -= max(-5,min(5,drift))/1000
                    last_audio_sync = now
                updates = {}
                for index, output in enumerate(outputs):
                    backend = PINS[output['gpio']][0]
                    if now >= due[index] and now >= context_due.get(backend, float('-inf')):
                        if due[index] != float('-inf') and now-due[index] > 1/output['fps']:
                            self.line_stats[index]['late_frames'] += 1
                        updates[index] = renderer.frame(position, output)
                        totals[index] += 1
                        period = 1/output['fps']
                        due[index] = max(now, due[index]+period) if due[index] != float('-inf') else now+period
                if updates and bus:
                    bus.show(updates)
                    for index in updates:
                        backend = PINS[outputs[index]['gpio']][0]
                        context_due[backend] = now+context_period[backend]
                if now-measured >= 1:
                    for index, total in enumerate(totals):
                        self.line_stats[index]['actual_fps'] = round(total/(now-measured),1)
                    totals, measured = [0]*len(outputs), now
                self.cancel.wait(.002)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if self.audio:
                self.audio.stop()
            if bus:
                try:
                    bus.show({i: np.zeros((3,o['count']),dtype=np.uint8) for i,o in enumerate(outputs)})
                except Exception as exc:
                    self.error = self.error or str(exc)
                finally:
                    bus.close()
            self.state = 'error' if self.error else 'idle'
            self.release()

    def set_paused(self, paused):
        with self.lock:
            if paused and not self.paused:
                self.pause_ms = self.position()
                self.paused = True
            elif not paused and self.paused:
                self.anchor = time.monotonic()-self.pause_ms/1000
                self.paused = False

    def heartbeat(self, position_ms, paused=False):
        self.lease = time.monotonic()+6
        if self.remote:
            if self.project and self.project['loop']:
                duration = self.project['duration_ms']
                local = self.position() % duration if self.position() >= 0 else self.position()
            else:
                local = self.position()
            drift = position_ms-local
            self.anchor -= (drift if abs(drift)>500 else max(-20,min(20,drift)))/1000
            self.set_paused(paused)

    def stop(self):
        self.cancel.set()
        if self.audio:
            self.audio.stop()
        thread = self.thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError('Previous output thread is still stopping; retry Stop')
        self.thread = None
        if self.state != 'error':
            self.state = 'idle'
