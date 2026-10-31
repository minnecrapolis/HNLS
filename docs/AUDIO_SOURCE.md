# Music source: Pi songs or Windows stream

Home and Music begin with a visible source card. Both play through the selected
Pi headphone or Bluetooth speaker and drive the normal automatic Light Show.

**Play songs on the Pi** starts the uploaded playlist on shuffle, using the same
manual schedule override as Play now. It stops PC reception. The local playlist,
transport and seek controls are visible when streaming is off.

**Stream from PC** selects authenticated live audio. Open Start-HNLS-Audio.cmd on
Windows and play Spotify/Pandora there. Local song controls disappear while PC
streaming is selected, including while waiting for sender packets. Pause, skip
and choose streaming songs in the Windows app. HNLS does not record this audio.

**Stop PC sound & lights** stops receiving on the Pi. It cannot stop Spotify on
Windows. Schedule boundaries continue to apply. Re-select streaming after reboot.

The same source card appears at the top of Home and Music. Color, brightness and
speaker controls remain usable in either mode. Sender download instructions are
in an expandable section of the card. See PC_AUDIO.md for connection details.

Install updates/audio-source (hnls-audio-source-update.zip) on the main Pi only.
It includes the pending Home/Easy UI/Play now updates and supports published
rc.11–rc.14 predecessor hashes. No config template, driver, DSP, cue renderer or
slave code is modified. Unknown source versions are refused; rollback is printed.

Tests cover source-aware controls, explicit requests only, polling races, errors,
and cumulative install/rollback from actual rc.11/12/13/14 source snapshots.
Actual Windows-to-Pi audio and real browser visual acceptance remain pending.
