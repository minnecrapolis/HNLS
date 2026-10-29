# Publishing HNLS

1. Resolve every blocker in RELEASE_STATUS.md. Preserve applicable licenses and attribution.
2. Create an empty GitHub repository named HNLS or hournerd-lightshow. Extract this archive and open a terminal inside HNLS.
3. Run `python3 tools/validate.py` and review source and assets for private information.
4. Run `git init`, `git add .`, and `git commit -m "Prepare HNLS source release candidate"`.
5. Use GitHub's displayed remote URL for your own repository; push the main branch using your normal authenticated Git client. No repository/account has been created by this package.
6. Run `python3 tools/build_release.py`. Review generated files in dist. The archive excludes live settings, media, caches and the optional private bridge.
7. Create a GitHub prerelease tagged v0.1.0-rc.1. Use CHANGELOG.md as the description and attach the generated ZIP and SHA256SUMS.txt. The included tag workflow builds those assets as a downloadable Actions artifact; it intentionally does not publish automatically.
8. After spare-Pi installation/rollback and hardware checks pass, update release status/version and make a stable tag. Never label this candidate a tested SD image or blank-Pi installer.

## Hardware acceptance record

Record OS image, Pi model, Python and dependency versions; cold boot; audio destinations; primary RGB colors; short and long strips; cue entry/exit/overlap/reserve; seek/replay/skip; song gap; shuffle; remote packet loss/reconnection/watchdog; mobile navigation; toolbar; install/rollback and power behavior. Keep results with the release.
