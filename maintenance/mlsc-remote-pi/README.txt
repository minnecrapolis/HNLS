MLSC REMOTE PI — LED03 + LED-SLAVE

Prepared for LED-SLAVE: Raspberry Pi 3 Model A+, Raspbian Bullseye 11,
32-bit armv7l, Python 3.9.2, LAN IPv4 192.168.1.34.
Requires the working second-string update on LED03.

Copy this ZIP to /home/pi on BOTH Pis. Extract on each Pi:

python3 -m zipfile -e /home/pi/mlsc-remote-pi.zip /home/pi

1. ON LED-SLAVE ONLY:

sudo python3 /home/pi/mlsc-remote-pi/install_remote_pi.py --receiver

The receiver installer downloads OS packages and rpi_ws281x==5.0.0 from PyPI
into its own /opt/mlsc-receiver/venv. Internet access is needed for installation.
It creates/enables mlsc-receiver.service. No full MLSC installation or audio
software is needed. GPIO21 uses PCM; no SPI setup or reboot is normally needed.
If another application owns GPIO21/PCM/I2S, it must be stopped first.
The installer refuses to run while mlsc.service is active on that Pi.

At the end, COPY THE 64-CHARACTER PAIRING KEY printed by the installer.
On repeat installs, the existing key is retained.
To show it again locally: sudo cat /etc/mlsc-receiver/key
Don't post this key publicly; use it in LED03's pairing field.

2. ON LED03 ONLY:

sudo python3 /home/pi/mlsc-remote-pi/install_remote_pi.py --master

This briefly restarts mlsc.service and backs up every changed code/UI file.
It patches existing functions/routes rather than replacing the whole application.
It does not replace the native local GPIO driver, audio code, music, configuration,
Bluetooth preferences, or GPIO10 boot settings. The rollback command is printed.
Remove remote Pi device entries through Device Settings before restoring older
code: old plain UDP and the authenticated receiver protocol are different.

3. WEB PAIRING ON LED03:

Refresh with Ctrl+F5. Open Device Settings → Add remote Pi.
Address: 192.168.1.34
Key: paste the key from LED-SLAVE's installer
Name: LED-SLAVE (or a name for this light string)
Copy settings from: choose one of the working devices
Number of LEDs: enter this string's actual count
Physical color order: GRB for the previously discussed GRB lights
Starting brightness: 10% default; choose for your installation
Click Pair Pi and add string.

The receiver's first string is on GPIO21, PHYSICAL HEADER PIN 40.
Use an appropriate data level shifter where required, separately powered LEDs
and a ground shared between LED-SLAVE and its local LED supply/string.
Power off the relevant hardware before changing wiring.

No LED count, GPIO, color or grouping files need manual editing. Select the
new device in Device Settings for count/order/brightness, or Song Show for its
colors and grouping. Main and remote strings follow the same music and song
blackouts, with separate effect instances. Copied settings are a starting point;
later edits to the source device don't automatically copy to the remote device.
This is not pixel-for-pixel mirroring of the local strip.

The remote Pi status list has a Check connection button reporting whether
frames are arriving and any GPIO initialization error. Pairing verifies the
service/key; actual GPIO initialization occurs when its output starts. A pair
can succeed even if hardware initialization subsequently fails: check its status.

NETWORK / TIMING:
Both Pis must be on the same reachable trusted LAN, without Wi-Fi client isolation.
The receiver uses TCP 8943 for pairing/status and UDP 8944 for light frames.
No router port forwarding is needed. Management is HTTP on the trusted LAN;
frames are HMAC-authenticated, session-scoped and sequenced, not encrypted.
Do not expose the receiver to the public internet.

The sender runs outside the main rendering loop, only retains the newest frame,
and splits frames into packets under 1400 bytes. The receiver discards incomplete,
expired, old-session and out-of-order frames. One second without a complete valid
frame blacks out the remote string while its receiver process is running. Normal
service shutdown also blacks out; power loss/hardware failure cannot be corrected
by software. Service restart initializes the last configured line to black.
The sender reconnects automatically after receiver service/network recovery.

This is LIVE lighting-frame distribution for the normal music-reactive player,
not FPP MultiSync or preloaded timeline playback. Wi-Fi adds variable delay and
packet loss, so frame-perfect synchronization is not guaranteed. Audio remains
on LED03; headphone/Bluetooth selection is retained. This update doesn't add an
LED/audio offset control. Keep a good Wi-Fi signal; USB Ethernet is an option.

This initial receiver supports ONE GPIO21 RGB line per remote Pi, 7–2500 LEDs.
This is a tested software bound for this implementation, not a universal LED limit.
You can add more remote Pis. 2500 LEDs are not an electrical power budget.
Starting output rate is limited to 25 FPS or the wire-time limit, whichever is
lower. For example, 1200 LEDs start at 25 FPS; 2500 at 12 FPS. Large installations
should use more lines/controllers. Normal Device Settings prevents unsupported
remote counts/orders/rates. RGBW and additional receiver GPIO lines aren't included.
Use a DHCP reservation for LED-SLAVE so 192.168.1.34 remains stable. To change an
address later, delete the old remote device and pair it at the new address.

COMMANDS ON LED-SLAVE (receiver service, NOT mlsc):
sudo systemctl status mlsc-receiver --no-pager -l
sudo journalctl -u mlsc-receiver -n 60 --no-pager
sudo systemctl restart mlsc-receiver
sudo systemctl stop mlsc-receiver
sudo systemctl disable --now mlsc-receiver

If the receiver installer fails downloading dependencies, copy the actual error.
If pairing reports unreachable, check the receiver status, Wi-Fi/client isolation,
and ports above. Don't change the working LED03 local GPIO or audio settings.

VALIDATION:
Python 3.9 syntax checked for receiver and installer. Local HTTP/UDP integration
verified authentication, color bytes, reconnection and blackout using a simulated
pixel driver. Protocol tests cover chunk loss/order/expiry and replay rejection.
Master installer repeat/rollback and preservation checks passed. Existing audio,
Song Show, second-string and Advanced Users regression tests and UI simulations
passed. Actual Pi GPIO timing, Wi-Fi behavior, dependency installation and LED
wiring need verification on your hardware.
