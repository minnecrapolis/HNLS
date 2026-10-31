# Hardware and power

Every physical LED line needs a supported data output, correct color order, common reference ground and an appropriately sized power supply/wiring system. Power injection supplies electrical power; additional Pis provide data outputs. Adding injectors does not remove data timing limits.

| BCM GPIO | Physical header pin | Backend used in this project |
| --- | --- | --- |
| 21 | 40 | PCM local/receiver output |
| 10 | 19 | SPI additional controller output |

A diagram's WiringPi 29 corresponds to BCM21 on physical pin40. Always use BCM numbering in HNLS settings. GPIO13/18 PWM can conflict with built-in analog audio on the tested setup; retain the known working PCM/SPI combination unless separately validated. The current receiver implements one line; a second receiver GPIO is not included.

Use a suitable data level shifter as required by your LED hardware. Switch power off before wiring. Size fuses, wire and supplies for the LED manufacturer's maximum current and actual distribution. Never advertise that a Pi 5V header can power 900 or 1,200 LEDs safely. Sparse effects or low brightness do not guarantee protection against all-white cues, startup state or a software failure. Prefer separately powered LED distribution with correct grounding and avoid backfeeding Pi supplies.

The proposed Powered by Pi / Injected Power UI and an aggregate current budget are not implemented here. Software density limits are not electrical protection.

## Receiver network

Pair using the receiver-generated private key through the web interface. The current protocol uses TCP8943 for pairing/status and UDP8944 for authenticated, chunked frames. Use a trusted LAN without client isolation; do not forward these ports from the internet. HMAC authenticates frames; it does not encrypt the network traffic. No fixed household IP is required by the product; enter the receiver's current LAN address.

## Mixed RGB byte orders on a serial line

Range overrides correct RGB wire order, not electrical/protocol differences. The driver retains its global order P; the output layer precompensates each configured range with P^-1 Q so its physical bytes match the actual order Q. Brightness is unchanged and logical renderer frames are not mutated. The remote sender applies compensation before transmission; the receiver retains its existing global order. Native alias resolution reads only constants and does not initialize GPIO.

Two 300-LED strips followed by three 50-LED sets total 750 serial addresses. Seven 50-LED slave sets total 350. Four 300-LED serial strips total 1200. A parallel/mirrored branch repeats addresses instead. Normal configured outputs support these range corrections; the independent Advanced Studio bus does not inherit them. Different pixel protocols/RGBW are outside this RGB-range feature.
