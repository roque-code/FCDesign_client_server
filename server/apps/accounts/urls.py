from django.urls import path

from apps.accounts.views import (
    CsrfView,
    EmailConfirmResendView,
    EmailConfirmView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("confirm-email/", EmailConfirmView.as_view(), name="confirm-email"),
    path("confirm-email/resend/", EmailConfirmResendView.as_view(), name="confirm-email-resend"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"
    ),
]
