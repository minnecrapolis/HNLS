HNLS SECOND COLOR SUPPORT — MAIN PI ONLY

Requires the working designer-effects (rc.4) update already installed.
Copy hnls-two-color-update.zip to /home/pi, then:

python3 -m zipfile -e /home/pi/hnls-two-color-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-two-color-update/install_update.py

The installer verifies/backups four known-version files and briefly restarts HNLS.
Saved songs, cues, schedules, wiring settings and receiver pairing are retained.
No slave update is needed. The installer prints the exact rollback command.

Refresh Song Designer with Ctrl+F5, edit the moment and open Fine-tune.
Choose Second color and enable Use second color, then Save moment.
Changing the second-color swatch also checks Use second color automatically.

Flash/strobe: alternate Color 1 and Color 2. Set Color 2 to black for on/off.
Bounce/Comet/Chase: moving Color 1 over a Color 2 background.
Gentle pulse: fade back and forth between the chosen colors.
Wipe: Color 1 fills a Color 2 background, then repeats.
Rainbow/palette scroll: checked uses the two chosen colors; unchecked keeps the
full rainbow. Scroll/Blocks use the two colors; unchecked uses Color 1 and black.
Twinkle: two sparkle colors on black; unchecked uses only Color 1.
Solid and Lights off still do not need a second color.

The selected range is entirely controlled by the moment: the chosen background
is part of the cue, not automatic lighting showing through. If you want dark
backgrounds/trails/gaps, use black or uncheck Use second color. Existing moments
retain their old appearance until you explicitly edit/save the new color option.
Two-color background illumination applies only to the selected LEDs.

Tests exercise color endpoints, backgrounds, blending, palette/full rainbow,
brightness, legacy behavior, saved settings and UI field enablement. Actual
Pi playback still needs a check. No dependency installation is required.
