"""
Unit tests for ISIS Resource bindings.

Author: Geng Xun
Created: 2026-04-09
Last Modified: 2026-04-09
Updated: 2026-04-09  Geng Xun aligned Resource.is_equal() tests with upstream name-based, case-insensitive equality semantics.
"""
import unittest

from _unit_test_support import ip


class ResourceUnitTest(unittest.TestCase):
    """Test suite for Resource class bindings. Added: 2026-04-09."""

    def test_construction_default(self):
        """Resource() constructs without error and has default name 'Resource'."""
        r = ip.Resource()
        self.assertIsNotNone(r)
        self.assertEqual(r.name(), "Resource")

    def test_construction_with_name(self):
        """Resource(name) sets the name on construction."""
        r = ip.Resource("TestResource")
        self.assertEqual(r.name(), "TestResource")

    def test_copy_construction(self):
        """Copy-constructed Resource has the same name as original."""
        r = ip.Resource("Original")
        r2 = ip.Resource(r)
        self.assertEqual(r2.name(), "Original")

    def test_set_name(self):
        """set_name changes the resource name."""
        r = ip.Resource("Before")
        r.set_name("After")
        self.assertEqual(r.name(), "After")

    def test_add_and_exists(self):
        """add(name, value) creates a keyword that exists() confirms."""
        r = ip.Resource("Res")
        self.assertFalse(r.exists("CenterLat"))
        r.add("CenterLat", "45.0")
        self.assertTrue(r.exists("CenterLat"))

    def test_value_retrieval(self):
        """value(name) returns the stored string value."""
        r = ip.Resource("Res")
        r.add("PixelScale", "0.25")
        self.assertEqual(r.value("PixelScale"), "0.25")

    def test_value_with_default(self):
        """value(name, default) returns default when keyword is absent."""
        r = ip.Resource("Res")
        v = r.value("Missing", "DEFAULT")
        self.assertEqual(v, "DEFAULT")

    def test_value_existing_ignores_default(self):
        """value(name, default) returns stored value when keyword exists."""
        r = ip.Resource("Res")
        r.add("Band", "3")
        v = r.value("Band", "999")
        self.assertEqual(v, "3")

    def test_count_single_value(self):
        """count() returns 1 for a keyword with a single value."""
        r = ip.Resource("Res")
        r.add("Key", "Val")
        self.assertEqual(r.count("Key"), 1)

    def test_erase_keyword(self):
        """erase() removes the keyword and exists() confirms absence."""
        r = ip.Resource("Res")
        r.add("ToDelete", "yes")
        self.assertTrue(r.exists("ToDelete"))
        r.erase("ToDelete")
        self.assertFalse(r.exists("ToDelete"))

    def test_is_null_absent_keyword(self):
        """is_null() returns True when the keyword does not exist."""
        r = ip.Resource("Res")
        self.assertTrue(r.is_null("NeverAdded"))

    def test_active_discard_lifecycle(self):
        """Resources start active; discard() marks them inactive; activate() restores."""
        r = ip.Resource("Res")
        self.assertTrue(r.is_active())
        self.assertFalse(r.is_discarded())

        r.discard()
        self.assertFalse(r.is_active())
        self.assertTrue(r.is_discarded())

        r.activate()
        self.assertTrue(r.is_active())
        self.assertFalse(r.is_discarded())

    def test_is_equal_same_name_case_insensitive(self):
        """Resources compare equal when their names match case-insensitively."""
        r1 = ip.Resource("A")
        r1.add("X", "1")
        r2 = ip.Resource("a")
        r2.add("Y", "2")
        self.assertTrue(r1.is_equal(r2))

    def test_is_equal_different_names(self):
        """Resources with different names compare as not equal even if keywords match."""
        r1 = ip.Resource("A")
        r1.add("X", "1")
        r2 = ip.Resource("B")
        r2.add("X", "1")
        self.assertFalse(r1.is_equal(r2))

    def test_to_pvl(self):
        """to_pvl() returns a PvlObject."""
        r = ip.Resource("MyRes")
        r.add("Alpha", "beta")
        pvl_obj = r.to_pvl()
        self.assertIsNotNone(pvl_obj)
        self.assertIsInstance(pvl_obj, ip.PvlObject)

    def test_to_pvl_custom_name(self):
        """to_pvl(pvl_name) uses the provided name for the PvlObject."""
        r = ip.Resource("MyRes")
        pvl_obj = r.to_pvl("CustomLabel")
        self.assertEqual(pvl_obj.name(), "CustomLabel")

    def test_repr(self):
        """__repr__ contains 'Resource' and the resource name."""
        r = ip.Resource("MyRes")
        s = repr(r)
        self.assertIn("Resource", s)
        self.assertIn("MyRes", s)


if __name__ == "__main__":
    unittest.main()
