# Parallel Pointreg DOM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add process-level parallelism to DOM-space point registration by splitting a large ControlNet with cnetsplit, dispatching N parallel pointreg_dom workers, and merging results with cnetmerge.

**Architecture:** A new standalone script `scripts/parallel_pointreg_dom.py` orchestrates split-dispatch-merge. It does not import from `pointreg_dom.py` — each worker is a subprocess.run call. Uses concurrent.futures.ProcessPoolExecutor for parallel dispatch.

**Tech Stack:** Python 3.10+, subprocess, concurrent.futures, tempfile, shutil, argparse. ISIS executables: cnetsplit, cnetmerge.

## Global Constraints

- Do not modify `scripts/pointreg_dom.py`.
- Author: Geng Xun. Created: 2026-07-02.
- `--num-processes` defaults to 1 (serial fallback).
- Auto-created temp dirs are cleaned up; user-specified `--work-dir` is preserved.
- Error codes: 0 = success, 1 = cnetsplit failed, 2 = worker failed, 3 = cnetmerge failed.

---

## File Structure

```
scripts/
  pointreg_dom.py                    (untouched)
  parallel_pointreg_dom.py           (new file - all implementation)

tests/unitTest/
  parallel_pointreg_dom_unit_test.py (new file - all tests)
```

---

### Task 1: CLI Argument Parsing

**Files:**
- Create: `scripts/parallel_pointreg_dom.py`
- Test: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

**Interfaces:**
- Produces: `build_argument_parser() -> argparse.ArgumentParser`
- Produces: `normalize_isis_style_args(argv: list[str]) -> list[str]`

- [ ] **Step 1: Write the failing test for argument parsing**

```python
# tests/unitTest/parallel_pointreg_dom_unit_test.py
import unittest
from pathlib import Path


class ParallelPointregDomUnitTest(unittest.TestCase):

    def test_build_argument_parser_requires_core_args(self):
        from scripts.parallel_pointreg_dom import build_argument_parser
        parser = build_argument_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_build_argument_parser_accepts_full_args(self):
        from scripts.parallel_pointreg_dom import build_argument_parser
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis",
            "--domlist", "dom.lis",
            "--cnet", "input.net",
            "--deffile", "template.pvl",
            "--onet", "output.net",
            "--num-processes", "8",
            "--work-dir", "/tmp/work",
            "--cnetsplit", "/usr/bin/cnetsplit",
            "--cnetmerge", "/usr/bin/cnetmerge",
            "--dom-band", "2",
            "--original-band", "3",
            "--max-open-cubes", "128",
            "--skip-serial-check",
            "--pvl",
        ])
        self.assertEqual(args.fromlist, "ori.lis")
        self.assertEqual(args.domlist, "dom.lis")
        self.assertEqual(args.cnet, "input.net")
        self.assertEqual(args.deffile, "template.pvl")
        self.assertEqual(args.onet, "output.net")
        self.assertEqual(args.num_processes, 8)
        self.assertEqual(args.work_dir, "/tmp/work")
        self.assertEqual(args.cnetsplit, "/usr/bin/cnetsplit")
        self.assertEqual(args.cnetmerge, "/usr/bin/cnetmerge")
        self.assertEqual(args.dom_band, 2)
        self.assertEqual(args.original_band, 3)
        self.assertEqual(args.max_open_cubes, 128)
        self.assertTrue(args.skip_serial_check)
        self.assertTrue(args.pvl)

    def test_num_processes_defaults_to_one(self):
        from scripts.parallel_pointreg_dom import build_argument_parser
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis",
            "--domlist", "dom.lis",
            "--cnet", "input.net",
            "--deffile", "template.pvl",
            "--onet", "output.net",
        ])
        self.assertEqual(args.num_processes, 1)

    def test_normalize_isis_style_args_converts_equals_syntax(self):
        from scripts.parallel_pointreg_dom import normalize_isis_style_args
        result = normalize_isis_style_args([
            "fromlist=original.lis",
            "cnet=input.net",
            "--pvl",
        ])
        self.assertEqual(result, [
            "--fromlist", "original.lis",
            "--cnet", "input.net",
            "--pvl",
        ])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement CLI parsing**

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

from __future__ import annotations

import argparse
import sys


def normalize_isis_style_args(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in argv:
        if token.startswith("--") or "=" not in token:
            normalized.append(token)
            continue
        key, value = token.split("=", 1)
        normalized.extend([f"--{key.strip().lower()}", value])
    return normalized


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parallel DOM-space point registration for ISIS ControlNets.",
    )
    parser.add_argument("--fromlist", required=True, help="Original-image cube list.")
    parser.add_argument("--domlist", required=True, help="DOM cube list aligned one-to-one with --fromlist.")
    parser.add_argument("--cnet", required=True, help="Input ISIS control network.")
    parser.add_argument("--deffile", required=True, help="ISIS AutoReg/pointreg registration template PVL.")
    parser.add_argument("--onet", required=True, help="Output ISIS control network.")
    parser.add_argument("--num-processes", type=int, default=1, help="Number of parallel worker processes. Default: 1.")
    parser.add_argument("--work-dir", default=None, help="Working directory for chunk files. Default: auto temp dir.")
    parser.add_argument("--cnetsplit", default="cnetsplit", help="Path to cnetsplit executable. Default: cnetsplit.")
    parser.add_argument("--cnetmerge", default="cnetmerge", help="Path to cnetmerge executable. Default: cnetmerge.")
    parser.add_argument("--dom-band", type=int, default=1, help="Band used for DOM projection and matching.")
    parser.add_argument("--original-band", type=int, default=1, help="Band used for original-image camera projection.")
    parser.add_argument("--max-open-cubes", type=int, default=64, help="Maximum number of ISIS cubes kept open at once.")
    parser.add_argument("--skip-serial-check", action="store_true", help="Allow original/DOM list rows with different serial numbers.")
    parser.add_argument("--pvl", action="store_true", help="Write output ControlNet in PVL text format.")
    return parser
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "feat: add parallel_pointreg_dom CLI argument parsing"
```

