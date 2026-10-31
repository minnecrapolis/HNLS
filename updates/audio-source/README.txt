HNLS MUSIC SOURCE CHOICE — MAIN PI ONLY

One cumulative update for rc.11, rc.12, rc.13 or rc.14. Includes Home controls,
Easy UI and Play now. You do not need to install earlier UI ZIPs first.

Copy hnls-audio-source-update.zip to /home/pi on LED03, then:
python3 -m zipfile -e /home/pi/hnls-audio-source-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-audio-source-update/install_update.py

HNLS briefly restarts. Refresh Ctrl+F5. No slave update is required.

Home and Music now show Where is the music coming from? at the top:
- Play songs on the Pi starts the saved local playlist on shuffle with lights.
- Stream from PC selects live Windows audio for the Pi speaker and lights.
- Stop PC sound & lights stops reception, not Spotify on Windows.
The existing selected Pi headphone/Bluetooth speaker is used for both sources.
PC streaming is not recorded. Leave the Windows sender running while streaming.
Use Download sender under Connect the Windows PC if it is not already installed.

While a PC stream is selected, local playlist/seek/song controls are hidden.
Switch back to Pi songs to use them. Color/effect/brightness/speaker controls
stay available. Uploaded-song timed moments do not run against live streams.
Schedule boundaries still take control. Streaming is selected again after reboot.

All code is verified before service interruption. Unexpected installed versions
are refused without changes. Private settings, speaker selection, cues, wiring,
counts, GPIOs, local config template and pairing are retained. A private code
backup and exact rollback command are printed. A stopped service stays stopped.

244 automated Python tests and Node UI simulations passed locally. Pi playback
and real desktop/phone visual acceptance have not been tested in this environment.
