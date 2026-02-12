"""Unit tests for agents/name_extractor.py — name cleaning logic."""

from agents.name_extractor import _clean_name


class TestCleanName:
    """Test name validation and normalization."""

    def test_valid_name(self):
        assert _clean_name("Sarah") == "Sarah"

    def test_lowercase_capitalized(self):
        assert _clean_name("sarah") == "Sarah"

    def test_uppercase_capitalized(self):
        assert _clean_name("JOHN") == "John"

    def test_strips_punctuation(self):
        assert _clean_name("Sarah,") == "Sarah"
        assert _clean_name("John.") == "John"
        assert _clean_name('"Rachel"') == "Rachel"

    def test_hyphenated_name(self):
        assert _clean_name("Mary-Jane") == "Mary-jane"

    def test_apostrophe_name(self):
        assert _clean_name("O'Brien") == "O'brien"

    def test_too_short(self):
        assert _clean_name("A") is None

    def test_contains_digits(self):
        assert _clean_name("John123") is None

    def test_empty_string(self):
        assert _clean_name("") is None

    def test_none(self):
        assert _clean_name(None) is None

    def test_whitespace_only(self):
        assert _clean_name("   ") is None

    def test_accented_characters(self):
        assert _clean_name("José") == "José"

    def test_too_long(self):
        assert _clean_name("A" * 31) is None

    def test_max_length(self):
        assert _clean_name("A" * 30) == "A" + "a" * 29
