import unittest

from scripts.pointreg_dom import (
    DomPoint,
    ImagePair,
    PointregDomFailure,
    normalize_isis_style_args,
    validate_paired_image_lists,
    register_control_point_in_dom_space,
)


class FakeMeasure:
    def __init__(self, serial, sample, line):
        self.serial = serial
        self.sample = sample
        self.line = line
        self.updated = None
        self.measure_type = None
        self.chooser = None

    def get_cube_serial_number(self):
        return self.serial

    def get_sample(self):
        return self.sample

    def get_line(self):
        return self.line

    def set_apriori_sample(self, value):
        self.apriori_sample = value

    def set_apriori_line(self, value):
        self.apriori_line = value

    def set_coordinate(self, sample, line):
        self.updated = (sample, line)
        self.sample = sample
        self.line = line

    def set_type(self, measure_type):
        self.measure_type = measure_type

    def set_chooser_name(self, chooser):
        self.chooser = chooser


class FakePoint:
    def __init__(self, measures, ref_index=0):
        self.measures = measures
        self.ref_index = ref_index

    def get_id(self):
        return "P1"

    def get_num_measures(self):
        return len(self.measures)

    def get_measure(self, index):
        return self.measures[index]

    def has_ref_measure(self):
        return True

    def index_of_ref_measure(self):
        return self.ref_index


class PointregDomUnitTest(unittest.TestCase):
    def test_normalize_isis_style_args_accepts_pointreg_like_tokens(self):
        self.assertEqual(
            normalize_isis_style_args(
                [
                    "fromlist=original.lis",
                    "domlist=dom.lis",
                    "cnet=input.net",
                    "deffile=template.def",
                    "onet=output.net",
                    "--pvl",
                ]
            ),
            [
                "--fromlist",
                "original.lis",
                "--domlist",
                "dom.lis",
                "--cnet",
                "input.net",
                "--deffile",
                "template.def",
                "--onet",
                "output.net",
                "--pvl",
            ],
        )

    def test_validate_paired_image_lists_requires_matching_counts_and_serials(self):
        original_images = ["A.cub", "B.cub"]
        dom_images = ["dom_A.cub", "dom_B.cub"]

        pairs = validate_paired_image_lists(
            original_images,
            dom_images,
            serial_resolver=lambda path: {"A.cub": "SN-A", "dom_A.cub": "SN-A", "B.cub": "SN-B", "dom_B.cub": "SN-B"}[path],
        )

        self.assertEqual(list(pairs), ["SN-A", "SN-B"])
        self.assertEqual(pairs["SN-A"].original_path, "A.cub")
        self.assertEqual(pairs["SN-A"].dom_path, "dom_A.cub")

    def test_validate_paired_image_lists_rejects_serial_mismatch(self):
        with self.assertRaisesRegex(ValueError, "serial mismatch"):
            validate_paired_image_lists(
                ["A.cub"],
                ["dom_A.cub"],
                serial_resolver=lambda path: {"A.cub": "SN-A", "dom_A.cub": "SN-X"}[path],
            )

    def test_register_control_point_projects_matches_and_updates_candidate_measure(self):
        ref = FakeMeasure("SN-A", 10.0, 20.0)
        candidate = FakeMeasure("SN-B", 30.0, 40.0)
        point = FakePoint([ref, candidate])
        pairs = {
            "SN-A": ImagePair("A.cub", "dom_A.cub", "SN-A"),
            "SN-B": ImagePair("B.cub", "dom_B.cub", "SN-B"),
        }

        def original_to_dom(pair, sample, line):
            return DomPoint(sample + 100.0, line + 200.0)

        def dom_to_original(pair, sample, line):
            return sample - 10.0, line - 20.0

        def match_dom(ref_pair, cand_pair, ref_dom_point, cand_dom_guess):
            self.assertEqual(ref_dom_point, DomPoint(110.0, 220.0))
            self.assertEqual(cand_dom_guess, DomPoint(130.0, 240.0))
            return DomPoint(131.5, 242.5)

        summary = register_control_point_in_dom_space(
            point,
            pairs,
            original_to_dom=original_to_dom,
            dom_to_original=dom_to_original,
            match_dom=match_dom,
            registered_measure_type="RegisteredSubPixel",
        )

        self.assertEqual(summary.updated_measures, 1)
        self.assertEqual(candidate.updated, (121.5, 222.5))
        self.assertEqual(candidate.apriori_sample, 30.0)
        self.assertEqual(candidate.apriori_line, 40.0)
        self.assertEqual(candidate.measure_type, "RegisteredSubPixel")
        self.assertEqual(candidate.chooser, "pointreg_dom")

    def test_register_control_point_records_failure_when_projection_fails(self):
        point = FakePoint([FakeMeasure("SN-A", 10.0, 20.0), FakeMeasure("SN-B", 30.0, 40.0)])
        pairs = {
            "SN-A": ImagePair("A.cub", "dom_A.cub", "SN-A"),
            "SN-B": ImagePair("B.cub", "dom_B.cub", "SN-B"),
        }

        def original_to_dom(pair, sample, line):
            if pair.serial == "SN-B":
                raise PointregDomFailure("candidate_projection_failed")
            return DomPoint(sample, line)

        summary = register_control_point_in_dom_space(
            point,
            pairs,
            original_to_dom=original_to_dom,
            dom_to_original=lambda pair, sample, line: (sample, line),
            match_dom=lambda *_args: DomPoint(1.0, 1.0),
            registered_measure_type="RegisteredSubPixel",
        )

        self.assertEqual(summary.updated_measures, 0)
        self.assertEqual(summary.failed_measures, 1)
        self.assertEqual(summary.failure_reasons["candidate_projection_failed"], 1)

    def test_register_control_point_converts_unexpected_projection_exception_to_failure(self):
        point = FakePoint([FakeMeasure("SN-A", 10.0, 20.0), FakeMeasure("SN-B", 30.0, 40.0)])
        pairs = {
            "SN-A": ImagePair("A.cub", "dom_A.cub", "SN-A"),
            "SN-B": ImagePair("B.cub", "dom_B.cub", "SN-B"),
        }

        def original_to_dom(pair, sample, line):
            if pair.serial == "SN-B":
                raise RuntimeError("camera init failed")
            return DomPoint(sample, line)

        summary = register_control_point_in_dom_space(
            point,
            pairs,
            original_to_dom=original_to_dom,
            dom_to_original=lambda pair, sample, line: (sample, line),
            match_dom=lambda *_args: DomPoint(1.0, 1.0),
            registered_measure_type="RegisteredSubPixel",
        )

        self.assertEqual(summary.updated_measures, 0)
        self.assertEqual(summary.failed_measures, 1)
        self.assertEqual(summary.failure_reasons["candidate_processing_exception"], 1)


if __name__ == "__main__":
    unittest.main()
