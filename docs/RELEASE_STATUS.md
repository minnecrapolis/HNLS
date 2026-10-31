# Release status — 0.1.0-rc.16

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

rc.4 adds range-exclusive designer effects and worker hardening. Tests reproduce nonblocking queue competition and an abandoned multiprocessing clock lock, as well as reserved range behavior and cache restoration. They do not establish that the reservation checkbox was the sole cause of the reported physical all-on/cycling symptom. Retest on the working Pi and inspect service/power logs if that symptom persists.

rc.5 extends second-color rendering and adds a four-file rc.4 updater. Local tests and UI simulations pass; physical playback of the new color combinations is pending a user check.

rc.6 improves explicit saved-moment editing. The previous handler only populated a form above the table without opening or scrolling it into view. This can explain an apparently inactive Edit button; it is not a claim that all browser-side failures share that cause. Errors now appear on the page. Actual browser acceptance on the Pi is pending.

rc.7 supports mixed physical RGB orders within normal configured outputs, with main-side compensation for the paired slave. All 36 default/range permutations and native/remote integration have offline coverage. Actual mixed-strip colors still require a physical test; Advanced Studio remains a separate output path and does not inherit these mappings.

Windows PC audio is new in rc.8. Receiver/protocol/source/UI/update tests pass locally. Windows compile/conversion/packet CI is defined but has not run here; actual endpoint capture, service content and Pi playback/LEDs must be checked on hardware before declaring this feature accepted.

Holiday palettes and analysis-directed Song Show (rc.9): core, UI and rollback tests pass locally; Classic frames match the recorded rc.8 renderer. Confirm performance, palette appearance and motion preferences on actual strips. No Pi was remotely changed during packaging.

rc.12 changes web templates/browser assets only. The scoped updater performs no service restart or runtime/config-template replacement. Task navigation and UI regression tests pass; actual browser/phone visual acceptance remains pending.

rc.13 adds manual Play now/Stop show and scheduler ownership handling. It uses a guarded backend update with a brief main-service restart; it is distinct from the prior interface-only hot reload. Unit/UI/install tests pass, but live Pi manual playback and clock-boundary acceptance remain to be checked.

rc.14 places everyday controls on Home and provides a cumulative update from actual rc.11/12/13 source baselines. Unit/UI/install checks pass; actual Pi audio/LED and viewport acceptance remain pending. Existing rendering, GPIO and private configuration templates are not replaced by this scope.

rc.15 source selector: include hnls-audio-source-update.zip; see AUDIO_SOURCE.md.

rc.16 adds a complete-release download/install entry point. Generated GitHub commands require a real published repository/release. Download/extraction/validation/cleanup are tested with local fixtures; live GitHub and clean Pi installation/reboot acceptance remain pending.
