# Findings

- Workflow run: `37403508140` (`main`, GitHub-hosted fallback).
- Effective runners: Windows jobs `windows-2022`; Linux jobs `ubuntu-24.04` plus hosted Ubuntu 22.04/24.04/26.04 install validation.
- ISIS 9 Windows cp312 wheel build: passed.
- ISIS 10 Windows cp313 wheel build: passed.
- ISIS 9 Linux cp312 manylinux wheel build and Ubuntu 22.04/24.04/26.04 install tests: passed.
- ISIS 10 Linux cp313 manylinux wheel build and Ubuntu 22.04/24.04/26.04 install tests: passed.
- The optional Windows ISIS application smoke was excluded because the repository mock `ISISDATA` does not contain the NAIF kernel set required by `campt`; native application validation remains in `windows-native-app-clean-host.yml`.
- Existing prerelease wheel assets remain `v1.3.0rc3-isis9.0.0` and `v1.4.0rc3-isis10.0.0`; the wheel workflow correctly skips publication when configured tags already exist.
