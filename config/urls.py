"""Root URL configuration.

Wires up the admin, Django's built-in auth views (login/logout), and the game app.
"""
from django.contrib import admin
from django.urls import include, path

from game import views as game_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Our signup view, before the built-in auth urls.
    path("accounts/signup/", game_views.signup, name="signup"),
    # Django's built-in auth: /accounts/login/, /accounts/logout/, etc.
    path("accounts/", include("django.contrib.auth.urls")),
    # The game itself.
    path("", include("game.urls")),
]
