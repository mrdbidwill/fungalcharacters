from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy

FORM = "characters/form.html"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name=FORM, extra_context={"title": "Log in", "submit": "Log in"}), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/password/", auth_views.PasswordChangeView.as_view(
        template_name=FORM, success_url=reverse_lazy("password_change_done"),
        extra_context={"title": "Change password", "submit": "Change password"}), name="password_change"),
    path("accounts/password/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="characters/message.html",
        extra_context={"title": "Password changed", "text": "Your password has been changed."}), name="password_change_done"),
    # One-time "set your password" links (made by the admin; no email is sent).
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="characters/password_set.html", success_url=reverse_lazy("password_reset_complete")),
        name="password_reset_confirm"),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="characters/message.html",
        extra_context={"title": "Password set", "text": "Your password is set. You can now log in."}),
        name="password_reset_complete"),
    path("", include("characters.urls")),
]
