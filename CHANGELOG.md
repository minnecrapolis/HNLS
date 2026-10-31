# 0.1.0-rc.16

- MLSC-style one-command full HNLS installer with Main Pi / Additional Pi choice and boot startup.
- Pinned release download, checksum/payload verification, guarded ZIP extraction and temporary cleanup.
- Existing installations refused before download or package changes.
- GitHub tag build bakes the actual repository and version into hnls-setup.sh; publishing instructions and real-command generator included.

# 0.1.0-rc.15

- Visible Pi songs / live PC stream choice on Home and Music; streamed audio uses the Pi speaker without recording.
- Hide local song controls during streaming; keep look and speaker controls available.
- Cumulative guarded updater supports rc.11–rc.14; source status polling cannot undo a newer user request.

# Changelog

## 0.1.0-rc.14 — 2026-10-31

- Made Home an all-in-one control panel with actual music, upload/transport/shuffle, palette/effect, brightness, hours, speaker and PC audio controls.
- Preserved the existing visual style and moved optional links/legacy effect controls below everyday controls.
- Added scoped Home look settings with mixed-value handling, explicit saves, edit preservation and partial-failure reporting.
- Added selected-song manual show start that retains shuffle choice and schedule override semantics.
- Added a single cumulative 22-file update for the published rc.11/12/13 baselines, plus regression/rollback fixtures.

## 0.1.0-rc.13 — 2026-10-31

- Added Play now and Stop show on Home/Music plus a searchable manual-show task.
- Manual starts use uploaded-song shuffle and the saved Light Show on all normal outputs without changing saved schedule hours.
- Added scheduler ownership for outside-hours playback, next-opening handover and in-window closing; manual Stop is not undone by the next poll.
- Kept override state temporary across restarts and added empty-library/partial-start handling.
- Added guarded nine-file updater and scheduler/API/UI/rollback regressions; actual Pi playback acceptance remains pending.

## 0.1.0-rc.12 — 2026-10-31

- Reorganized navigation as Home, Music, Light Show, Song Editor, My Lights and Advanced with consistent page/popup names.
- Added Home task cards and searchable task links that reveal the correct settings section.
- Put playlist/playback and light-string basics first, with clearly labeled optional setup sections and a three-step Light Show flow.
- Made Save & use this look explicitly save and activate the selected string, with partial-failure feedback.
- Added an interface-only guarded updater with template validation, rollback and no service/music restart; retained all runtime/configuration behavior.
- Added task navigation, deep-link/focus, save-flow, static markup and UI-installer regression checks. Real desktop/mobile visual acceptance remains pending.

## 0.1.0-rc.11 — 2026-10-31

- Fixed Python startup failure caused by an import placed before the config validator future import.
- Added semantic Python compilation to release validation and the palette updater before any service/file changes.
- Added a regression proving misplaced future imports are refused without interrupting the service.
- Allowed the corrected updater to replace the exact previously shipped broken validator hash as well as the original baseline.

## 0.1.0-rc.10 — 2026-10-31

- Fixed the palette updater rejecting working systems whose local config_template.json differs from the clean release template.
- Removed the unnecessary template replacement; retained all twelve required code/UI source guards and optional-field defaults.
- Added a regression using actual rc.8 baseline files and a different local template; install/rollback preserve that template byte-for-byte.

## 0.1.0-rc.9 — 2026-10-31

- Added 14 editable holiday palettes and eight frequency-band colors plus beat and POWER accents.
- Added analysis-directed phrase-paced motion selection and seven held-motion options while preserving Classic frame output.
- Kept existing FFT/profile compatibility, physical coverage and POWER constraints, saved-cue overlay and RGB-order output correction.
- Added legacy-compatible optional settings/schema, live saves, guarded thirteen-file updater and targeted rollback cleanup.
- Added frequency/color/director/UI/persistence/installer regression tests and documented live-stream limitations.

## 0.1.0-rc.8 — 2026-10-31

