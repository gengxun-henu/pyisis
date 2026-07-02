# Parallel DOM-Space Point Registration Design

**Date:** 2026-07-02
**Author:** Geng Xun
**Status:** Draft
**Target file:** `scripts/parallel_pointreg_dom.py`

---

## Overview

`parallel_pointreg_dom` adds process-level parallelism to DOM-space point
registration for ISIS ControlNets with 100万+ ControlPoints. It splits a
large ControlNet with ISIS `cnetsplit`, dispatches N parallel `pointreg_dom`
workers via `subprocess`, then merges results with ISIS `cnetmerge`.

The existing `scripts/pointreg_dom.py` is **not modified**. The new script
is a pure orchestration layer that invokes the existing program as a
subprocess.

## Motivation

Serial `pointreg_dom` on a 100万+ point ControlNet is CPU-bound and
single-threaded. Each ControlPoint is processed independently — the only
shared state is the read-only cube cache — making the workload
embarrassingly parallel once the ControlNet is partitioned.

## Architecture

```
parallel_pointreg_dom.py --num-processes N
    │
    ├─ 1. cnetsplit CNET=input.net ONET_PREFIX=chunk NUM_OUTPUT_FILES=N
    │      → tempdir/chunk_001.net ... chunk_N.net
    │
    ├─ 2. N × subprocess:
    │      python pointreg_dom.py --cnet chunk_i --onet result_i ...
    │      (each worker gets its own PyisisDomRegistrar and cube cache)
    │
    ├─ 3. cnetmerge INPUTTYPE=list CLIST=results.lis ONET=output.net
    │      DUPLICATEPOINTS=merge
    │
    └─ 4. Cleanup tempdir (unless --work-dir was user-specified)
```

## File Structure

```
scripts/
├── pointreg_dom.py              ← untouched
└── parallel_pointreg_dom.py     ← new file
```

`parallel_pointreg_dom.py` does **not** import from `pointreg_dom.py`.
Each worker is launched as a `subprocess.run` call invoking
`pointreg_dom.py` as a standalone program. This avoids all pickle,
shared-state, and import-path issues.

## CLI

```bash
python scripts/parallel_pointreg_dom.py \
    --fromlist       ori_cubes.lis \
    --domlist        dom_cubes.lis \
    --cnet           input.net \
    --deffile        autoreg.pvl \
    --onet           output.net \
    --num-processes  8 \
    --work-dir       /tmp/pointreg \
    --cnetsplit      cnetsplit \
    --cnetmerge      cnetmerge
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--num-processes` | 1 | Number of parallel worker processes. 1 = serial fallback (runs pointreg_dom directly). |
| `--work-dir` | auto tempdir | Directory for chunk and result files. User-specified dirs are preserved; auto dirs are cleaned up. |
| `--cnetsplit` | `cnetsplit` | Path to the ISIS cnetsplit executable. |
| `--cnetmerge` | `cnetmerge` | Path to the ISIS cnetmerge executable. |

All other parameters (`--fromlist`, `--domlist`, `--cnet`, `--deffile`,
`--onet`, `--dom-band`, `--original-band`, `--max-open-cubes`,
`--skip-serial-check`, `--pvl`) are forwarded verbatim to each worker.

## Detailed Steps

### Step 1: Split

```python
subprocess.run([
    cnetsplit_path,
    f"CNET={args.cnet}",
    f"ONET_PREFIX={work_dir}/chunk",
    f"NUM_OUTPUT_FILES={args.num_processes}",
], check=True)
```

Discover generated chunk files by globbing `work_dir/chunk*.net`.

### Step 2: Dispatch Workers

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

with ProcessPoolExecutor(max_workers=num_processes) as executor:
    futures = {}
    for chunk_path in sorted(chunk_files):
        worker_cmd = build_worker_command(chunk_path, result_path, args)
        futures[executor.submit(subprocess.run, worker_cmd, check=False)] = chunk_path
    for future in as_completed(futures):
        result = future.result()
```

Each worker command is:
```
python scripts/pointreg_dom.py \
    --fromlist ori_cubes.lis \
    --domlist dom_cubes.lis \
    --cnet <chunk_path> \
    --deffile autoreg.pvl \
    --onet <result_path> \
    [--dom-band N] [--original-band N] [--max-open-cubes N] [--skip-serial-check] [--pvl]
```

### Step 3: Merge

Write a results list file, then:
```python
subprocess.run([
    cnetmerge_path,
    "INPUTTYPE=list",
    f"CLIST={results_list_path}",
    f"ONET={args.onet}",
    "DUPLICATEPOINTS=merge",
], check=True)
```

### Step 4: Cleanup

- If `--work-dir` was auto-created: `shutil.rmtree(work_dir)`
- If `--work-dir` was user-specified: keep files, print path

## Error Handling

| Scenario | Behavior |
|---|---|
| cnetsplit fails | Exit immediately, clean tempdir, return code 1 |
| Worker subprocess fails | Collect all completed results, print failed chunk index, return code 2 |
| cnetmerge fails | Preserve work-dir for debugging, return code 3 |
| All succeed | Clean tempdir (if auto), return code 0 |

## Progress Output

Per-worker completion:
```
[parallel_pointreg_dom] worker 3/8 done (chunk_003.net -> result_003.net) exit=0
```

Final summary:
```
[parallel_pointreg_dom] 8/8 workers succeeded in 312.4s
[parallel_pointreg_dom] merging 8 result chunks -> output.net
[parallel_pointreg_dom] done. total_time=328.1s
```

## File Header

```python
#!/usr/bin/env python3
"""Parallel DOM-space point registration for ISIS ControlNets.

Splits a large ControlNet with cnetsplit, dispatches N parallel
pointreg_dom workers via subprocess, then merges results with cnetmerge.

Author: Geng Xun
Created: 2026-07-02
Updated: 2026-07-02  Geng Xun added parallel orchestration for DOM-space
    point registration using cnetsplit, subprocess workers, and cnetmerge.
"""
```

## Out of Scope

- Modifying `pointreg_dom.py` in any way.
- Thread-level or shared-memory parallelism.
- GPU acceleration of the registration step.
- Progress bars or GUI.
