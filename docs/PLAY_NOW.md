# Play now outside the schedule

Open **Home** or **Music**, then click **Play now** under **Run the show now**.
HNLS starts a shuffled uploaded song and activates the saved Light Show on all
configured normal outputs, including paired Pis. It keeps the palette, grouping,
LED budgets, brightness and saved song moments already configured for those outputs.
It starts a fresh shuffled show; use Music's Resume if you only want to resume a
paused track. For Spotify/Pandora use the separate PC audio controls.

**Stop show** stops music and turns off the normal outputs. The schedule remains
saved and enabled/disabled exactly as it was. Stopping manually inside an active
window does not get reversed by the next two-second schedule poll.

| When you click Play now | What the scheduler does afterward |
|---|---|
| Outside enabled show hours | Lets the manual show continue; the next scheduled opening starts normal scheduled playback |
| During enabled show hours | Lets playback continue until the scheduled closing time |
| Schedule disabled | Leaves manual playback running until you stop it |

After a manual Stop, the next scheduled opening can run normally. A closing
boundary does not unexpectedly start a stopped show. Overnight windows still
belong to their start day, and existing local-time/DST handling is retained.
Changing saved hours can cause the existing immediate window transition behavior.

Manual command state lives in the main web process and is intentionally temporary.
A main-service/Pi restart returns to the saved schedule: inside hours it can start;
outside enabled hours it forces lights/music off once. These buttons do not write
`show_schedule.json`. They use the existing shuffle/main-show start and all-output
stop actions rather than bypassing the rendering/audio pipeline or GPIO settings.

The visible status explains when schedule control resumes. A request is queued;
actual audio/LED startup still depends on the normal worker queues and playable
media. An empty library yields an upload instruction without interrupting an
existing source. A partial start failure uses the established fail-dark action.
Stop remains callable even when the schedule file needs repair.

## Installing on current rc.12

Copy `hnls-play-now-update.zip` to `/home/pi` on the main Pi and run:

```sh
python3 -m zipfile -e /home/pi/hnls-play-now-update.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-play-now-update/install_update.py
```

This nine-file guarded update briefly restarts an active main service because it
includes scheduler/API changes. It verifies supported hashes, semantically compiles
Python and parses bundled templates before changes, makes a private code backup,
and prints the exact rollback command. Existing saved hours/private configuration
are not replaced. No receiver install is needed. Refresh Home/Music with Ctrl+F5.

## Verification

Tests cover manual starts before the first scheduler tick, repeated outside-hours
polls, handover at opening and stop at closing, manual stops inside a window,
disabled and overnight schedules, restart behavior, unchanged schedule bytes,
empty library, partial start failure, stop with a malformed schedule, authenticated
API action validation, deliberate UI commands/double-click protection/errors, and
installer rollback/version/template failure handling. Real Pi sound/LED and clock
boundary acceptance is still required; no live Pi was changed during packaging.
