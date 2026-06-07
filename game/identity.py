"""The identity seam.

This is the ONLY place that answers "who is the current player?". Today it reads
the logged-in Django user. If auth ever changes, only this function changes — the
engine never knows about users or login at all.
"""
from .models import Character


def get_current_player(request) -> Character | None:
    """Return the request user's Character, or None if not logged in / no character."""
    if not request.user.is_authenticated:
        return None
    return Character.objects.filter(owner=request.user).first()
