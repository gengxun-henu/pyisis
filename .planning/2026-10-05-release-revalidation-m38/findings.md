# Findings & Decisions

## Findings
- Run `37258043592` passed all four wheel builds and all six Linux clean-install jobs.
- The publish job failed only because `v1.3.0rc3-isis9.0.0` already exists.
- Both configured prereleases already exist with Linux wheelhouse, Windows wheelhouse, and `SHA256SUMS.txt` assets.

## Decision
Classify M38 as technically passed and publication idempotency-guarded; do not delete or overwrite existing releases.
