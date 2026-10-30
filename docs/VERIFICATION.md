# Release verification — 2026-10-30

- Both uploaded capture ZIPs and every recorded application-file SHA256 verified.
- 76 automated tests passed, including cue bounds/restoration, grouping, shuffle/analysis, authenticated remote chunk ordering/watchdog/recovery, loopback sender/receiver behavior, export exclusions, installer refusal/tamper detection, and dependency/service-failure cleanup.
- 161 Python source files passed AST parsing. Controller/tooling parsed with Python 3.11 grammar; receiver files parsed with Python 3.9 grammar. Parsing does not test native drivers or every version's runtime semantics.
- 301 application/dependency payload files passed release-manifest verification.
- All literal template include/extend and static URL targets resolve to included files.
- Receiver sources match the working capture exactly. Controller capture differences are limited to the explicit runtime requirements and opt-in diagnostic logging; the added clean default config and restored upstream files are documented separately.
- Clean default values passed a local inspection against the extracted schema constraints. Formal jsonschema validation and Jinja parsing are implemented in tools/check_defaults.py and the installer/CI but were not run locally because the build environment's package index did not provide those dependencies.
- Fresh installer OS-package/dependency resolution, real service startup and clean-Pi hardware acceptance are pending. Existing Pis were not modified.

Reproducibility is checked by comparing repeated source-ZIP hashes after all final source/documentation changes. SHA256SUMS.txt belongs to the generated source asset. Release-manifest hashes verify bundled application files; they are not a cryptographic signature or dependency wheel lockfile.

rc.3 also passed Node-based Music/schedule UI simulations and JavaScript syntax checks. Schedule tests cover closing boundaries, overnight start weekdays, DST, reboot startup, empty-library retries, failed actions and disabling. Scoped-update tests cover version refusal, repeat installation, exact rollback and simulated partial-copy failure. No live Pi schedule was changed during these checks.
