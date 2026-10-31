# Find your way around HNLS

The same names now appear in navigation, page titles, the Home task cards and
second-screen controls. On a phone, tap Menu to see the same destinations.

| I want to… | Go to… |
|---|---|
| Run the full show outside scheduled hours | Home / Music → Play now |
| Stop music and all lights | Home / Music → Stop show |
| Play, pause, skip or replay a song | Music → click a song title / playback controls |
| Upload music | Music → Add songs |
| Stream Spotify/Pandora from Windows | Music → Spotify / Pandora from PC |
| Choose Christmas/Halloween/other colors | Light Show → Holiday colors |
| Let song analysis choose the motion | Light Show → Automatic effects → Let HNLS choose |
| Set bass/treble/other colors individually | Light Show → Individual colors |
| Mirror or group sections | Light Show → Match sections |
| Limit how many LEDs light up | Light Show → LED limit |
| Make selected LEDs do something at a song time | Song Editor |
| Change string name, LED count or brightness | My Lights → choose a string |
| Fix a range with different RGB/GRB order | My Lights → Fix RGB / GRB colors |
| Add a GPIO string or another Pi | My Lights → Add a string / Add a Pi |
| Set daily start and stop times | Music → Show hours |
| Select the jack or Bluetooth speaker | Music → Speakers |
| Shuffle or prepare song analysis | Music → Shuffle & analysis |
| Import sequences or edit network timing | Advanced |

If you are unsure, use **Find a setting**. It searches a local list of tasks;
searching itself does not contact a service or change the show. Links open the
appropriate section even when it is normally collapsed. Close/Escape returns
focus to the button that opened the search.

## A first show

1. **My Lights:** add or check the light strings.
2. **Music:** upload/choose a song or set up PC audio.
3. **Light Show:** select a string, pick a palette and motion, then click
   **Save & use this look**. Repeat for other strings when desired.
4. **Song Editor** is optional: use it to add special moments that override the
   normal automatic show on selected pixels.

Light Show keeps the main choices visible. Group matching and LED limits are
expandable options; individual band colors can be opened when you want them.
Selecting a palette does not save it automatically. The main save button now saves
and activates that string's look. A failure after saving is reported as saved but
not activated, so you can retry **Use last saved look**. Existing LED budgets,
Song Designer moment behavior, stream input and playback engine are retained.

## Installation on the working main Pi

Copy `hnls-easy-ui-update.zip` to `/home/pi` on LED03, then:

```sh
python3 -m zipfile -e /home/pi/hnls-easy-ui-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-easy-ui-update/install_update.py
```

Refresh with Ctrl+F5. This update affects only web templates/browser assets and
uses the existing template auto-reload. It does not restart the main service or
music, alter config templates/private settings, or require a slave install.
The installer validates templates with the Pi's installed Jinja before mutation,
checks known predecessor hashes, creates a private rollback backup and restores
assets on partial failure. It prints its exact UI-only rollback command.

## Verification limits

Node simulations cover task search, valid destinations/anchors, nested disclosure
opening/focus, dialog closing, consistent labels, retained popup-to-main routing,
no API calls for navigation, and explicit save/activation plus partial failure.
Existing Music, Song Editor, palette, range, schedule and stream simulations also
pass. HTML checks cover unique IDs and balanced disclosures. Python updater tests
verify no service commands, private/runtime preservation, parsing before changes,
path/version checks and rollback. The full source is semantically compiled.

This environment has no runnable browser executable or installed Jinja dependency.
A real desktop/phone visual review and installed-Jinja parsing remain to be done;
the actual updater parses before changing any file. The tests do not claim a
physical Pi/display acceptance or pixel-perfect viewport validation.

## Home now contains controls directly

In rc.14, Home includes the actual everyday music, color/effect, brightness, hours, speaker and PC audio controls. Optional task links are below them. See [HOME_CONTROLS.md](HOME_CONTROLS.md). Install the single cumulative Home-controls ZIP instead of chaining the earlier Easy UI/Play now ZIPs.
