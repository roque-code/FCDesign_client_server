"""Crea la cuenta que define los niveles. No aparece en el alta pública."""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Profile, User
from apps.accounts.services import clean_email, clean_label, ensure_password
from apps.editor.models import EditorPreference
from config.errors import DomainError


class Command(BaseCommand):
    help = "Crea un administrador. La contraseña se guarda con el hasher de Django."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--name", default="Administrador")

    def handle(self, *args, **options):
        try:
            email = clean_email(options["email"])
            secret = ensure_password(options["password"])
            visible = clean_label(options["name"], field="El nombre", limit=80, required=False)
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        if User.objects.filter(email=email).exists():
            raise CommandError("Ese correo ya está registrado.")
        user = User.objects.create_user(
            email=email,
            password=secret,
            email_confirmed=True,
            is_staff=False,
            is_superuser=False,
        )
        Profile.objects.create(
            user=user,
            display_name=visible or "Administrador",
            role=Profile.ADMIN,
        )
        EditorPreference.objects.create(user=user)
        self.stdout.write(f"Administrador creado: {email}")
