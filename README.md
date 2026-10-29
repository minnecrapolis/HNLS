# HNLS — HourNerd LightShow

Music-driven, individually addressable holiday lighting, controlled from a mobile-friendly web interface.

**Version 0.1.0-rc.1 · source consolidation candidate · not a validated standalone installer.**

HNLS builds on Music LED Strip Control by TobKra96 and contributors. HNLS is the product name; existing installations retain `mlsc` service names and legacy filesystem paths for compatibility.

## What is included

- Controller Python source and a new responsive lighting-desk interface.
- MP3 playback, looping playlist, shuffle, song preparation and music-reactive effects.
- Bass/mid/treble/beat palettes, section synchronization and pixel density controls.
- Per-song timecoded cues for selected output and LED ranges, plus named light groups.
- Song boundaries with LEDs off and a two-second gap.
- Local GPIO outputs, authenticated network receiver source and pairing tools.
- A second-monitor toolbar that controls the main browser window.
- Source validation, reproducible release packaging, checksums, documentation and GitHub workflows.

No music, live configuration, pairing keys, SSH keys or private ChatGPT bridge is included.

## Start here

| Goal | Guide |
| --- | --- |
| Understand release readiness | [Release status](docs/RELEASE_STATUS.md) |
| Install or maintain | [Installation](docs/INSTALLATION.md) |
| Operate the lights | [User guide](docs/USER_GUIDE.md) |
| Wire and expand | [Hardware](docs/HARDWARE.md) |
| Understand internals | [Architecture](docs/ARCHITECTURE.md) |
| Diagnose a problem | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Publish a GitHub release | [Release guide](docs/RELEASING.md) |
| Review attribution | [Third-party notices](THIRD_PARTY.md) |

## Validate and build

Requires Python 3.9 or newer for repository tools:

```sh
python3 tools/validate.py
python3 tools/build_release.py
```

This checks source syntax and release structure, not GPIO, browser rendering or audible playback. See release status before deploying to a working show.

## Licensing status

The inherited project identifies MIT licensing. Exact upstream copyright notices, matching revision and bundled web-asset licenses still require reconciliation. No blanket replacement license is asserted here. Public distribution is gated on that review; see THIRD_PARTY.md.
