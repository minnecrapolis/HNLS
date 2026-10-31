# HNLS — HourNerd LightShow

**Your music. Your lights. Your show.**

A Raspberry Pi music and holiday-lighting system with a responsive web interface, automatic song analysis and visual, per-song LED cues.

**0.1.0-rc.16 — reconciled source prerelease.** Controller and receiver code were reconciled with captures from the working installation on October 29, 2026. The new fresh-install script is automated and tested with simulated failures, but has not yet been installed on a clean physical Pi. See [release status](docs/RELEASE_STATUS.md) and [verification results](docs/VERIFICATION.md).

## Start here

Use Home for direct everyday controls: music, colors/effects, brightness, show hours, speakers and PC audio. Find a setting locates detailed controls. Everyday pages are Music, Light Show, Song Editor and My Lights; specialist tools remain under Advanced. See [Find your way around HNLS](docs/EASY_INTERFACE.md).

## Features

- Click any song title to play; loop, shuffle, pause, seek, skip and replay.
- Set weekly show hours: shuffled main show starts automatically, then music and lights stop at closing time—even with the browser closed.
- Prepare songs in the background for section/tempo/onset-aware automatic lighting.
- Assign colors to bass, midrange, treble, beat accents and POWER beats.
- Synchronize sections, pair opposite sections or make custom groups.
- Mark song intervals and apply 12 effects to inclusive LED ranges: solid, flash, smooth/bold scroll, chase, comet, bounce, pulse, twinkle, rainbow, wipe and blackout.
- Set seconds per cycle, band/trail width and direction, with overlap warnings and song-specific pixel reservation.
- Add local data outputs and pair a remote Pi through the web interface.
- Assign different physical RGB/GRB/RBG/GBR/BRG/BGR orders to inclusive ranges on a normal configured data line, including the paired slave.
- Use mobile navigation or a static second-monitor toolbar that controls the main window.
- Turn lights off and reset show state between songs, with a two-second gap.

No fixed 1,200-LED layout is assumed. Each output has real timing, backend and power constraints. An LED density setting is not an electrical current limiter.

## One-command installation

HNLS includes a complete download-and-install entry point, like the original MLSC setup command. It installs this full HNLS release: the redesigned interface, Home controls, source switching, PC audio, holiday palettes, song analysis, schedules, Song Designer, RGB/GRB ranges and remote receiver support. No original MLSC checkout or incremental update ZIPs are needed for a new Pi.

Publish the repository and release assets first. GitHub Actions generates `hnls-setup.sh` with the real repository and exact version already included. Run the release’s displayed `curl … | bash` command on a fresh Pi, choose **Main Pi** or **Additional Pi**, then finish the light/audio setup in the web interface. Boot startup is enabled automatically.

The public URL cannot work before the GitHub release exists. See [the exact minnecrapolis/HNLS publishing steps and commands](docs/GITHUB_INSTALL.md), or [the general installation guide](docs/QUICK_INSTALL.md).

## Fresh controller installation

Use a spare **Pi 4 with 64-bit Raspberry Pi OS Bookworm / Python 3.11+**, internet access and appropriately powered LEDs. Download/extract the release, open the HNLS directory and run:

```sh
python3 install.py --check
sudo bash install.sh --role controller
```

Open `http://<your-Pi-LAN-address>:8080`. The installer enables boot startup. Clean defaults have **no configured outputs** and the default effect is Off. Configure the first line in the web interface before playing a show.

## Fresh remote receiver

On a separate Pi (the captured reference is Pi 3 A+, Bullseye / Python 3.9):

```sh
sudo bash install.sh --role receiver
```

Pair from the controller's web interface using the receiver's LAN address and locally generated pairing key. The current receiver drives BCM GPIO21 / physical pin40. See [installation](docs/INSTALLATION.md).

**Existing working installation?** Do not run the fresh installer there. It refuses existing code, environments, configuration and service units. The scoped [show-hours update](updates/show-hours/README.txt) supports the captured working build and rc.2. Other upgrades are not claimed.

## Update the working controller

The small update package changes only the scheduler and Music UI files. Copy hnls-show-hours-update.zip to /home/pi on the main Pi, then follow [these instructions](updates/show-hours/README.txt). It verifies known source versions, backs up files and briefly restarts HNLS. No receiver update is needed.

