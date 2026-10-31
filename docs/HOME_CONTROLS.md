# Run the show from Home

Home is the everyday control panel. It retains the HourNerd visual style and keeps
setup and detailed editing available in the other pages.

| On Home | What it does |
|---|---|
| Play now / Stop show | Starts uploaded-song shuffle and the saved Light Show on all normal outputs, or stops music/lights |
| Choose a song → Play selected song + lights | Starts that song with the show, keeping your current shuffle preference |
| Pause / Resume, Previous, Next, Replay, song position | Controls uploaded-song playback |
| Shuffle playlist | Changes the order at the next song transition |
| Add songs | Uploads one or more audio files without leaving Home |
| Colors & effects | Saves a holiday palette and/or automatic effect choice for all lights or one named string |
| Brightness → Set brightness | Changes only that selected output set’s brightness |
| Show hours | Saves enabled state and start/stop times; days/time zone expand inline |
| Speakers | Chooses the Pi jack or an already-paired Bluetooth speaker |
| Stream Spotify / Pandora from Windows | Expands the sender download and PC audio source buttons inline |

## Predictable behavior

Opening Home and polling its status do not save anything or start playback.
**Play now** and **Play selected song + lights** deliberately start the show.
Their temporary schedule ownership prevents normal outside-hours polls from
immediately stopping it; the next scheduled opening/closing takes control as
explained in [PLAY_NOW.md](PLAY_NOW.md). Choosing a particular song retains the
current shuffle preference, whereas Play now deliberately enables shuffle.

**Save look** and **Set brightness** do not turn on a stopped show. They update
saved settings through the existing executers and refresh path; use Play now to
start. A palette replaces the ten music colors and enables eight-band mode. A
mode-only change preserves individual colors. Brightness-only changes preserve
colors/effects. Grouping, LED limits, counts, physical color orders and wiring are
not changed by these Home controls.

The target initially is All lights. If strings have different settings, the UI
shows keep/mixed choices rather than silently replacing all of them. Only a
setting you deliberately change is submitted. Unsaved look and brightness edits
survive saving the other category, and changing targets asks before discarding
edits. All selected look settings validate before the first save; per-string I/O
failures can still partially apply. Those responses name successes/failures and
keep the choice retryable rather than claiming everything succeeded.

Speaker changes use the existing audio output path and briefly reopen audio.
New Bluetooth pairing is a one-time setup on Music → Speakers. Spotify/Pandora
transport controls stay in the PC app. Upload errors are listed per file, and
uploaded filenames are displayed as text. Song deletion/management stays on Music;
detailed band colors, group matching and LED coverage stay on Light Show; Song
Editor handles special moments. My Lights and Advanced keep hardware/studio tools.

## One catch-up update

For the current corrected palette build (rc.11), Easy UI (rc.12) or Play now
(rc.13), install **only** `hnls-home-controls-update.zip`. It contains the pending
navigation/Play now work as well as Home controls, so earlier incremental ZIPs are
not prerequisites.

```sh
python3 -m zipfile -e /home/pi/hnls-home-controls-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-home-controls-update/install_update.py
```

This 22-file update briefly restarts an active main service. It checks known
published predecessor hashes, compiles Python, parses templates, creates a private
backup, restores on partial failure, and prints the exact rollback command. It
does not replace private settings or the local config template. No receiver
installation is needed. Refresh Ctrl+F5 → Home.

## Verification limits

Automated tests exercise Home read-only startup, selected-song/transport/seek/
shuffle/upload, palette/mode/brightness scope, mixed values, edit preservation,
partial failures, speaker settings and API login/validation. Cumulative installer
fixtures reproduce all three shipped source baselines and a different local
config template; install/restore and version/parser/copy failures are checked.
Existing scheduler, rendering and UI regression suites remain in use.

Real Pi audio/LED operation and real desktop/phone visual acceptance have not been
performed in this environment. Installed Jinja parsing runs before file changes;
the local environment has no Jinja package or runnable browser executable. No live
Pi was modified during packaging.
