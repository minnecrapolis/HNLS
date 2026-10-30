# Release status — 0.1.0-rc.3

The source reconciliation is complete against the supplied working controller/receiver capture and original upstream archive. The complete source, static assets, clean defaults, direct dependencies, service generation, documentation and release workflows are assembled here.

## Verified locally

Captured file hashes; original upstream revision/archive hash; preservation of the eight working controller differences and unchanged receiver code; corrected native RGB packing; parsed Python sources; automated core music/cue/grouping/remote regression tests; packaging/exclusion checks; fresh-installer failure cleanup simulations; deterministic source ZIP generation. See the release verification record for exact results.

## Remaining physical acceptance

The new installer has not been run on a clean Pi. Confirm package availability/native builds, sustained service startup, default first-run behavior, boot startup, analog/Bluetooth audio, pure RGB and GRB colors, cue entry/exit/reserve/overlap, shuffle/seek/replay, remote loss/reconnection/watchdog, mobile navigation and second-monitor controls. Record OS/model/counts/FPS and results. Existing working-install behavior does not substitute for this test.

The local build environment cannot install the additional Flask/Jinja/jsonschema test dependencies from its configured package index. Offline tests run; formal Draft 2020-12 validation and template parsing are also wired into CI/installer for an environment with those dependencies. The local schema-constraint inspection passes, but is not described as a full installed-jsonschema run.

## Deliberate scope

No SD-card image, arbitrary-version install migration, unconditional boot playlist autoplay, second receiver GPIO, web electrical-current budget, FPP MultiSync compatibility or unlimited output capacity is promised. Controller fresh installation currently targets the captured 64-bit Pi 4 baseline. The source contains inherited advanced studio/FSEQ functionality; those paths need renewed end-to-end hardware/UI acceptance as part of this prerelease.

## Attribution

Original MIT license and copyright notice were recovered and retained. Embedded vendor notices were preserved and an asset inventory is included. Third-party assets retain separate terms; this is not a claim that every bundled dependency or font is covered solely by the root MIT license.

rc.3 adds server-side weekly show hours, scheduled boot recovery, automatic shuffle/main-show startup and closing blackout, plus clickable song titles. The scoped updater supports known captured/rc.2 files, with offline install/rollback tests. Real scheduled playback and cutoff still require a check on the working Pi.
