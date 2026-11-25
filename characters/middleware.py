from django.shortcuts import redirect
from django.urls import reverse


class AdminTwoFactorMiddleware:
    """The admin account must use two-factor sign-in (docs/DECISIONS.md).

    A signed-in admin without an authenticator app is sent to set one up before using
    any other page. Account pages, sign-out and static files stay reachable.
    """

    ALLOWED_PREFIXES = ("/accounts/", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_superuser \
                and not request.path.startswith(self.ALLOWED_PREFIXES):
            from allauth.mfa.utils import is_mfa_enabled
            if not is_mfa_enabled(user):
                return redirect(reverse("mfa_activate_totp"))
        return self.get_response(request)
