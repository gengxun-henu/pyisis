# Windows ISIS native APP release contract

`release.json` is the immutable packaging boundary for the ISIS 9.0.0 Win64
native-application archive. It publishes the 150 CLI APPs pinned by
`ports/windows/isis/windows-app-manifest.json`, plus the `qnet` GUI APP.
`isisui` is a runtime helper and is not part of the public APP count.

The CLI manifest SHA-256 is calculated after normalizing CRLF and bare CR line
endings to LF. This keeps the content lock identical on Windows and Linux Git
checkouts while still rejecting any semantic or byte-content drift.

Validate the contract from the repository root with:

```powershell
D:/pyisis-win-env/python.exe tools/packaging/windows_native_app_manifest.py `
  --release packaging/native-apps-win64/release.json `
  --cli-manifest ports/windows/isis/windows-app-manifest.json `
  --check
```

The check fails closed on schema, type, hash, inventory, ISIS 9 support/build
status, name-overlap, or mandatory-APP errors.
