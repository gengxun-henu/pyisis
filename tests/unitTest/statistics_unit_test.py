"""
Unit tests for ISIS statistics, histogram, and vector-filter bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-10
Updated: 2026-04-10  Geng Xun added PrincipalComponentAnalysis and OverlapStatistics unit tests.
"""

import unittest

from _unit_test_support import ip


class StatisticsUnitTest(unittest.TestCase):
    def test_statistics_basic_accumulation_and_reset(self):
        stats = ip.Statistics()
        stats.add_data([1.0, 2.0, 3.0, 4.0])

        self.assertEqual(stats.total_pixels(), 4)
        self.assertEqual(stats.valid_pixels(), 4)
        self.assertAlmostEqual(stats.average(), 2.5, places=12)
        self.assertAlmostEqual(stats.sum(), 10.0, places=12)
        self.assertAlmostEqual(stats.minimum(), 1.0, places=12)
        self.assertAlmostEqual(stats.maximum(), 4.0, places=12)
        self.assertIn("Statistics(valid_pixels=4", repr(stats))

        stats.reset()
        self.assertEqual(stats.total_pixels(), 0)

    def test_statistics_valid_range_and_remove_data(self):
        stats = ip.Statistics()
        stats.set_valid_range(0.0, 10.0)
        stats.add_data([-1.0, 1.0, 2.0, 11.0])

        self.assertEqual(stats.valid_pixels(), 2)
        self.assertEqual(stats.total_pixels(), 4)
        self.assertTrue(stats.in_range(5.0))
        self.assertTrue(stats.below_range(-1.0))
        self.assertTrue(stats.above_range(11.0))
        self.assertEqual(stats.under_range_pixels(), 1)
        self.assertEqual(stats.over_range_pixels(), 1)

        stats.remove_data(2.0)
        self.assertEqual(stats.valid_pixels(), 1)
        self.assertAlmostEqual(stats.average(), 1.0, places=12)

    def test_statistics_copy_and_pvl_export(self):
        stats = ip.Statistics()
        stats.add_data([1.0, 2.0, 3.0])

        copied = stats.copy()
        self.assertEqual(copied.valid_pixels(), 3)
        self.assertAlmostEqual(copied.average(), 2.0, places=12)

        pvl_group = stats.to_pvl("ExampleStatistics")
        self.assertEqual(pvl_group.name(), "ExampleStatistics")
        self.assertTrue(pvl_group.has_keyword("Average"))

    def test_histogram_basic_operations(self):
        histogram = ip.Histogram(0.0, 10.0, 5)
        histogram.add_data([0.5, 1.5, 2.5, 9.5])

        self.assertEqual(histogram.bins(), 5)
        self.assertEqual(histogram.valid_pixels(), 4)
        self.assertEqual(histogram.bin_count(0), 2)
        low, high = histogram.bin_range(0)
        self.assertLessEqual(low, 0.5)
        self.assertGreaterEqual(high, 1.5)
        self.assertGreater(histogram.bin_size(), 0.0)
        self.assertGreaterEqual(histogram.max_bin_count(), 1)

    def test_histogram_distribution_queries(self):
        histogram = ip.Histogram(0.0, 4.0, 4)
        histogram.add_data([0.25, 1.25, 2.25, 3.25])

        self.assertAlmostEqual(histogram.median(), 1.5, places=12)
        self.assertAlmostEqual(histogram.percent(50.0), histogram.median(), places=12)
        self.assertIsInstance(histogram.mode(), float)
        self.assertIsInstance(histogram.skew(), float)

    def test_gaussian_distribution(self):
        distribution = ip.GaussianDistribution(0.0, 1.0)
        self.assertAlmostEqual(distribution.mean(), 0.0, places=12)
        self.assertAlmostEqual(distribution.distribution_standard_deviation(), 1.0, places=12)
        self.assertGreater(distribution.probability(0.0), 0.0)
        self.assertAlmostEqual(distribution.cumulative_distribution(0.0), 50.0, places=6)
        self.assertAlmostEqual(distribution.inverse_cumulative_distribution(50.0), 0.0, places=6)

    def test_grouped_statistics(self):
        grouped = ip.GroupedStatistics()
        grouped.add_statistic("residual", 1.0)
        grouped.add_statistic("residual", 3.0)
        grouped.add_statistic("magnitude", 5.0)

        self.assertIn("residual", grouped.get_statistic_types())
        self.assertIn("magnitude", grouped.get_statistic_types())
        self.assertEqual(grouped.get_statistics("residual").valid_pixels(), 2)
        self.assertAlmostEqual(grouped.get_statistics("residual").average(), 2.0, places=12)

    def test_multivariate_statistics(self):
        multi = ip.MultivariateStatistics()
        multi.add_data([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])

        self.assertEqual(multi.valid_pixels(), 3)
        self.assertEqual(multi.total_pixels(), 3)
        self.assertGreater(multi.correlation(), 0.99)
        self.assertGreater(multi.covariance(), 0.0)
        intercept, slope = multi.linear_regression()
        self.assertAlmostEqual(intercept, 0.0, places=10)
        self.assertAlmostEqual(slope, 2.0, places=10)
        self.assertEqual(multi.x_statistics().valid_pixels(), 3)
        self.assertEqual(multi.y_statistics().valid_pixels(), 3)

    def test_multivariate_statistics_requires_matching_lengths(self):
        multi = ip.MultivariateStatistics()
        with self.assertRaises(ValueError):
            multi.add_data([1.0, 2.0], [1.0])

    def test_vec_filter(self):
        vec_filter = ip.VecFilter()
        low_pass = vec_filter.low_pass([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(len(low_pass), 5)

        high_pass = vec_filter.high_pass([3.0, 4.0, 5.0], [1.0, 1.0, 1.0])
        self.assertEqual(high_pass, [2.0, 3.0, 4.0])


class PrincipalComponentAnalysisUnitTest(unittest.TestCase):
    """Focused unit tests for PrincipalComponentAnalysis binding. Added: 2026-04-10."""

    def test_construction_with_n(self):
        """PCA constructs with dimension count."""
        pca = ip.PrincipalComponentAnalysis(3)
        self.assertIsInstance(pca, ip.PrincipalComponentAnalysis)
        self.assertEqual(pca.dimensions(), 3)

    def test_repr(self):
        """repr includes class name and dimensions."""
        pca = ip.PrincipalComponentAnalysis(2)
        r = repr(pca)
        self.assertIn("PrincipalComponentAnalysis", r)
        self.assertIn("2", r)

    def test_add_data_and_compute(self):
        """add_data + compute_transform produces a non-empty transform matrix."""
        pca = ip.PrincipalComponentAnalysis(2)
        # Two-dimensional data: unit circle samples
        import math
        for i in range(36):
            angle = i * 10.0 * math.pi / 180.0
            pca.add_data([math.cos(angle), math.sin(angle)])
        pca.compute_transform()
        mat = pca.transform_matrix()
        self.assertIsInstance(mat, list)
        self.assertGreater(len(mat), 0)
        self.assertGreater(len(mat[0]), 0)

    def test_transform_roundtrip(self):
        """forward transform followed by inverse returns approximately original data."""
        pca = ip.PrincipalComponentAnalysis(2)
        import math
        observations = [[math.cos(i * 0.1), math.sin(i * 0.1)] for i in range(20)]
        for obs in observations:
            pca.add_data(obs)
        pca.compute_transform()
        row = observations[0]
        forward = pca.transform([[row[0], row[1]]])
        recovered = pca.inverse(forward)
        self.assertAlmostEqual(recovered[0][0], row[0], places=8)
        self.assertAlmostEqual(recovered[0][1], row[1], places=8)

    def test_construct_from_transform_matrix(self):
        """Constructor with precomputed identity-like matrix is accepted."""
        identity = [[1.0, 0.0], [0.0, 1.0]]
        pca = ip.PrincipalComponentAnalysis(identity)
        self.assertIsInstance(pca, ip.PrincipalComponentAnalysis)

    def test_invalid_add_data_size_raises(self):
        """add_data with wrong dimension count raises."""
        pca = ip.PrincipalComponentAnalysis(3)
        with self.assertRaises(Exception):
            pca.add_data([1.0, 2.0])  # too few dimensions


class OverlapStatisticsUnitTest(unittest.TestCase):
    """Focused unit tests for OverlapStatistics binding. Added: 2026-04-10."""

    def test_class_is_exported(self):
        """OverlapStatistics is accessible as an isis_pybind symbol."""
        self.assertTrue(hasattr(ip, "OverlapStatistics"))

    def test_expected_api_surface(self):
        """OverlapStatistics exposes the expected method names."""
        self.assertTrue(hasattr(ip.OverlapStatistics, "has_overlap"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "has_any_overlap"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "lines"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "samples"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "bands"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "samp_percent"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "file_name_x"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "file_name_y"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "get_mstats"))
        self.assertTrue(hasattr(ip.OverlapStatistics, "to_pvl"))

    def test_construction_from_invalid_pvl_raises(self):
        """Constructing OverlapStatistics from an incomplete PvlObject raises IException.

        This verifies that the binding correctly forwards to upstream parsing
        logic. An incomplete PvlObject (missing required File1/File2 groups)
        should raise rather than silently return a corrupted object.
        """
        pvl = ip.PvlObject("OverlapStatistics")
        pvl.add_keyword(ip.PvlKeyword("Width", "10"))
        with self.assertRaises(Exception):
            # Missing required groups (File1, File2) must raise
            ip.OverlapStatistics(pvl)


if __name__ == "__main__":
    unittest.main()