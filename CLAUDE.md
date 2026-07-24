# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Also read and
follow the repository's `AGENTS.md`; its project-specific rules are mandatory.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. ISIS Version Expansion

Before adding or updating support for an ISIS version, read and follow
`docs/isis-version-expansion-policy.md`.

The local ISIS 10 authority is the `asp370` environment containing USGS
`isis 10.0.0 h1f94ec8_1` on CPython 3.13. Keep `csm 3.0.3.3` pinned because
`csm 3.1.0` is ABI-incompatible with that ISIS binary. Do not use the removed
NASA ASP `asp_4` package as the ISIS 10 binding surface.

Do not infer the binding scope from newly installed header names alone:

- record the official tag/commit and exact conda version, build, channel,
  platform, and subdir
- compare added, removed, renamed, and same-name changed headers and public C++
  declarations
- inspect the official Changelog for Added, Changed, Deprecated, Removed, and
  Breaking entries, while treating the target conda prefix as the compile/link
  source of truth
- record differences between the official source tag and channel-specific
  package contents
- verify Linux `.so` and Windows DLL/import-library symbols before exposing an
  API
- classify every discovered item, including explicit reasons for exclusions
- keep compatible bindings shared and use version guards only where necessary
- do not publish until the Linux/Windows × supported-ISIS-version validation
  matrix is complete

## 6. Disk Space and Build Cleanup

This workstation has limited disk space. After a build succeeds and its result
is verified, keep only artifacts needed for later use, such as wheels, shared
libraries/DLLs, install packages, and reports. Promptly remove disposable build
directories, downloaded CI copies, staging trees, build-only caches, and other
temporary files. Identify and preserve the exact final artifacts first; never
delete user files, reusable source/reference checkouts, or an active build.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
