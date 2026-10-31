"""AudioProcessService integration; streaming shares the normal output/DSP path."""
import copy
from time import monotonic, sleep
import numpy as np
from libs.pc_stream import Receiver, credentials
from libs.music_library import write_status


class PCStreamMixin:
    def _close_pc_stream(self):
        receiver = getattr(self, '_pc_receiver', None)
        if receiver is not None:
            receiver.close()
            self._pc_receiver = None

    def _start_pc_stream(self):
        # Bind before stopping the current source so port errors preserve playback.
        if getattr(self, '_pc_receiver', None) is not None:
            return
        receiver = Receiver(credentials(), self._frames_per_buffer)
        self._cleanup_music()
        self._close_microphone_stream()
        self._pc_receiver = receiver
        self._source_mode = 'pc_stream'
        self._pc_active = False
        self._pc_status_at = 0.
        self._pc_last_audio = monotonic()
        self._pc_output_error = None
        self._music_position = 0.
        self._music_duration = None
        self._playback_epoch += 1
        self._show_analyzer.start_song(None)
        self._publish_playback(True)
        write_status('pc_stream_waiting')

    def _stop_pc_stream(self):
        self._cleanup_music()
        self._source_mode = 'playlist_idle'
        self._playback_epoch += 1
        self._publish_playback(True)
        write_status('stopped')

    def _pc_stream_routine(self):
        from libs.dsp import DSP
        from libs.alsa_music_output import HeadphoneOutput
        receiver = self._pc_receiver
        data = receiver.read()
        now = monotonic()
        if data is None:
            if now-self._pc_last_audio > .35:
                if self._pc_active:
                    self._pc_active = False
                    self._playback_epoch += 1
                    if self._music_output_stream is not None:
                        self._music_output_stream.close()
                        self._music_output_stream = None
                self._publish_playback(True)
            if now-self._pc_status_at >= .5:
                self._pc_status_at = now
                write_status('pc_stream' if self._pc_active else 'pc_stream_waiting', error=self._pc_output_error)
            sleep(.003)
            return
        rate = receiver.buffer.rate
        self._pc_last_audio = now
        if not self._pc_active or self._device_rate != rate:
            if self._music_output_stream is not None:
                self._music_output_stream.close()
                self._music_output_stream = None
            self._pc_active = True
            self._device_rate = rate
            dsp_config = copy.deepcopy(self._config)
            dsp_config['general_settings']['default_sample_rate'] = rate
            self._dsp = DSP(dsp_config)
            self._show_analyzer.start_song(None)
            self._playback_epoch += 1
            self._pc_output_error = None
            try:
                self._music_output_stream = HeadphoneOutput(rate=rate, channels=2)
            except Exception as exc:
                self._pc_output_error = str(exc)
                self._music_output_stream = None
        if self._music_output_stream is not None:
            try:
                self._music_output_stream.write(data)
            except OSError as exc:
                self._pc_output_error = str(exc)
                self._music_output_stream.close()
                self._music_output_stream = None
        else:
            sleep(self._frames_per_buffer / float(rate))
        stereo = np.frombuffer(data, dtype='<i2').reshape(-1, 2)
        mono = stereo.astype(np.int32).mean(axis=1).astype(np.int16)
        self._music_position += len(mono)/float(rate)
        self._process_samples(mono)
        if now-self._pc_status_at >= .5:
            self._pc_status_at = now
            write_status('pc_stream', error=self._pc_output_error)
