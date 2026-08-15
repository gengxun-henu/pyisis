# Windows ISIS Archive Resume Design

## Goal

Make the Windows ISIS archive fallback deterministic when the GitHub codeload
endpoint does not honour byte-range requests, without changing the Git fetch
path or the installed-prefix build contract.

## Observed Failure

`fetch_isis.ps1` unconditionally passes `curl.exe --continue-at -`. A direct
Range request to the ISIS 9.0.0 codeload archive returned HTTP 200 rather than
206, so an existing partial archive is not a resumable input. Repeated retries
can replace or truncate that file rather than make verified progress.

## Selected Design

The archive path will probe whether the existing archive can be resumed before
adding `--continue-at -` to the download command. If resume is unsupported,
the script will fail with a precise message that identifies the archive and
requires an explicit clean retry, preserving the existing file for diagnosis.
It will not silently restart or delete a partial archive.

This is deliberately conservative: automatic deletion would discard the only
transfer evidence, while silently using `--continue-at -` risks presenting an
incomplete archive as a download retry. A clean retry remains available through
the script's existing `-Force` contract after the user or operator has reviewed
the exact generated archive target.

## Alternatives Considered

1. Always disable `--continue-at -`: avoids the bug but regresses working
   resumable archive downloads.
2. Automatically delete and restart on HTTP 200: may work here but silently
   destroys diagnostic transfer state.
3. Detect non-resumable responses and fail explicitly: preserves current
   behavior for servers that support ranges and makes the unsafe case visible.

Option 3 is selected.

## Test Strategy

Add a focused Python unit test for `fetch_isis.ps1` that exercises archive mode
against a local HTTP fixture which returns HTTP 200 to a Range request. The
test must prove that a pre-existing partial archive is preserved and the script
fails before extraction. A companion passing case will use a range-capable
fixture and prove the script invokes the normal archive validation path.

No external network is used by the regression tests.
