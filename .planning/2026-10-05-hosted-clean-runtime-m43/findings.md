# Findings

- Initial hosted attempt `37274861782` built and staged the ISIS 9 package successfully but clean-runtime correctly rejected Windows Server 2022 (`runtime host must be Windows 11`).
- The workflow was updated to `windows-2025`, and run `37280009059` passed all jobs.
- Passing jobs: ISIS 9 prefix/package build, Windows 2025 clean-runtime matrix, and final evidence binding.
- Final evidence artifacts are unexpired: `native-app-final-evidence-37280009059` (108,007,705 bytes), `native-app-clean-runtime-37280009059` (2,357 bytes), `native-app-dependency-evidence-37280009059` (21,301 bytes), and runtime input (107,992,391 bytes).
- The self-hosted runner is no longer required for this clean-runtime path; the workflow now uses GitHub-hosted Windows 2025.
