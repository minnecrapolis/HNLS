import subprocess
import math
import sys
from multiprocessing import Queue
from time import sleep, time, monotonic

import numpy as np
import pyaudio
from loguru import logger

from libs.audio_info import AudioInfo
from libs.alsa_music_output import HeadphoneOutput
from libs.config_service import ConfigService
from libs.dsp import DSP
from libs.fps_limiter import FPSLimiter
from libs.music_library import safe_music_path, write_status, trash_music_file
from libs.notification_enum import NotificationEnum
from libs.notification_item import NotificationItem
from libs.queue_wrapper import QueueWrapper
from libs.song_analysis import SongShowAnalyzer


class AudioProcessService:
    def start(self, config_lock, notification_queue_in, notification_queue_out, audio_queue, py_audio):
        self._config_lock = config_lock
        self._notification_queue_in = QueueWrapper(notification_queue_in)
        self._notification_queue_out = QueueWrapper(notification_queue_out)
        self._audio_queue = QueueWrapper(audio_queue)

        self.audio_buffer_queue = QueueWrapper(Queue(2))
        self._py_audio = py_audio
        self.stream = None

        # Internal music source state.
        self._source_mode = "microphone"
        self._music_process = None
        self._music_output_stream = None
        self._music_file = None
        self._music_paused = False
        self._music_output_channels = 2
        self._music_had_samples = False
        self._music_failed_files = set()
        self._music_gap_until = None
        self._music_gap_paused_at = None
        self._playback_epoch = 0
        self._music_position = 0.0
        self._music_duration = None
        self._music_status_at = 0.0
        self._music_gap_direction = 1
        self._show_analyzer = SongShowAnalyzer()

        self.init_audio_service(show_output=True)
        write_status("microphone")

        try:
            while True:
                self.audio_service_routine()
                self._fps_limiter.fps_limiter()
        except KeyboardInterrupt:
            self._cleanup_music()
            self._show_analyzer.close()
            sys.exit()

    def init_audio_service(self, show_output=False):
        try:
            # Initial config load.
            ConfigService.instance(self._config_lock).load_config()
            self._config = ConfigService.instance(self._config_lock).config

            # Audio/DSP parameters are source-independent. Initialize these even if
            # no microphone is configured so internal files can still drive effects.
            self._device_rate = self._config["general_settings"]["default_sample_rate"]
            self._frames_per_buffer = self._config["general_settings"]["frames_per_buffer"]
            self.n_fft_bins = self._config["general_settings"]["n_fft_bins"]
            self._dsp = DSP(self._config)
            self.audio = np.empty((self._frames_per_buffer), dtype="int16")

            # Init FPS Limiter.
            self._fps_limiter = FPSLimiter(120)
            self._skip_routine = False
            self._devices = AudioInfo.get_audio_devices(self._py_audio)

            self.log_output(show_output, "INFO", "Found the following audio sources:")

            # Select the audio device you want to use.
            selected_device_list_index = 0
            try:
                mic_id = self._config["general_settings"]["device_id"]
                # -1 means no mic available. File playback still works.
                if mic_id == -1:
                    self.selected_device = None
                    self.stream = None
                    return
                selected_device_list_index = int(mic_id)
            except Exception:
                logger.exception("Could not parse audio id.")

            # Check if the index is inside the list.
            self.selected_device = None
            for current_audio_device in self._devices:
                if current_audio_device.device_id == selected_device_list_index:
                    self.selected_device = current_audio_device

            logger.debug(f"Selected Device: {self.selected_device}")

            # Could not find a mic with the selected mic id, so use the first available device.
            if self.selected_device is None:
                self.log_output(show_output, "ERROR", "********************************************************")
                self.log_output(show_output, "ERROR", "*                      Error                           *")
                self.log_output(show_output, "ERROR", "********************************************************")
                self.log_output(show_output, "ERROR", f"Could not find the mic with the id: {selected_device_list_index}")
                self.log_output(show_output, "ERROR", "Using the first mic as fallback.")
                self.log_output(show_output, "ERROR", "Please change the id of the mic inside the config.")
                try:
                    self.selected_device = self._devices[0]
                except IndexError:
                    self.selected_device = AudioInfo.get_default_audio_device(self._py_audio)

            if self.selected_device is None:
                self.stream = None
                return

            self.log_output(show_output, "INFO", f"Selected Device: {self.selected_device.to_string()}")

            # Init Timer
            self.start_time_1 = time()
            self.ten_seconds_counter_1 = time()
            self.start_time_2 = time()
            self.ten_seconds_counter_2 = time()

            # Reinit buffer queue
            self.audio_buffer_queue = QueueWrapper(Queue(2))

            # Callback function to stream microphone audio in another thread.
            def callback(in_data, frame_count, time_info, status):
                if self._skip_routine or self._source_mode != "microphone":
                    return (self.audio, pyaudio.paContinue)

                self.audio_buffer_queue.put_none_blocking(in_data)

                self.end_time_1 = time()
                if time() - self.ten_seconds_counter_1 > 10:
                    self.ten_seconds_counter_1 = time()
                    time_dif = self.end_time_1 - self.start_time_1
                    if time_dif > 0:
                        logger.info(f"Callback | FPS: {1 / time_dif:.2f}")
                self.start_time_1 = time()

                return (self.audio, pyaudio.paContinue)

            self.log_output(show_output, "DEBUG", "Starting Open Audio Stream...")
            self.stream = self._py_audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._device_rate,
                input=True,
                input_device_index=self.selected_device.device_id,
                frames_per_buffer=self._frames_per_buffer,
                stream_callback=callback
            )
        except Exception:
            logger.exception("Unexpected error in init_audio_service.")

    @staticmethod
    def log_output(show_output, log_level, message) -> None:
        if show_output:
            if log_level == "INFO":
                logger.info(message)
            elif log_level == "DEBUG":
                logger.debug(message)
            elif log_level == "ERROR":
                logger.error(message)
            else:
                logger.debug(message)
        else:
            logger.debug(message)

    def _close_microphone_stream(self):
        if self.stream is not None:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _cleanup_music(self):
        self._music_gap_until = None
        self._music_gap_paused_at = None
        if self._music_process is not None:
            try:
                if self._music_process.poll() is None:
                    self._music_process.terminate()
                    self._music_process.wait(timeout=2)
            except Exception:
                try:
                    self._music_process.kill()
                except Exception:
                    pass
            self._music_process = None

        if self._music_output_stream is not None:
            try:
                self._music_output_stream.stop_stream()
            except Exception:
                pass
            try:
                self._music_output_stream.close()
            except Exception:
                pass
            self._music_output_stream = None

        self._music_paused = False
        self._music_file = None

    def _publish_playback(self, blackout):
        self._audio_queue.put_none_blocking({'_playback': {
            'epoch': self._playback_epoch, 'blackout': blackout}})

    def _begin_song_gap(self, direction=1):
        current, had_samples = self._music_file, self._music_had_samples
        self._cleanup_music()
        self._music_file, self._music_had_samples = current, had_samples
        self._playback_epoch += 1
        self._publish_playback(True)
        self._music_gap_direction = direction
        self._music_gap_until = monotonic() + 2.0
        self._write_music_status('between_songs')
        logger.info('Song finished: LEDs off; next song starts after two seconds.')

    def _restore_microphone(self):
        self._cleanup_music()
        self._source_mode = "microphone"
        self._playback_epoch += 1
        self._publish_playback(False)
        self._show_analyzer.start_song(None)
        self.init_audio_service()
        write_status("microphone")

    def _probe_music_duration(self, path):
        try:
            result = subprocess.run(['/usr/bin/ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                capture_output=True, text=True, timeout=3, check=True)
            value = float(result.stdout.strip())
            return value if math.isfinite(value) and value > 0 else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def _write_music_status(self, state=None):
        write_status(state or ('paused' if self._music_paused else 'playing'), self._music_file,
            error=getattr(self, '_music_audio_error', None), position=self._music_position, duration=self._music_duration)
        self._music_status_at = monotonic()

    def _start_music(self, filename, start_seconds=0.0, paused=False):
        try:
            path = safe_music_path(filename)
            if not path.is_file():
                raise FileNotFoundError(filename)

            if self._source_mode == "music":
                self._cleanup_music()
            else:
                self._close_microphone_stream()

            self._music_duration = self._probe_music_duration(path)
            self._music_position = max(0.0, float(start_seconds))
            # Decode to signed 16-bit stereo PCM. The same frames are sent to the
            # Pi's audio output and downmixed to mono for the existing DSP pipeline.
            command = [
                "/usr/bin/ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-ss", str(self._music_position),
                "-i", str(path),
                "-vn",
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ac", str(self._music_output_channels),
                "-ar", str(self._device_rate),
                "pipe:1",
            ]
            self._music_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )

            self._music_audio_error = None
            try:
                self._music_output_stream = HeadphoneOutput(
                    rate=self._device_rate, channels=self._music_output_channels
                )
            except Exception as exc:
                self._music_audio_error = str(exc)
                # LEDs can still react if no audio output device is available.
                logger.exception("Could not open the ALSA headphone output. LEDs will continue without audible playback.")
                self._music_output_stream = None

            self._source_mode = "music"
            self._music_paused = paused
            self._music_file = filename
            self._music_had_samples = self._music_position > 0
            self._playback_epoch += 1
            self._dsp = DSP(self._config)
            self._show_analyzer.start_song(path)
            self._show_analyzer.position = self._music_position
            self._write_music_status()
            logger.info(f"Playing internal music file: {filename}")
            return True
        except Exception as exc:
            logger.exception("Could not start internal music file.")
            write_status("error", filename, str(exc))
            self._restore_microphone()
            return False

    def _advance_music(self, direction=1):
        """Refresh the uploaded library and play the next song, wrapping at the end."""
        current = self._music_file
        try:
            directory = safe_music_path(current).parent
            extensions = {
                ".mp3", ".wav", ".flac", ".ogg", ".oga", ".opus",
                ".m4a", ".aac", ".wma", ".aif", ".aiff", ".mp4", ".webm",
            }
            if self._music_had_samples:
                self._music_failed_files.discard(current)
            else:
                self._music_failed_files.add(current)
                logger.warning(f"Skipping music file with no decoded audio: {current}")

            songs = sorted(
                (p.name for p in directory.iterdir()
                 if p.is_file() and p.suffix.lower() in extensions),
                key=lambda name: (name.casefold(), name),
            )
            # Retain the alphabetical position even if the playing file was deleted.
            current_key = (current.casefold(), current)
            later = [name for name in songs if (name.casefold(), name) > current_key]
            earlier = [name for name in songs if (name.casefold(), name) <= current_key]
            ordered = later + earlier if direction > 0 else list(reversed([name for name in songs if (name.casefold(), name) < current_key])) + list(reversed([name for name in songs if (name.casefold(), name) >= current_key]))
            from libs.hnls_playlist import shuffle_order, shuffle_selected
            available = [name for name in songs if name not in self._music_failed_files]
            ordered = shuffle_order(self, available, current, direction, ordered)
            for filename in ordered:
                if filename in self._music_failed_files:
                    continue
                logger.info(f"Playlist advancing to: {filename}")
                if self._start_music(filename):
                    shuffle_selected(self, filename)
                    return
                self._music_failed_files.add(filename)

            logger.warning("Playlist stopped: no playable music files remain.")
        except Exception:
            logger.exception("Could not advance the music playlist.")
        self._cleanup_music()
        self._source_mode = "playlist_idle"
        self._publish_playback(True)
        write_status("stopped")

    def _handle_notifications(self):
        while not self._notification_queue_in.empty():
            current_notification_item = self._notification_queue_in.get_blocking()
            notification = current_notification_item.notification_enum

            if notification is NotificationEnum.config_refresh:
                self._close_microphone_stream()
                self._cleanup_music()
                self._source_mode = "microphone"
                self._playback_epoch += 1
                self._publish_playback(False)
                self._show_analyzer.start_song(None)
                self.init_audio_service()
                write_status("microphone")
                self._notification_queue_out.put_blocking(
                    NotificationItem(NotificationEnum.config_refresh_finished, current_notification_item.device_id)
                )
            elif notification is NotificationEnum.process_continue:
                self._skip_routine = False
            elif notification is NotificationEnum.process_pause:
                self._skip_routine = True
            elif notification is NotificationEnum.music_play:
                # An explicit Play retries any files skipped during the previous run.
                payload = current_notification_item.payload or {}
                if payload.get('action'):
                    self._handle_music_command(payload)
                else:
                    self._music_failed_files.clear()
                    self._start_music(payload.get("file"))
            elif notification is NotificationEnum.music_pause:
                if self._source_mode == "music" and not self._music_paused:
                    self._music_paused = True
                    if self._music_gap_until is not None:
                        self._music_gap_paused_at = monotonic()
                    self._write_music_status("paused")
            elif notification is NotificationEnum.music_resume:
                if self._source_mode == "music" and self._music_paused:
                    self._music_paused = False
                    if self._music_gap_until is not None and self._music_gap_paused_at is not None:
                        self._music_gap_until += monotonic() - self._music_gap_paused_at
                        self._music_gap_paused_at = None
                    self._write_music_status("between_songs" if self._music_gap_until is not None else "playing")
            elif notification is NotificationEnum.music_stop:
                self._restore_microphone()

    def _handle_music_command(self, payload):
        try:
            action = payload.get('action')
            if action == 'output_changed':
                if self._source_mode == 'music' and self._music_file and self._music_gap_until is None:
                    filename, position, paused = self._music_file, self._music_position, self._music_paused
                    self._playback_epoch += 1
                    self._publish_playback(True)
                    self._start_music(filename, position, paused)
                return
            if action == 'delete':
                filename = payload.get('file')
                trash_music_file(filename)
                if self._source_mode == 'music' and self._music_file == filename:
                    self._music_had_samples = True
                    self._begin_song_gap()
                return
            if self._source_mode != 'music' or not self._music_file:
                raise ValueError('Choose a song to play first.')
            if action in ('next', 'previous'):
                self._music_had_samples = True
                self._begin_song_gap(-1 if action == 'previous' else 1)
            elif action in ('replay', 'seek', 'seek_relative'):
                target = 0.0 if action == 'replay' else float(payload.get('seconds', 0))
                if action == 'seek_relative':
                    target += self._music_position
                target = max(0.0, target)
                if not math.isfinite(target):
                    raise ValueError('Invalid seek position')
                if self._music_duration is not None and target >= self._music_duration:
                    self._music_had_samples = True
                    self._begin_song_gap()
                    return
                filename, paused = self._music_file, self._music_paused and action != 'replay'
                self._playback_epoch += 1
                self._publish_playback(True)
                self._start_music(filename, target, paused)
            else:
                raise ValueError('Unknown music control')
        except (OSError, ValueError, TypeError):
            logger.exception('Music control failed.')
            write_status('error', self._music_file, 'Could not complete music control. Check the MLSC log.')

    def _process_samples(self, y):
        y = y.astype(np.float32)
        audio_datas = self._dsp.update(y)
        audio_datas["_playback"] = {"epoch": self._playback_epoch, "blackout": False,
            "file": getattr(self, '_music_file', None) if getattr(self, '_source_mode', None) == 'music' else None,
            "position": getattr(self, '_music_position', 0.)}
        audio_datas["show"] = self._show_analyzer.update(
            audio_datas["show_raw"], len(y) / float(self._device_rate)
        )

        if audio_datas["vol"] < self._config["general_settings"]["min_volume_threshold"]:
            audio_datas["mel"] = np.zeros(self.n_fft_bins)

        self._audio_queue.put_none_blocking(audio_datas)

    def _music_routine(self):
        if self._music_paused:
            sleep(0.02)
            return

        if self._music_gap_until is not None:
            self._publish_playback(True)
            if monotonic() >= self._music_gap_until:
                self._music_gap_until = None
                self._advance_music(self._music_gap_direction)
            else:
                sleep(0.01)
            return

        if self._music_process is None or self._music_process.stdout is None:
            self._restore_microphone()
            return

        bytes_per_frame = 2 * self._music_output_channels
        data = self._music_process.stdout.read(self._frames_per_buffer * bytes_per_frame)
        if not data:
            logger.info("Internal music file finished.")
            if self._music_output_stream is not None:
                try:
                    self._music_output_stream.finish()
                except Exception:
                    logger.exception("Could not drain the final headphone audio samples.")
            self._begin_song_gap()
            return

        self._music_had_samples = True

        # Keep audible playback and LED analysis on exactly the same decoded frames.
        if self._music_output_stream is not None:
            try:
                self._music_output_stream.write(data)
            except Exception as exc:
                self._music_audio_error = str(exc)
                self._write_music_status()
                logger.exception("Audio output failed; continuing LED analysis without playback.")
                try:
                    self._music_output_stream.close()
                except Exception:
                    pass
                self._music_output_stream = None
        else:
            # Without an output stream there is nothing to pace ffmpeg, so preserve real-time speed.
            frame_count = len(data) // bytes_per_frame
            sleep(frame_count / float(self._device_rate))

        stereo = np.frombuffer(data, dtype=np.int16)
        if stereo.size < self._music_output_channels:
            return

        usable = stereo.size - (stereo.size % self._music_output_channels)
        stereo = stereo[:usable].reshape(-1, self._music_output_channels)
        self._music_position += len(stereo) / float(self._device_rate)
        if monotonic() - self._music_status_at >= 0.25:
            self._write_music_status()
        mono = stereo.astype(np.int32).mean(axis=1).astype(np.int16)

        # DSP expects the configured chunk size. Pad the final partial chunk with silence.
        if mono.size < self._frames_per_buffer:
            mono = np.pad(mono, (0, self._frames_per_buffer - mono.size))
        elif mono.size > self._frames_per_buffer:
            mono = mono[:self._frames_per_buffer]

        self._process_samples(mono)

    def audio_service_routine(self):
        try:
            self._handle_notifications()

            if self._skip_routine:
                return

            if self._source_mode == "playlist_idle":
                sleep(0.02)
                return

            if self._source_mode == "music":
                self._music_routine()
                return

            in_data = self.audio_buffer_queue.get_blocking_with_timeout()
            if in_data is None:
                logger.debug("Audio in timeout. Queue is Empty")
                return

            y = np.frombuffer(in_data, dtype=np.int16)
            self._process_samples(y)

            self.end_time_2 = time()
            if time() - self.ten_seconds_counter_2 > 10:
                self.ten_seconds_counter_2 = time()
                time_dif = self.end_time_2 - self.start_time_2
                if time_dif > 0:
                    logger.info(f"Routine | FPS: {1 / time_dif:.2f}")
            self.start_time_2 = time()

        except OSError:
            logger.exception("OSError while reading the audio stream.")
        except Exception:
            logger.exception("Unexpected error in audio routine.")
