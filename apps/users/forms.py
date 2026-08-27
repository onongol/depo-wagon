from django import forms
from django.utils.translation import gettext_lazy as _


class EmployeeSignupForm(forms.Form):
    """Restricts signup to people HR has already entered in the employee list.

    Mixed into allauth's signup form via ``ACCOUNT_SIGNUP_FORM_CLASS``. There is
    no open registration: an account may only be *claimed*, and only by someone
    who can prove — through allauth's verification email — that they own the
    address on an active ``Employee`` record that no user has claimed yet.

    This is the same invariant the Telegram bot enforces with its own OTP; the
    channel used to prove ownership is not what authorises the account, the
    Employee record is. Keeping both channels means an employee without a work
    Telegram account can still reach the web app.

    Note this does reveal whether a given address belongs to an employee. For an
    internal tool that trade is worth the far clearer error a real employee gets
    after mistyping their own address.
    """

    def clean(self):
        """Reject addresses that don't correspond to a claimable Employee.

        This deliberately hooks ``clean()`` and not ``clean_email()``: allauth's
        own ``BaseSignupForm`` subclasses this form and defines
        ``clean_email()`` itself, so a method of that name here is silently
        overridden and never runs. ``BaseSignupForm.clean()`` does call
        ``super().clean()``, which reaches us.
        """
        from apps.core.models import Employee

        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if not email:
            return cleaned_data

        claimable = Employee.objects.filter(
            email__iexact=email.strip(), is_active=True, user__isnull=True
        )
        if not claimable.exists():
            self.add_error(
                "email",
                _(
                    "This address is not on the employee list, or an account "
                    "for it already exists. Contact your manager."
                ),
            )
        return cleaned_data

    def signup(self, request, user) -> None:
        """Attach the new user to the Employee record it just claimed.

        Called by allauth once the user row exists. Without this the account
        would authenticate but carry no role, and every check in
        ``apps.users.permissions`` would deny it.
        """
        from apps.core.models import Employee

        Employee.objects.filter(
            email__iexact=user.email, is_active=True, user__isnull=True
        ).update(user=user)
