import io
import unittest

from scripts.filter_controlnet_by_images import (
    filter_controlnet_pvl_stream,
    image_id_from_path,
)


class FilterControlNetByImagesUnitTest(unittest.TestCase):
    def test_image_id_from_path_normalizes_reduced_lroc_names(self):
        self.assertEqual(
            image_id_from_path("/tmp/REDUCED_M1108984529RE.echo.cal.cub"),
            "REDUCED_M1108984529RE.echo.cal.cub",
        )

    def test_filter_removes_whole_control_point_with_removed_serial(self):
        pvl = """Object = ControlNetwork
  Object = ControlPoint
    PointId = keep
    Group = ControlMeasure
      SerialNumber = LRO/1/111:222/NACL
    End_Group
    Group = ControlMeasure
      SerialNumber = LRO/1/333:444/NACR
    End_Group
  End_Object

  Object = ControlPoint
    PointId = drop
    Group = ControlMeasure
      SerialNumber = LRO/1/999:888/NACR
    End_Group
    Group = ControlMeasure
      SerialNumber = LRO/1/111:222/NACL
    End_Group
  End_Object
End_Object
"""
        output = io.StringIO()

        summary = filter_controlnet_pvl_stream(
            io.StringIO(pvl),
            output,
            removed_serials={"LRO/1/999:888/NACR"},
        )

        filtered = output.getvalue()
        self.assertIn("PointId = keep", filtered)
        self.assertNotIn("PointId = drop", filtered)
        self.assertEqual(summary.total_points, 2)
        self.assertEqual(summary.removed_points, 1)
        self.assertEqual(summary.kept_points, 1)
        self.assertEqual(summary.matched_removed_serials, {"LRO/1/999:888/NACR"})


if __name__ == "__main__":
    unittest.main()
