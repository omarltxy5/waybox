#!/usr/bin/env python3
"""A small, safe file organizer."""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import os
import shutil
import sys
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

CATEGORIES = {
    "documents": (".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"),
    "images": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff"),
    "video": (".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"),
    "audio": (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"),
    "archives": (".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tgz"),
}


def load_config(path: Path) -> dict:
    if tomllib is None:
        raise RuntimeError("waybox requires Python 3.11 or newer")
    try:
        with path.open("rb") as stream:
            config = tomllib.load(stream)
    except FileNotFoundError:
        raise RuntimeError(f"config not found: {path}; run 'waybox init'")
    if not config.get("waybox", {}).get("directory"):
        raise RuntimeError("config must contain [waybox] directory")
    return config


def paths(config_path: Path, config: dict) -> tuple[Path, Path]:
    root = Path(config["waybox"]["directory"]).expanduser().resolve()
    history = Path(config["waybox"].get("state", config_path.parent / "history.jsonl")).expanduser()
    return root, history


def snapshot_path(config_path: Path) -> Path:
    return config_path.with_name("snapshot.json")


def snapshot(root: Path) -> dict[str, dict[str, int]]:
    if not root.is_dir():
        raise RuntimeError(f"directory not found: {root}; create it or update [waybox] directory")
    result = {}
    for file in root.iterdir():
        if file.is_file() and not file.name.startswith("."):
            stat = file.stat()
            result[str(file.relative_to(root))] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return result


def save_snapshot(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def init_snapshot(config_path: Path, config: dict) -> None:
    root, _ = paths(config_path, config)
    save_snapshot(snapshot_path(config_path), snapshot(root))


def validate_rules(config: dict) -> None:
    rules = config.get("rule", [])
    if not isinstance(rules, list):
        raise RuntimeError("rules must use [[rule]] sections")
    for number, rule in enumerate(rules, 1):
        if not isinstance(rule, dict) or not rule.get("destination"):
            raise RuntimeError(f"rule {number} needs a destination")
        unknown = set(rule) - {"extension", "pattern", "destination"}
        if unknown:
            names = ", ".join(sorted(unknown))
            raise RuntimeError(f"rule {number} has unsupported option(s): {names}")


def matching(file: Path, rule: dict) -> bool:
    return (not rule.get("extension") or file.suffix.lower() == str(rule["extension"]).lower()) and (
        not rule.get("pattern") or fnmatch.fnmatch(file.name, rule["pattern"])
    )


def move_plan(root: Path, config: dict) -> list[tuple[Path, Path]]:
    if not root.is_dir():
        raise RuntimeError(f"directory not found: {root}; create it or update [waybox] directory")
    plan = []
    for file in sorted(root.iterdir()):
        if not file.is_file() or file.name.startswith("."):
            continue
        for rule in config.get("rule", []):
            if matching(file, rule):
                plan.append((file, Path(str(rule["destination"])).expanduser() / file.name))
                break
    return plan


def record(history: Path, source: Path, target: Path) -> None:
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"source": str(source), "target": str(target)}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def organize(config_path: Path, dry_run: bool = False) -> int:
    config = load_config(config_path)
    validate_rules(config)
    root, history = paths(config_path, config)
    count = 0
    for source, target in move_plan(root, config):
        if target.exists():
            print(f"skip (exists): {source} -> {target}")
            continue
        print(f"{'would move' if dry_run else 'move'}: {source} -> {target}")
        if dry_run:
            count += 1
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                print(f"skip (exists): {source} -> {target}")
                continue
            shutil.move(str(source), str(target))
            record(history, source, target)
        except OSError as error:
            print(f"failed: {source} -> {target}: {error}", file=sys.stderr)
            continue
        count += 1
    return count


def status(config_path: Path) -> int:
    config = load_config(config_path)
    validate_rules(config)
    root, _ = paths(config_path, config)
    current = snapshot(root)
    path = snapshot_path(config_path)
    if not path.exists():
        save_snapshot(path, current)
        print("No changes since last check.")
        return 0
    previous = json.loads(path.read_text(encoding="utf-8"))
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    changed = sorted(name for name in set(current) & set(previous) if current[name] != previous[name])
    if not added and not removed and not changed:
        print("No changes since last check.")
    else:
        print(f"Waybox\n{root}\n\nSince last check:\n")
        for name in added:
            print(f"  + {name}")
        for name in removed:
            print(f"  - {name}")
        for name in changed:
            print(f"  * {name} (changed)")
        print(f"\n{len(added)} new, {len(removed)} removed, {len(changed)} changed.")
    save_snapshot(path, current)
    return 0


def undo(config_path: Path, count: int) -> int:
    if count < 1:
        raise RuntimeError("undo count must be positive")
    config = load_config(config_path)
    validate_rules(config)
    _, history = paths(config_path, config)
    if not history.exists():
        print("Nothing to undo.")
        return 0
    lines = [line for line in history.read_text(encoding="utf-8").splitlines() if line]
    undone = 0
    for index in range(len(lines) - 1, -1, -1):
        if undone == count:
            break
        entry = json.loads(lines[index])
        source, target = Path(entry["source"]), Path(entry["target"])
        if not target.is_file():
            print(f"skip (missing): {target}")
            continue
        if source.exists():
            print(f"skip (exists): {source}")
            continue
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(source))
        except OSError as error:
            print(f"failed: {target} -> {source}: {error}", file=sys.stderr)
            continue
        lines.pop(index)
        undone += 1
        print(f"undo: {target} -> {source}")
    history.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return undone


