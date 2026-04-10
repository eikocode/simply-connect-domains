# Save My Brain — Tests

Automated test suite for the save-my-brain simply-connect domain extension.

## Running tests

```bash
# From the save-my-brain domain directory
cd /Users/eiko/Dev/simply-connect-domains/domains/save-my-brain

# Run all tests
/Users/eiko/Dev/simply-connect/.venv/bin/python3.12 -m pytest tests/ -v

# Run a specific test file
/Users/eiko/Dev/simply-connect/.venv/bin/python3.12 -m pytest tests/test_onboarding.py -v

# Run a specific test class
/Users/eiko/Dev/simply-connect/.venv/bin/python3.12 -m pytest tests/test_onboarding.py::TestConsentStep -v

# Run a single test
/Users/eiko/Dev/simply-connect/.venv/bin/python3.12 -m pytest tests/test_name_parser.py::TestConjunctions::test_reported_bug -v
```

## Test files

| File | Coverage |
|---|---|
| `test_name_parser.py` | Name parsing: separators, "and", max-7 enforcement, edge cases |
| `test_onboarding.py` | FSM state transitions, language detection, privacy/help queries, regression bugs |
| `test_family_tools.py` | add/remove/rename family members, case insensitivity, max-7 limit |
| `test_web_api.py` | Web API endpoints: /api/health, /api/context, /api/tool |

## Regression tests (bugs found + fixed via manual testing)

These tests prevent the exact bugs Eiko found during manual testing:

- **`test_agreement_word_does_NOT_advance`** — "Can I see the privacy agreement?" previously matched "agree" substring and advanced past consent. Now uses strict matching.
- **`test_reject_9_names_with_and`** — "Jo, rose, honey, Dan, Joseph, Teresa, Tammy, Andy and Pete" was parsed as 8 names. Now the parser handles "and", "&", "及", "と" as separators.
- **`test_reject_8_names_with_warning`** — Onboarding silently truncated at 7. Now rejects with a warning.
- **`test_primary_user_note_present`** — Claude was asking users about their own name. The `primary_user.note` field now instructs Claude not to ask.
- **`test_rename_member`** — "Replace Jen with Susan" didn't work — no edit tool existed. Now `rename_family_member` tool handles it.

## Adding new tests

When fixing a bug, always add a regression test. When adding a new feature, add tests for:

1. **Happy path** — does it work for normal input?
2. **Edge cases** — empty, too long, special characters, unicode
3. **Error handling** — what if the input is invalid?
4. **Side effects** — are files written correctly? state updated?

## Test counts (as of last run)

- `test_name_parser.py`: 26 tests
- `test_onboarding.py`: 28 tests
- `test_family_tools.py`: 26 tests
- `test_web_api.py`: 11 tests
- **Total: 91 tests**
