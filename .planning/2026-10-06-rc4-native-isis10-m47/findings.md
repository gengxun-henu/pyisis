# Findings

- Existing `windows-native-app-clean-host.yml` is hard-coded to ISIS 9 and `packaging/native-apps-win64/release.json`.
- `ports/windows/env/pyisis-isis10-win64.yml`, the ISIS10 source/patch queue, and `windows-isis-apps.yml` already provide the ISIS10 build path.
- `stage_windows_native_apps.py`, `archive_windows_native_apps.py`, and `test_isis_native_app_package.ps1` are version-neutral except for the release contract and archive paths.
- Native APP/GUI ZIPs are Windows x64 portable distributions; they are separate from Linux PyISIS wheels.
