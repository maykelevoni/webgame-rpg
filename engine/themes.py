"""Theme discovery.

A *theme* is a folder containing a ``theme.css`` file. To add a new look to the
game you just drop a new folder in the themes directory — it then shows up in the
theme picker automatically. This module only finds them; the web layer serves the
CSS and remembers each player's choice.
"""
from __future__ import annotations

from pathlib import Path


def available_themes(themes_dir: str | Path) -> list[str]:
    """Return the sorted names of folders that contain a ``theme.css`` file."""
    base = Path(themes_dir)
    if not base.is_dir():
        return []
    return sorted(
        p.name
        for p in base.iterdir()
        if p.is_dir() and (p / "theme.css").is_file()
    )
