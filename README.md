# soln-installer-releases
Official Soln installer downloads

Download installers from [GitHub Releases](https://github.com/solnsu/soln-installer-releases/releases).
Domestic mirror: [GitCode Releases](https://gitcode.com/lunaris_soln/soln-installer-releases).

## Release synchronization

Publishing a GitHub release starts the **Sync release to GitCode** workflow.
It mirrors the release title, notes, version tag and binary attachments. Every
installer must be listed in `SHA256SUMS.txt`. Downloads are checked against
GitHub asset digests and the checksum file before upload; GitCode downloads
are then checked without authentication. Preview releases remain previews.

To sync an existing release or resume a failed upload, open **Actions → Sync
release to GitCode → Run workflow**, enter its tag (for example `v1.0.0`),
and run. Existing matching attachments are reused. A conflicting attachment
causes failure rather than silently replacing a published binary.

The repository requires the Actions secret `GITCODE_TOKEN` with project write
access to `lunaris_soln/soln-installer-releases`. Keep the token out of source
files, release notes and logs. This repository distributes binaries; it does
not contain the Soln application source code.
