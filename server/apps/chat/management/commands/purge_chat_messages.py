from django.core.management.base import BaseCommand

from apps.chat.services import purge_expired


class Command(BaseCommand):
    help = "Borra los mensajes que superaron la duración definida por el administrador."

    def handle(self, *args, **options):
        deleted = purge_expired()
        self.stdout.write(f"Se borraron {deleted} mensajes.")
