"""
Unit tests for ISIS PVL and PvlSequence bindings.

Author: Geng Xun
Created: 2026-03-21
Last Modified: 2026-04-09
Updated: 2026-03-30  Geng Xun added PvlSequence regression coverage alongside core PVL keyword, group, object, and container tests.
Updated: 2026-04-09  Geng Xun added PvlToken and PvlTokenizer focused unit tests.
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


class PvlTokenUnitTest(unittest.TestCase):
    """Focused unit tests for PvlToken binding. Added: 2026-04-09."""

    def test_construct_with_key(self):
        """PvlToken(key) stores the keyword name."""
        tok = ip.PvlToken("Dog")
        self.assertEqual(tok.key(), "Dog")

    def test_construct_default(self):
        """PvlToken() constructs with an empty key."""
        tok = ip.PvlToken()
        self.assertEqual(tok.key(), "")

    def test_set_key(self):
        """set_key() changes the keyword name."""
        tok = ip.PvlToken("Old")
        tok.set_key("New")
        self.assertEqual(tok.key(), "New")

    def test_key_upper(self):
        """key_upper() returns the keyword name in uppercase."""
        tok = ip.PvlToken("dog")
        self.assertEqual(tok.key_upper(), "DOG")

    def test_add_value_and_size(self):
        """add_value() appends to the value list and value_size() counts them."""
        tok = ip.PvlToken("Cat")
        self.assertEqual(tok.value_size(), 0)
        tok.add_value("tabby")
        tok.add_value("calico")
        self.assertEqual(tok.value_size(), 2)

    def test_value_default_index(self):
        """value() with no argument returns the first value."""
        tok = ip.PvlToken("Bird")
        tok.add_value("parrot")
        tok.add_value("canary")
        self.assertEqual(tok.value(), "parrot")

    def test_value_by_index(self):
        """value(index) returns the value at the given index."""
        tok = ip.PvlToken("Bird")
        tok.add_value("parrot")
        tok.add_value("canary")
        self.assertEqual(tok.value(1), "canary")

    def test_value_upper(self):
        """value_upper() returns the value in uppercase."""
        tok = ip.PvlToken("Animal")
        tok.add_value("poodle")
        self.assertEqual(tok.value_upper(), "POODLE")

    def test_value_clear(self):
        """value_clear() removes all values."""
        tok = ip.PvlToken("Dog")
        tok.add_value("drools")
        tok.value_clear()
        self.assertEqual(tok.value_size(), 0)

    def test_value_vector(self):
        """value_vector() returns all values as a list."""
        tok = ip.PvlToken("Multi")
        tok.add_value("a")
        tok.add_value("b")
        tok.add_value("c")
        vec = tok.value_vector()
        self.assertEqual(vec, ["a", "b", "c"])

    def test_value_out_of_range_raises(self):
        """value(-1) and value(beyond size) raise IException."""
        tok = ip.PvlToken("Dog")
        with self.assertRaises(Exception):
            tok.value(-1)
        with self.assertRaises(Exception):
            tok.value(1)  # no values added

    def test_repr(self):
        """repr(PvlToken) includes key and value count."""
        tok = ip.PvlToken("Key")
        tok.add_value("val1")
        tok.add_value("val2")
        r = repr(tok)
        self.assertIn("PvlToken", r)
        self.assertIn("Key", r)
        self.assertIn("2", r)


class PvlTokenizerUnitTest(unittest.TestCase):
    """Focused unit tests for PvlTokenizer binding. Added: 2026-04-09."""

    def test_construct(self):
        """PvlTokenizer() constructs with zero tokens."""
        tizer = ip.PvlTokenizer()
        self.assertEqual(len(tizer.get_token_list()), 0)

    def test_load_simple_pvl(self):
        """load() parses a simple PVL assignment."""
        tizer = ip.PvlTokenizer()
        tizer.load("DOG=POODLE ")
        tokens = tizer.get_token_list()
        self.assertGreater(len(tokens), 0)
        keys = [t.key() for t in tokens]
        self.assertIn("DOG", keys)

    def test_load_quoted_value(self):
        """load() handles quoted values."""
        tizer = ip.PvlTokenizer()
        tizer.load('CAT="TABBY" ')
        tokens = tizer.get_token_list()
        keys = [t.key() for t in tokens]
        self.assertIn("CAT", keys)
        cat_tok = next(t for t in tokens if t.key() == "CAT")
        self.assertEqual(cat_tok.value(), "TABBY")

    def test_load_paren_value(self):
        """load() parses parenthesised value lists."""
        tizer = ip.PvlTokenizer()
        tizer.load("BIRD=(PARROT) ")
        tokens = tizer.get_token_list()
        bird_tok = next((t for t in tokens if t.key() == "BIRD"), None)
        self.assertIsNotNone(bird_tok)
        self.assertEqual(bird_tok.value(), "PARROT")

    def test_load_multiple_keywords(self):
        """load() accumulates multiple keyword assignments."""
        tizer = ip.PvlTokenizer()
        tizer.load("DOG=POODLE CAT=TABBY BIRD=PARROT ")
        tokens = tizer.get_token_list()
        keys = {t.key() for t in tokens}
        self.assertIn("DOG", keys)
        self.assertIn("CAT", keys)
        self.assertIn("BIRD", keys)

    def test_clear(self):
        """clear() removes all parsed tokens."""
        tizer = ip.PvlTokenizer()
        tizer.load("A=1 B=2 ")
        tizer.clear()
        self.assertEqual(len(tizer.get_token_list()), 0)

    def test_load_with_comment(self):
        """load() skips comment lines."""
        tizer = ip.PvlTokenizer()
        tizer.load("A=1 # This is a comment\nB=2 ")
        tokens = tizer.get_token_list()
        keys = {t.key() for t in tokens}
        self.assertIn("A", keys)
        self.assertIn("B", keys)

    def test_repr(self):
        """repr(PvlTokenizer) includes token count."""
        tizer = ip.PvlTokenizer()
        tizer.load("X=1 Y=2 ")
        r = repr(tizer)
        self.assertIn("PvlTokenizer", r)


class PvlFormatUnitTest(unittest.TestCase):
    """Focused unit tests for PvlFormat and KeywordType binding. Added: 2026-04-09."""

    def test_construct_default(self):
        """PvlFormat() constructs without error."""
        fmt = ip.PvlFormat()
        self.assertIsNotNone(fmt)

    def test_char_limit_default(self):
        """Default char_limit is a positive integer."""
        fmt = ip.PvlFormat()
        self.assertIsInstance(fmt.char_limit(), int)
        self.assertGreater(fmt.char_limit(), 0)

    def test_set_char_limit(self):
        """set_char_limit() changes the char_limit value."""
        fmt = ip.PvlFormat()
        fmt.set_char_limit(100)
        self.assertEqual(fmt.char_limit(), 100)

    def test_format_eol_returns_newline(self):
        """format_eol() returns a newline by default."""
        fmt = ip.PvlFormat()
        self.assertIn("\n", fmt.format_eol())

    def test_format_name(self):
        """format_name() returns the keyword name as a string."""
        fmt = ip.PvlFormat()
        kw = ip.PvlKeyword("MyKey", "val")
        result = fmt.format_name(kw)
        self.assertIsInstance(result, str)
        self.assertIn("MyKey", result)

    def test_format_value(self):
        """format_value() returns the keyword value as a string."""
        fmt = ip.PvlFormat()
        kw = ip.PvlKeyword("MyKey", "testval")
        result = fmt.format_value(kw)
        self.assertIsInstance(result, str)

    def test_type_no_map_returns_no_type(self):
        """type() returns NoTypeKeyword when no keyword map is loaded."""
        fmt = ip.PvlFormat()
        kw = ip.PvlKeyword("Unknown", "value")
        result = fmt.type(kw)
        self.assertEqual(result, ip.KeywordType.NoTypeKeyword)

    def test_is_single_unit_no_units(self):
        """is_single_unit() returns False when the keyword has no units."""
        fmt = ip.PvlFormat()
        kw = ip.PvlKeyword("NoUnits", "42")
        result = fmt.is_single_unit(kw)
        # Without units, returns False
        self.assertFalse(result)

    def test_repr(self):
        """repr(PvlFormat) returns a non-empty string."""
        fmt = ip.PvlFormat()
        self.assertIn("PvlFormat", repr(fmt))

    def test_keyword_type_enum_values(self):
        """KeywordType enum has expected values."""
        self.assertTrue(hasattr(ip.KeywordType, "NoTypeKeyword"))
        self.assertTrue(hasattr(ip.KeywordType, "StringKeyword"))
        self.assertTrue(hasattr(ip.KeywordType, "IntegerKeyword"))
        self.assertTrue(hasattr(ip.KeywordType, "RealKeyword"))


class PvlTranslationTableUnitTest(unittest.TestCase):
    """Focused unit tests for PvlTranslationTable binding. Added: 2026-04-09."""

    SIMPLE_TABLE = (
        "Group = CoreLines\n"
        "  InputPosition = IMAGE\n"
        "  InputKey = LINES\n"
        "  Translation = (*,*)\n"
        "EndGroup\n"
        "Group = CoreBitsPerPixel\n"
        "  Auto = 1\n"
        "  OutputName = BitsPerPixel\n"
        "  InputPosition = IMAGE\n"
        "  InputKey = SAMPLE_BITS\n"
        "  InputDefault = 8\n"
        "  Translation = (8,8)\n"
        "  Translation = (16,16)\n"
        "EndGroup\n"
        "End\n"
    )

    def _make_table(self):
        return ip.PvlTranslationTable(self.SIMPLE_TABLE)

    def test_construct(self):
        """PvlTranslationTable(text) constructs without error."""
        table = self._make_table()
        self.assertIsNotNone(table)

    def test_input_keyword_name(self):
        """input_keyword_name() returns the InputKey for the group."""
        table = self._make_table()
        self.assertEqual(table.input_keyword_name("CoreLines"), "LINES")
        self.assertEqual(table.input_keyword_name("CoreBitsPerPixel"), "SAMPLE_BITS")

    def test_input_default(self):
        """input_default() returns the InputDefault value."""
        table = self._make_table()
        self.assertEqual(table.input_default("CoreBitsPerPixel"), "8")

    def test_has_input_default_true(self):
        """has_input_default() returns True for groups with a default."""
        table = self._make_table()
        self.assertTrue(table.has_input_default("CoreBitsPerPixel"))

    def test_has_input_default_false(self):
        """has_input_default() returns False for groups without a default."""
        table = self._make_table()
        self.assertFalse(table.has_input_default("CoreLines"))

    def test_is_auto_true(self):
        """is_auto() returns True for groups with Auto = 1."""
        table = self._make_table()
        self.assertTrue(table.is_auto("CoreBitsPerPixel"))

    def test_is_auto_false(self):
        """is_auto() returns False for groups without Auto."""
        table = self._make_table()
        self.assertFalse(table.is_auto("CoreLines"))

    def test_translate_wildcard(self):
        """translate() passes through values using (*,*) translation rule."""
        table = self._make_table()
        result = table.translate("CoreLines", "256")
        self.assertEqual(result, "256")

    def test_translate_mapped_value(self):
        """translate() maps concrete input values to output values."""
        table = self._make_table()
        result = table.translate("CoreBitsPerPixel", "16")
        self.assertEqual(result, "16")

    def test_add_table(self):
        """add_table() appends additional translation groups."""
        table = self._make_table()
        extra = (
            "Group = ExtraKey\n"
            "  InputKey = EXTRA\n"
            "  Translation = (*,*)\n"
            "EndGroup\n"
            "End\n"
        )
        table.add_table(extra)
        self.assertEqual(table.input_keyword_name("ExtraKey"), "EXTRA")

    def test_repr(self):
        """repr(PvlTranslationTable) returns a non-empty string."""
        table = self._make_table()
        self.assertIn("PvlTranslationTable", repr(table))


if __name__ == "__main__":
    unittest.main()