# GitHub repository and releases

## Windows / GitHub Desktop

1. Extract the delivery ZIP. Use the HNLS folder containing README.md, LICENSE, install.py, src, docs, tools and .github as the repository root.
2. Open GitHub Desktop and select File > Add local repository. Choose HNLS. If it is not a Git repository, select the option to create one in that folder. Do not overwrite the included README, license or gitignore.
3. Review Changes, commit the source with a summary such as Reconcile HNLS release candidate, and Publish repository under your own account. Private visibility is useful while completing spare-Pi acceptance.
4. Check that README renders and .github/workflows is present. dist is intentionally ignored by Git; it holds downloadable release files rather than tracked source.
5. Open the GitHub repository > Releases > Draft a new release. Create tag v0.1.0-rc.16 targeting the committed main branch. Title it HNLS 0.1.0-rc.16. Copy the rc.16 notes from CHANGELOG.md and mark it as a pre-release.
6. Attach the configured hnls-setup.sh, HNLS-0.1.0-rc.16-source.zip and SHA256SUMS.txt from the GitHub Actions release artifact. Publish the prerelease when ready. GitHub also generates source archives from the tag automatically.

No repository was created or release published by preparing this package. Public stable release should follow the physical acceptance listed in RELEASE_STATUS.md.

## Building again

```sh
python3 -m pip install -r requirements/test.txt
python3 -m unittest discover -s tests -v
python3 tools/validate.py
python3 tools/check_defaults.py
python3 tools/build_release.py
```

Build locally with `--repository` followed by your actual OWNER/REPOSITORY, or use the tag workflow (which supplies it automatically). See [Quick installation](QUICK_INSTALL.md). The release builder validates source and release-manifest checksums, produces a deterministic source ZIP, and creates SHA256SUMS.txt. Update VERSION and CHANGELOG before making a new release. If source/requirements change, explicitly regenerate release-manifest.json using tools/update_manifest.py and review the diff before committing; ordinary builds never silently replace the expected hashes.

GitHub CI runs tests, source validation, default schema validation and Jinja template parsing. Pushing a v-prefixed tag builds the ZIP and uploads an Actions artifact for review. It does not automatically publish a GitHub release. Attach the reviewed assets through Releases.

## Hardware acceptance

Record clean OS/card, Pi model, Python/dependencies, install logs, reboot, audio destination, RGB/GRB order, actual strip count/FPS, cue end restoration, overlap/reserve, seek/replay/skip, song gap, shuffle, remote watchdog/reconnection, mobile controls and toolbar. Keep music and pairing keys out of issues and releases.

Existing installations use dist/hnls-designer-effects-update.zip for the Song Designer changes; this is separate from the complete source asset. Its exact install commands and supported versions are in updates/designer-effects/README.txt.

The rc.5 assets also include hnls-two-color-update.zip, intended for rc.4 systems already running the designer-effects update. The complete designer-effects package supports the earlier known captured/release builds.

For the current rc.5 installation, hnls-moment-edit-update.zip is the small saved-moment editing fix. It is also included in the refreshed complete designer/two-color update payloads.

The rc.7 assets include hnls-color-ranges-update.zip for the current rc.6 main Pi. This applies the mixed-range output correction without changing the slave. See updates/color-ranges/README.txt.

For rc.8 also attach dist/hnls-pc-audio-update.zip for existing rc.7 controllers. Do not publish a personalized sender download (it includes its private connection key). Historical scoped updates are retained for their matching versions and are not replacements for the newest update.

The rc.9 incremental attachment is dist/hnls-palettes-update.zip for current rc.8 controllers. Prior incremental assets remain version-specific.

rc.10 corrects the incremental palette installer to preserve local config templates. Its palette update remains for the rc.8 code baseline or already-applied matching palette payload.

rc.12 adds dist/hnls-easy-ui-update.zip for the current corrected palette interface. This is a hot-reload interface-only update; prior feature updaters remain version-specific.

rc.13 incremental attachment: dist/hnls-play-now-update.zip for the rc.12 interface. This scheduler/API update briefly restarts the main service.

rc.14 incremental attachment: dist/hnls-home-controls-update.zip. It is the single catch-up installer for working rc.11, rc.12 or rc.13; users do not need to chain earlier UI/Play now ZIPs. It briefly restarts the main service.

rc.15 source selector: include hnls-audio-source-update.zip; see AUDIO_SOURCE.md.
