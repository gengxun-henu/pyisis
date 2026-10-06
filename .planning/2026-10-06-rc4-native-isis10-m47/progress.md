# Progress Log

## Session: 2026-10-06

- Confirmed the current releases point to the old RC3 commit and the native workflow is ISIS9-only.
- Confirmed the ISIS10 Windows build environment and 150-APP manifest already exist.
- Started M47 from clean `main` after M46 merge.

- M47 PR #428 added conditional qisis retention for qnet; PR #429 corrected its patch hunk metadata.
- Hosted run 37509859168 proved qisis compiles but failed at MSVC LNK1189 while linking monolithic `isis.dll` (65,535-member limit).
- RC4 wheel assets were published manually after the workflow release step hit GitHub API HTTP 500: `v1.3.0rc4-isis9.0.0` and `v1.4.0rc4-isis10.0.0`.
- ISIS9 native ZIP was copied from the validated RC3 package into the RC4 release; ISIS10 native GUI remains blocked pending a split-DLL design.