---

### Task 2: Worker Command Builder

**Files:**
- Modify: `scripts/parallel_pointreg_dom.py`
- Modify: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

**Interfaces:**
- Consumes: argparse.Namespace from Task 1
- Produces: `build_worker_command(python_executable: str, script_path: str, chunk_cnet: str, result_onet: str, args: argparse.Namespace) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
    def test_build_worker_command_includes_all_forwarded_args(self):
        from scripts.parallel_pointreg_dom import build_worker_command, build_argument_parser
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "template.pvl",
            "--onet", "output.net", "--dom-band", "2",
            "--original-band", "3", "--max-open-cubes", "128",
            "--skip-serial-check", "--pvl",
        ])
        cmd = build_worker_command("python3", "/repo/scripts/pointreg_dom.py",
                                   "/tmp/chunk_001.net", "/tmp/result_001.net", args)
        self.assertEqual(cmd[0], "python3")
        self.assertEqual(cmd[1], "/repo/scripts/pointreg_dom.py")
        self.assertIn("--cnet", cmd)
        self.assertIn("/tmp/chunk_001.net", cmd)
        self.assertIn("--onet", cmd)
        self.assertIn("/tmp/result_001.net", cmd)
        self.assertIn("--fromlist", cmd)
        self.assertIn("ori.lis", cmd)
        self.assertIn("--domlist", cmd)
        self.assertIn("dom.lis", cmd)
        self.assertIn("--deffile", cmd)
        self.assertIn("template.pvl", cmd)
        self.assertIn("--dom-band", cmd)
        self.assertIn("2", cmd)
        self.assertIn("--original-band", cmd)
        self.assertIn("3", cmd)
        self.assertIn("--max-open-cubes", cmd)
        self.assertIn("128", cmd)
        self.assertIn("--skip-serial-check", cmd)
        self.assertIn("--pvl", cmd)

    def test_build_worker_command_omits_false_flags(self):
        from scripts.parallel_pointreg_dom import build_worker_command, build_argument_parser
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "template.pvl",
            "--onet", "output.net",
        ])
        cmd = build_worker_command("python3", "pointreg_dom.py", "/c.net", "/o.net", args)
        self.assertNotIn("--skip-serial-check", cmd)
        self.assertNotIn("--pvl", cmd)

    def test_build_worker_command_overrides_cnet_and_onet(self):
        from scripts.parallel_pointreg_dom import build_worker_command, build_argument_parser
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "ORIGINAL_INPUT.net", "--deffile", "template.pvl",
            "--onet", "ORIGINAL_OUTPUT.net",
        ])
        cmd = build_worker_command("python3", "pointreg_dom.py", "/chunk.net", "/result.net", args)
        cnet_index = cmd.index("--cnet")
        onet_index = cmd.index("--onet")
        self.assertEqual(cmd[cnet_index + 1], "/chunk.net")
        self.assertEqual(cmd[onet_index + 1], "/result.net")
        self.assertNotIn("ORIGINAL_INPUT.net", cmd)
        self.assertNotIn("ORIGINAL_OUTPUT.net", cmd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -k "test_build_worker_command_includes" -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement build_worker_command**

Add to `scripts/parallel_pointreg_dom.py` after `build_argument_parser`:

```python
def build_worker_command(
    python_executable: str,
    script_path: str,
    chunk_cnet: str,
    result_onet: str,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        python_executable,
        script_path,
        "--fromlist", args.fromlist,
        "--domlist", args.domlist,
        "--cnet", chunk_cnet,
        "--deffile", args.deffile,
        "--onet", result_onet,
        "--dom-band", str(args.dom_band),
        "--original-band", str(args.original_band),
        "--max-open-cubes", str(args.max_open_cubes),
    ]
    if args.skip_serial_check:
        cmd.append("--skip-serial-check")
    if args.pvl:
        cmd.append("--pvl")
    return cmd
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "feat: add worker command builder for parallel pointreg_dom"
```

---

### Task 3: Chunk Discovery

**Files:**
- Modify: `scripts/parallel_pointreg_dom.py`
- Modify: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

**Interfaces:**
- Produces: `discover_chunk_files(work_dir: str, prefix: str = "chunk") -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
    def test_discover_chunk_files_finds_net_files_sorted(self):
        import tempfile, os
        from scripts.parallel_pointreg_dom import discover_chunk_files
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["chunk_003.net", "chunk_001.net", "chunk_002.net"]:
                Path(os.path.join(tmpdir, name)).touch()
            Path(os.path.join(tmpdir, "results.lis")).touch()
            result = discover_chunk_files(tmpdir)
            self.assertEqual(len(result), 3)
            self.assertTrue(result[0].endswith("chunk_001.net"))
            self.assertTrue(result[1].endswith("chunk_002.net"))
            self.assertTrue(result[2].endswith("chunk_003.net"))

    def test_discover_chunk_files_raises_on_empty(self):
        import tempfile
        from scripts.parallel_pointreg_dom import discover_chunk_files
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                discover_chunk_files(tmpdir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -k "discover_chunk" -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement discover_chunk_files**

Add imports at top of `scripts/parallel_pointreg_dom.py`:

```python
from pathlib import Path
```

Add function:

```python
def discover_chunk_files(work_dir: str, prefix: str = "chunk") -> list[str]:
    chunks = sorted(str(p) for p in Path(work_dir).glob(f"{prefix}*.net"))
    if not chunks:
        raise FileNotFoundError(
            f"No chunk files found matching '{prefix}*.net' in {work_dir}. "
            f"cnetsplit may have failed."
        )
    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "feat: add chunk file discovery for parallel pointreg_dom"
```

---

### Task 4: Split, Dispatch, Merge Functions

**Files:**
- Modify: `scripts/parallel_pointreg_dom.py`
- Modify: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

**Interfaces:**
- Consumes: build_worker_command from Task 2, discover_chunk_files from Task 3
- Produces: `run_cnetsplit(cnetsplit_path: str, cnet: str, work_dir: str, num_output: int) -> None`
- Produces: `dispatch_workers(worker_commands: list[list[str]], num_processes: int) -> list[tuple[int, subprocess.CompletedProcess]]`
- Produces: `run_cnetmerge(cnetmerge_path: str, result_files: list[str], onet: str, work_dir: str) -> None`

- [ ] **Step 1: Write the failing tests**

```python
    def test_dispatch_workers_returns_exit_codes(self):
        from scripts.parallel_pointreg_dom import dispatch_workers
        commands = [
            ["python3", "-c", "import sys; sys.exit(0)"],
            ["python3", "-c", "import sys; sys.exit(0)"],
        ]
        results = dispatch_workers(commands, num_processes=2)
        self.assertEqual(len(results), 2)
        for index, completed in results:
            self.assertEqual(completed.returncode, 0)

    def test_dispatch_workers_reports_failure(self):
        from scripts.parallel_pointreg_dom import dispatch_workers
        commands = [
            ["python3", "-c", "import sys; sys.exit(0)"],
            ["python3", "-c", "import sys; sys.exit(1)"],
        ]
        results = dispatch_workers(commands, num_processes=2)
        exit_codes = [completed.returncode for _, completed in results]
        self.assertIn(1, exit_codes)

    def test_run_cnetmerge_writes_results_list(self):
        import tempfile
        from scripts.parallel_pointreg_dom import run_cnetmerge
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmpdir:
            result_files = ["/tmp/r1.net", "/tmp/r2.net"]
            with patch("scripts.parallel_pointreg_dom.subprocess.run") as mock_run:
                mock_run.return_value = None
                run_cnetmerge("cnetmerge", result_files, "/out.net", tmpdir)
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                self.assertEqual(call_args[0], "cnetmerge")
                self.assertIn("INPUTTYPE=list", call_args)
                self.assertIn("ONET=/out.net", call_args)
                self.assertIn("DUPLICATEPOINTS=merge", call_args)
                clist_arg = [a for a in call_args if a.startswith("CLIST=")][0]
                list_path = clist_arg.split("=", 1)[1]
                content = Path(list_path).read_text()
                self.assertIn("/tmp/r1.net", content)
                self.assertIn("/tmp/r2.net", content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -k "dispatch_workers or run_cnetmerge" -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement split, dispatch, and merge**

Add imports at top of `scripts/parallel_pointreg_dom.py`:

```python
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
```

Add functions:

```python
_LOG_PREFIX = "[parallel_pointreg_dom]"


def run_cnetsplit(cnetsplit_path: str, cnet: str, work_dir: str, num_output: int) -> None:
    subprocess.run(
        [
            cnetsplit_path,
            f"CNET={cnet}",
            f"ONET_PREFIX={str(Path(work_dir) / 'chunk')}",
            f"NUM_OUTPUT_FILES={num_output}",
        ],
        check=True,
    )


def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=False)


