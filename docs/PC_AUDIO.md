# Windows PC audio — Spotify, Pandora and other playback

HNLS can receive the audio already playing on a Windows 10/11 PC on the same
reachable LAN. A small included sender uses Windows WASAPI endpoint loopback;
there is no media-service login, third-party capture driver or cloud audio relay.
It captures the default playback device's **whole system mix**, including alerts.
It is not a native Spotify Connect or Pandora client.

## Existing HNLS installation

For a known rc.7 controller, copy `hnls-pc-audio-update.zip` to `/home/pi` on the
main Pi and run:

```sh
python3 -m zipfile -e /home/pi/hnls-pc-audio-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-pc-audio-update/install_update.py
```

The main service briefly restarts. The installer verifies source versions, backs
up all twelve changed/new files, preserves existing settings and prints its exact
rollback command. Unrecognized sources are refused before changes. Do not apply
older scoped updates over this release; their versions are deliberately guarded.
No slave update is needed. Fresh installations from the full source include this
feature without applying the scoped update.

## Everyday use

1. On Windows open the main Pi's Music page by its LAN address, for example
   `http://192.168.1.37:<your existing HNLS web port>/music.html`. Use your normal
   working HNLS address rather than assuming a new web port or URL route.
2. Under **Spotify / Pandora from PC**, download the Windows sender. Extract the entire ZIP
   to a private local folder. Keep its five files together.
3. Click **Use PC audio** in HNLS. It selects Song Show on normal
   outputs and replaces uploaded-file playback. Advanced Studio is released.
4. Double-click `Start-HNLS-Audio.cmd` in the extracted folder on Windows.
5. Play Spotify or Pandora in its desktop app or browser. The application must
   use the default Windows playback device. Keep its volume above zero. The Pi
   plays through the audio output selected on the Music page (3.5 mm or Bluetooth)
   while normal live effects and paired slave outputs follow the same audio.
6. Press Q in the sender window, or Ctrl+C, to stop transmitting. After a short
   timeout HNLS blacks out the LEDs and waits. **Stop PC audio** stops receiving
   and blacks out LEDs immediately through the normal queued source control.
   Click an uploaded song to return to the playlist.

The sender does not require administrator rights, Python, NuGet packages, virtual
cables or media-service passwords. Windows PowerShell uses Add-Type to compile the
included C# against built-in Windows components. Organizational policies may block
scripts or compilation; the sender reports errors rather than changing policies
system-wide or requesting elevation.

## Limits and interactions

- This is live adaptive analysis. HNLS does not learn the streaming track name,
  pre-analyze a complete streaming song, run uploaded-song timed cues or remotely
  control Pandora/Spotify play/seek/shuffle. Those controls stay in the PC app.
- Existing color/order mappings and Song Show settings still apply. Advanced
  Studio uses a separate audio/output path and does not use this receiver.
- Schedule boundaries retain control: opening selects uploaded-song shuffle,
  closing stops sound/lights. Disable the schedule for an uninterrupted manual
  streaming session. Selecting PC audio is manual after a main Pi reboot; boot
  services themselves remain unchanged. The slave receives normal authenticated
  LED frames and never needs the PC audio sender.
- Loopback captures the playback device, not a single named application. Windows
  Volume Mixer can route an app to a different device, so check it if silent.
  Mute/volume settings and content protection may affect capture. The sender does
  not bypass protection. Test an ordinary unprotected Windows sound first.
- Restart the sender after changing the default Windows playback device. Use a
  mono/stereo endpoint; surround is rejected with instructions. Native 44.1, 48,
  88.2, 96 and 192 kHz PCM/float formats are supported. 48 kHz stereo is a sensible
  first setup. Samples are converted to stereo signed 16 bit; there is no lossy
  codec or sender-side sample-rate conversion. DSP and Pi playback use the source
  sample rate without changing the saved microphone/file-playback configuration.
- If the PC speakers and Pi speakers are both audible, network delay creates an
  echo. Leave the Windows playback endpoint active and turn off PC speakers
  externally or use an unused headphone output. Muting the captured endpoint can
  silence capture on some systems. The Pi 3.5 mm jack has less output latency than
  Bluetooth. This version does not offer a manual LED/audio delay slider.
- Wi-Fi congestion can cause gaps. The receiver reorders small packet inversions,
  skips missing packets after a short wait and discards old queued audio to bound
  latency. It is not a lossless network transport or a multiroom clock system.

## LAN access and private credentials

Only the main Pi listens on UDP **8950**, and only while PC audio is selected.
Both machines must reach each other; guest networks/AP isolation can prevent it.
Do not forward the port through your router. HNLS does not alter firewall rules.
If a firewall is enabled, allow UDP 8950 to the main Pi from the sender PC only.
No inbound listener is added on Windows.

The private `pc_stream.json` in the HNLS settings directory contains a random
32-byte pairing key, created on first download/start, mode 0600. The authenticated
sender download embeds it in `connection.json`. The response is marked no-store.
Do not share that sender ZIP or commit either JSON file to GitHub. Include private
state in private backups only. Source/release archives contain no pairing key.
Anyone holding a downloaded key can send audio while the receiver is selected.
Stop receiving when unused. To revoke a sender, stop PC audio, remove only
`/share/.mlsc/pc_stream.json` on the main Pi, and download a fresh sender; the old
key will fail when receiving starts again. No account passwords are changed.

Packets carry HMAC-SHA256 authentication, a random per-sender stream ID and sequence
numbers. Authentication is **not encryption**: other devices able to observe LAN
traffic can read the audio. Web login controls source selection and downloads.
Do not expose the HNLS web interface/audio input directly to the public internet.

## Developer verification

`python3 -m unittest discover -s tests -v` covers actual local UDP interoperability,
authentication/tampering, replay/competing sender handling, reordering, rate changes,
loss, bounded buffers, private download data, native-rate audio/DSP, stall blackout,
source lifecycle, API requests and scoped-installer rollback/refusal.
`node tests/test_pc_stream_ui.js` exercises source controls, polling and errors.

The Windows GitHub Actions workflow compiles the sender using Windows PowerShell,
checks PCM conversion and emits a packet that Python compares byte-for-byte.
That workflow has been added but has not been executed from this environment.
Manual Windows capture, PC-to-Pi audio playback, Bluetooth latency and physical
LED acceptance remain required. No live Pi was modified during packaging.

## Primary Windows references

- [Microsoft: WASAPI loopback recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)
- [Microsoft: Capturing a stream](https://learn.microsoft.com/en-us/windows/win32/coreaudio/capturing-a-stream)
- [Microsoft: IAudioCaptureClient GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
