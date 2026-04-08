"""
Unit tests for ISIS statistics, histogram, and vector-filter bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-21
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


if __name__ == "__main__":
    unittest.main()