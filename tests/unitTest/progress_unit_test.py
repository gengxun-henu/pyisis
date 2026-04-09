"""
Unit tests for ISIS Progress and IException bindings.

Author: Geng Xun
Created: 2026-04-09
Last Modified: 2026-04-09
"""
import unittest

from _unit_test_support import ip


class ProgressUnitTest(unittest.TestCase):
    """Test suite for Progress class bindings. Added: 2026-04-09."""

    def _make_progress(self):
        """Create a Progress with automatic display disabled to avoid stdout output."""
        p = ip.Progress()
        p.disable_automatic_display()
        return p

    def test_construction(self):
        """Progress() constructs without error."""
        p = self._make_progress()
        self.assertIsNotNone(p)

    def test_defaults(self):
        """Freshly constructed Progress starts at step 0 with maximum 0."""
        p = self._make_progress()
        self.assertEqual(p.maximum_steps(), 0)
        self.assertEqual(p.current_step(), 0)

    def test_set_and_get_text(self):
        """set_text/text round-trips correctly."""
        p = self._make_progress()
        p.set_text("Loading data")
        self.assertEqual(p.text(), "Loading data")

    def test_default_text(self):
        """Default text is 'Working'."""
        p = self._make_progress()
        self.assertEqual(p.text(), "Working")

    def test_set_maximum_steps_and_advance(self):
        """Setting maximum steps and calling check_status advances current_step."""
        p = self._make_progress()
        p.set_maximum_steps(5)
        self.assertEqual(p.maximum_steps(), 5)
        self.assertEqual(p.current_step(), 0)
        p.check_status()
        self.assertEqual(p.current_step(), 1)
        p.check_status()
        self.assertEqual(p.current_step(), 2)

    def test_advance_through_all_steps(self):
        """check_status can be called up to maximum_steps+1 times total."""
        p = self._make_progress()
        p.set_maximum_steps(3)
        # Initial call at step 0 + 3 more = 4 calls are valid
        for _ in range(4):
            p.check_status()
        self.assertEqual(p.current_step(), 4)

    def test_exceeding_maximum_raises(self):
        """Calling check_status beyond maximum raises IException."""
        p = self._make_progress()
        p.set_maximum_steps(2)
        for _ in range(3):   # 0, 1, 2 are valid
            p.check_status()
        with self.assertRaises(ip.IException):
            p.check_status()  # step 3 > maximum 2

    def test_set_maximum_steps_resets_counter(self):
        """Calling set_maximum_steps resets current_step to 0."""
        p = self._make_progress()
        p.set_maximum_steps(4)
        p.check_status()
        p.check_status()
        self.assertEqual(p.current_step(), 2)
        p.set_maximum_steps(10)  # reset
        self.assertEqual(p.current_step(), 0)

    def test_negative_maximum_raises(self):
        """set_maximum_steps with negative value raises IException."""
        p = self._make_progress()
        with self.assertRaises(ip.IException):
            p.set_maximum_steps(-1)

    def test_add_steps(self):
        """add_steps increases the maximum step count."""
        p = self._make_progress()
        p.set_maximum_steps(5)
        p.add_steps(3)
        self.assertEqual(p.maximum_steps(), 8)

    def test_add_steps_zero_raises(self):
        """add_steps with 0 raises IException."""
        p = self._make_progress()
        p.set_maximum_steps(5)
        with self.assertRaises(ip.IException):
            p.add_steps(0)

    def test_repr(self):
        """__repr__ contains step information."""
        p = self._make_progress()
        p.set_maximum_steps(10)
        r = repr(p)
        self.assertIn("Progress", r)
        self.assertIn("10", r)


class IExceptionErrorTypeUnitTest(unittest.TestCase):
    """Test suite for IExceptionErrorType enum bindings. Added: 2026-04-09."""

    def test_enum_values_exist(self):
        """All four ErrorType enum values are accessible."""
        self.assertTrue(hasattr(ip.IExceptionErrorType, "Unknown"))
        self.assertTrue(hasattr(ip.IExceptionErrorType, "User"))
        self.assertTrue(hasattr(ip.IExceptionErrorType, "Programmer"))
        self.assertTrue(hasattr(ip.IExceptionErrorType, "Io"))

    def test_enum_numeric_values(self):
        """ErrorType enum numeric values match upstream definitions (Unknown=1)."""
        self.assertEqual(int(ip.IExceptionErrorType.Unknown), 1)
        self.assertEqual(int(ip.IExceptionErrorType.User), 2)
        self.assertEqual(int(ip.IExceptionErrorType.Programmer), 3)
        self.assertEqual(int(ip.IExceptionErrorType.Io), 4)

    def test_enum_is_distinct(self):
        """Each ErrorType value is distinct."""
        values = {
            ip.IExceptionErrorType.Unknown,
            ip.IExceptionErrorType.User,
            ip.IExceptionErrorType.Programmer,
            ip.IExceptionErrorType.Io,
        }
        self.assertEqual(len(values), 4)

    def test_iexception_is_catchable(self):
        """IException can be caught as a Python exception."""
        p = ip.Progress()
        p.disable_automatic_display()
        p.set_maximum_steps(0)
        try:
            p.check_status()
            # second call should raise
            p.check_status()
        except ip.IException:
            pass
        except Exception as e:
            self.fail(f"Expected ip.IException but got {type(e)}: {e}")


if __name__ == "__main__":
    unittest.main()
