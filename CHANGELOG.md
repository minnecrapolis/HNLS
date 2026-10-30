# Changelog

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
