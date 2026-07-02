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
