"""Alta, sesión y restablecimiento. La contraseña solo pasa por el hasher de Django."""

import base64
import binascii
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.accounts.models import Profile, SignupPolicy, User
from apps.audit.services import record
from apps.editor.models import EditorPreference
from apps.projects.examples import seed_examples
from config.errors import DomainError


def clean_email(value: object) -> str:
    if not isinstance(value, str):
        raise DomainError("El correo no es válido.")
    email = value.strip().casefold()
    try:
        validate_email(email)
    except ValidationError as exc:
        raise DomainError("El correo no es válido.") from exc
    return email


def clean_label(value: object, *, field: str, limit: int, required: bool) -> str:
    if value is None or value == "":
        if required:
            raise DomainError(f"Falta {field}.")
        return ""
    if not isinstance(value, str):
        raise DomainError(f"{field} no es válido.")
    text = value.strip()
    if required and not text:
        raise DomainError(f"Falta {field}.")
    if any(ord(ch) < 32 for ch in text):
        raise DomainError(f"{field} contiene caracteres de control.")
    if len(text) > limit:
        raise DomainError(f"{field} es demasiado largo.")
    return text


def ensure_password(password: object, user: User | None = None) -> str:
    if not isinstance(password, str) or password == "":
        raise DomainError("La contraseña no es válida.")
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise DomainError(" ".join(exc.messages)) from exc
    return password


def clean_role(value: object) -> str:
    if value in (Profile.STUDENT, Profile.TEACHER):
        return value
    raise DomainError("El perfil debe ser docente o estudiante.")


def signup_policy() -> SignupPolicy:
    row, _created = SignupPolicy.objects.get_or_create(pk=1)
    return row


def signup_payload(policy: SignupPolicy | None = None) -> dict[str, bool]:
    row = signup_policy() if policy is None else policy
    return {"student": row.student, "teacher": row.teacher}


@transaction.atomic
def update_signup_policy(data: dict) -> SignupPolicy:
    signup_policy()
    row = SignupPolicy.objects.select_for_update().get(pk=1)
    changed = False
    for key in ("student", "teacher"):
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, bool):
            raise DomainError("Indica si ese tipo de cuenta se puede crear.")
        setattr(row, key, value)
        changed = True
    if changed:
        row.save()
    return row


def ensure_signup_open(role: str) -> None:
    policy = signup_policy()
    if role == Profile.STUDENT and policy.student:
        return
    if role == Profile.TEACHER and policy.teacher:
        return
    if role == Profile.TEACHER:
        raise DomainError("Ahora no se pueden crear cuentas de docente.")
    raise DomainError("Ahora no se pueden crear cuentas de alumno.")


class EmailConfirmTokenGenerator(PasswordResetTokenGenerator):
    """Caduca al confirmar: el hash incluye email_confirmed."""

    def _make_hash_value(self, user: User, timestamp: int) -> str:
        return f"{user.pk}{user.email}{user.email_confirmed}{timestamp}"


email_confirm_token = EmailConfirmTokenGenerator()


def _open_links(kind: str, uid: str, token: str) -> str:
    """La web sigue siendo el enlace principal. El esquema abre la aplicación si está instalada."""
    if kind == "confirmar":
        web = (
            f"{settings.TRAZA_PUBLIC_ORIGIN}/api/v1/auth/confirm-email/open/"
            f"?{urlencode({'confirmar': uid, 'token': token})}"
        )
    else:
        web = f"{settings.TRAZA_PUBLIC_ORIGIN}/?{urlencode({kind: uid, 'token': token})}"
    app = f"Aulivana-FCDdesign://open/?{urlencode({kind: uid, 'token': token})}"
    return f"{web}\n{app}"


def confirmation_notice() -> str:
    message = "Te enviamos un enlace para confirmar el correo. Ábrelo para activar la cuenta."
    mailbox = settings.TRAZA_MAIL_UI
    if mailbox:
        message += f" En este entorno el mensaje está en {mailbox}."
    return message


def _deliver(subject: str, body: str, recipient: str) -> None:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
    except (OSError, SMTPException) as exc:
        raise DomainError(
            "No se pudo enviar el correo. Inténtalo de nuevo en unos minutos."
        ) from exc


