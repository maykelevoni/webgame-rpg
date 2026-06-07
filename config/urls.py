"""Root URL configuration.

Wires up the admin, Django's built-in auth views (login/logout), and the game app.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django's built-in auth: /accounts/login/, /accounts/logout/, etc.
    path("accounts/", include("django.contrib.auth.urls")),
    # The game itself.
    path("", include("game.urls")),
]
