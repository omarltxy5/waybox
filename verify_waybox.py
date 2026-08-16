"""Dependency-free smoke checks for waybox's core behavior."""
import tempfile
import builtins
import contextlib
import io
from pathlib import Path
import waybox

with tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary); root, out = base / "in box [safe]", base / "out folder"; root.mkdir()
    config = base / "config.toml"; state = base / "history.jsonl"
    config.write_text(f'[waybox]\ndirectory = "{root.as_posix()}"\nstate = "{state.as_posix()}"\n\n[[rule]]\nextension = ".pdf"\ndestination = "{out.as_posix()}"\n')
    (root / "report.pdf").write_text("pdf"); (root / "notes.txt").write_text("txt")
    assert waybox.organize(config, True) == 1 and (root / "report.pdf").exists() and not state.exists()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert waybox.status(config) == 0
    assert "No changes" in output.getvalue()
    (root / "new.pdf").write_text("new")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        waybox.status(config)
    assert "+ new.pdf" in output.getvalue()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        waybox.status(config)
    assert "No changes" in output.getvalue()
    (root / "gone.pdf").write_text("gone")
    waybox.status(config)
    (root / "gone.pdf").unlink()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        waybox.status(config)
    assert "- gone.pdf" in output.getvalue()
    assert waybox.organize(config) == 2 and (out / "report.pdf").exists() and "report.pdf" in state.read_text()
    assert waybox.undo(config, 1) == 1 and (root / "report.pdf").read_text() == "pdf"
    (root / "report.pdf").write_text("new")
    (out / "report.pdf").write_text("old")
    assert waybox.organize(config) == 0 and (root / "report.pdf").read_text() == "new"
    (root / "broken.pdf").write_text("broken"); out.mkdir(exist_ok=True); (out / "broken.pdf").write_text("keep")
    assert waybox.organize(config) == 0 and (root / "broken.pdf").exists()
    original_move = waybox.shutil.move
    waybox.shutil.move = lambda *args: (_ for _ in ()).throw(OSError("blocked"))
    (root / "failed.pdf").write_text("failed")
    before = state.read_text()
    assert waybox.organize(config) == 0 and state.read_text() == before and (root / "failed.pdf").exists()
    waybox.shutil.move = original_move

    setup_dir = base / "setup"
    setup_dir.mkdir()
    answers = iter([str(setup_dir), "all", str(out), str(out), str(out), str(out), str(out)])
    original_input = builtins.input
    builtins.input = lambda prompt="": next(answers)
    setup_config = base / "setup.toml"
    waybox.init_config(setup_config)
    builtins.input = original_input
    setup_data = waybox.load_config(setup_config)
    assert len(setup_data["rule"]) == sum(len(exts) for exts in waybox.CATEGORIES.values())
    assert waybox.snapshot_path(setup_config).exists()
print("verification passed")
