from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """allauth's default behaviour, with reauthentication tightened."""

    def get_reauthentication_methods(self, user):
        """Demand a second factor, not a password, from users who have one.

        allauth offers every configured method when it asks someone to confirm
        who they are before a sensitive change. Leaving the password in that
        list means a stolen password alone is enough to disable the very
        second factor that was supposed to make it insufficient — so once MFA
        is set up, only MFA satisfies the prompt.
        """
        methods = super().get_reauthentication_methods(user)
        mfa_methods = [m for m in methods if m["id"] == "mfa_reauthenticate"]
        return mfa_methods or methods
