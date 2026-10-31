HNLS MIXED PHYSICAL RGB ORDERS — MAIN PI ONLY

For the current rc.6 build. Copy hnls-color-ranges-update.zip to /home/pi:

python3 -m zipfile -e /home/pi/hnls-color-ranges-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-color-ranges-update/install_update.py

The installer verifies/backups eight known-version source/UI files and briefly
restarts HNLS. Settings/cues/audio/schedules/pairing/counts are not replaced.
The native and UDP output methods receive one prepare-frame call; existing RGB
integer packing, native initialization and brightness code are retained. The
installer rejects an unrecognized native driver version before any changes.
No slave installation is required: remote compensation occurs on the main Pi
before authenticated frames are sent to the receiver's existing global order.

Refresh Device Settings with Ctrl+F5. Find Mixed RGB / GRB ranges.
Choose the output, Add range, enter inclusive first/last and its actual order,
then Save color-order ranges. Gaps inherit the output default. Saving mappings
does not restart music; they apply to outgoing frames after the cache refresh.
For paused/held playback, wait until new frames are sent.

EXAMPLE: total output count 750, default GRB, actual LEDs 601–650 are RGB.
Add first 601, last 650, order RGB. Exactly 50 LEDs are remapped. The others use
GRB. Add more nonoverlapping rows for other sets with different physical orders.
Do not change the entire output's strip type just to correct a small range.

Native ws2812_strip aliases are resolved from the installed driver's constants
when possible; otherwise select an explicit RGB/GRB/RBG/GBR/BRG/BGR strip type in
the existing Configuration panel, save it and reload outputs. RGBW or different
pixel protocols cannot be mixed by this RGB byte-order feature. Unsupported
aliases can always have their ranges cleared through the UI.

These numbers refer to a CONTINUOUS DATA CHAIN. Four 300-LED strips connected
in series have addresses 1–1200. Parallel data branches repeat the same pixel
addresses and cannot receive independent color-order correction at that address.
2 x 300 + 3 x 50 is 750 LEDs; ranges 601–650, 651–700 and 701–750 identify its
three 50-LED sets. Seven 50-LED sets in series on the slave total 350 addresses.
This update does not automatically change any configured LED count.

SCOPE: normal Device Settings outputs and effects/Song Designer on those outputs.
Advanced Studio uses a separate line configuration and does not inherit these
normal-device mappings. Configure its own whole-line order separately.

Rows are saved privately in /share/.mlsc/color_ranges.json. Include that file in
private full-settings backups. They are separate from music-cue timing/sync groups.
Overlaps/out-of-bounds ranges are rejected. Reducing a count later shows a warning
in the range editor; runtime clipping prevents indexing outside the actual frame.
If the base order becomes unresolvable or the frame becomes RGBW, only the mapped
ranges are blacked out rather than sending incorrectly interpreted colors.
Deleting a device removes its saved ranges so reusing its ID does not inherit them.
Clear ranges + Save restores the output default everywhere. Code rollback retains
range data; the older output layer ignores it and returns to whole-output ordering.

Tests cover all 36 default/range RGB permutations, exact 601–650 boundaries,
source-frame preservation, native packing and remote compensation, persistence,
validation, alias lookup, cleanup and UI controls. Physical colors still need a
check on the actual hardware. Use the existing color controls for that check.
