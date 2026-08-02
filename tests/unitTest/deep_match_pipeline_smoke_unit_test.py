"""Smoke-style tests for deep-match pipeline docs and wrapper summaries.

Author: Geng Xun
Created: 2026-05-20
Last Modified: 2026-08-02
Updated: 2026-05-20  Geng Xun added stage-8 smoke coverage for deep-match mode documentation and import-summary wrapper structure.
Updated: 2026-06-18  Geng Xun skipped shell wrapper execution when only WSL bash is available on Windows.
Updated: 2026-08-02  Geng Xun restored Chinese README coverage for the recommended deep-match workflows.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
import unittest


UNIT_TEST_DIR = Path(__file__).resolve().parent
if str(UNIT_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_DIR))

from _unit_test_support import temporary_directory, write_synthetic_stereo_lists


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_image_match_batch_example.sh"
PRESETS_README_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "PRESETS_README.md"
README_ZH_PATH = PROJECT_ROOT / "README.zh-CN.md"


def _require_native_bash_for_windows_paths(test_case: unittest.TestCase) -> None:
    bash_path = shutil.which("bash")
    if bash_path is None:
        test_case.skipTest("bash is unavailable in PATH.")
    if os.name == "nt" and Path(bash_path).resolve().as_posix().lower().endswith("/windows/system32/bash.exe"):
        test_case.skipTest("WSL bash cannot execute this native Windows-path shell wrapper test.")


def _embedded_python_script(source: str) -> str:
    lines = source.splitlines()
    normalized = [line[20:] if line.startswith(" " * 20) else line for line in lines]
    return "\n".join(normalized).lstrip() + "\n"


class DeepMatchPipelineSmokeUnitTest(unittest.TestCase):
    def test_presets_readme_documents_modes_and_support_table(self):
        content = PRESETS_README_PATH.read_text(encoding="utf-8")

        self.assertIn("direct", content)
        self.assertIn("export", content)
        self.assertIn("import", content)
        for column in (
            "preset file",
            "matcher",
            "extractor",
            "runtime support",
            "required environment",
            "known limitations",
        ):
            self.assertIn(column, content.lower())
        self.assertIn("lightglue_default.json", content)
        self.assertIn("loftr_default.json", content)

    def test_readme_zh_documents_recommended_deep_match_workflows(self):
        content = README_ZH_PATH.read_text(encoding="utf-8")

        self.assertIn("direct / export / import", content)
        self.assertIn("run_deep_match_manifest.py", content)
        self.assertIn("deep_match_manifests.json", content)
        self.assertIn("PRESETS_README.md", content)

    def test_batch_wrapper_import_mode_writes_manifest_summary_structure(self):
        _require_native_bash_for_windows_paths(self)
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            manifest_dir = temp_dir / "imported_manifests"
            work_dir.mkdir()
            manifest_dir.mkdir()

            write_synthetic_stereo_lists(work_dir / "original_images.lis", work_dir / "doms.lis", work_dir / "inputs")
            (work_dir / "images_overlap.lis").write_text("left.cub,right.cub\n", encoding="utf-8")

            pair_manifest_dir = manifest_dir / "left__right"
            pair_manifest_dir.mkdir()
            (pair_manifest_dir / "tasks.json").write_text("{\"tasks\": []}\n", encoding="utf-8")

            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            fake_python_dispatcher.write_text(
                _embedded_python_script(
                    f"""
                    #!{sys.executable}
                    import json
                    import sys
                    from pathlib import Path

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ['-'] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]
                        if script_name == "image_match.py":
                            if "--deep-match-mode" not in args:
                                raise SystemExit("missing --deep-match-mode forwarding")
                            mode = args[args.index("--deep-match-mode") + 1]
                            if mode != "import":
                                raise SystemExit(f"unexpected deep-match mode: {{mode}}")
                            manifest_path = Path(args[args.index("--deep-match-manifest") + 1])
                            if manifest_path.name != "tasks.json":
                                raise SystemExit(f"unexpected deep-match manifest path: {{manifest_path}}")
                            metadata_path = Path(args[args.index("--metadata-output") + 1])
                            metadata_path.parent.mkdir(parents=True, exist_ok=True)
                            metadata_path.write_text(
                                json.dumps(
                                    {{
                                        "status": "matched",
                                        "point_count": 12,
                                        "deep_match_import": {{
                                            "manifest_path": str(manifest_path),
                                            "workspace_root": str(manifest_path.parent),
                                            "results_dir": str(manifest_path.parent / "results"),
                                            "logs_dir": str(manifest_path.parent / "logs"),
                                            "pair_id": "left__right",
                                            "imported_task_count": 1,
                                            "missing_result_count": 0,
                                            "failed_task_count": 0,
                                        }},
                                    }}
                                ),
                                encoding="utf-8",
                            )
                            Path(args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0
                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ),
                encoding="utf-8",
            )
            fake_python.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    exec {sys.executable} "{fake_python_dispatcher}" "$@"
                    """
                ).lstrip()
                + "\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(RUN_IMAGE_MATCH_BATCH_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--python",
                    str(fake_python),
                    "--matcher-method",
                    "lightglue",
                    "--deep-match-mode",
                    "import",
                    "--deep-match-manifest-dir",
                    str(manifest_dir),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary = json.loads((work_dir / "deep_match_manifests.json").read_text(encoding="utf-8"))

        self.assertIn("Deep-match mode: import", completed.stdout)
        self.assertEqual(summary["deep_match_mode"], "import")
        self.assertEqual(summary["deep_match_manifest_dir"], str(manifest_dir))
        self.assertEqual(summary["pairs"][0]["pair_tag"], "left__right")
        self.assertEqual(summary["pairs"][0]["imported_task_count"], 1)
        self.assertEqual(summary["pairs"][0]["missing_result_count"], 0)
        self.assertEqual(summary["pairs"][0]["failed_task_count"], 0)


if __name__ == "__main__":
    unittest.main()
