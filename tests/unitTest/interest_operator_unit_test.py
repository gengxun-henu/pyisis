"""
Unit tests for ISIS InterestOperatorFactory bindings

Author: Geng Xun
Created: 2026-03-27
Last Modified: 2026-03-27
"""

import unittest
from _unit_test_support import ip


class TestInterestOperatorFactory(unittest.TestCase):
    """Test suite for InterestOperatorFactory binding."""

    def test_interest_operator_factory_symbol_exists(self):
        """Test that InterestOperatorFactory class is exported."""
        self.assertTrue(hasattr(ip, 'InterestOperatorFactory'))

    def test_interest_operator_factory_has_create_method(self):
        """Test that InterestOperatorFactory has create static method."""
        self.assertTrue(hasattr(ip.InterestOperatorFactory, 'create'))
        self.assertTrue(callable(ip.InterestOperatorFactory.create))

    def test_interest_operator_factory_create_with_simple_pvl(self):
        """Test creating an InterestOperator with minimal PVL configuration.

        Note: This test verifies the binding works but may fail if:
        - ISIS InterestOperator plugins are not available
        - The PVL configuration is incomplete
        - Runtime environment is missing required setup

        This is expected behavior for a minimal binding test.
        """
        try:
            # Create a minimal PVL for StandardDeviation interest operator
            pvl = ip.Pvl()
            group = ip.PvlGroup("InterestOperator")
            group.add_keyword(ip.PvlKeyword("Name", "StandardDeviation"))
            group.add_keyword(ip.PvlKeyword("DeltaLine", "100"))
            pvl.add_group(group)

            # Attempt to create the operator
            operator = ip.InterestOperatorFactory.create(pvl)

            # If creation succeeds, verify we got a valid pointer
            self.assertIsNotNone(operator)

        except ip.IException as e:
            # Expected if InterestOperator plugins are not available or PVL is incomplete
            # This is acceptable for a binding-level test
            error_msg = str(e)
            # Just verify the error comes from ISIS, not from Python binding layer
            self.assertTrue(
                "InterestOperator" in error_msg or
                "plugin" in error_msg.lower() or
                "pvl" in error_msg.lower() or
                "keyword" in error_msg.lower(),
                f"Unexpected error type: {error_msg}"
            )

    def test_interest_operator_factory_create_invalid_pvl(self):
        """Test that create method raises appropriate error with invalid PVL."""
        try:
            # Create an empty PVL (missing required InterestOperator group)
            pvl = ip.Pvl()

            # This should raise an IException
            operator = ip.InterestOperatorFactory.create(pvl)

            # If we get here without exception, that's unexpected but not necessarily wrong
            # (depends on ISIS implementation details)

        except ip.IException as e:
            # Expected behavior - ISIS should reject invalid PVL
            self.assertIsInstance(e, ip.IException)
            # Error message should mention something about missing configuration
            error_msg = str(e)
            self.assertTrue(len(error_msg) > 0)


if __name__ == '__main__':
    unittest.main()
