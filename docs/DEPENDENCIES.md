# Dependencies and supported baseline

| Role | Captured environment | Captured service |
| --- | --- | --- |
| Controller | Raspberry Pi OS/Raspbian Bookworm 12, aarch64, Python 3.11.2 | mlsc |
| Receiver | Raspberry Pi OS/Raspbian Bullseye 11, armv7l, Python 3.9.2 | mlsc-receiver |

`requirements/controller.txt` lists direct runtime dependencies using versions captured on the working controller. PyAudio is supplied by apt python3-pyaudio in a venv created with --system-site-packages. The controller needs ffmpeg, ALSA aplay/amixer tools and native rpi-ws281x. Python 3.11+ is required by the controller dependency baseline; Python 3.9 remains the receiver baseline.

`requirements/*-observed.json` retain the complete pip list and OS/Python information for reference. They are **not installation lockfiles**: the captured environment includes desktop tools, apt-installed packages and unrelated type stubs. Installing that whole list would not be a sensible application setup. Direct requirements are pinned; their transitive dependencies are not a full hash-locked dependency graph.

The installer performs dependency resolution, runtime imports and real Draft 2020-12 default-configuration validation before starting the controller. Package download, wheel availability, native compilation and runtime startup still require a physical fresh-Pi test. No packaged Python wheels, OS image, arbitrary-architecture support or Pi 5 native-output support is claimed.

Bluetooth support is in the application. Select it through the web audio controls; BlueZ/BlueALSA availability is checked there. The fresh installer does not replace your system ALSA configuration or claim Bluetooth pairing works without the appropriate adapter/backend. Analog audio requires supported Pi hardware and its OS audio driver.
