"""Tests for the onboarding FSM (consent → household → family → complete)."""

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class TestLanguageDetection:
    def test_english(self, tools_module):
        assert tools_module._detect_language("Hello world") == "en"

    def test_traditional_chinese(self, tools_module):
        assert tools_module._detect_language("你好世界") == "zh-tw"

    def test_japanese(self, tools_module):
        assert tools_module._detect_language("こんにちは") == "ja"

    def test_mixed_english_chinese_defaults_to_zh(self, tools_module):
        assert tools_module._detect_language("Hi 你好") == "zh-tw"

    def test_empty(self, tools_module):
        assert tools_module._detect_language("") == "en"


# ---------------------------------------------------------------------------
# Step 1: Consent
# ---------------------------------------------------------------------------

class TestConsentStep:
    def test_new_user_gets_consent(self, tools_module, mock_cm, deploy_env):
        reply = tools_module._onboarding_step("user1", "Hi there", mock_cm, first_name="Ada")
        assert "Hi Ada" in reply
        assert "I agree" in reply
        assert "No thanks" in reply

    def test_new_user_chinese_consent(self, tools_module, mock_cm, deploy_env):
        reply = tools_module._onboarding_step("user2", "你好", mock_cm, first_name="美美")
        assert "美美" in reply
        assert "我同意" in reply
        assert "不用了" in reply

    def test_consent_agree_with_1(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u1", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u1", "1", mock_cm, first_name="Ada")
        assert "Just me" in reply  # advances to household step

    def test_consent_agree_with_yes(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u2", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u2", "yes", mock_cm, first_name="Ada")
        assert "Just me" in reply

    def test_consent_decline_with_2(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u3", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u3", "2", mock_cm, first_name="Ada")
        assert "No problem" in reply

    def test_agreement_word_does_NOT_advance(self, tools_module, mock_cm, deploy_env):
        """REGRESSION: 'agreement' contains 'agree' but must not be treated as consent."""
        tools_module._onboarding_step("u4", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u4", "Can I see the privacy agreement?", mock_cm, first_name="Ada")
        assert "Just me" not in reply  # did NOT advance to household
        assert "Privacy Policy" in reply or "Privacy" in reply

    def test_privacy_query_shows_policy(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u5", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u5", "privacy", mock_cm, first_name="Ada")
        assert "Privacy" in reply
        assert "collect" in reply.lower() or "data" in reply.lower()

    def test_help_query_shows_info(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u6", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u6", "what is this?", mock_cm, first_name="Ada")
        # Should show help or consent — not advance
        assert "household" not in reply.lower() or "upload" in reply.lower()

    def test_garbage_shows_help(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("u7", "hi", mock_cm, first_name="Ada")
        reply = tools_module._onboarding_step("u7", "asdfghjkl", mock_cm, first_name="Ada")
        # Must NOT advance
        assert "Just me" not in reply


# ---------------------------------------------------------------------------
# Step 2: Household
# ---------------------------------------------------------------------------

class TestHouseholdStep:
    def _advance_to_household(self, tools_module, mock_cm, user_id="user"):
        tools_module._onboarding_step(user_id, "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step(user_id, "1", mock_cm, first_name="Ada")  # agree

    def test_solo_completes_onboarding(self, tools_module, mock_cm, deploy_env):
        self._advance_to_household(tools_module, mock_cm, "h1")
        reply = tools_module._onboarding_step("h1", "1", mock_cm, first_name="Ada")
        assert "all set" in reply.lower()

    def test_family_goes_to_collecting(self, tools_module, mock_cm, deploy_env):
        self._advance_to_household(tools_module, mock_cm, "h2")
        reply = tools_module._onboarding_step("h2", "2", mock_cm, first_name="Ada")
        assert "household" in reply.lower() or "name" in reply.lower()
        assert "comma" in reply.lower()  # new instruction

    def test_household_garbage_re_asks(self, tools_module, mock_cm, deploy_env):
        self._advance_to_household(tools_module, mock_cm, "h3")
        reply = tools_module._onboarding_step("h3", "purple", mock_cm, first_name="Ada")
        assert "Just me" in reply  # re-shows options


# ---------------------------------------------------------------------------
# Step 3: Collecting family names
# ---------------------------------------------------------------------------

class TestCollectingFamily:
    def _advance_to_family_input(self, tools_module, mock_cm, user_id="family_user"):
        tools_module._onboarding_step(user_id, "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step(user_id, "1", mock_cm, first_name="Ada")  # agree
        tools_module._onboarding_step(user_id, "2", mock_cm, first_name="Ada")  # me + family

    def test_single_name_completes(self, tools_module, mock_cm, deploy_env):
        self._advance_to_family_input(tools_module, mock_cm, "f1")
        reply = tools_module._onboarding_step("f1", "Sam", mock_cm, first_name="Ada")
        assert "Sam" in reply
        assert "all set" in reply.lower()

    def test_comma_separated_names(self, tools_module, mock_cm, deploy_env):
        self._advance_to_family_input(tools_module, mock_cm, "f2")
        reply = tools_module._onboarding_step("f2", "Sam, Jen, Bob", mock_cm, first_name="Ada")
        assert "Sam" in reply and "Jen" in reply and "Bob" in reply

    def test_reject_8_names_with_warning(self, tools_module, mock_cm, deploy_env):
        """REGRESSION: 8 names must be rejected with clear warning."""
        self._advance_to_family_input(tools_module, mock_cm, "f3")
        reply = tools_module._onboarding_step(
            "f3", "Sam, Jen, Bob, Alice, Tom, Mike, Sue, Pat",
            mock_cm, first_name="Ada",
        )
        assert "⚠️" in reply
        assert "8" in reply  # count shown
        assert "7" in reply  # max mentioned
        # Must NOT have completed
        assert "all set" not in reply.lower()

    def test_reject_9_names_with_and(self, tools_module, mock_cm, deploy_env):
        """REGRESSION: Eiko's exact bug — 9 names with 'and' must be detected."""
        self._advance_to_family_input(tools_module, mock_cm, "f4")
        reply = tools_module._onboarding_step(
            "f4", "Jo, rose, honey, Dan, Joseph, Teresa, Tammy, Andy and Pete",
            mock_cm, first_name="Ada",
        )
        assert "⚠️" in reply
        assert "9" in reply  # must show 9, not 8
        assert "all set" not in reply.lower()

    def test_accept_7_names_exactly(self, tools_module, mock_cm, deploy_env):
        self._advance_to_family_input(tools_module, mock_cm, "f5")
        reply = tools_module._onboarding_step(
            "f5", "Sam, Jen, Bob, Alice, Tom, Mike, Sue",
            mock_cm, first_name="Ada",
        )
        assert "all set" in reply.lower()

    def test_empty_input_re_asks(self, tools_module, mock_cm, deploy_env):
        self._advance_to_family_input(tools_module, mock_cm, "f6")
        reply = tools_module._onboarding_step("f6", "   ", mock_cm, first_name="Ada")
        assert "comma" in reply.lower() or "names" in reply.lower()
        assert "all set" not in reply.lower()

    def test_duplicate_names_deduped_with_notice(self, tools_module, mock_cm, deploy_env):
        """REGRESSION: 'Sam, Sam, Jen' must dedup to 'Sam, Jen' with a notice."""
        self._advance_to_family_input(tools_module, mock_cm, "f7")
        reply = tools_module._onboarding_step(
            "f7", "Sam, Sam, Jen", mock_cm, first_name="Ada",
        )
        # Should show a dedup notice (ℹ️ emoji or "duplicate")
        assert "ℹ️" in reply or "duplicate" in reply.lower()
        # Should still complete — just with deduped list
        assert "all set" in reply.lower()

        # Verify family.md has Sam + Jen (not Sam + Sam + Jen)
        family_md = (deploy_env / "context" / "family.md").read_text()
        # Count occurrences of "## Sam" headings
        sam_count = family_md.count("## Sam")
        assert sam_count == 1
        assert "## Jen" in family_md

    def test_duplicate_case_insensitive_dedup(self, tools_module, mock_cm, deploy_env):
        """'Sam, sam, SAM' should become just one 'Sam'."""
        self._advance_to_family_input(tools_module, mock_cm, "f8")
        reply = tools_module._onboarding_step(
            "f8", "Sam, sam, SAM, Jen", mock_cm, first_name="Ada",
        )
        assert "all set" in reply.lower()

        # Verify family.md — only one Sam (the first one seen)
        family_md = (deploy_env / "context" / "family.md").read_text()
        assert family_md.count("## Sam") == 1
        # The lowercase variants should NOT appear as separate entries
        assert "## sam\n" not in family_md
        assert "## SAM\n" not in family_md

    def test_no_dup_notice_when_no_duplicates(self, tools_module, mock_cm, deploy_env):
        """Don't show the dedup notice unless there actually were duplicates."""
        self._advance_to_family_input(tools_module, mock_cm, "f9")
        reply = tools_module._onboarding_step(
            "f9", "Sam, Jen, Bob", mock_cm, first_name="Ada",
        )
        # No duplicate notice expected
        assert "ℹ️" not in reply
        assert "duplicate" not in reply.lower()
        assert "all set" in reply.lower()

    def test_duplicates_count_towards_limit_check_after_dedup(self, tools_module, mock_cm, deploy_env):
        """8 names with one duplicate = 7 unique = should succeed."""
        self._advance_to_family_input(tools_module, mock_cm, "f10")
        reply = tools_module._onboarding_step(
            "f10", "Sam, Sam, Jen, Bob, Alice, Tom, Mike, Sue",
            mock_cm, first_name="Ada",
        )
        # 8 raw → 7 unique → should succeed
        assert "all set" in reply.lower()
        assert "⚠️" not in reply  # no too_many warning

    def test_too_many_uniques_still_rejects(self, tools_module, mock_cm, deploy_env):
        """8 unique names (no dups) must still be rejected."""
        self._advance_to_family_input(tools_module, mock_cm, "f11")
        reply = tools_module._onboarding_step(
            "f11", "Sam, Jen, Bob, Alice, Tom, Mike, Sue, Pat",
            mock_cm, first_name="Ada",
        )
        assert "⚠️" in reply
        assert "8" in reply  # count shown
        assert "all set" not in reply.lower()


# ---------------------------------------------------------------------------
# Completion state + file writes
# ---------------------------------------------------------------------------

class TestCompletion:
    def test_solo_writes_family_md(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("s1", "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s1", "1", mock_cm, first_name="Ada")  # agree
        tools_module._onboarding_step("s1", "1", mock_cm, first_name="Ada")  # just me

        family_md = (deploy_env / "context" / "family.md").read_text()
        assert "Ada" in family_md
        assert "primary user" in family_md

    def test_family_writes_all_names(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("s2", "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s2", "1", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s2", "2", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s2", "Sam, Jen", mock_cm, first_name="Ada")

        family_md = (deploy_env / "context" / "family.md").read_text()
        assert "Ada" in family_md
        assert "Sam" in family_md
        assert "Jen" in family_md

    def test_completed_state_passes_through(self, tools_module, mock_cm, deploy_env):
        """After completion, subsequent messages return None (handed to Claude)."""
        tools_module._onboarding_step("s3", "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s3", "1", mock_cm, first_name="Ada")
        tools_module._onboarding_step("s3", "1", mock_cm, first_name="Ada")  # complete

        # Now subsequent messages should return None
        reply = tools_module._onboarding_step("s3", "hello", mock_cm, first_name="Ada")
        assert reply is None

    def test_state_persists_in_json_file(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("persist1", "hi", mock_cm, first_name="Ada")
        state_file = deploy_env / "data" / "onboarding" / "persist1.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["step"] == "consent"
        assert state["first_name"] == "Ada"
        assert state["language"] == "en"

    def test_decline_deletes_state(self, tools_module, mock_cm, deploy_env):
        tools_module._onboarding_step("d1", "hi", mock_cm, first_name="Ada")
        tools_module._onboarding_step("d1", "2", mock_cm, first_name="Ada")  # decline
        state_file = deploy_env / "data" / "onboarding" / "d1.json"
        assert not state_file.exists()
