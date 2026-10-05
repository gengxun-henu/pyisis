# Findings

- Focused regression command ran 49 tests across `windows_native_app_manifest_unit_test`, `windows_native_app_validation_unit_test`, and `wheel_workflow_unit_test`; all passed in 1.206 seconds under `asp360_new`.
- `ports/windows/isis/windows-app-manifest.json` contains exactly 150 unique APP entries.
- `packaging/native-apps-win64/release.json` keeps `qnet` as the public GUI app, `isisui` as the runtime helper, and `reduce`, `jigsaw`, and `qnet` as mandatory inventory entries.
- M39 provides GitHub-hosted Windows ISIS 10 APP batch evidence; M40 records the remaining self-hosted runner permission blocker for the ISIS 9 clean-host package path.