## Song Designer effects update

For the captured working build or rc.2/rc.3, use dist/hnls-designer-effects-update.zip on the main Pi. It updates only the cue/worker and designer files, preserves saved settings and provides rollback. See [update instructions](updates/designer-effects/README.txt). No receiver change is required.

## Two-color update for existing rc.4 systems

Use dist/hnls-two-color-update.zip to enable second-color choices for Bounce, Flash, Comet, Chase, Pulse, Wipe and Rainbow/palette scroll. It changes four designer files on the main Pi and retains saved moments/settings. See [instructions](updates/two-color/README.txt). Picking a second color enables it; black or an unchecked switch preserves dark backgrounds. Existing cues keep their prior look until saved with the option.

## Saved-moment Edit update

On the current rc.5 build use dist/hnls-moment-edit-update.zip. Edit now loads the chosen moment, opens Fine-tune, scrolls/focuses the editing controls and shows a selected-row/banner state. This changes only three UI files. See [instructions](updates/moment-edit/README.txt).

## Mixed RGB/GRB ranges on one output

On the current rc.6 main Pi, use dist/hnls-color-ranges-update.zip. Device Settings > Mixed RGB / GRB ranges lets you select the output, add an inclusive range and choose that segment's actual order. Unlisted LEDs inherit the output default. This supports serial data chains, not independently addressed parallel branches. See [instructions](updates/color-ranges/README.txt). No slave install is required; Advanced Studio has separate line settings.

## Documentation

| Topic | Guide |
| --- | --- |
| Install, boot, service management, recovery | [Installation](docs/INSTALLATION.md) |
| Playlist, colors, grouping and song moments | [User guide](docs/USER_GUIDE.md) |
| Wiring, output pins, power and remote network | [Hardware](docs/HARDWARE.md) |
| Runtime design | [Architecture](docs/ARCHITECTURE.md) |
| Troubleshooting | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Reconciled files and exact origins | [Reconciliation](docs/RECONCILIATION.md) |
| Dependencies and reference systems | [Dependencies](docs/DEPENDENCIES.md) |
| GitHub publishing and release assets | [Publishing](docs/RELEASING.md) |
| Limitations and hardware acceptance | [Release status](docs/RELEASE_STATUS.md) |

## Development and release builds

```sh
python3 -m pip install -r requirements/test.txt
python3 -m unittest discover -s tests -v
python3 tools/validate.py
python3 tools/check_defaults.py
python3 tools/build_release.py
```

Release ZIPs and SHA256SUMS.txt are written to `dist/`. CI runs the same checks; the tag workflow uploads release assets to Actions for review rather than publishing automatically.

## Credits and license

HNLS builds on Music LED Strip Control by TobKra96 and contributors. The original MIT license and copyright notice are retained unchanged in [LICENSE](LICENSE). Vendor assets retain their respective terms and embedded notices; see [THIRD_PARTY.md](THIRD_PARTY.md). Legacy service names and paths remain compatibility details.

No music, personal show configuration, live PIN, pairing key or private ChatGPT bridge is included.

## Windows PC audio

Stream the default Windows playback device to HNLS for live lights and Pi audio playback, including Pandora or Spotify. Music provides the sender download and source controls. See [PC audio setup](docs/PC_AUDIO.md) for installation, privacy, schedule interactions and current testing limits.

## Holiday palettes and automatic choreography

Song Show now offers 14 editable holiday recipes, eight frequency colors plus beat/POWER accents, and analysis-directed motion choices. Existing shows remain in Classic mode. See [Palettes and choreography](docs/PALETTES.md).

## Run outside scheduled hours

Use Play now on Home or Music to start the shuffled Light Show without editing saved hours. Stop show turns off music/lights. The next scheduled opening or closing takes control again. See [Play now](docs/PLAY_NOW.md).

## All-in-one Home controls

See [Home controls](docs/HOME_CONTROLS.md). The single hnls-home-controls-update.zip catches up the working palette, Easy UI or Play now installation; those earlier incremental updates are not required first.

Music source choice: see [AUDIO_SOURCE.md](docs/AUDIO_SOURCE.md). Existing rc.11–rc.14 systems can use the single cumulative `hnls-audio-source-update.zip` instead of earlier UI updates.
