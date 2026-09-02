import pytest
from django.core.cache import cache

from apps.users import telegram_tokens


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield


class TestIssueAndRedeem:
    def test_redeem_returns_the_user_id(self):
        token = telegram_tokens.issue(42)
        assert telegram_tokens.redeem(token) == 42

    def test_token_works_only_once(self):
        token = telegram_tokens.issue(42)
        telegram_tokens.redeem(token)
        assert telegram_tokens.redeem(token) is None

    def test_unknown_token_returns_none(self):
        assert telegram_tokens.redeem("never-issued") is None

    def test_empty_token_returns_none(self):
        assert telegram_tokens.redeem("") is None

    def test_two_tokens_are_distinct(self):
        assert telegram_tokens.issue(1) != telegram_tokens.issue(1)


class TestTokensAreStoredHashed:
    """Reading the cache must not hand anybody a working token."""

    def test_the_plaintext_token_is_not_a_cache_key(self):
        token = telegram_tokens.issue(42)
        assert cache.get(f"tg_link_token:{token}") is None

    def test_the_user_index_holds_no_plaintext_token(self):
        token = telegram_tokens.issue(42)
        assert cache.get("tg_link_user:42") != token


class TestOnlyOneLiveTokenPerUser:
    def test_issuing_again_revokes_the_previous_token(self):
        first = telegram_tokens.issue(42)
        telegram_tokens.issue(42)
        assert telegram_tokens.redeem(first) is None

    def test_the_newest_token_still_works(self):
        telegram_tokens.issue(42)
        second = telegram_tokens.issue(42)
        assert telegram_tokens.redeem(second) == 42

    def test_revocation_is_scoped_to_one_user(self):
        theirs = telegram_tokens.issue(1)
        telegram_tokens.issue(2)
        assert telegram_tokens.redeem(theirs) == 1

    def test_a_redeemed_user_can_be_issued_a_working_token_again(self):
        telegram_tokens.redeem(telegram_tokens.issue(42))
        token = telegram_tokens.issue(42)
        assert telegram_tokens.redeem(token) == 42
