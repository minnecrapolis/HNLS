HNLS EASY INTERFACE — MAIN PI ONLY

For the current working rc.11 / corrected palette interface. This update changes
thirteen HTML/CSS/JavaScript files. It does not change controller Python modules,
configuration templates, LED rendering, audio transport, private settings or cues.
It does not stop/restart services or music. Flask's existing template auto-reload
serves the revised templates on refresh; browser assets have new cache versions.

Copy hnls-easy-ui-update.zip to /home/pi on LED03, then run:

python3 -m zipfile -e /home/pi/hnls-easy-ui-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-easy-ui-update/install_update.py

Refresh with Ctrl+F5. Open Home. No slave update is required.

NEW EVERYDAY NAVIGATION
Home       Large task cards: play music, change the look, edit a song moment,
           set up lights, set hours or choose speakers.
Music      Playlist/playback first. Clear links open uploads, Windows PC audio,
           show hours, speakers and shuffle/song analysis.
Light Show Choose a string, holiday/custom colors, and movement. Save & use this
           look saves and then activates the selected string's light show.
Song Editor Pick a song/time, select lights, choose an effect, save the moment.
My Lights  Choose a string first for name, count and brightness. Wiring, mixed
           color order and Pi pairing are in clearly labeled expandable sections.
Advanced   Studio/import/timing tools and the optional effect library.

Find a setting is available in the header and Home. Search words such as Spotify,
Christmas, brightness, GRB, schedule or frequency. Results open the right page and
expand/focus the matching section. Searching/navigation does not start playback or
change settings. Existing source/output actions still require their normal buttons.
The optional second-screen controls remain static and navigate the main window.

Save & use this look is an explicit two-request action: first save the settings,
then activate Song Show for that string. If saving succeeds but activation fails,
the UI reports that distinction and offers Use last saved look. Colors/preset
selection alone still does not auto-save. Other outputs retain their own settings.

The installer checks known UI source hashes and all bundled templates before any
changes. New assets are copied first and base.html last. It backs up original
assets privately and prints the exact rollback command. A partial copy failure
restores the previous UI automatically. Unknown customized UI files are refused.
Rollback restores only interface assets, preserving private state and runtime.

Verification: core regression suite, task search and actual-anchor checks, nested
section reveal/focus, dialog behavior, naming consistency, popup routing checks,
no navigation-side API calls, save/activation and partial-error handling, installer
version/path/parser/failure/rollback tests. No live Pi was changed here. A real
browser viewport/phone usability check remains pending.
