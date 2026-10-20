from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import (
    confirm_email,
    confirm_password_reset,
    confirmation_notice,
    login_user,
    logout_user,
    register_user,
    request_password_reset,
    resend_confirmation,
    update_profile,
    user_payload,
)
from apps.accounts.guard import begin_session
from apps.http import client_ip, current_user, object_body
from config.errors import DomainError

_CONFIRMED_ELSEWHERE = "El correo quedó confirmado. Esa cuenta ya puede entrar desde cualquier equipo."


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"ok": True})


class RegisterView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        user = register_user(
            email=data.get("email"),
            password=data.get("password"),
            display_name=data.get("display_name"),
            institution=data.get("institution"),
            role=data.get("role"),
            ip_address=client_ip(request),
        )
        if not user.email_confirmed:
            return Response(
                {"pending_confirmation": True, "message": confirmation_notice()},
                status=201,
            )
        begin_session(request, user)
        return Response(user_payload(user), status=201)


class LoginView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        user = login_user(request, data.get("email"), data.get("password"))
        return Response(user_payload(user))


class LogoutView(APIView):
    def post(self, request: Request) -> Response:
        logout_user(request)
        return Response(status=204)


class MeView(APIView):
    def get(self, request: Request) -> Response:
        return Response(user_payload(current_user(request)))

    def patch(self, request: Request) -> Response:
        user = update_profile(current_user(request), object_body(request.data), request)
        return Response(user_payload(user))


def _other_session(request, user) -> bool:
    current = getattr(request, "user", None)
    return bool(getattr(current, "is_authenticated", False) and getattr(current, "pk", None) != user.pk)


class EmailConfirmView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        user = confirm_email(data.get("uid"), data.get("token"), client_ip(request))
        if _other_session(request, user):
            return Response({"confirmed": True, "message": _CONFIRMED_ELSEWHERE})
        try:
            begin_session(request, user)
        except DomainError as exc:
            if exc.code != "session_open":
                raise
            return Response({"confirmed": True, "message": exc.message})
        return Response(user_payload(user))


class EmailConfirmOpenView(View):
    """El enlace del correo confirma la cuenta en cualquier equipo.

    Si ese navegador ya entró con otra cuenta, la sesión no cambia: el alta
    queda confirmada y se puede usar desde el equipo donde se creó.
    """

    def get(self, request):
        try:
            user = confirm_email(
                request.GET.get("confirmar"),
                request.GET.get("token"),
                client_ip(request),
            )
        except DomainError as exc:
            if exc.code == "already_confirmed":
                return HttpResponseRedirect("/?correo=confirmado")
            return HttpResponse(
                (
                    "<!DOCTYPE html><html lang=\"es\"><meta charset=\"utf-8\">"
                    f"<title>{escape(exc.message)}</title><body><p>{escape(exc.message)}</p></body></html>"
                ),
                status=exc.status_code,
                content_type="text/html; charset=utf-8",
            )
        if _other_session(request, user):
            return HttpResponseRedirect("/?correo=confirmado")
        try:
            begin_session(request, user)
        except DomainError as exc:
            if exc.code != "session_open":
                raise
            return HttpResponseRedirect("/?sesion=abierta")
        return HttpResponseRedirect("/")


class EmailConfirmResendView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        resend_confirmation(data.get("email"))
        return Response({"message": confirmation_notice()})


class PasswordResetView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        request_password_reset(data.get("email"), client_ip(request))
        return Response(
            {"message": "Si el correo está registrado, enviamos instrucciones para restablecerla."}
        )


class PasswordResetConfirmView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        confirm_password_reset(data.get("uid"), data.get("token"), data.get("password"))
        return Response({"message": "La contraseña quedó actualizada."})