def _send_confirmation(user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_confirm_token.make_token(user)
    _deliver(
        "Confirma tu correo en Aulivana-FCDdesign",
        (
            "Para activar la cuenta confirma que este correo es tuyo.\n\n"
            f"{_open_links('confirmar', uid, token)}\n\n"
            "Si no creaste la cuenta, ignora este mensaje.\n"
        ),
        user.email,
    )


def standing_of(user: User) -> dict[str, int]:
    points = Profile.objects.values_list("points", flat=True).get(user=user)
    rank = Profile.objects.filter(points__gt=points).count() + 1
    return {"points": int(points), "rank": rank}


def user_payload(user: User) -> dict[str, object]:
    from apps.billing.services import account_access
    from apps.classroom.services import paste_allowed, translation_allowed

    profile = user.profile
    standing = standing_of(user)
    try:
        entitlement = account_access(user)
    except Exception:
        entitlement = {
            "plan": None,
            "access": {
                "browser_app": False,
                "features": {},
                "limits": {"max_projects": None, "max_algorithms": None},
            },
            "usage": {"projects": 0, "algorithms": 0},
        }
    return {
        "id": user.pk,
        "email": user.email,
        "display_name": profile.display_name,
        "institution": profile.institution,
        "role": profile.role,
        "points": standing["points"],
        "rank": standing["rank"],
        "translation_enabled": translation_allowed(user),
        "paste_enabled": paste_allowed(user),
        "avatar": _avatar_data_url(profile),
        "plan": entitlement["plan"],
        "access": entitlement["access"],
        "usage": entitlement["usage"],
    }


@transaction.atomic
def register_user(
    *,
    email: object,
    password: object,
    display_name: object = None,
    institution: object = None,
    role: object = None,
    ip_address: str | None = None,
) -> User:
    cleaned = clean_email(email)
    secret = ensure_password(password)
    visible = clean_label(display_name, field="El nombre", limit=80, required=False)
    school = clean_label(institution, field="La institución", limit=120, required=False)
    chosen = Profile.STUDENT if role is None or role == "" else clean_role(role)
    ensure_signup_open(chosen)
    existing = User.objects.filter(email=cleaned).first()
    if existing is not None:
        if existing.email_confirmed or not settings.EMAIL_CONFIRMATION_REQUIRED:
            raise DomainError("Ese correo ya está registrado.")
        existing.set_password(secret)
        existing.save(update_fields=["password"])
        profile = existing.profile
        if visible:
            profile.display_name = visible
        if school:
            profile.institution = school
        if role not in (None, ""):
            profile.role = chosen
        profile.save()
        from apps.billing.services import assign_default_subscription

        assign_default_subscription(existing)
        _send_confirmation(existing)
        return existing
    user = User.objects.create_user(
        email=cleaned,
        password=secret,
        email_confirmed=not settings.EMAIL_CONFIRMATION_REQUIRED,
    )
    Profile.objects.create(
        user=user,
        display_name=visible or cleaned.split("@", 1)[0],
        institution=school,
        role=chosen,
    )
    EditorPreference.objects.create(user=user)
    from apps.billing.services import assign_default_subscription

    assign_default_subscription(user)
    if chosen != Profile.ADMIN:
        seed_examples(user)
    record(
        "auth.register",
        actor=user,
        object_type="user",
        object_id=str(user.pk),
        metadata={},
        ip_address=ip_address,
    )
    if settings.EMAIL_CONFIRMATION_REQUIRED:
        _send_confirmation(user)
    return user


def login_user(request, email: object, password: object) -> User:
    from apps.accounts.guard import (
        begin_session,
        clear_login_failures,
        note_login_failure,
        refuse_locked_login,
    )

    cleaned = clean_email(email)
    refuse_locked_login(cleaned)
    authenticated = None
    if isinstance(password, str):
        authenticated = authenticate(request, username=cleaned, password=password)
    if not isinstance(authenticated, User):
        note_login_failure(cleaned)
        raise DomainError("Correo o contraseña incorrectos.")
    user = authenticated
    clear_login_failures(cleaned)
    if not user.email_confirmed:
        raise DomainError(
            "Confirma el correo antes de entrar. Revisa el mensaje que te enviamos.",
            code="email_unconfirmed",
        )
    user = begin_session(request, user)
    record(
        "auth.login",
        actor=user,
        object_type="user",
        object_id=str(user.pk),
        metadata={},
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return user


def logout_user(request) -> None:
    from apps.accounts.guard import release_session

    user = request.user if getattr(request.user, "is_authenticated", False) else None
    if isinstance(user, User):
        release_session(user, request.session.session_key)
    logout(request)
    if user is not None:
        record(
            "auth.logout",
            actor=user,
            object_type="user",
            object_id=str(user.pk),
            metadata={},
            ip_address=request.META.get("REMOTE_ADDR"),
        )


def request_password_reset(email: object, ip_address: str | None) -> None:
    try:
        cleaned = clean_email(email)
    except DomainError:
        return
    user = User.objects.filter(email=cleaned).first()
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    _deliver(
        "Restablecer contraseña de Aulivana-FCDdesign",
        f"uid={uid}\ntoken={token}\n{_open_links('restablecer', uid, token)}\n",
        user.email,
    )
    record(
        "auth.password_reset",
        actor=user,
        object_type="user",
        object_id=str(user.pk),
        metadata={},
        ip_address=ip_address,
    )


_AVATAR_KINDS = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}
_MAX_AVATAR = 120_000


def clean_avatar(value: object) -> tuple[bytes, str] | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith("data:") or "," not in value:
        raise DomainError("La imagen no es válida.")
    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise DomainError("La imagen no es válida.")
    kind = header[5:].split(";", 1)[0]
    if kind not in _AVATAR_KINDS:
        raise DomainError("La imagen debe ser JPG o PNG.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise DomainError("La imagen no es válida.") from exc
    if len(raw) < 32 or len(raw) > _MAX_AVATAR or not raw.startswith(_AVATAR_KINDS[kind]):
        raise DomainError("La imagen no es válida.")
    return raw, kind


def _avatar_data_url(profile: Profile) -> str | None:
    if not profile.avatar or not profile.avatar_type:
        return None
    encoded = base64.b64encode(bytes(profile.avatar)).decode("ascii")
    return f"data:{profile.avatar_type};base64,{encoded}"


def update_profile(user: User, data: dict, request=None) -> User:
    profile = user.profile
    fields: list[str] = []
    secret = None
    if "display_name" in data:
        profile.display_name = clean_label(
            data.get("display_name"), field="El nombre", limit=80, required=True
        )
        fields.append("display_name")
    if "avatar" in data:
        cleaned = clean_avatar(data.get("avatar"))
        if cleaned is None:
            profile.avatar = None
            profile.avatar_type = ""
        else:
            profile.avatar, profile.avatar_type = cleaned
        fields.extend(["avatar", "avatar_type"])
    if "role" in data:
        raise DomainError("El tipo de cuenta se elige al registrarse y no se puede cambiar.")
    password = data.get("password")
    if password not in (None, ""):
        current = data.get("current_password")
        if not isinstance(current, str) or not user.check_password(current):
            raise DomainError("La contraseña actual no coincide.")
        secret = ensure_password(password, user)
    if secret is not None:
        user.set_password(secret)
        user.save(update_fields=["password"])
        http_request = getattr(request, "_request", request)
        if http_request is not None:
            update_session_auth_hash(http_request, user)
    if fields:
        fields.append("updated_at")
        profile.save(update_fields=fields)
    return user


def confirm_email(uid: object, token: object, ip_address: str | None) -> User:
    if not isinstance(uid, str) or not isinstance(token, str):
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token")
    try:
        pk = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError, UnicodeDecodeError) as exc:
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token") from exc
    if not email_confirm_token.check_token(user, token):
        if user.email_confirmed:
            raise DomainError(
                "El correo ya está confirmado. Entra con tu contraseña.",
                code="already_confirmed",
            )
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token")
    user.email_confirmed = True
    user.save(update_fields=["email_confirmed"])
    record(
        "auth.email_confirm",
        actor=user,
        object_type="user",
        object_id=str(user.pk),
        metadata={},
        ip_address=ip_address,
    )
    return user


def resend_confirmation(email: object) -> None:
    try:
        cleaned = clean_email(email)
    except DomainError:
        return
    user = User.objects.filter(email=cleaned, email_confirmed=False).first()
    if user is None:
        return
    _send_confirmation(user)


def confirm_password_reset(uid: object, token: object, password: object) -> None:
    if not isinstance(uid, str) or not isinstance(token, str):
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token")
    try:
        pk = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError, UnicodeDecodeError) as exc:
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token") from exc
    if not default_token_generator.check_token(user, token):
        raise DomainError("El enlace no es válido o ya caducó.", code="invalid_token")
    secret = ensure_password(password, user)
    user.set_password(secret)
    user.save(update_fields=["password"])
