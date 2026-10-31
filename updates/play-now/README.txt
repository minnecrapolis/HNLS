HNLS PLAY NOW — MAIN PI ONLY, FOR THE CURRENT rc.12 INTERFACE

Copy hnls-play-now-update.zip to /home/pi on LED03, then:

python3 -m zipfile -e /home/pi/hnls-play-now-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-play-now-update/install_update.py

This update includes scheduler/API changes and briefly restarts an active main
service. It semantically compiles all bundled Python and parses bundled templates
before changing files. Known-version checks, a private code backup, partial-failure
rollback and an exact rollback command are included. Private settings, saved hours,
GPIOs, LED counts, colors, brightness, song moments and pairing are retained.
No slave installation is needed. Refresh Home or Music with Ctrl+F5 afterward.

Home and Music now have Play now and Stop show buttons.
- Play now starts an uploaded song on shuffle and the saved Light Show on every
  configured output, including the remote Pi. It can replace a paused/file/PC source.
- Outside enabled show hours, manual playback survives normal scheduler checks.
  The next scheduled start resumes normal scheduled playback, and the scheduled
  closing time then stops it normally.
- Inside show hours, manual playback still stops at the scheduled closing time.
- With the schedule disabled, it continues until you stop it.
- Stop show turns all normal outputs off and stops music. A manual stop inside a
  scheduled window is not undone on the next scheduler poll; the next scheduled
  opening can start normally.
- The saved schedule file is not written by either button. Manual override state
  is intentionally temporary and is not retained across a main-service restart.
- Empty libraries show an upload instruction. Spotify/Pandora still use Music's
  PC audio controls; Play now uses the uploaded playlist and enables shuffle.

Status text explains when schedule control returns. Changing/enabling saved hours
can immediately enter/leave a schedule window as before. Opening a page, searching,
or polling status never starts the show; the Play now click is required.

Tests cover cold/outside-hours start, in-window closing, next-opening handover,
manual stop without immediate restart, disabled/overnight/reboot cases, unchanged
schedule bytes, empty library, fail-dark start error, authenticated API validation,
double-click/error handling and install/refusal/rollback. Actual Pi playback and
schedule-boundary acceptance remain hardware checks.
