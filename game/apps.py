from django.apps import AppConfig


class GameConfig(AppConfig):
    """The Django app that wraps the pure-Python game engine."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "game"
