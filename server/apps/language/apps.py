from django.apps import AppConfig


class LanguageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.language"
    verbose_name = "Lenguaje"

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        from apps.language.services import seed_profiles

        post_migrate.connect(seed_profiles, sender=self)
