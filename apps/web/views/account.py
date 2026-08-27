from allauth.mfa.utils import is_mfa_enabled
from allauth.usersessions.models import UserSession
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST


@login_required
def account_overview(request):
    """One page listing what the signed-in person can change about their account.

    allauth ships a page per action but no index, so without this the password,
    email, two-factor and session pages exist at URLs nothing in the app links
    to. Deliberately ``login_required`` and not ``employee_required``: someone
    whose Employee record was deactivated should still be able to reach their
    own security settings.
    """
    context = {
        # None for a superuser created with `createsuperuser`, who has no HR
        # record; the template drops the rows that need one.
        "employee": getattr(request.user, "employee", None),
        "is_mfa_enabled": is_mfa_enabled(request.user),
        # purge_and_list drops rows whose Django session has already expired,
        # so the count matches what the sessions page will show.
        "session_count": len(UserSession.objects.purge_and_list(request.user)),
    }
    return render(request, "web/account/overview.html", context)


@require_POST
@login_required
def end_user_session(request, session_id):
    """Sign out one of this user's other sessions.

    allauth's own sessions page only offers "sign out all other sessions"; this
    backs the per-row button, so losing one device doesn't mean ending every
    session you have. Scoped to ``request.user`` so the id in the URL can only
    ever name a session of the person asking.
    """
    session = get_object_or_404(UserSession, pk=session_id, user=request.user)
    if not session.is_current():
        session.end()
        messages.success(request, _("Session signed out."))
    return redirect("web:account_overview")
