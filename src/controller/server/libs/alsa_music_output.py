"""Direct ALSA headphone playback, using the path verified on LED03."""
import subprocess
import tempfile


class HeadphoneOutput:
    def __init__(self, rate, channels=2):
        from libs.audio_output import playback_command
        command = playback_command(rate, channels)
        self._errors = tempfile.TemporaryFile()
        self._process = None
        try:
            self._process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=self._errors, bufsize=0, pipesize=4096)
        except Exception:
            self._errors.close()
            raise

    def _error_message(self):
        if self._errors.closed:
            return "output is closed"
        self._errors.seek(0)
        return self._errors.read(4096).decode("utf-8", errors="replace").strip()

    def write(self, data):
        process = self._process
        if process is None or process.poll() is not None:
            raise OSError("Selected audio output stopped: " + self._error_message())
        remaining = memoryview(data)
        try:
            while remaining:
                written = process.stdin.write(remaining)
                if not written:
                    raise BrokenPipeError("No audio bytes written")
                remaining = remaining[written:]
        except (BrokenPipeError, OSError) as exc:
            raise OSError("Selected audio output failed: " + self._error_message()) from exc

    def finish(self):
        """At a natural song end, drain the final samples before changing tracks."""
        process = self._process
        if process is None:
            return
        try:
            process.stdin.close()
            code = process.wait(timeout=2)
            if code:
                raise OSError("Selected audio output failed: " + self._error_message())
        except subprocess.TimeoutExpired:
            self.stop_stream()
            raise OSError("Timed out draining headphone output")

    def stop_stream(self):
        """An explicit Stop discards queued audio instead of waiting for a drain."""
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def close(self):
        try:
            self.stop_stream()
        finally:
            if self._process is not None and self._process.stdin is not None:
                try:
                    self._process.stdin.close()
                except OSError:
                    pass
            self._process = None
            self._errors.close()
