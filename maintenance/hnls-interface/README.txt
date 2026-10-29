HNLS LIGHTING DESK — presentation update

Open preview.html on your computer first. It is a self-contained visual preview
with sample content and no live API calls. It includes Show desk, Music and Song
Designer. Settings inherit the same component styling on the actual Pi.

Copy hnls-interface.zip to /home/pi/ on LED03. Run each command separately:

python3 -m zipfile -e /home/pi/hnls-interface.zip /home/pi

sudo /share/.venv/bin/python3 /home/pi/hnls-interface/install_hnls_interface.py

Refresh the browser with Ctrl+F5. The installer restarts playback. Do not install
on LED-SLAVE. Only interface templates, styles and UI scripts change; audio, lighting,
network receiver, song cues and configuration files are not modified. No sample
cues are created. Previous power and brightness settings remain in effect.

The service is still named mlsc for compatibility. The product is HNLS.

The installer prints a backup path and an exact rollback command. To restore:
sudo /share/.venv/bin/python3 /home/pi/hnls-interface/install_hnls_interface.py --restore /share/hnls-interface-backup-TIMESTAMP
Replace TIMESTAMP with the exact printed backup folder.

This edition intentionally uses a single dark desk theme. The old light/dark
toggle and sidebar are removed. The effect library remains under Advanced Users.
Music's cue editing moves to the dedicated Song Designer tab; saved cues remain.
Original project attribution and existing license files remain in place.

MULTIPLE MONITORS
Click "Do you have multiple monitors?" in the header. Move the smaller window
to your second monitor. It stays a fixed toolbar: Dashboard, Music, Song Designer,
My lights, Automatic show and Advanced Users open in the ORIGINAL big window.
The toolbar never follows those page changes. It indicates the main window's
current page and provides Previous, Next, Replay, Pause, Resume and +/-10 seconds.
Both windows read the same Pi playback state, polled once a second. Browser
background throttling can delay the displayed status. No second show is started.
Allow pop-ups for your HNLS address if the browser blocks it. Popup size is a
request to the browser; resize it and drag it to your chosen monitor. This
feature does not automatically detect monitors or position windows on them.
Close the toolbar with its header button. If you close the main window, reopen
HNLS and launch the toolbar from there again to reconnect its controls.

MOBILE
The desktop navigation stays across the top. On phones, the Menu button opens
large navigation rows. Escape closes the menu and returns focus to its button.
Song timeline and pixel map scroll horizontally inside their own containers;
exact time and pixel number fields remain available beneath them.

Validation: template control IDs, existing JS simulations, fixed-toolbar parent
navigation and shared transport, menu/popup interactions, installer exact
rollback and checksum rejection are checked locally. Jinja syntax is checked
using the Pi's installed environment before installation. Full browser layout
and actual Pi operation still need your review. This is a visual redesign,
not a determination of rights or a guarantee against anyone's similarity claim.
