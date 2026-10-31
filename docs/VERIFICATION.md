# Release verification — 0.1.0-rc.16

## Passed locally

- Captured application hashes and original archive revision/hash were verified during reconciliation. Source origins and subsequent release changes are recorded in reconciliation.json.
- 253 automated Python tests passed: cue boundaries/ranges/reservations/restoration, 12 designer effects, grouping, shuffle/analysis, authenticated remote transport/watchdog, fresh-installer failure cleanup, both scoped-update installers, and simulated worker concurrency/clock failures.
- 238 Python files parsed. Controller/tooling uses Python 3.11 grammar checks; receiver sources use Python 3.9 grammar checks. Parsing does not prove every runtime/backend works.
- 322 application/dependency payload files passed the release-manifest hash check.
- Node Music, schedule and Song Designer UI simulations passed, including title playback, edit preservation, motion controls, the exact second-string 700–750 selection, reservation checkbox without playback restart, and overlap warnings.
- A forked-process test terminated a clock lock holder, then verified nonblocking overlay output and recreated shared state. Queue tests cover competing consumers, bounded drains, and absence of blocking reads in realtime output/effect routines.
- Real output-loop tests verified reserved darkness before/after a cue, range-exclusive frames during it, cached base restoration without a new automatic frame, and song blackout priority.
- Update tests verified supported-source checks, unchanged driver/private settings, repeat installation, exact code rollback and partial-copy failure recovery.

## Not run here

Additional Flask/Jinja/jsonschema test dependencies could not be installed from this environment's package index. Formal jsonschema validation/template parsing remain in tools/check_defaults.py, CI and installer paths for systems with those dependencies. Local schema-constraint inspection passed during the base release; the new fields belong to separate song-moment documents and do not change the device config schema.

No running Pi was modified. Fresh-OS installer acceptance and actual scheduled/designer playback must still be tested on Pi hardware. The reported reservation/all-on/restart symptom is not proven to have one cause solely from the description; the update fixes identified software hazards and needs a real-Pi retest. No new electrical capacity guarantee is made.

Repeated source/update ZIP hashes are compared after final changes. SHA256SUMS.txt belongs to the generated release assets; payload hashes are not a signature or a hash-locked dependency graph.

Installer correction: a hardcoded Music-template validation path in the designer updater was caught on the Pi before service shutdown. It now validates only the bundled HTML files. Regression tests exercise the non-offline validation path with a parser stub, verifying both successful restart order and that parser errors change no files/services. Actual Jinja parsing still uses the Pi's installed Jinja library.

Two-color checks cover both flash endpoints, moving/fading backgrounds, pulse color endpoints and midpoint, palette vs full rainbow, dark-background opt-out, brightness limits, legacy defaults, persisted options, UI enablement for the reported effects, and the four-file installer including its non-offline template validation path.

Saved-moment Edit UI simulation: clicked the second saved row, verified both colors/effect/range and selected-row state, opened Fine-tune, scrolled/focused the editor, asserted no save/playback request on Edit, then saved changes to the selected cue ID without removing the other cue. A simulated display error was surfaced visibly. The three-file updater has install/rollback, version-refusal, partial-copy and non-offline template-validation tests. Real browser testing on the Pi remains pending.

Mixed-order verification covers all 36 RGB permutations, exact inclusive 601–650 boundaries, unmodified source/unlisted pixels, unchanged brightness, driver constant alias lookup, native packing and paired-transport compensation, identity-vs-equal device lookup, overlap/bounds validation, private persistence, failed-write preservation, last-good cache, count shrink clipping/warnings and deleted-ID cleanup. The native-driver diff is verified to be exactly one prepare_frame call; existing packing code is preserved. The range UI simulation covers device selection, unsaved edits, errors and clearing. The eight-file updater has offline install/restore/refusal/failure and template-validation checks. No mixed-strip hardware test was performed here.

Windows PC audio: authenticated packet/tamper/order/loss/bounds, real local UDP, private sender download and API control, native-rate output/DSP, stall blackout and source cleanup checks pass. Node UI and twelve-file update rollback/version guards pass. Windows PowerShell compile/conversion/interoperability CI has been added but was not executed here. Actual Windows-to-Pi playback remains untested. Historical scoped packages are verified against their own payload hashes and explicit successor ancestry where source files changed.

Palette/director checks: all eight test-tone bands and isolated band colors, 14 recipes, optional legacy schema, deterministic phrase selection, Classic frame parity, each motion under the physical budget, synchronized ends, transient POWER exit, legacy save without an audio restart, editable preset UI and targeted rollback field archival pass. Prepared whole-song sections/tempo are used when available; eight-band levels and stream fallback are live.

Palette installer correction: a local template hash difference no longer blocks installation because the template is not part of this update. Real rc.8 baseline fixture installation/rollback with a different template passes; all required source hash checks remain. No live Pi installation was performed here.

Startup correction: the previous AST-only checks missed a misplaced future import. All release Python sources now undergo semantic compilation as well as grammar parsing. The palette updater compiles payloads before stopping services, and a regression checks rejection of the same error without changing files. Actual Pi restart remains to be verified.

Easy-interface verification: task search matches common terms and every target anchor exists; nested collapsed sections open and focus correctly; dialog/results do not call APIs; consistent navigation/popup labels and opener-only routing checks pass. Save & use saves before activation and reports partial failure. Existing UI suites pass. Installer tests verify only HTML/CSS/JS payloads, no service calls, private/runtime preservation, template-parse refusal, version/path checks and exact rollback. Actual desktop/phone rendering is unverified because a browser executable/Jinja are unavailable locally; the installer uses real Jinja before mutation.

Play now verification covers enabled outside-hours start before the first tick, repeated polling without stopping, next-opening handover/closing, in-window manual stop, disabled/overnight/restart behavior, schedule-byte preservation, empty library, fail-dark start error, stop with malformed settings, API action/login checks and deliberate UI/double-click/error behavior. The nine-file updater has guarded install/restore/refusal/copy/parser tests. No physical Pi was changed here.

Home control checks cover read-only initialization, literal filenames, selected-song manual start/shuffle retention, transport/seek/upload, scoped look/brightness, mixed values, unsaved edits and partial failure, speaker choices and authenticated APIs. Cumulative update fixtures reproduce published rc.11/12/13 source files with a custom local template and verify exact install/rollback. Real Pi and browser viewport acceptance remain pending.

Audio-source UI simulations verify explicit source choices, hidden local controls during streaming, error recovery and stale-poll protection. Guarded cumulative updater tests install/rollback actual rc.11–rc.14 snapshots.

Full-release bootstrap tests cover piped execution, baked repository/version, receiver role, download-only checks, checksum/version refusal, unsafe archive paths/symlinks, argument guards and temporary cleanup. No live GitHub download or fresh Pi hardware installation was performed here.
