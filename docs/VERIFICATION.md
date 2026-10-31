# Release verification — 0.1.0-rc.6

## Passed locally

- Captured application hashes and original archive revision/hash were verified during reconciliation. Source origins and subsequent release changes are recorded in reconciliation.json.
- 105 automated Python tests passed: cue boundaries/ranges/reservations/restoration, 12 designer effects, grouping, shuffle/analysis, authenticated remote transport/watchdog, fresh-installer failure cleanup, both scoped-update installers, and simulated worker concurrency/clock failures.
- 177 Python files parsed. Controller/tooling uses Python 3.11 grammar checks; receiver sources use Python 3.9 grammar checks. Parsing does not prove every runtime/backend works.
- 301 application/dependency payload files passed the release-manifest hash check.
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
