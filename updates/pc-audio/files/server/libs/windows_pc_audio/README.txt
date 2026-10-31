HNLS WINDOWS PC AUDIO — Windows 10/11

1. Extract the ENTIRE downloaded ZIP on your Windows PC.
2. Open HNLS Music. Click Receive Windows PC audio.
3. Double-click Start-HNLS-Audio.cmd in the extracted folder.
4. Play Spotify or Pandora normally (desktop app or browser) on the default
   Windows playback device. Keep that device's volume above zero.
5. Sound plays through the Pi's selected Music audio output and drives its normal
   live effects, including paired slave LEDs. Q or Ctrl+C stops the sender.
   Stop PC audio on the Music page stops receiving and blacks out the LEDs.

No administrator account, virtual audio driver, Python, media-service credentials
or service API integration is required. PowerShell compiles the included C# code
with built-in Windows components. An enterprise policy may prohibit scripts or
Add-Type; contact your administrator if Windows blocks them.

Captures ALL sound on the default playback device, including notification sounds.
The Spotify/Pandora app must use that same device (check Windows Volume Mixer).
Do not mute that playback device; use a spare headphone output or turn off the PC
speakers externally if you hear double audio. Changing the default playback device
requires restarting the sender. Select stereo rather than surround; 48 kHz is
recommended. Native 44.1/48/88.2/96/192 kHz PCM/float input is supported.

The main Pi uses UDP 8950. Both machines must reach each other on the LAN;
guest Wi-Fi/AP isolation or firewalls may block it. No router port forwarding is
needed. Packets are authenticated with a private pairing key, but LAN audio is NOT
encrypted. connection.json contains that key: keep this folder private and do not
put it on GitHub. Do not download a sender from an untrusted HNLS installation.
The Pi web login still controls source selection and access to this download.

Live streaming has a short network/buffer delay. Prefer the Pi 3.5 mm output for
low latency; Bluetooth adds its own delay. Wi-Fi loss can cause gaps; old audio is
dropped to prevent accumulating delay. When the sender disappears the LEDs black
out automatically. Streaming is selected manually after each Pi reboot.

Playback/shuffle/seek remain in Spotify/Pandora. HNLS cannot identify their tracks
or seek them. It analyzes incoming audio live; it does not do full-file preparation
or uploaded-song time cues for streaming tracks. Schedule boundaries still take
control of HNLS: scheduled opening selects the uploaded-song shuffle, closing
stops audio/lights. Turn off the schedule for a manual streaming session if needed.

Some protected audio may not be available to Windows loopback capture. This sender
does not bypass content protection. If audio is silent, check app/device/volume
settings and whether other unprotected Windows sounds are received first.

The Windows sender requires a real Windows audio endpoint. It has automated packet
and conversion checks, but end-to-end playback must be checked on your PC and Pi.
