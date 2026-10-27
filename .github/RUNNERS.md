# GitHub Actions runners

This public repository intentionally uses GitHub-hosted runners. Its existing
Ubuntu version pins are retained. `GENERAL_RUNNER=ubuntu-latest` also keeps the
on-demand health check hosted. The self-hosted policy below applies to private
repositories, or a future explicitly approved migration.

Compatible Linux x64 jobs default to the organization self-hosted `wf-general`
pool. They queue for that pool when it is busy or offline; they do not silently
fall back to paid GitHub-hosted runners. New compatible Linux jobs should follow
this default. Native ARM, Windows, macOS and builds needing an older glibc
baseline retain their existing runners. External-fork pull requests retain
GitHub-hosted isolation.

For an emergency repository-wide override, set the Actions repository variable
`GENERAL_RUNNER` to `ubuntu-latest`. Delete that variable or restore `wf-general`
to return to self-hosted operation. Existing manual `runner: ubuntu-latest`
inputs also remain available. The Runner health check workflow offers both
choices and reports the selected runner and available disk space.

Yocto jobs use `DATAPLICITY_OS_RUNNER`, defaulting to `vlan400-yocto`, independently
of the general pool. CodeQL default setup has a separate runner setting under
repository Settings > Code security > Code scanning; workflow defaults do not
override it.
