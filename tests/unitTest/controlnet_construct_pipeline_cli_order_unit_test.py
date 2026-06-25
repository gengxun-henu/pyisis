"""Regression tests for run_pipeline_example image_match argument ordering.

Author: Geng Xun
Created: 2026-05-27
Last Modified: 2026-06-18
Updated: 2026-06-18  Geng Xun skipped shell wrapper execution when only WSL bash is available on Windows.
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
RUN_PIPELINE_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "controlnet_construct" / "run_pipeline_example.sh"


def _require_native_bash_for_windows_paths(test_case: unittest.TestCase) -> None:
    bash_path = shutil.which("bash")
    if bash_path is None:
        test_case.skipTest("bash is unavailable in PATH.")
    if os.name == "nt" and Path(bash_path).resolve().as_posix().lower().endswith("/windows/system32/bash.exe"):
        test_case.skipTest("WSL bash cannot execute this native Windows-path shell wrapper test.")


class ControlNetConstructPipelineCliOrderUnitTest(unittest.TestCase):
    def test_run_pipeline_example_keeps_image_match_positionals_before_compact_stdout_flags(self):
        _require_native_bash_for_windows_paths(self)
        with temporary_directory() as temp_dir:
            work_dir = temp_dir / "work"
            work_dir.mkdir()
            original_list = work_dir / "original_images.lis"
            dom_list = work_dir / "doms.lis"
            config_path = temp_dir / "controlnet_config.json"
            fake_python_dispatcher = temp_dir / "fake_python_dispatcher.py"
            fake_python = temp_dir / "fake_python"
            image_match_argv_path = temp_dir / "image_match_argv.json"

            write_synthetic_stereo_lists(original_list, dom_list, work_dir / "inputs")
            config_path.write_text(
                json.dumps(
                    {
                        "NetworkId": "order-net",
                        "TargetName": "Mars",
                        "UserName": "unit-test",
                        "PointIdPrefix": "TMP",
                    }
                ),
                encoding="utf-8",
            )

            fake_python_dispatcher.write_text(
                textwrap.dedent(
                    f"""
                    #!{sys.executable}
                    import json
                    import os
                    import sys
                    from pathlib import Path

                    VALUE_OPTIONS = {{
                        "--config",
                        "--metadata-output",
                        "--result-output",
                        "--match-visualization-output-dir",
                        "--invalid-pixel-radius",
                        "--matcher-method",
                        "--adaptive-routing-profile",
                        "--num-worker-parallel-cpu",
                    }}

                    def _run_stdin_python() -> int:
                        code = sys.stdin.read()
                        globals_dict = {{"__name__": "__main__", "__file__": "<stdin>"}}
                        sys.argv = ["-"] + sys.argv[2:]
                        exec(compile(code, "<stdin>", "exec"), globals_dict)
                        return 0

                    def _positionals(args: list[str]) -> list[str]:
                        values = []
                        index = 0
                        while index < len(args):
                            token = args[index]
                            if token in VALUE_OPTIONS:
                                index += 2
                                continue
                            if token.startswith("--"):
                                index += 1
                                continue
                            values.append(token)
                            index += 1
                        return values

                    def main() -> int:
                        if len(sys.argv) < 2:
                            return 0
                        if sys.argv[1] == "-":
                            return _run_stdin_python()

                        script_name = Path(sys.argv[1]).name
                        args = sys.argv[2:]

                        if script_name == "image_overlap.py":
                            report_json_path = Path(args[args.index("--report-json") + 1])
                            report_json_path.parent.mkdir(parents=True, exist_ok=True)
                            report_json_path.write_text(json.dumps({{"pair_count": 1, "image_count": 2}}), encoding="utf-8")
                            Path(args[1]).write_text("left.cub,right.cub\\n", encoding="utf-8")
                            return 0

                        if script_name == "image_match.py":
                            if "--print-config-default" in args:
                                print("")
                                return 0
                            Path({str(image_match_argv_path)!r}).write_text(json.dumps(args), encoding="utf-8")
                            result_output_path = Path(args[args.index("--result-output") + 1])
                            result_output_path.parent.mkdir(parents=True, exist_ok=True)
                            result_output_path.write_text(json.dumps({{"point_count": 1}}), encoding="utf-8")
                            metadata_path = Path(args[args.index("--metadata-output") + 1])
                            metadata_path.parent.mkdir(parents=True, exist_ok=True)
                            metadata_path.write_text(json.dumps({{"status": "matched"}}), encoding="utf-8")
                            positional_args = _positionals(args)
                            Path(positional_args[2]).write_text("synthetic-left-key\\n", encoding="utf-8")
                            Path(positional_args[3]).write_text("synthetic-right-key\\n", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_stereopair.py":
                            report_dir = Path(args[args.index("--report-dir") + 1])
                            report_dir.mkdir(parents=True, exist_ok=True)
                            (report_dir / "controlnet_batch_summary.json").write_text(
                                json.dumps({{"pair_count": 1, "total_final_control_point_count": 1, "total_dom2ori_retained_count": 1}}),
                                encoding="utf-8",
                            )
                            output_dir = Path(args[6])
                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "synthetic_pair.net").write_text("net", encoding="utf-8")
                            return 0

                        if script_name == "controlnet_merge.py":
                            report_json_path = Path(args[args.index("--report-json") + 1])
                            report_json_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path = Path(args[3])
                            merge_script_path.parent.mkdir(parents=True, exist_ok=True)
                            merge_script_path.write_text("#!/usr/bin/env bash\\nexit 0\\n", encoding="utf-8")
                            os.chmod(merge_script_path, 0o755)
                            report_json_path.write_text(json.dumps({{"included_count": 1, "skipped_missing_count": 0}}), encoding="utf-8")
                            return 0

                        raise SystemExit(f"Unhandled fake python script: {{script_name}}")

                    raise SystemExit(main())
                    """
                ).lstrip()
                + "\n",
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
                    str(RUN_PIPELINE_EXAMPLE_PATH),
                    "--work-dir",
                    str(work_dir),
                    "--config",
                    str(config_path),
                    "--python",
                    str(fake_python),
                    "--skip-final-merge",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            image_match_argv = json.loads(image_match_argv_path.read_text(encoding="utf-8"))
            self.assertEqual(image_match_argv[0:2], ["--config", str(config_path)])
            self.assertFalse(image_match_argv[2].startswith("--"), image_match_argv)
            self.assertEqual(image_match_argv[6], "--omit-tile-details")


if __name__ == "__main__":
    unittest.main()
