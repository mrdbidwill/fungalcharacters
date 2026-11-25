from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.utils.translation.trans_real import parse_accept_lang_header


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


class SiteLocaleMiddleware(LocaleMiddleware):
    """Choose the interface language.

    1. The visitor's own choice (language cookie), among every language being translated, so translators
       can preview unfinished work.
    2. Otherwise the browser's preferred languages, but only among PUBLISHED_LANGUAGES, so nobody lands on a
       half-translated site by accident.
    3. Otherwise English.
    """

    def process_request(self, request):
        codes = {code for code, _ in settings.LANGUAGES}
        chosen = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        lang = chosen if chosen in codes else self.from_browser(request)
        translation.activate(lang)
        request.LANGUAGE_CODE = translation.get_language()

    @staticmethod
    def from_browser(request):
        published = [c.lower() for c in settings.PUBLISHED_LANGUAGES]
        for code, _q in parse_accept_lang_header(request.META.get("HTTP_ACCEPT_LANGUAGE", "")):
            code = code.lower()
            for pub in published:
                if code == pub or code.split("-")[0] == pub.split("-")[0]:
                    return pub
        return settings.LANGUAGE_CODE
