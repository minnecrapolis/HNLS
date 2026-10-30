# Working-build reconciliation

The supplied capture HNLS-working-build-20261029-223610.zip contains 259 controller files and two receiver files. Every captured source file was checked against its recorded SHA256 before use. Both service snapshots were active and enabled. This is evidence about the captured installation, not a remote test performed by this release build.

The original uploaded upstream archive identifies commit `adcc5fdbc55e438396231360ebbc4bff62bae39c` in its ZIP comment. That archive supplies static/template files the collector excluded. The running installation has no Git revision available; the archive revision is the baseline, not a claim that the working Pi was an unmodified checkout.

## Merge rules

1. Start with the original upstream archive's server/client/docs/test files.
2. Overlay every captured application file in those directories, preserving the working Pi versions over both upstream and rc.1.
3. Copy the captured receiver code exactly.
4. Build clean distributable defaults from the earlier application template and captured schema, without personal output entries or song cues.
5. Gate explicitly temporary HNLS FRAME logging behind HNLS_FRAME_DIAGNOSTICS=1. Rendering/output logic is retained.
6. Add explicit release tooling, dependency manifests, fresh-install logic and documentation.

## Working fixes preserved

Eight files differed from rc.1: app/home/routes.py, app/static/assets/js/studio.js, app/templates/home/advanced.html, device.py, device_manager.py, output_service.py, studio_project.py, and webserver/blueprints/music_library_api.py. The working receiver files matched the candidate. The native controller color driver and music-analysis code matched and were preserved.

Restored material includes API YAML descriptions, font assets, original MIT notice and runtime requirements. The inherited requirement list omitted the flask_openapi module imported by the running web server; requirements/controller.txt explicitly includes the captured flask-openapi distribution version.

`docs/reconciliation.json` records captured file hashes, candidate differences, archive hashes, baseline revision and file origins. Runtime configuration, PIN, remote pairing state, music and media analysis caches are intentionally absent. They must never be reconstructed from public documentation as if they were the owner's private setup.
