# Installation, startup and recovery

## Fresh controller: prerelease hardware test

Use a spare Pi 4 with 64-bit Raspberry Pi OS Bookworm, Python 3.11+ and internet access. Extract the release, change into HNLS and run:

```sh
python3 install.py --check
sudo bash install.sh --role controller
```

The --check command verifies release file hashes without changing the machine; it does not test hardware. Installation refuses existing application code, /share/.venv, /share/.mlsc or an installed mlsc service unit. It installs OS dependencies, copies the complete bundled application, creates its venv, installs direct runtime requirements and validates imports/defaults before installing the boot service. It does not clone or run an external upstream setup script.

The controller uses /share/music_led_strip_control, /share/.venv, /share/.mlsc and /share/music. These legacy paths preserve compatibility. Open `http://<Pi-LAN-address>:8080`; find the address with `hostname -I`.

Clean defaults contain no output entries, and the default effect is Off. Add/configure a line in Device Settings: actual count, color order, backend/pin and conservative brightness. Keep the hardware powered appropriately. Select Song Show and upload music through Music. Enabling the service at boot starts the server. An enabled saved schedule also starts the playlist when the Pi boots during its show window.

## Fresh receiver

Use a separate Pi with Python 3.9+; the captured baseline is Pi 3 Model A+ on Bullseye. Run:

```sh
sudo bash install.sh --role receiver
sudo cat /etc/mlsc-receiver/key
```

The key is created locally with private file permissions. Paste it only into the controller's Add remote Pi pairing form, with the receiver LAN address, actual pixel count and physical color order. The receiver uses BCM21 / physical40. It stays dark until configured/paired frames arrive. Do not publish the key.

The existing scoped receiver installer under maintenance is retained for historical reference. Prefer the root fresh installer for a new HNLS installation. None of the maintenance installers constitutes a complete upgrade path for the reconciled release.

## Existing installations

Do not copy this source over a working Pi. The fresh installer deliberately refuses it. Your uploaded capture was read-only and no running device has been changed. To trial rc.2, use a spare Pi or a separate OS card. Keep a private backup of the old application, configuration, service unit and exact dependency state. Configuration recovery and historical scoped patches are under tools/maintenance; read their own options before use.

## Boot startup

The installer enables the appropriate service. To verify or enable manually on the controller:

```sh
sudo systemctl enable --now mlsc
systemctl is-enabled mlsc
```

On the receiver:

```sh
sudo systemctl enable --now mlsc-receiver
systemctl is-enabled mlsc-receiver
```

No cron entry is needed. These commands start the server/receiver; an enabled show schedule controls automatic playlist playback.

## Stop, start and restart

Controller: `sudo systemctl stop mlsc`, `sudo systemctl start mlsc`, `sudo systemctl restart mlsc`.
Receiver: substitute `mlsc-receiver`.

## Installation failure and rollback

Before service installation, dependency or validation failures remove newly staged application code and newly created virtual environments. If a later service step fails, the installer stops/disables its new unit, removes that unit and new application files, and removes any pairing key it created. It retains OS packages and generated runtime data; it does not undo apt transactions. This is fresh-install cleanup, not an upgrade rollback system. Do not delete preexisting data to bypass the fresh-install guard.

A successful systemctl start is not a sustained health or hardware test. Verify logs, UI access, reboot behavior, low-brightness RGB/GRB, audio, cues and remote recovery on a spare Pi before public stable release.

## Scoped show-hours update on the current main Pi

Use the supplied hnls-show-hours-update.zip for the captured working build or rc.2. Copy it to /home/pi on the main Pi, extract and run its installer with /share/.venv/bin/python3. See updates/show-hours/README.txt for exact commands. All eight modified files are validated/backed up before restart. Unrecognized file hashes are refused before changes. Driver/audio files, settings and pairing are preserved. Rollback restores code; saved show_schedule.json is retained and is ignored by older code. No receiver installation is required.

## Song Designer update on the working main Pi

Copy dist/hnls-designer-effects-update.zip to /home/pi on LED03. Extract it and run its install_update.py using sudo /share/.venv/bin/python3, as shown in updates/designer-effects/README.txt. It verifies and backs up ten known-version files before briefly restarting HNLS. No receiver update is required. Counts, brightness, GPIO assignments, colors, saved moments, schedules and pairing files are retained. Native output/audio-routing drivers are not replaced; the audio-process change adds playback clock metadata and paused heartbeats.

If rolling back after creating new effect moments, first change or delete those moments in the web UI: older renderers do not support the new effect names. Code rollback deliberately does not overwrite saved song data.

## Second-color update after the designer-effects update

Use dist/hnls-two-color-update.zip on the existing main Pi. It checks four known rc.4 files, backs them up, validates Python/Jinja and briefly restarts HNLS. Follow updates/two-color/README.txt. No slave or driver update is required. The complete designer-effects updater also contains the new color support for earlier supported builds. Rollback retains saved cues; the prior renderer ignores the new use_color2 option and resumes its prior color behavior.

## Saved-moment Edit UI update

Use dist/hnls-moment-edit-update.zip on a current rc.5 main Pi. It validates and backs up the JavaScript, designer page and included moment controls, then briefly restarts the service. Follow updates/moment-edit/README.txt. Refresh with Ctrl+F5 afterwards. No renderer, audio, worker, cue data or receiver changes are made. Older supported installations can use the refreshed full designer-effects update instead.
