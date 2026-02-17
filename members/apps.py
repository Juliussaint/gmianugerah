from django.apps import AppConfig


class MembersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "members"
    verbose_name       = "Data Jemaat"

    def ready(self):
        # Daftarkan signal handlers
        import members.signals  # noqa: F401