from django.apps import AppConfig


class ResumeGenConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resume_gen'

    def ready(self):
        from . import signals  # noqa: F401
