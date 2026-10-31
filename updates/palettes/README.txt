HNLS HOLIDAY PALETTES + ANALYSIS-DIRECTED SHOWS — MAIN PI ONLY
For the current rc.8 build with Windows PC audio installed.

Copy hnls-palettes-update.zip to /home/pi on LED03, then run:

python3 -m zipfile -e /home/pi/hnls-palettes-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-palettes-update/install_update.py

The installer verifies twelve source/template files, makes a private backup,
and briefly restarts HNLS if it was running. It does not replace your private
configuration, song cues, GPIOs, LED counts, brightness, color-order mappings,
audio routing, schedule or slave pairing. No slave installation is needed.

Refresh Automatic show with Ctrl+F5. Select an LED device.
- Holiday palette: choose a preset, then adjust any of ten colors if desired.
- Use all eight frequency bands: enables the extra musical color layers.
- Who chooses the effects? Select Analysis-directed show to let HNLS choose.
- Save settings, then Use Song Show if it is not already active.
Repeat for other outputs if you want them to use the same/new palette and mode.

Existing shows keep Classic mode until you choose the new mode. Picking a preset
fills editable colors and enables eight bands; it does not save, change grouping,
increase coverage/brightness, or change the chosen choreography mode. Save applies
without restarting the music. Custom color edits switch the preset label to Custom.

The director selects comets, waves, ribbons, chases, twinkles, soft pulses and
bounces from analyzed tempo, energy, bass/treble and quiet/steady/intense passages.
Changes are phrase-paced, at least eight seconds apart. Prepared file analysis is
used when available; live adaptation works otherwise, including Windows streaming.
It cannot scan ahead through anonymous Spotify/Pandora streams. This is a bounded
musical heuristic, not a promise of the objectively best effect for every song.

Your selected colors, sync groups, ordinary LED budget and saved song moments are
retained. POWER impacts keep the existing brief full-strip exception. Frequency
bands overlap instruments; these are not isolated vocals/drum stems. Color-order
mapping still occurs at the physical output, after rendering.

Rollback: use the exact command printed by the installer. It archives current
settings and removes only the eight new palette/mode keys from Song Show settings
before restoring the old schema. Existing five colors, limits, counts and other
settings are retained. The code backup remains available. Older scoped updates
are for their matching earlier versions, not for use over this version.

Offline tests cover each frequency/color layer, Classic frame parity, all modes'
coverage/grouping, POWER exit, deterministic phrase choices, settings saving,
editable UI and install/refusal/partial-failure/rollback. Actual Pi timing, colors
and listening/viewing acceptance should be checked on your display.

Installer correction: the existing config_template.json is not checked or replaced. The palette schema accepts legacy rows, and runtime/UI defaults supply the new optional fields. A regression fixture verifies the actual rc.8 changed-file baseline with a different local template through installation and rollback.

Startup fix: the config validator future import is first again. All bundled Python files are semantically compiled before the installer interrupts playback. The exact previously shipped broken validator is an accepted predecessor for this correction; unknown edits are still refused.
