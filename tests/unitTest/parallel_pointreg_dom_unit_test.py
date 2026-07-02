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