def dispatch_workers(
    worker_commands: list[list[str]],
    num_processes: int,
) -> list[tuple[int, subprocess.CompletedProcess]]:
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = {
            executor.submit(_run_subprocess, cmd): index
            for index, cmd in enumerate(worker_commands)
        }
        results = []
        for future in as_completed(futures):
            index = futures[future]
            results.append((index, future.result()))
    return sorted(results, key=lambda pair: pair[0])


def run_cnetmerge(
    cnetmerge_path: str,
    result_files: list[str],
    onet: str,
    work_dir: str,
) -> None:
    list_path = str(Path(work_dir) / "results.lis")
    Path(list_path).write_text("\n".join(result_files) + "\n", encoding="utf-8")
    subprocess.run(
        [
            cnetmerge_path,
            "INPUTTYPE=list",
            f"CLIST={list_path}",
            f"ONET={onet}",
            "DUPLICATEPOINTS=merge",
        ],
        check=True,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 12 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "feat: add cnetsplit, dispatch, and cnetmerge functions"
```

---

### Task 5: Main Orchestration with Error Handling

**Files:**
- Modify: `scripts/parallel_pointreg_dom.py`
- Modify: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

**Interfaces:**
- Consumes: all functions from Tasks 1-4
- Produces: `run_parallel_pointreg_dom(args: argparse.Namespace) -> int`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing tests for error codes**

```python
    def test_run_parallel_returns_1_on_cnetsplit_failure(self):
        from scripts.parallel_pointreg_dom import run_parallel_pointreg_dom, build_argument_parser
        from unittest.mock import patch
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "t.pvl",
            "--onet", "output.net", "--num-processes", "2",
        ])
        with patch("scripts.parallel_pointreg_dom.run_cnetsplit",
                    side_effect=subprocess.CalledProcessError(1, "cnetsplit")):
            exit_code = run_parallel_pointreg_dom(args)
        self.assertEqual(exit_code, 1)

    def test_run_parallel_returns_2_on_worker_failure(self):
        from scripts.parallel_pointreg_dom import run_parallel_pointreg_dom, build_argument_parser
        from unittest.mock import patch, MagicMock
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "t.pvl",
            "--onet", "output.net", "--num-processes", "2",
        ])
        failed_result = MagicMock()
        failed_result.returncode = 1
        ok_result = MagicMock()
        ok_result.returncode = 0
        with patch("scripts.parallel_pointreg_dom.run_cnetsplit"), \
             patch("scripts.parallel_pointreg_dom.discover_chunk_files",
                    return_value=["/tmp/c1.net", "/tmp/c2.net"]), \
             patch("scripts.parallel_pointreg_dom.dispatch_workers",
                    return_value=[(0, ok_result), (1, failed_result)]):
            exit_code = run_parallel_pointreg_dom(args)
        self.assertEqual(exit_code, 2)

    def test_run_parallel_returns_3_on_cnetmerge_failure(self):
        from scripts.parallel_pointreg_dom import run_parallel_pointreg_dom, build_argument_parser
        from unittest.mock import patch, MagicMock
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "t.pvl",
            "--onet", "output.net", "--num-processes", "2",
        ])
        ok_result = MagicMock()
        ok_result.returncode = 0
        with patch("scripts.parallel_pointreg_dom.run_cnetsplit"), \
             patch("scripts.parallel_pointreg_dom.discover_chunk_files",
                    return_value=["/tmp/c1.net", "/tmp/c2.net"]), \
             patch("scripts.parallel_pointreg_dom.dispatch_workers",
                    return_value=[(0, ok_result), (1, ok_result)]), \
             patch("scripts.parallel_pointreg_dom.run_cnetmerge",
                    side_effect=subprocess.CalledProcessError(1, "cnetmerge")):
            exit_code = run_parallel_pointreg_dom(args)
        self.assertEqual(exit_code, 3)

    def test_run_parallel_returns_0_on_success(self):
        from scripts.parallel_pointreg_dom import run_parallel_pointreg_dom, build_argument_parser
        from unittest.mock import patch, MagicMock
        parser = build_argument_parser()
        args = parser.parse_args([
            "--fromlist", "ori.lis", "--domlist", "dom.lis",
            "--cnet", "input.net", "--deffile", "t.pvl",
            "--onet", "output.net", "--num-processes", "2",
        ])
        ok_result = MagicMock()
        ok_result.returncode = 0
        with patch("scripts.parallel_pointreg_dom.run_cnetsplit"), \
             patch("scripts.parallel_pointreg_dom.discover_chunk_files",
                    return_value=["/tmp/c1.net", "/tmp/c2.net"]), \
             patch("scripts.parallel_pointreg_dom.dispatch_workers",
                    return_value=[(0, ok_result), (1, ok_result)]), \
             patch("scripts.parallel_pointreg_dom.run_cnetmerge"):
            exit_code = run_parallel_pointreg_dom(args)
        self.assertEqual(exit_code, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -k "run_parallel" -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement main orchestration**

Add to `scripts/parallel_pointreg_dom.py`:

```python
def run_parallel_pointreg_dom(args: argparse.Namespace) -> int:
    script_path = str(Path(__file__).resolve().parent / "pointreg_dom.py")
    python_executable = sys.executable

    auto_work_dir = args.work_dir is None
    work_dir = args.work_dir if args.work_dir else tempfile.mkdtemp(prefix="pointreg_dom_")
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()

    # Step 1: Split
    try:
        run_cnetsplit(args.cnetsplit, args.cnet, work_dir, args.num_processes)
    except subprocess.CalledProcessError:
        print(f"{_LOG_PREFIX} cnetsplit failed.", file=sys.stderr, flush=True)
        if auto_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
        return 1

    chunk_files = discover_chunk_files(work_dir)
    print(f"{_LOG_PREFIX} split into {len(chunk_files)} chunks.", file=sys.stderr, flush=True)

    # Step 2: Dispatch workers
    worker_commands = []
    result_files = []
    for index, chunk_path in enumerate(chunk_files):
        result_path = str(Path(work_dir) / f"result_{index:03d}.net")
        cmd = build_worker_command(python_executable, script_path, chunk_path, result_path, args)
        worker_commands.append(cmd)
        result_files.append(result_path)

    worker_results = dispatch_workers(worker_commands, args.num_processes)

    failed_workers = [(i, r) for i, r in worker_results if r.returncode != 0]
    succeeded = len(worker_results) - len(failed_workers)
    elapsed = time.monotonic() - start_time

    for index, completed in worker_results:
        status = "done" if completed.returncode == 0 else "FAILED"
        chunk_name = Path(chunk_files[index]).name
        result_name = Path(result_files[index]).name
        print(
            f"{_LOG_PREFIX} worker {index + 1}/{len(chunk_files)} {status} "
            f"({chunk_name} -> {result_name}) exit={completed.returncode}",
            file=sys.stderr,
            flush=True,
        )

    if failed_workers:
        print(
            f"{_LOG_PREFIX} {len(failed_workers)} worker(s) failed. "
            f"Work dir preserved: {work_dir}",
            file=sys.stderr,
            flush=True,
        )
        return 2

    print(
        f"{_LOG_PREFIX} {succeeded}/{len(chunk_files)} workers succeeded in {elapsed:.1f}s",
        file=sys.stderr,
        flush=True,
    )

    # Step 3: Merge
    print(
        f"{_LOG_PREFIX} merging {len(result_files)} result chunks -> {args.onet}",
        file=sys.stderr,
        flush=True,
    )
    try:
        run_cnetmerge(args.cnetmerge, result_files, args.onet, work_dir)
    except subprocess.CalledProcessError:
        print(
            f"{_LOG_PREFIX} cnetmerge failed. Work dir preserved: {work_dir}",
            file=sys.stderr,
            flush=True,
        )
        return 3

    total_time = time.monotonic() - start_time
    print(f"{_LOG_PREFIX} done. total_time={total_time:.1f}s", file=sys.stderr, flush=True)

    # Step 4: Cleanup
    if auto_work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)
    else:
        print(f"{_LOG_PREFIX} work dir preserved: {work_dir}", file=sys.stderr, flush=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(
        normalize_isis_style_args(argv or sys.argv[1:])
    )
    if args.num_processes <= 1:
        script_path = str(Path(__file__).resolve().parent / "pointreg_dom.py")
        forwarded = normalize_isis_style_args(argv or sys.argv[1:])
        cmd = [sys.executable, script_path] + [
            t for i, t in enumerate(forwarded)
            if not (t == "--num-processes"
                    or (i > 0 and forwarded[i - 1] == "--num-processes"))
        ]
        result = subprocess.run(cmd, check=False)
        return result.returncode
    return run_parallel_pointreg_dom(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 16 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "feat: add parallel orchestration with error handling for pointreg_dom"
```

---

### Task 6: Final Verification

**Files:**
- Verify: `scripts/parallel_pointreg_dom.py`
- Verify: `tests/unitTest/parallel_pointreg_dom_unit_test.py`

- [ ] **Step 1: Run full test suite**

Run: `cd /home/gengxun/code/pyisis && python -m pytest tests/unitTest/parallel_pointreg_dom_unit_test.py -v`
Expected: 16 PASS, 0 FAIL

- [ ] **Step 2: Verify --help output**

Run: `cd /home/gengxun/code/pyisis && python scripts/parallel_pointreg_dom.py --help`
Expected: All CLI arguments listed with descriptions.

- [ ] **Step 3: Verify no modifications to pointreg_dom.py**

Run: `cd /home/gengxun/code/pyisis && git diff scripts/pointreg_dom.py`
Expected: Empty output (no changes).

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add scripts/parallel_pointreg_dom.py tests/unitTest/parallel_pointreg_dom_unit_test.py
git commit -m "fix: final adjustments for parallel_pointreg_dom"
```