- Added Windows PC audio source, web controls and private sender download for Pandora/Spotify or other endpoint playback.
- Added built-in WASAPI loopback sender with native-rate stereo PCM, authenticated LAN packets, bounded jitter buffering and disconnect blackout.
- Reused Pi analog/Bluetooth output and live DSP/Song Show path; retained slave transport and color-range corrections.
- Added twelve-file guarded updater, source/loss/transport/UI/rollback tests and Windows compile/packet CI. Windows/Pi playback acceptance remains pending.

## 0.1.0-rc.7 — 2026-10-31

- Added per-range physical RGB byte-order configuration for normal native and UDP/paired-slave outputs.
- Added Device Settings range editor with inherited defaults, overlap/bounds checks and live saves.
- Added P^-1 Q compensation while preserving the corrected native RGB packing and existing receiver protocol.
- Resolved native strip aliases from installed constants where possible; rejected unresolved aliases/RGBW for mappings.
- Added deletion cleanup, eight-file updater, 36-order-combination checks, native/remote/UI and rollback regression tests.

## 0.1.0-rc.6 — 2026-10-31

- Made saved-row Edit open Fine-tune, scroll to the editor, focus the effect and identify/highlight the selected moment.
- Added visible error reporting for failed edit operations and a cache-version bump.
- Added a three-file UI updater and tests for edit selection, correct update ID, no playback/save on Edit, and error feedback.

## 0.1.0-rc.5 — 2026-10-31

- Enabled second colors for Bounce, Flash/Strobe, Comet, Chase, Pulse, Wipe and Rainbow/palette scroll.
- Added a saved Use second color switch; selecting a color enables it automatically.
- Kept prior behavior for legacy moments until explicitly edited/saved.
- Added a four-file updater for working rc.4 systems, while retaining the complete designer updater.
- Added endpoint/background/brightness/legacy/persistence/UI and installer regression tests.

## 0.1.0-rc.4 — 2026-10-30

- Installer correction: validate only bundled designer templates; added live-validation-path regression tests.

- Expanded Song Designer to 12 effects with seconds-per-cycle, band/trail width and direction controls.
- Added high-contrast color blocks and range-exclusive chase/trail effects; preserved legacy cue timing until edited.
- Added overlap warnings and clarified reservation behavior.
- Replaced blocking realtime queue reads/drains with bounded nonblocking operations.
- Recreated shared playback state after worker refresh; clock readers/writers no longer wait on abandoned locks.
- Added paused clock heartbeats, jitter-tolerant cue ownership, stale-clock blackout and malformed-cue isolation.
- Added a scoped main-Pi installer and regression coverage. Actual Pi reproduction/acceptance remains pending.

## 0.1.0-rc.3 — 2026-10-30

- Added persistent weekly show hours, IANA time zone, overnight windows and reboot recovery.
- Automatically starts a random song, shuffle and main Song Show; closing stops music and sets all outputs Off.
- Added playable titles in both Music lists and preserved row focus during polling.
- Added a scoped eight-file updater with known-version checks, backups and rollback.
- Added schedule, UI and update regression coverage; fresh-hardware acceptance remains pending.

## 0.1.0-rc.2 — 2026-10-30

- Reconciled 259 controller and two receiver files against the actual working Pis.
- Preserved eight controller differences from rc.1, including device lifecycle and cue/output behavior.
- Restored static fonts, API descriptions and upstream files from the original archive.
- Retained the original MIT notice and recorded baseline revision/hash provenance.
- Created clean defaults with no live devices/cues and default effect Off.
- Added explicit runtime dependency manifests, including previously missing flask-openapi.
- Added guarded fresh-controller/receiver installers and boot services; existing installs are refused.
- Made temporary frame diagnostics opt-in.
- Expanded regression coverage, release checks, GitHub workflows and full documentation.

Fresh-Pi installation remains a hardware-test prerelease. No running Pi was modified during packaging.

## 0.1.0-rc.1 — 2026-10-29

Initial source consolidation and documentation candidate, superseded by rc.2 reconciliation.
