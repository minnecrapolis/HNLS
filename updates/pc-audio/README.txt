HNLS WINDOWS PC AUDIO UPDATE — MAIN PI ONLY, for rc.7

Copy hnls-pc-audio-update.zip to /home/pi on LED03. Run:

python3 -m zipfile -e /home/pi/hnls-pc-audio-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-pc-audio-update/install_update.py

The installer checks known source hashes, makes a private rollback backup and
briefly restarts the main service. Existing settings, colors, LED counts, cues,
schedules, audio routes and remote Pi pairing are not replaced. No slave update
is needed. A changed/unrecognized installed file is refused before changes.

Refresh Music with Ctrl+F5. Under Windows PC audio, download the Windows sender
on your Windows PC. Extract the entire ZIP. Click Receive Windows PC audio in
HNLS, then double-click Start-HNLS-Audio.cmd. Play Spotify or Pandora normally
on the default Windows playback device. This captures that device's system mix,
including alerts; keep its volume above zero. It sends to the main Pi UDP 8950.
Q or Ctrl+C stops the sender; Stop PC audio in HNLS stops receiving and blacks
out the lights. Play an uploaded song to return to the playlist.

Use the Music Audio Output selector for the Pi's 3.5 mm jack/Bluetooth output.
Default Song Show effects on all normal outputs, including paired slaves, follow
the live audio. Color-range mappings are retained. Uploaded-song time cues and
full-song preparation are not applied to anonymous live streams. Advanced Studio
has its own audio path. Schedule boundaries still take control of the source.
PC audio is selected manually after reboot.

The downloaded sender connection.json contains a private key: never commit it
to GitHub. Audio packets are authenticated but not encrypted. No internet relay
or media-service passwords are involved. For troubleshooting and Windows format
limits, see the sender README.txt or docs/PC_AUDIO.md in the full package.

Validation: real local UDP, signed packet/tamper/reorder/loss/bounded-buffer checks,
source lifecycle and web UI simulations. Windows sender has a compile/conversion/
protocol CI check; it has not been run on real Windows/Pi audio hardware here.
The installer prints its exact rollback command and preserves service state.
