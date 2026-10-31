# Song Show palettes and analysis-directed choreography

Open **Light Show**, choose the device, and use the **Holiday palette** dropdown.
There are 14 editable recipes: Christmas, icy winter, Halloween, Thanksgiving,
Independence Day, Memorial Day, Veterans Day, Labor Day, Valentine’s Day,
St. Patrick’s Day, Easter, Hanukkah, New Year’s Eve and Juneteenth. A black color
makes its musical layer dark. Presets are color recipes, not date schedules.

Picking a recipe fills ten color controls and enables **Use all eight frequency
bands**. It does not save automatically, activate Song Show, alter the LED count,
grouping, ordinary coverage limit or brightness, or change your choreography mode.
Adjusting a color changes the label to Custom. Click **Save & use this look** to save and activate it for the selected string. Repeat per device as desired.
Saving uses the existing Song Show refresh path and does not restart music.

| Musical color layer | Analyzed frequency range |
|---|---|
| Sub-bass | 20–60 Hz |
| Bass | 60–250 Hz |
| Low mids | 250–500 Hz |
| Mids / vocals | 500–2,000 Hz |
| Upper mids | 2–4 kHz |
| Presence | 4–6 kHz |
| Treble | 6–10 kHz |
| Brilliance | 10–16 kHz |
| Beat accents | Detected bass onsets |
| POWER beats | Existing confirmed heavy bass impacts |

These are frequency layers, not separated instruments. Vocals, drums and other
instruments overlap. Bands above a source's Nyquist frequency contain no energy.
The additional frequency energies reuse the current FFT; no additional FFT or
source decoding pass is added. The four legacy RMS/bass/mid/treble profile values
and cached song analysis format remain compatible. Eight bands normalize live per
song and reset at song start. With eight-band mode off, the original broad bands
and color behavior remain in use.

Under **How should the show work?**, choose **Let HNLS choose — recommended**. The director uses available whole-song tempo and local section energy/
quiet-steady-intense labels, together with live bass/treble activity, to choose
comets, waves, ribbons, chases, twinkles, pulses and bounces. It changes on phrase/
section opportunities with at least eight seconds between changes; a 20-second
fallback keeps beatless passages moving. A separate stable per-song decision seed
prevents render-frame sparkle randomness from selecting the choreography.

For uploaded songs, use Music's preparation controls to scan the collection ahead
of playback. If the cached profile is not ready, live analysis works while the
existing analysis worker prepares it. Windows PC audio/microphones use live input;
HNLS cannot pre-scan a full anonymous streaming track. This is musical heuristic
selection rather than a genre model, instrument separation or an objectively best
show. It does not edit saved moments or build a timeline of persistent cues.

**Classic** retains the previous choreography. Named-motion options hold a single
movement while reacting to the music. Existing settings default to Classic and
unexpanded bands, so installation alone does not change the established show.
Old config rows remain valid; the new eight settings keys are optional in the
schema and are filled by defaults/UI or added during normal compatibility checks.

Selected colors, sync grouping and physical LED limits remain authoritative.
Ordinary motion never bypasses the existing limit. Only confirmed POWER impacts
retain the existing maximum 120 ms full-strip exception; this does not increase
the existing brightness. Saved Song Designer moments still overlay the automatic
frame and return to it at their end. RGB/GRB range compensation still occurs later
in the output pipeline. Remote slave effects are rendered on the main Pi, so no
slave update is needed. Advanced Studio uses separate settings and does not
inherit normal Song Show mode/palette configuration.

## Installing on the current rc.8 system

Copy `hnls-palettes-update.zip` to `/home/pi` on the main Pi and run:

```sh
python3 -m zipfile -e /home/pi/hnls-palettes-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-palettes-update/install_update.py
```

The guarded twelve-file update briefly restarts an active main service and
makes a private code backup. It preserves private settings and provides an exact
rollback command. Rollback archives the current config documents and removes only
the new optional Song Show fields before restoring the old schema. Original five
colors and unrelated settings remain. Use this updater on its supported rc.8
baseline; do not apply older scoped updaters over the latest release.

Tests verify pure-tone frequency assignment, isolated band colors, original
Classic frame parity, motion limits and synchronization, transient POWER exit,
phrase/reset determinism, legacy-settings saving, preset edits without auto-save,
unchanged grouping/budget, and guarded install/rollback. Actual color appearance,
Pi performance and whether the chosen motions suit each song remain display-side
acceptance checks.

Installer correction: the existing config_template.json is not checked or replaced. The palette schema accepts legacy rows, and runtime/UI defaults supply the new optional fields. A regression fixture verifies the actual rc.8 changed-file baseline with a different local template through installation and rollback.
