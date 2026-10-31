HNLS SAVED-MOMENT EDIT FIX — MAIN PI ONLY

For the current two-color designer build (rc.5).
Copy hnls-moment-edit-update.zip to /home/pi, then run:

python3 -m zipfile -e /home/pi/hnls-moment-edit-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-moment-edit-update/install_update.py

This validates/backups three known-version UI files and briefly restarts HNLS.
Saved song moments, music, schedule, audio, GPIO settings and receiver pairing
are retained. No renderer/worker/native driver changes; no slave update needed.
The installer prints its backup and exact rollback command.

Refresh Song Designer with Ctrl+F5. In Moment sheet, click Edit.
It loads that saved moment, opens Fine-tune, scrolls the form into view, focuses
the effect control and highlights the selected row. An Editing banner identifies
the time, effect and LED range. Change the controls and click Update moment.
Selecting Edit does not play, pause or save anything. Timeline-block selection
uses the same edit handler. New selection returns the form to new-moment mode.
If a loading/display operation fails, the error is shown on the page rather than
being left only in the browser console. Reduced-motion preferences are honored.

The old handler filled the form above the table without opening/scrolling it;
that can appear to do nothing. It is not proof that every reported failure has
that cause; stale/mismatched browser assets can also fail. The cache version is
bumped, and Ctrl+F5 ensures the matching controls/script are loaded together.

UI regression checks click an actual second-row Edit button, verify its colors,
range and selection, assert no playback/save request on Edit, and save the update
to the clicked cue ID while preserving the other moment. They also verify visible
error reporting. Test the browser behavior after installing on the Pi.
