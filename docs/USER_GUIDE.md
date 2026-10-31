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

## Slower, clearer Song Designer effects

The effect selector now offers Solid, Flash, smooth Color scroll, bold Color blocks, Chase on black, Comet trail, Bounce, Pulse, Twinkle, Rainbow, Wipe and Lights off. Color blocks use sharp bands of two colors; smooth Color scroll blends those colors. A larger Seconds per cycle/trip value is slower. Band/trail width is measured in actual selected LEDs. Forward moves toward increasing LED addresses; Reverse mirrors the pattern inside the selected range.

For a prominent scroll on the second string's LEDs 700–750: select only that string, set first 700/last 750, choose Color blocks, cycle 8 seconds, width 8 LEDs, and two distinct colors. Save the moment. That range contains 51 LEDs. Color scroll/block seconds refer to one repeating color-pattern cycle; chase/comet/wipe seconds refer to travel through the selected range. Bounce seconds include the return trip. Pulse seconds mean one full brightness cycle, and Flash seconds mean one on/off cycle.

An active cue completely replaces the automatic frame on those pixels. Black gaps in chase/comet/twinkle remain black. Pixels outside the selected range continue their normal show. Reservation masks automatic lighting on the range outside that moment for this song; other saved moments can explicitly control the same range. If two moments overlap, later rows take priority; the editor warns about overlapping ranges and times. Update/delete conflicting rows if you want only one effect there.

Legacy saved scroll/flash cues retain their former speed until edited. The new form proposes a slower scroll cycle when an old scroll is opened; Save applies the chosen timing. Checking the reservation box only changes the form; Save applies it without restarting playback or changing LED counts.

Paused music now supplies a paused clock, so the cue holds its song position. Short clock jitter no longer exposes automatic effects on the active range. If timing becomes stale, affected cue ranges go dark rather than falling through to unrelated automatic frames. Manual Off and song-gap blackout remain authoritative.

## Second colors for moving and flashing effects

Fine-tune includes Second color and Use second color. Selecting a second color automatically enables it; the choice is applied when the moment is saved. Legacy moments preserve their earlier appearance until explicitly edited/saved with this option.

| Effect | What the second color does |
| --- | --- |
| Flash / strobe | Alternates Color 1 and Color 2; black gives on/off flashing |
| Bounce, Comet, Chase | Color 1 moves/fades over the Color 2 background |
| Gentle pulse | Fades between Color 2 and Color 1 |
| Color wipe | Color 1 fills a Color 2 background, then repeats |
| Rainbow / palette scroll | Checked: use the selected two-color palette; unchecked: full rainbow |
| Color scroll / Color blocks | Uses both colors; unchecked uses Color 1 and black |
| Twinkle | Two sparkle colors on black; unchecked uses just Color 1 |
| Solid / Lights off | Second color is unused |

A chosen background is part of the saved effect, not automatic lighting. Use black or uncheck the switch if you want dark gaps/trails. Counts, range bounds and hardware brightness still apply.

## Editing a saved moment

In Moment sheet, click Edit on the desired row. HNLS fills the form, opens Fine-tune, scrolls the editor into view and focuses the effect control. An Editing banner names the time, effect and LEDs; the selected row is highlighted. Change the controls and click Update moment to save back to that cue ID. Edit itself does not play, pause or save. New selection leaves edit mode. Timeline blocks use the same explicit editing behavior. If the page shows an error opening a moment, reload with Ctrl+F5 and report the visible error if it persists.
