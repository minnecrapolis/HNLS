HNLS SONG INTELLIGENCE + SHUFFLE PLAYLIST

Install on LED03 only, after the new HNLS interface. No update on LED-SLAVE is
needed for analysis or shuffle. The shared audio features still drive all outputs.

Copy hnls-music-intelligence.zip to /home/pi/ on LED03. Run separately:
python3 -m zipfile -e /home/pi/hnls-music-intelligence.zip /home/pi
sudo /share/.venv/bin/python3 /home/pi/hnls-music-intelligence/install_music_intelligence.py

Refresh Music with Ctrl+F5. Opening Music queues preparation of existing files.
New uploads queue automatically. Analyze playlist retries unfinished/failed files.
Cached profiles are reused if the source file has not changed. Ready counts and
per-song status are shown under Song intelligence; expand Song analysis details.

The scanner runs locally at low priority, one file at a time across both bulk
and playback-triggered workers. It reads the decoded song, does not modify your
music, and adds no external AI/cloud dependencies. Scanning is throttled to about
four times real time, so a four-minute song can take roughly a minute or longer
on a busy Pi. Playback remains available while preparation runs. For the most
consistent first-versus-later playback, let the playlist reach Ready first.

Analysis version 2 adds eight-second dynamics passages, spectral attack times,
conservative heavy-bass impact candidates, and an estimated tempo when the
signal is sufficiently regular. Automatic movement follows tempo and passage
intensity. Tempo may be unavailable or land on a half/double-time interpretation;
there is no claim of perfect beat tracking, chorus recognition or isolated vocals
and instruments. Detected events follow decoded audio time through pauses/seeks.
Microphone input retains its existing live analysis. Manual song moments retain
priority; configured colors, brightness and automatic lit-LED budgets are retained.

Shuffle playlist saves immediately. It applies at the NEXT transition, retaining
the currently playing song and existing two-second lights-off/reset gap. Each
running shuffle pass uses every playable file before reshuffling, avoids an
immediate same-song boundary repeat when alternatives exist, and skips known
unplayable files. New/deleted uploads are included at transitions. Previous
retraces session history, and Next can return forward through that history.
Single-song libraries repeat normally. Turning Shuffle off restores alphabetical
advancement. The preference survives reboot; history/order restart with the service.

The installer patches only the audio service's playlist-advance method; retains
its audio output, song clock, cue propagation, seek and reset methods; and retains
the current output driver (including its corrected GRB packing), debug logging,
receiver, pairing, templates outside Music, static toolbar and mobile navigation.
It replaces the analyzer and automatic renderer, adds one playlist helper and
one UI script, and appends three authenticated API routes. Settings live in
/share/.mlsc/playlist_settings.json, not the strict original config schema.
No sample white flashes or other song cues are created.

Rollback: the installer prints the exact command and backup path. Original
code is backed up before changes. Songs, manual cues and settings are not removed.
Cached version-2 profiles can remain after rollback; the prior analyzer ignores
them by versioned cache identity. Both installers preserve the HNLS interface.

START AT BOOT
On LED03: sudo systemctl enable --now mlsc
Check: systemctl is-enabled mlsc
On LED-SLAVE: sudo systemctl enable --now mlsc-receiver
Check: systemctl is-enabled mlsc-receiver
Both checks should print enabled. Existing service names are retained for
compatibility; the product is HNLS. Enabling a service starts HNLS/its receiver,
not a specific song automatically. This update does not add boot-time autoplay.

Validation: shuffle/history/deletion, settings validation, synthetic song dynamics,
regular attack/tempo detection, event timing and seek behavior, authenticated route
contracts, AST-scoped patch preservation, rollback after write failure, existing
real-MP3 cache/renderer/control/gap tests, and simulated UI interactions pass
locally. Actual Raspberry Pi performance and musical results need listening and
visual review on your setup. No change increases your configured brightness.
