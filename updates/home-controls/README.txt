HNLS ALL-IN-ONE HOME CONTROLS — MAIN PI ONLY

This is ONE catch-up update for the working holiday-palette build (rc.11), the
Easy UI build (rc.12), or the Play now build (rc.13). It includes the navigation
and Play now changes. You do not need to install those earlier ZIPs first.

Copy hnls-home-controls-update.zip to /home/pi on LED03, then:

python3 -m zipfile -e /home/pi/hnls-home-controls-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-home-controls-update/install_update.py

The guarded 22-file update briefly restarts HNLS because it includes API/scheduler
changes. Python is semantically compiled and templates parsed before changes.
Known predecessor hashes are checked; a private code backup and exact rollback
command are provided. Private settings, local config templates, GPIO assignments,
counts, colors, saved moments, speaker routes, schedule and pairing are retained.
No slave installation is required. Refresh with Ctrl+F5 and open Home.

EVERYDAY CONTROLS ARE NOW ON HOME
- Play now and Stop show.
- Choose and play a particular song with all lights; pause/resume, previous/next,
  replay, seek and shuffle. Add one or more songs from the same page.
- Holiday colors and HNLS-selected / Classic effects for all lights or one string.
- A brightness slider and explicit Set brightness button for that selection.
- Enable/disable show hours, start/stop times, and expandable days/time zone.
- Choose the headphone jack or a saved Bluetooth speaker.
- Inline Windows PC audio sender/download/start/stop controls for Spotify/Pandora.

Opening Home does not start music or save settings. Play now starts shuffled
uploaded-song playback. Play selected song starts that song with lights and keeps
your existing shuffle choice. Both participate in the manual schedule override:
normal schedule control resumes at the next scheduled opening/closing boundary.

Save look changes only the selected colors/effect choice; Set brightness changes
only brightness. Neither starts a stopped show. Unchanged settings (sync groups,
LED limits, individual colors when no preset is selected) stay per-string. If a
batch partially fails, the response names updated and failed strings, keeps the
choices retryable and refreshes the saved-state snapshot. Speaker changes briefly
reopen audio. New Bluetooth pairing, detailed frequency colors/grouping, wiring
and custom song moments remain in their existing detailed pages.

The visual theme is retained. Task cards and legacy manual effects remain under
optional More tools / Advanced sections on Home. Find a setting points common
controls back to Home.

Tests cover Home's read-only load, safe filenames, music/upload/transport/shuffle,
selected-song override, scoped/preserved/partial look changes, mixed values,
unsaved edits, speakers, authenticated APIs and cumulative install/rollback from
actual source snapshots of rc.11/12/13 with a different local template. Real Pi
playback and desktop/phone visual acceptance still require a check on the display.
