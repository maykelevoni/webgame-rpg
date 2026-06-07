"""Tests for the plugin loader and theme discovery (uses temp folders)."""
from engine.plugins import load_plugins
from engine.themes import available_themes


GOOD_PLUGIN = '''
def register(registry):
    registry.add_town_action("Test Action", lambda character: None)
    registry.on_victory(lambda character: None)
'''

BROKEN_PLUGIN = "def register(registry):\n    this is not valid python\n"


def write(dirpath, name, content):
    (dirpath / name).write_text(content)


def test_only_enabled_plugins_load(tmp_path):
    write(tmp_path, "good.py", GOOD_PLUGIN)
    write(tmp_path, "disabled.py", GOOD_PLUGIN)
    write(tmp_path, "_template.py", GOOD_PLUGIN)  # underscore -> always skipped

    registry = load_plugins(tmp_path, enabled_names={"good"})

    assert "Test Action" in registry.town_actions
    assert len(registry.victory_hooks) == 1  # only "good" ran, not "disabled"


def test_none_means_load_all(tmp_path):
    write(tmp_path, "a.py", GOOD_PLUGIN)
    write(tmp_path, "b.py", GOOD_PLUGIN)
    registry = load_plugins(tmp_path, enabled_names=None)
    assert len(registry.victory_hooks) == 2


def test_broken_plugin_does_not_crash_the_loader(tmp_path):
    write(tmp_path, "ok.py", GOOD_PLUGIN)
    write(tmp_path, "broken.py", BROKEN_PLUGIN)
    registry = load_plugins(tmp_path, enabled_names={"ok", "broken"})
    assert "Test Action" in registry.town_actions  # the good one still loaded


def test_available_themes_lists_only_folders_with_css(tmp_path):
    (tmp_path / "dark-fantasy").mkdir()
    (tmp_path / "dark-fantasy" / "theme.css").write_text("body{}")
    (tmp_path / "light-parchment").mkdir()
    (tmp_path / "light-parchment" / "theme.css").write_text("body{}")
    (tmp_path / "not-a-theme").mkdir()  # no theme.css -> ignored

    assert available_themes(tmp_path) == ["dark-fantasy", "light-parchment"]
