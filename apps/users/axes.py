def get_username(request, credentials=None) -> str | None:
    """Resolve the account an attempt was aimed at, whichever form it came from.

    Axes reads one credential key by default, but the app has three entry points
    that name it differently: allauth and the API pass ``email``, Django's admin
    form always passes ``username``. Missing it would key every admin lockout on
    ``None``, which stops the lockout from matching the account at all.
    """
    if credentials:
        value = credentials.get("email") or credentials.get("username")
    else:
        value = request.POST.get("login") or request.POST.get("username")
    return value.strip().lower() if value else None
