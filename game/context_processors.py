"""Template context processors.

`theme` runs on every template render and supplies the active theme plus the list
of available themes, so the base layout can load the right CSS and show the picker
everywhere without each view having to pass them in.
"""
from engine.themes import available_themes

from .models import Profile
from .services import THEMES_DIR

DEFAULT_THEME = "dark-fantasy"


def theme(request):
    themes = available_themes(THEMES_DIR)
    active = DEFAULT_THEME
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        active = profile.theme
    if themes and active not in themes:
        active = themes[0]
    return {"active_theme": active, "available_themes": themes}
