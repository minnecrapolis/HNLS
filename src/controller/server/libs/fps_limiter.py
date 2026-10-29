from time import sleep, time


def effective_device_fps(config):
    """Leave room for wire transfer and rendering on long Raspberry Pi chains."""
    requested = max(1.0, float(config["fps"]))
    if config.get("output_type") != "output_raspi":
        return requested
    bits = 32 if config.get("led_strip", "").startswith("sk6812") else 24
    frequency = max(1, config["output"]["output_raspi"]["led_freq_hz"])
    wire_time = config["led_count"] * bits / float(frequency)
    return min(requested, 1.0 / (wire_time + 0.004))


class FPSLimiter:

    def __init__(self, fps) -> None:
        self._fps = fps

        # Init FPS Limiter.
        self.fps_limiter_start = time()
        self.max_fps = self._fps
        self.min_waiting_time = 1 / self.max_fps

    def fps_limiter(self):
        self.fps_limiter_end = time()
        time_between_last_cycle = self.fps_limiter_end - self.fps_limiter_start
        if time_between_last_cycle < self.min_waiting_time:
            time_diff = self.min_waiting_time - time_between_last_cycle
            if time_diff > 0.001:
                sleep(time_diff)

        self.fps_limiter_start = time()
