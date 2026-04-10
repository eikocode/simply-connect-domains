"""Tests for name parser — handles newline, comma, ampersand, "and", CJK separators."""

import re
import pytest


# Extracted regex from extension/tools.py collecting_family step
NAME_SPLIT_PATTERN = r'[\n,，、&]|\s+and\s+|\s+及\s+|\s*と\s*'


def parse_names(msg: str) -> list[str]:
    """Reference implementation — must match extension/tools.py."""
    raw = re.split(NAME_SPLIT_PATTERN, msg, flags=re.IGNORECASE)
    return [n.strip() for n in raw if n.strip() and len(n.strip()) < 60]


# ---------------------------------------------------------------------------
# Basic separators
# ---------------------------------------------------------------------------

class TestBasicSeparators:
    def test_single_name(self):
        assert parse_names("John") == ["John"]

    def test_comma_separated(self):
        assert parse_names("John, Mary") == ["John", "Mary"]

    def test_newline_separated(self):
        assert parse_names("John\nMary") == ["John", "Mary"]

    def test_chinese_comma(self):
        assert parse_names("John，Mary") == ["John", "Mary"]

    def test_japanese_mark(self):
        assert parse_names("John、Mary") == ["John", "Mary"]

    def test_mixed_separators(self):
        assert parse_names("John, Mary\nBob") == ["John", "Mary", "Bob"]


# ---------------------------------------------------------------------------
# Conjunctions — the bug we just fixed
# ---------------------------------------------------------------------------

class TestConjunctions:
    def test_english_and(self):
        """Critical: 'Andy and Pete' must be TWO names, not one."""
        assert parse_names("Andy and Pete") == ["Andy", "Pete"]

    def test_and_uppercase(self):
        assert parse_names("Andy AND Pete") == ["Andy", "Pete"]

    def test_ampersand(self):
        assert parse_names("Sam & Jen") == ["Sam", "Jen"]

    def test_chinese_ji(self):
        """Chinese 及 = 'and'"""
        assert parse_names("大明 及 美美") == ["大明", "美美"]

    def test_japanese_to(self):
        """Japanese と = 'and'"""
        assert parse_names("三郎と雅美") == ["三郎", "雅美"]

    def test_reported_bug(self):
        """The exact message from Eiko's test — must return 9 names."""
        msg = "Jo, rose, honey, Dan, Joseph, Teresa, Tammy, Andy and Pete"
        names = parse_names(msg)
        assert len(names) == 9
        assert names == ["Jo", "rose", "honey", "Dan", "Joseph", "Teresa", "Tammy", "Andy", "Pete"]

    def test_multiple_ands(self):
        assert parse_names("A and B and C") == ["A", "B", "C"]

    def test_and_within_a_name_not_separated(self):
        """'Andrew' contains 'and' — but only as substring, not word. Must stay one name."""
        assert parse_names("Andrew") == ["Andrew"]
        assert parse_names("Andrea") == ["Andrea"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        assert parse_names("") == []

    def test_only_whitespace(self):
        assert parse_names("   \n  ") == []

    def test_only_separators(self):
        assert parse_names(",,,") == []

    def test_trailing_separator(self):
        assert parse_names("John, Mary,") == ["John", "Mary"]

    def test_leading_separator(self):
        assert parse_names(",John, Mary") == ["John", "Mary"]

    def test_extra_whitespace(self):
        assert parse_names("  John  ,   Mary  ") == ["John", "Mary"]

    def test_name_too_long_is_rejected(self):
        """Names over 60 chars should be filtered out (sanity limit)."""
        long_name = "A" * 61
        assert parse_names(long_name) == []
        assert parse_names(f"John, {long_name}, Mary") == ["John", "Mary"]

    def test_duplicate_names_preserved_by_parser(self):
        """Parser keeps duplicates — dedup happens in the FSM step."""
        assert parse_names("John, John") == ["John", "John"]


# ---------------------------------------------------------------------------
# Real-world messy input
# ---------------------------------------------------------------------------

class TestMessyInput:
    def test_mixed_all_separators(self):
        msg = "Sam, Jen & Bob\nAlice and Mary、Tom"
        names = parse_names(msg)
        assert names == ["Sam", "Jen", "Bob", "Alice", "Mary", "Tom"]

    def test_unicode_cjk_names(self):
        msg = "大明、美美、小華"
        assert parse_names(msg) == ["大明", "美美", "小華"]

    def test_japanese_names(self):
        msg = "三郎、雅美、健太"
        assert parse_names(msg) == ["三郎", "雅美", "健太"]

    def test_max_limit_not_enforced_by_parser(self):
        """Parser returns all names — limit enforcement is in FSM."""
        msg = ", ".join(f"Name{i}" for i in range(20))
        assert len(parse_names(msg)) == 20
