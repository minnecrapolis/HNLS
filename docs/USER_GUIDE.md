# User guide

## Music and automatic shows

Upload supported music through the Music page. Song preparation runs in the background and caches the analysis; the live fallback remains available before preparation finishes. The playlist loops; enable Shuffle for randomized passes without immediate repeat when another song exists. Preparation estimates sections, tempo, attacks and frequency-band energy; it does not isolate stems or guarantee musical beat accuracy.

Use playback controls to pause, resume, seek, skip and replay. Song completion blanks the outputs and resets show state before the next song after two seconds. Delete music through the interface; keep your own copies.

## Colors and sections

Choose Song Show for the desired output. Save bass, midrange, treble, beat and POWER colors. Select the physical strip's color order in Device Settings. An orange swatch with wrong LED colors requires pure red/green/blue testing before changing artistic palettes.

Set section size and grouping. Paired sections synchronize opposite sections; custom groups synchronize sections assigned the same group. LED counts belong to each output; there is no fixed 1,200-pixel layout. A maximum lit-LED count is an artistic density control, not an electrical current limiter; POWER beats and custom cues may light more pixels.

## Program a song moment

Open the song designer from Music, choose a song, play or seek to the desired point and mark a time region. Select output(s), inclusive first/last LED numbers, effect, colors, speed and brightness. Save the moment. Example: LEDs 112–214 from 1:35 through 1:45, color scroll. Only those pixels receive that overlay while other pixels continue their automatic show.

Cue start is inclusive and end exclusive. Later saved overlapping rows win on overlapping pixels. Reserve keeps a range dark outside its cue; turn it off if those pixels should resume automatic effects. Two conflicting rows on the same pixels can hide an earlier effect. Named regions help reuse tree or prop ranges. Cues are associated with the song filename; renaming music requires checking associations.

## Mobile and multiple monitors

Use the mobile Menu for navigation. The multiple-monitor button opens a compact toolbar; move it to the second display. Dashboard and other navigation buttons target the original large window. Keep that main window open. Permit popups for the local HNLS address if the toolbar is blocked.

## Automatic show hours

Open Music > Automatic Show Hours. Enable the schedule, choose the days, start/stop times and IANA time zone, then Save show hours. The default zone is America/Chicago; check the displayed show clock. The selected weekdays refer to the start day when a window crosses midnight. Equal start and stop times are rejected.

At opening, HNLS selects a random first song, enables playlist shuffle and selects the main Song Show on every configured output. Saved song moments still overlay the show. At closing, all outputs switch Off and playback stops. Pis remain running for the next window. Schedule checks occur roughly every two seconds plus normal command-queue/OS latency.

The main Pi owns the schedule; receivers follow its output and watchdog. No browser or cron job is needed. Settings persist across reboots. A restart during the window starts a show; a restart outside enabled hours forces outputs/music off once. Empty playlists are retried without blocking the UI.

Enabling during active hours starts immediately. Disabling stops an owned scheduled show. Manual controls work: a manual pause/stop is not undone every poll, and manual playback is allowed outside hours; the next schedule boundary takes control again. Shuffle remains enabled after a scheduled start until you change its checkbox. The schedule changes no LED counts, colors or brightness.

Both Your Playlist and Song Analysis Details have clickable song titles. Tab to a title and press Enter/Space for keyboard playback. Polling preserves unchanged song rows and unsaved schedule edits.
