from imessage_data_foundry.utils.names import parse_name


class TestNameParsing:
    def test_single_name(self):
        first, middle, last = parse_name("John")
        assert first == "John"
        assert middle is None
        assert last is None

    def test_two_names(self):
        first, middle, last = parse_name("John Doe")
        assert first == "John"
        assert middle is None
        assert last == "Doe"

    def test_three_names(self):
        first, middle, last = parse_name("John Michael Doe")
        assert first == "John"
        assert middle == "Michael"
        assert last == "Doe"

    def test_four_names(self):
        first, middle, last = parse_name("John Paul Michael Doe")
        assert first == "John"
        assert middle == "Paul Michael"
        assert last == "Doe"

    def test_empty_string(self):
        first, middle, last = parse_name("")
        assert first is None
        assert middle is None
        assert last is None

    def test_whitespace_only(self):
        first, middle, last = parse_name("   ")
        assert first is None
        assert middle is None
        assert last is None

    def test_extra_whitespace(self):
        first, middle, last = parse_name("  John   Doe  ")
        assert first == "John"
        assert middle is None
        assert last == "Doe"

    def test_preserves_case(self):
        first, middle, last = parse_name("JOHN DOE")
        assert first == "JOHN"
        assert last == "DOE"

    def test_hyphenated_last_name(self):
        first, middle, last = parse_name("Mary Smith-Jones")
        assert first == "Mary"
        assert middle is None
        assert last == "Smith-Jones"

    def test_apostrophe_in_name(self):
        first, middle, last = parse_name("Patrick O'Brien")
        assert first == "Patrick"
        assert middle is None
        assert last == "O'Brien"
