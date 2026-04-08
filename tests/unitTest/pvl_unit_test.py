"""
Unit tests for ISIS PVL and PvlSequence bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-03-30
Updated: 2026-03-30  Geng Xun added PvlSequence regression coverage alongside core PVL keyword, group, object, and container tests.
"""

import unittest

from _unit_test_support import make_simple_pvl, temporary_text_file, ip


class PvlUnitTest(unittest.TestCase):
    def test_pvl_keyword_basic_operations(self):
        keyword = ip.PvlKeyword("InstrumentId", "HIRISE")
        self.assertEqual(keyword.name(), "InstrumentId")
        self.assertTrue(keyword.is_named("InstrumentId"))
        self.assertEqual(len(keyword), 1)
        self.assertEqual(keyword[0], "HIRISE")

        keyword.add_value("CTX")
        keyword.set_units_for_value("HIRISE", "unitless")
        keyword.add_comment("Primary instrument")
        self.assertEqual(keyword.unit(0), "unitless")
        self.assertEqual(keyword.comments(), 1)
        self.assertEqual(keyword.comment(0), "# Primary instrument")
        self.assertIn("InstrumentId", str(keyword))

    def test_pvl_group_and_container_keyword_management(self):
        group = ip.PvlGroup("Instrument")
        group.add_keyword(ip.PvlKeyword("InstrumentId", "HIRISE"))
        group.add_keyword(ip.PvlKeyword("SpacecraftName", "MRO"))

        self.assertEqual(group.name(), "Instrument")
        self.assertTrue(group.has_keyword("InstrumentId"))
        self.assertEqual(group.find_keyword("SpacecraftName")[0], "MRO")
        self.assertEqual(group.keyword("InstrumentId")[0], "HIRISE")

        group.add_keyword(
            ip.PvlKeyword("InstrumentId", "CTX"),
            ip.PvlContainer.InsertMode.Replace,
        )
        self.assertEqual(group.find_keyword("InstrumentId")[0], "CTX")

        group.delete_keyword("SpacecraftName")
        self.assertFalse(group.has_keyword("SpacecraftName"))
        self.assertIn("Group = Instrument", str(group))

    def test_pvl_object_and_recursive_lookup(self):
        pvl = make_simple_pvl()
        self.assertTrue(pvl.has_group("Instrument"))
        self.assertTrue(pvl.has_object("Archive"))

        archive = pvl.find_object("Archive")
        self.assertTrue(archive.has_group("Product"))
        self.assertEqual(archive.find_group("Product")[0][0], "PSP_010502_2090")
        self.assertTrue(pvl.has_keyword_recursive("ProductId"))
        self.assertEqual(pvl.find_keyword_recursive("ProductId")[0], "PSP_010502_2090")

        archive.delete_group("Product")
        self.assertFalse(archive.has_group("Product"))

    def test_pvl_read_write_and_terminator(self):
        pvl = make_simple_pvl()
        pvl.set_terminator("End")
        self.assertEqual(pvl.terminator(), "End")

        with temporary_text_file("sample.pvl", str(pvl)) as file_path:
            loaded = ip.Pvl(str(file_path))
            self.assertTrue(loaded.has_group("Instrument"))
            self.assertEqual(loaded.find_group("Instrument").find_keyword("InstrumentId")[0], "HIRISE")

    def test_pvl_object_add_and_delete_nested_object(self):
        pvl = ip.Pvl()
        archive = ip.PvlObject("Archive")
        product = ip.PvlObject("Product")
        archive.add_object(product)
        pvl.add_object(archive)

        self.assertTrue(pvl.has_object("Archive"))
        self.assertTrue(pvl.find_object("Archive").has_object("Product"))

        pvl.find_object("Archive").delete_object("Product")
        self.assertFalse(pvl.find_object("Archive").has_object("Product"))

    def test_pvl_sequence_construction(self):
        """Test PvlSequence construction and basic properties."""
        seq = ip.PvlSequence()
        self.assertEqual(seq.size(), 0)
        self.assertEqual(len(seq), 0)
        self.assertIn("size=0", repr(seq))

    def test_pvl_sequence_clear(self):
        """Test clearing an empty sequence is safe."""
        seq = ip.PvlSequence()
        seq.clear()
        self.assertEqual(seq.size(), 0)

    def test_pvl_sequence_add_string_array(self):
        """Test adding arrays using string notation."""
        seq = ip.PvlSequence()
        seq.add_array("(a,b,c)")
        self.assertEqual(seq.size(), 1)
        self.assertEqual(len(seq[0]), 3)

        seq.add_array("(d,e)")
        self.assertEqual(seq.size(), 2)
        self.assertEqual(len(seq[1]), 2)

    def test_pvl_sequence_add_vector_types(self):
        """Test adding vectors of different types."""
        seq = ip.PvlSequence()

        # Add string vector
        seq.add_string_vector(["x", "y", "z"])
        self.assertEqual(seq.size(), 1)
        self.assertEqual(len(seq[0]), 3)

        # Add int vector
        seq.add_int_vector([1, 2, 3, 4])
        self.assertEqual(seq.size(), 2)
        self.assertEqual(len(seq[1]), 4)

        # Add double vector
        seq.add_double_vector([1.5, 2.5, 3.5])
        self.assertEqual(seq.size(), 3)
        self.assertEqual(len(seq[2]), 3)

    def test_pvl_sequence_indexing(self):
        """Test 2D array indexing."""
        seq = ip.PvlSequence()
        seq.add_array("(alpha,beta,gamma)")
        seq.add_array("(one,two)")

        # Check first array
        array0 = seq[0]
        self.assertEqual(len(array0), 3)
        self.assertEqual(array0[0], "alpha")
        self.assertEqual(array0[1], "beta")
        self.assertEqual(array0[2], "gamma")

        # Check second array
        array1 = seq[1]
        self.assertEqual(len(array1), 2)
        self.assertEqual(array1[0], "one")
        self.assertEqual(array1[1], "two")

    def test_pvl_sequence_from_keyword(self):
        """Test assigning sequence from PvlKeyword."""
        keyword = ip.PvlKeyword("TestKey")
        keyword.add_value("(red,green,blue)")
        keyword.add_value("(10,20,30)")

        seq = ip.PvlSequence()
        seq.assign_from_keyword(keyword)

        self.assertEqual(seq.size(), 2)
        self.assertEqual(len(seq[0]), 3)
        self.assertEqual(seq[0][0], "red")

    def test_pvl_sequence_clear_after_adding(self):
        """Test clearing a populated sequence."""
        seq = ip.PvlSequence()
        seq.add_array("(a,b,c)")
        seq.add_array("(d,e,f)")
        self.assertEqual(seq.size(), 2)

        seq.clear()
        self.assertEqual(seq.size(), 0)
        self.assertEqual(len(seq), 0)


if __name__ == "__main__":
    unittest.main()