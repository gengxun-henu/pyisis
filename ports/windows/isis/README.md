# ISIS 9.0.0 Windows SDK/Runtime Prefix

This directory owns the ISIS side of the Windows native pyisis port.

The scripts fetch ISIS 9.0.0 source code into a generated local directory, apply
tracked patches, configure with MSVC and Ninja, build the SDK/runtime subset,
install it into a local prefix, and verify the installed prefix. Source fetching
defaults to the GitHub tag archive because it is more reliable on Windows
networks than a large shallow clone; `fetch_isis_900.ps1 -Method git` remains
available when direct Git traffic is preferred. Archive downloads prefer
`curl.exe` when available and fall back to PowerShell's `Invoke-WebRequest`.
The archive path supports `-DownloadTimeoutSeconds`, `-DownloadRetries`,
`-LowSpeedLimitBytesPerSecond`, and `-LowSpeedTimeoutSeconds` so slow network
failures are reported at the fetch layer instead of hanging silently.

Default local paths:

- source: `build/windows/external/isis-9.0.0-src`
- build: `build/windows/isis-build`
- prefix: `build/windows/isis-prefix`

The prefix is considered usable for the first pyisis milestone when
`verify_isis_prefix.ps1` passes.
