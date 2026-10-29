# Release status

This is a source consolidation, not a capture of the running Pis. The controller snapshot was merged with the song-cue, HNLS interface and music-intelligence updates. Logical RGB packing was corrected in the consolidated source; an existing Pi driver is not overwritten by these repository tools.

## Public release blockers

1. Capture the working controller application tree, dependency versions, original manifests and service unit using tools/export_installation.py. Review the resulting archive privately before sharing.
2. Reconcile the export against src/controller; preserve newer working fixes. Recover original runtime dependency manifests and missing vendor/static assets. The supplied snapshot lacks a complete standalone bootstrap environment.
3. Obtain the exact applicable upstream license, copyright notices, revision and web-asset licenses. Do not invent copyright text.
4. Validate install, rollback, cold boot, RGB/GRB, audio and cue exit on spare hardware.
5. Only then mark a release stable or advertise blank-Pi plug-and-play installation.

## Validation distinction

Repository checks compile Python and inspect package exclusions. They do not establish that Flask dependencies are complete, real LEDs work or a fresh OS can boot the show. The user has confirmed the separate updates work on their installation; that is not a clean installation test of this consolidation.

Not implemented by this package: a fresh-OS installer, prebuilt SD image, automatic boot-time playlist playback, multiple outputs on the receiver, web power-supply budgeting, or an unlimited-output guarantee. Legacy advanced studio/FSEQ modules are retained in the snapshot but require renewed integration tests with the current interface.
