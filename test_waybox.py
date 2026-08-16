import json
from pathlib import Path

import waybox


def write_config(path: Path, root: Path, destination: Path):
    path.write_text(f'''[waybox]\ndirectory = "{root.as_posix()}"\nstate = "{(path.parent / "history.jsonl").as_posix()}"\n\n[[rule]]\nextension = ".pdf"\ndestination = "{destination.as_posix()}"\n''')


def test_dry_run_does_not_move(tmp_path):
    root, destination = tmp_path / "in", tmp_path / "out"
    root.mkdir(); (root / "a.pdf").write_text("x")
    config = tmp_path / "config.toml"; write_config(config, root, destination)
    assert waybox.organize(config, dry_run=True) == 1
    assert (root / "a.pdf").exists()


def test_move_and_undo(tmp_path):
    root, destination = tmp_path / "in", tmp_path / "out"
    root.mkdir(); (root / "a.pdf").write_text("x")
    config = tmp_path / "config.toml"; write_config(config, root, destination)
    assert waybox.organize(config) == 1
    assert (destination / "a.pdf").exists()
    assert waybox.undo(config, 1) == 1
    assert (root / "a.pdf").exists()
    entry = (tmp_path / "history.jsonl").read_text()
    assert entry == ""


def test_existing_destination_is_safe(tmp_path):
    root, destination = tmp_path / "in", tmp_path / "out"
    root.mkdir(); destination.mkdir(); (root / "a.pdf").write_text("new"); (destination / "a.pdf").write_text("old")
    config = tmp_path / "config.toml"; write_config(config, root, destination)
    assert waybox.organize(config) == 0
    assert (root / "a.pdf").read_text() == "new"
    assert (destination / "a.pdf").read_text() == "old"
