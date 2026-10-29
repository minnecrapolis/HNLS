# Installation and recovery

## Existing working HNLS installations

Do not copy src/controller over a working Pi. This source consolidation needs comparison against the live install first. Legacy paths remain `/share/music_led_strip_control`, `/share/.mlsc`, `/share/.venv`; music is normally `/share/music`.

The maintenance folders retain previously supplied scoped update installers and their checksums. Read each included README before using it. The interface update requires the existing song designer and branding assets; music intelligence requires that interface. These updates are not a full installer and are not needed just because this archive exists. They can briefly interrupt playback and print backup/rollback instructions.

## Capture the current build

Copy tools/export_installation.py to /home/pi on the controller. Run:

```sh
sudo python3 /home/pi/export_installation.py --role controller --output /home/pi/capture-controller.zip
```

On the receiver, use the same tool:

```sh
sudo python3 /home/pi/export_installation.py --role receiver --output /home/pi/capture-receiver.zip
```

The collector reads approved application code/assets, dependency versions and the service unit. It excludes configuration, music, private keys and runtime state. Review the ZIP privately: code comments or custom service directives can still contain local information. It does not change services or files on either Pi. It reports skipped files.

## Start automatically at boot

On the controller:

```sh
sudo systemctl enable --now mlsc
systemctl is-enabled mlsc
```

On the receiver:

```sh
sudo systemctl enable --now mlsc-receiver
systemctl is-enabled mlsc-receiver
```

No cron job is needed. Enabling services starts the application/receiver at boot; it does not add playlist autoplay.

## Stop and restart

Controller: `sudo systemctl stop mlsc`, `sudo systemctl start mlsc`, or `sudo systemctl restart mlsc`.
Receiver: substitute `mlsc-receiver`.

## Backup and rollback

Before upgrades, privately back up the application, virtual environment dependency list, service unit and `/share/.mlsc`. Protect the backup because it contains access and pairing settings. Use the exact rollback command printed by the scoped installer. Do not restore old native output drivers blindly: older versions swapped red/green twice. A complete automated repository-level upgrade/rollback installer remains a release blocker.

## Fresh Raspberry Pi

No validated fresh-Pi installation command is supplied. Restore dependencies and assets from the working system, test on a spare Pi and record supported OS/Python/backend versions before publishing one. Do not run the inherited project installer and assume it installs HNLS.
