from django.apps import AppConfig


class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'

    def ready(self):
        from . import signals  # noqa: F401