def init_config(path: Path) -> int:
    if path.exists():
        print(f"already exists: {path}")
        return 1
    print("Welcome to Waybox setup.\n")
    directory = input("Directory to process [~/Waybox]: ").strip() or "~/Waybox"
    directory_path = Path(directory).expanduser()
    if not directory_path.is_dir():
        print(f"Directory not found: {directory_path}")
        if input("Create it? [Y/n]: ").strip().lower() not in {"", "y", "yes"}:
            raise RuntimeError("setup needs an existing directory")
        directory_path.mkdir(parents=True, exist_ok=True)
    selected = input("Categories (documents, images, video, audio, archives, or all): ").strip().lower()
    names = [name for name in selected.replace(",", " ").split() if name]
    if "all" in names:
        names = list(CATEGORIES)
    names = list(dict.fromkeys(names))
    invalid = [name for name in names if name not in CATEGORIES]
    if not names or invalid:
        raise RuntimeError("choose one or more supported categories: documents, images, video, audio, archives, all")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[waybox]", f'directory = "{directory_path.resolve().as_posix()}"', ""]
    for name in names:
        destination = input(f"Destination for {name} [{Path.home() / name.title()}]: ").strip() or str(Path.home() / name.title())
        for extension in CATEGORIES[name]:
            lines.extend(["[[rule]]", f'extension = "{extension}"', f'destination = "{Path(destination).expanduser().as_posix()}"', ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    config = load_config(path)
    init_snapshot(path, config)
    print(f"created {path}")
    print(f"initial snapshot created: {snapshot_path(path)}")
    return 0


def settings(config_path: Path) -> int:
    if not config_path.exists():
        init_config(config_path)
    config = load_config(config_path)
    current = config["waybox"]["directory"]
    while True:
        print(f"Directory: {current}")
        print("[D] Change directory   [P] Add to PATH   [Q] Quit")
        choice = input("> ").strip().lower()
        if choice == "q" or not choice:
            return 0
        if choice == "p":
            add_to_path()
            continue
        if choice != "d":
            print("Choose D, P, or Q.")
            continue
        directory = input("Directory: ").strip()
        if not directory:
            print("No directory entered.")
            continue
        candidate = Path(directory).expanduser()
        if not candidate.is_dir():
            print(f"Directory not found: {candidate}")
            parent = candidate.parent if candidate.parent != candidate else Path.cwd()
            if parent.is_dir():
                names = [item.name for item in parent.iterdir() if item.is_dir()]
                close = difflib.get_close_matches(candidate.name, names, n=3, cutoff=0.6)
                if close:
                    print("Did you mean: " + ", ".join(str(parent / name) for name in close) + "?")
            continue
        text = config_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("directory ="):
                lines[index] = f'directory = "{candidate.resolve().as_posix()}"'
                break
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        current = candidate.resolve().as_posix()
        print(f"Saved directory: {current}")


def add_to_path() -> None:
    script = Path(__file__).resolve()
    if os.name == "nt":
        bin_dir = Path.home() / "bin"
        launcher = bin_dir / "waybox.cmd"
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher.write_text(f'@python "{script}" %*\n', encoding="utf-8")
        print(f"Created: {launcher}")
        print("Add this directory to your User Path, then open a new terminal:")
    else:
        bin_dir = Path.home() / ".local" / "bin"
        launcher = bin_dir / "waybox"
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher.write_text(f'#!/bin/sh\nexec python3 "{script}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
        print(f"Created: {launcher}")
        print("Add this line to your shell profile, then open a new terminal:")
    print(f'  PATH="{bin_dir}{os.pathsep}$PATH"')
    return 0


def main(argv: list[str] | None = None) -> int:
    default = Path(os.environ.get("WAYBOX_CONFIG", "~/.config/waybox/config.toml")).expanduser()
    parser = argparse.ArgumentParser(prog="waybox", description="Put files where your rules say they belong.")
    parser.add_argument("--config", type=Path, default=default)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create an example configuration")
    sub.add_parser("settings", help="set the watched directory")
    organize_parser = sub.add_parser("organize", help="move matching files once")
    organize_parser.add_argument("--dry-run", action="store_true")
    sub.add_parser("status", help="show recent moves")
    undo_parser = sub.add_parser("undo", help="reverse recent moves")
    undo_parser.add_argument("count", nargs="?", type=int, default=1)
    watch = sub.add_parser("watch", help="organize new files continuously")
    watch.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "init": return init_config(args.config)
        if args.command == "settings": return settings(args.config)
        if args.command == "organize": return organize(args.config, args.dry_run)
        if args.command == "status": return status(args.config)
        if args.command == "undo": return undo(args.config, args.count)
        while True:
            organize(args.config)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("waybox: stopped")
        return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(f"waybox: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
