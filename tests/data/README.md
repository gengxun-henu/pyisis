# Test data policy

`tests/data` contains deterministic inputs that repository tests open directly.
Do not add complete mission archives, generated outputs, or developer-only
reference material here.

## Data tiers

1. **Smoke data**: small inputs needed by import and routine CI checks. Keep
   `tests/data/isisdata/mockup` in ordinary Git.
2. **Unit fixtures**: the smallest scientifically valid files that reproduce a
   binding or ISIS behavior. Keep small deterministic fixtures in ordinary Git.
3. **Integration data**: large mission products used only by explicitly
   selected integration tests. Store these in a versioned external archive with
   a manifest and SHA-256 checksums; fetch them only for the jobs that need them.

Git LFS is reserved for large binary fixtures that must remain coupled to every
checkout. It is not the default for optional integration datasets.

## Current audit priorities

The largest tracked groups should be reviewed first, without deleting or moving
them until every direct and indirect test consumer is identified:

| Directory | Approximate size | Current action |
| --- | ---: | --- |
| `lronaccal` | 105 MB | Map consumers and investigate scientifically valid minimization |
| `tagcams2isis` | 31 MB | Resolve file-level consumers before deciding whether to externalize |
| `mosrange` | 21 MB | Keep until forward-intersection and camera consumers are mapped |
| `clipper` | 21 MB | Keep until camera-model consumers are mapped |
| `tgoCassis` | 20 MB | Resolve file-level consumers before deciding whether to externalize |
| `kerneldbgen` | 17 MB | Separate small database fixtures from large kernel payloads |

Directory-name searches are only triage. Tests can reference individual
filenames or shared fixture helpers, so a missing direct directory-name match is
not evidence that data is unused.

## Adding or moving data

- Record the consuming test module and behavior being validated.
- Prefer cropped or reduced fixtures when the transformation preserves the
  behavior under test.
- Keep license/provenance metadata with externally archived data.
- Make missing optional integration data produce an explicit skip message.
- Never weaken a routine unit test into an unconditional skip merely to reduce
  repository size.
