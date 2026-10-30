HNLS SHOW HOURS + CLICKABLE SONGS

INSTALL ON MAIN PI ONLY. No receiver changes are required.
Copy hnls-show-hours-update.zip to /home/pi, then run:

python3 -m zipfile -e /home/pi/hnls-show-hours-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-show-hours-update/install_update.py

This briefly restarts HNLS if it is running, so music will stop during installation.
It backs up all eight changed files and prints an exact rollback command.
No audio/GPIO driver, count, color, brightness, music, cues or pairing settings
are replaced. Unrecognized installed file versions are refused before changes.

Refresh Music with Ctrl+F5. Automatic Show Hours is near the top.
Enable it, choose weekdays, start and stop, time zone, and Save show hours.
America/Chicago is the default for Minnesota; verify the displayed show clock.
Each selected day is the START day for a window that crosses midnight.

At the opening: random first song, shuffle enabled, main Song Show on all outputs.
At closing: all outputs Off and music stopped. The Pis stay on for tomorrow.
Windows are checked roughly every two seconds; queue/OS delays can add latency.
Do not power off the receiver: it follows the main Pi's output and watchdog.

The schedule runs server-side with the browser closed and is saved across reboots.
If the main Pi restarts during enabled show hours it starts a shuffled show.
If it restarts outside hours it forces music/lights off once.
Disabling the schedule stops a scheduled show. Manual controls remain available;
a manually stopped song is not constantly restarted during the same window.
The next schedule boundary takes control again. No songs: waits/retries.

Song titles are playable in both Your Playlist and Song Analysis Details.
Keyboard users can Tab to a title and press Enter/Space. Existing Play/Delete
buttons remain. Polling preserves unchanged rows and in-progress schedule edits.

Settings are stored privately in /share/.mlsc/show_schedule.json.
A failed settings save leaves the previous file intact. Use the web interface;
manual editing is not required. The schedule does not shut down the Pi OS.

Automated tests cover boundaries, overnight/day handling, DST, reboot recovery,
validation, schedule actions, UI controls and update rollback. Physical testing
of the new scheduled show is still needed on the actual Pi installation.
