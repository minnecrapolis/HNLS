# Publish the minnecrapolis/HNLS one-command installer

Repository: https://github.com/minnecrapolis/HNLS
Release tag: v0.1.0-rc.16

## Publish the full project

Use the HNLS directory in the delivery kit as the repository root. It includes
all current source changes, notices, documentation, installer, tests and GitHub
workflows. The dist directory contains generated downloadable release assets;
it is intentionally ignored by Git.

Commit/push the source to minnecrapolis/HNLS. Create release tag v0.1.0-rc.16
pointing to that source commit. Mark the release as a prerelease until clean-Pi
acceptance is complete. Attach these three files from dist:

- hnls-setup.sh (already configured for minnecrapolis/HNLS)
- HNLS-0.1.0-rc.16-source.zip (complete HNLS installation source)
- SHA256SUMS.txt

Then publish the release. Upload the complete checksum list unchanged. It may
also list optional historical scoped update assets; the installer only requires
the source ZIP and checksum file. Alternatively obtain the same three configured
assets from the tag workflow’s hnls-release-assets artifact.

## Share these commands AFTER the release and three assets are published

Main Pi (also offers the Main Pi / Additional Pi choice):

```bash
curl -fsSL https://github.com/minnecrapolis/HNLS/releases/download/v0.1.0-rc.16/hnls-setup.sh | bash
```

Additional Pi without the role-selection prompt:

```bash
curl -fsSL https://github.com/minnecrapolis/HNLS/releases/download/v0.1.0-rc.16/hnls-setup.sh | bash -s -- --role receiver
```

Download/verify without installing:

```bash
curl -fsSL https://github.com/minnecrapolis/HNLS/releases/download/v0.1.0-rc.16/hnls-setup.sh | bash -s -- --check
```

These commands require the published release. Preparing this kit does not
publish it, and public availability was not verified from this environment.
Use the commands on fresh Pis; existing HNLS/MLSC installations are refused.
Both roles are enabled at boot. This full install includes every current HNLS
feature; users do not chain incremental update ZIPs. Configure lights and sound
through the main web UI after installation. See QUICK_INSTALL.md for details.
