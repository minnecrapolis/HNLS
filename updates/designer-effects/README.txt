HNLS SONG DESIGNER EFFECTS + REALTIME WORKER UPDATE

MAIN PI ONLY. No receiver update required.
Copy hnls-designer-effects-update.zip to /home/pi, then run:

python3 -m zipfile -e /home/pi/hnls-designer-effects-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-designer-effects-update/install_update.py

The installer verifies known captured/rc.2/rc.3 file versions, backs up ten files,
briefly stops/restarts HNLS and prints the exact rollback command. It refuses
unrecognized source files before making changes. It does not modify saved cues,
counts, GPIO assignments, brightness, schedules or receiver pairing. Native GPIO
and audio routing drivers are not replaced. The audio process change adds only
clock metadata and paused-song heartbeats, keeping existing output routing.

Refresh Song Designer with Ctrl+F5.

FOR LEDS 700–750 ON THE SECOND STRING:
Uncheck Every configured string. Select only the second string.
Enter first 700, last 750. Choose Color blocks — bold scroll.
Try 8 seconds per cycle and width 8 LEDs, with two distinct colors.
Raise the seconds value for slower movement. Save the moment.
This inclusive range contains 51 LEDs; it is not the whole string.

EFFECTS:
Solid, Flash/strobe, Smooth color scroll, Bold color blocks, Chase on black,
Comet trail, Bouncing light, Gentle pulse, Twinkle, Rainbow scroll, Color wipe,
and Lights off.

An active moment replaces the automatic frame on its entire selected range.
Dark spaces in chase/comet/twinkle remain dark. Other pixels keep their normal
show. Reservation masks automatic lighting on those pixels for the rest of this
song; other explicitly saved moments may still use that range. Overlap warnings
identify moments competing on the same pixels/times; later saved rows win.
Saved legacy scroll/flash cues retain their timing until edited. Saving with the
new seconds-per-cycle controls adopts the chosen timing. No bulk cue migration
is performed.

WORKER HARDENING:
Realtime queue reads/drains no longer use empty-then-blocking reads, which can
race between workers during resets. Queue drains are bounded. Shared playback
state is recreated when workers are refreshed, avoiding abandoned lock reuse.
Clock reads/writes do not wait for a stuck clock lock. Paused playback publishes
clock heartbeats; cue animation follows the paused position. Short clock jitter
no longer falls through to automatic effects; a stale clock blanks affected cue
ranges instead. Invalid cue rows do not terminate the rendering worker, and a
failed file read retains the last good reservation data.

The checkbox save path does not restart processes or change LED counts. These
changes address verified software hazards; the exact cause of the reported
all-on/restart symptom cannot be confirmed without a test/logs on the actual Pi.

ROLLBACK:
Use the exact command printed by the installer. It restores code, not saved cue
content. Before rolling back after using new effects, change/remove those new
effect moments in the UI: the older renderer does not support those names.
The installer backup contains only changed code/UI files, not private settings.

SECOND COLOR SUPPORT (rc.5):
Fine-tune now allows Color 2 for Bounce, Flash, Comet, Chase, Pulse, Wipe and
Rainbow/palette scroll. Check Use second color, or choose a new second color
to enable it automatically, then Save. Motion effects can use Color 2 as an
explicit background; choose black or uncheck the switch for dark gaps/trails.
Rainbow uses the chosen palette when checked and full spectrum when unchecked.
Previously saved moments retain their appearance until edited/saved.
