from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def _safe_redirect_target(request):
    """Return the requested ``next`` target, but only if it stays on this site.

    Without this check an attacker can hand out /login/?next=https://evil/,
    turning a successful login into a redirect to their own page.
    """
    target = request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return "web:home"


def login_view(request):
    if request.user.is_authenticated:
        return redirect("web:home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user:
            login(request, user)
            return redirect(_safe_redirect_target(request))
    return render(request, "web/auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("web:login")
