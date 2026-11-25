from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.urls import include, path

# The admin pages use the site's sign-in, so two-factor sign-in cannot be bypassed there.
admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("i18n/", include("django.conf.urls.i18n")),  # set_language: the language menu and previews
    path("", include("characters.urls")),
]
