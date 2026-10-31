# Changelog

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
