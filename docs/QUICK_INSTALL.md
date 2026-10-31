# One command installs the complete HNLS system

## What it installs

The root setup.sh is HNLS’s download-and-install entry point. The published asset
is named hnls-setup.sh. It downloads the complete, versioned HNLS source release,
verifies the downloaded ZIP against SHA256SUMS.txt, safely extracts it, verifies
the complete application payload, and runs the bundled fresh-Pi installer.

The main-Pi installation includes all current application changes: redesigned
mobile UI and pop-out controls, everyday Home controls, local playlist and PC
stream source choice, Windows audio receiver and sender download, Bluetooth
speaker settings, holiday palettes, eight frequency bands plus beat/POWER,
analysis-directed shows, timed Song Designer effects, per-range RGB order,
show hours, manual Play now and remote Pi pairing. No original MLSC checkout,
manual source merges or incremental feature ZIPs are needed on a new Pi.

The same command asks whether this is the Main Pi or an Additional Pi. Main Pi
installs the web interface/audio/show controller; Additional Pi installs only the
LED receiver. Both services are enabled at boot. The receiver’s current output
is BCM GPIO21 / physical pin40. Configure and pair lights in the main web UI.

The Windows sender is downloaded separately from the main web UI, because its
pairing key belongs to that installation; a public generic sender cannot contain
that key. Bluetooth pairing, uploaded songs, hardware counts/order and speaker
selection are also completed through the UI. Music/accounts/private keys are not
bundled. Source switching does not record live Windows audio.

## Publish once, then share the command

1. Publish the HNLS folder as your GitHub repository. Preserve its source,
   notices, workflows and documentation.
2. Create/push tag v0.1.0-rc.16. The tag workflow uses the actual
   github.repository automatically when building the installer.
3. Open Actions → Build prerelease assets and download hnls-release-assets.
4. Attach hnls-setup.sh, HNLS-0.1.0-rc.16-source.zip and SHA256SUMS.txt to
   the GitHub release for that exact tag. Other scoped update ZIPs are optional
   attachments for matching existing installations.
5. The build log prints the concrete one-command Main Pi installer URL.
   You can also run python3 tools/install_command.py --repository followed by
   your actual OWNER/REPOSITORY to print both commands.

A URL is only live after its release and assets have been published. There is
no fabricated HourNerd/GitHub download URL in this package. Exact tagged URLs
also work for prereleases; GitHub’s latest-download shortcut is intentionally
not used because it does not resolve prereleases.

For a manual local build use python3 tools/build_release.py --repository followed
by your actual OWNER/REPOSITORY. Without that option (or GITHUB_REPOSITORY), the
bootstrap asset remains unconfigured and explicitly requires --repo; do not
publish that unconfigured asset as the finished one-command installer.

## User flow

Paste the generated command into the Pi terminal. If asked, choose 1 for the
main system or 2 for an additional Pi. Enter the Pi’s sudo password when needed.
The installer downloads the release, installs dependencies, validates imports
and defaults, enables the service at boot and prints how to open the web UI.
The default effect is Off and no LED outputs are preconfigured. Add the actual
light strings and choose speakers through the UI before playing a show.

The same installer supports --role controller, --role receiver, --check,
--repo and --version. For a piped command, pass options after bash -s --.
--check downloads/extracts/verifies without installing packages or services.
--help does not download anything.

## Existing installations and limits

The downloader checks standard existing install/service paths before download
or apt operations. The bundled installer checks again before installation.
It never silently replaces a running HNLS or MLSC installation. Use the matching
scoped update on an existing system. The earlier HNLS update ZIPs are not a
complete upgrade path for arbitrary original MLSC versions.

Controller baseline: Pi 4, 64-bit Raspberry Pi OS Bookworm, Python 3.11+.
Receiver reference: Pi 3 A+, Bullseye, Python 3.9. Native Pi 5 controller output
is not validated/supported by this installer. The one-command path automates
the existing prerequisites; it does not expand hardware compatibility.

The source ZIP checksum detects download corruption or inconsistent assets;
it is not an independent publisher signature. Both code and checksum are
trusted from the selected GitHub release. Network, apt and pip access are needed.
Temporary download files are removed on success or failure. Fresh installation
cleanup is documented in INSTALLATION.md; apt transactions are not reversed.
No system has been remotely modified while preparing these files.

## Verification

Automated tests exercise a piped installer, baked repository/version, both role
paths, read-only checks, checksum/version mismatch, unsafe ZIP paths/symlinks,
argument validation and cleanup using local download fixtures. They do not run
apt, access a real GitHub release or verify clean-Pi playback. A physical fresh
install and reboot acceptance are still required before a stable release.
