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


if __name__ == "__main__":
    unittest.main()