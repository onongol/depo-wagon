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


class TestConcurrentRedemption:
    """Two readers of one live token: only the one that removes it spends it."""

    def test_the_loser_of_the_race_gets_nothing(self, monkeypatch):
        token = telegram_tokens.issue(42)

        class RivalFinishesFirst:
            """A second process that redeems between our get and our delete."""

            def __getattr__(self, name):
                return getattr(cache, name)

            def get(self, key, *args, **kwargs):
                value = cache.get(key, *args, **kwargs)
                cache.delete(key)
                return value

        monkeypatch.setattr(telegram_tokens, "cache", RivalFinishesFirst())

        assert telegram_tokens.redeem(token) is None

    def test_a_token_issued_mid_redeem_stays_revocable(self, monkeypatch):
        spent = telegram_tokens.issue(42)
        fresh = []

        class PageReloadsMidRedeem:
            """The connect page issues again between our spend and our cleanup."""

            def __getattr__(self, name):
                return getattr(cache, name)

            def delete(self, key, *args, **kwargs):
                deleted = cache.delete(key, *args, **kwargs)
                if not fresh:
                    fresh.append(telegram_tokens.issue(42))
                return deleted

        monkeypatch.setattr(telegram_tokens, "cache", PageReloadsMidRedeem())
        assert telegram_tokens.redeem(spent) == 42
        monkeypatch.undo()

        telegram_tokens.issue(42)
        assert telegram_tokens.redeem(fresh[0]) is None


class TestTokensAreStoredHashed:
    """Reading the cache must not hand anybody a working token."""

    def test_the_plaintext_token_is_not_a_cache_key(self):
        token = telegram_tokens.issue(42)
        assert cache.get(f"tg_link_token:{token}") is None

    def test_the_user_index_holds_no_plaintext_token(self):
        token = telegram_tokens.issue(42)
        assert cache.get("tg_link_user:42") != token


class TestOnlyOneLiveTokenPerUser:
    """Holds for issues that follow one another; racing issues may leave both."""

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


class TestRevoke:
    def test_revoke_kills_the_live_token(self):
        token = telegram_tokens.issue(42)
        telegram_tokens.revoke(42)
        assert telegram_tokens.redeem(token) is None

    def test_revoke_is_scoped_to_one_user(self):
        theirs = telegram_tokens.issue(1)
        telegram_tokens.revoke(2)
        assert telegram_tokens.redeem(theirs) == 1

    def test_revoking_with_nothing_issued_is_harmless(self):
        telegram_tokens.revoke(42)
        token = telegram_tokens.issue(42)
        assert telegram_tokens.redeem(token) == 42
