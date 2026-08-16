# waybox

`waybox` is a small command-line utility that moves files from one local directory to destinations defined by explicit rules.

It has no GUI, cloud service, account system, database, or third-party runtime dependencies. Requires Python 3.11+.
## Why use Waybox?

Use Waybox when you want a predictable place to drop files without giving up control over where they go. You define simple rules yourself, preview the result before moving anything, and keep a readable history that can undo recent moves. It is useful for keeping downloads, project folders, scans, media, or shared local drop folders tidy while staying local, transparent, and easy to inspect.

Waybox is deliberately small: it does not guess what files mean, upload anything, rename files unexpectedly, overwrite collisions, or run as a background service unless you choose to use watch mode.

## Install

Copy `waybox.py` somewhere convenient and run it with Python:

```sh
python waybox.py --help
```

On macOS or Linux, it may be made executable with `chmod +x waybox.py`.

### Add the command to `PATH`

The easiest way to add Waybox to your `PATH` is to run the interactive settings menu, which can automatically create a launcher or setup the path configuration for you:

```sh
python waybox.py settings
```

Alternatively, you can configure your `PATH` manually:

**macOS or Linux:** Put `waybox.py` in a personal bin directory and add that directory to your `PATH`. 

```sh
mkdir -p "\$HOME/.local/bin"
cp waybox.py "\$HOME/.local/bin/waybox"
chmod +x "\$HOME/.local/bin/waybox"
export PATH="HOME/.local/bin:PATH"
```

Add the `export PATH=...` line to your shell profile to keep it after restarting the terminal.

**Windows:** Create a directory such as `%USERPROFILE%\bin`, copy `waybox.py` there, and add that directory to the User `Path` environment variable in **System Properties â†’ Environment Variables**. Then run it as `python waybox.py`, or create a `waybox.cmd` launcher in that directory:

```bat
@python "%~dp0waybox.py" %*
```

After opening a new terminal, `waybox --help` should work.

## Quick start

```sh
python waybox.py init
python waybox.py settings
python waybox.py organize --dry-run
python waybox.py organize
python waybox.py status
python waybox.py undo
```

Use `python waybox.py watch` to repeat organization every two seconds. Stop it with `Ctrl+C`.

`init` is an interactive setup wizard. It asks for the directory to process, the categories to organize, and a destination for each category. Supported categories are `documents`, `images`, `video`, `audio`, and `archives`; enter `all` or a comma-separated list. It creates explicit extension rules and an initial snapshot of the directory.

Run `python waybox.py settings` for a compact interactive menu that lets you change the watched directory or create a launcher for adding Waybox to `PATH`. Rules and destinations remain in the TOML file so they stay visible and easy to edit.

The directory setting checks that the path exists and is a directory. If a path is misspelled, Waybox suggests similarly named directories when it can. It never creates a directory silently from this menu.

Waybox watches for files inside the configured directory. It does not track files moved out of that directory; removing a file manually therefore does not create a history entry.

## Configuration

The default configuration is `~/.config/waybox/config.toml`. Select another file with `--config` or the `WAYBOX_CONFIG` environment variable.

```toml
[waybox]
directory = "~/Waybox"

[[rule]]
extension = ".pdf"
destination = "~/Documents/PDF"

[[rule]]
pattern = "photo-*"
destination = "~/Pictures"
```

Rules are checked from top to bottom. The first matching rule is used. `extension` matches case-insensitively; `pattern` uses shell-style wildcards. Every rule needs a `destination`. Both conditions must match when both are present. Original filenames are always preserved.

On Windows, forward slashes avoid TOML backslash escaping:

```toml
directory = "C:/Users/Example/Waybox"
destination = "C:/Users/Example/Documents/PDF"
```

Only files directly inside the configured directory are scanned. Unmatched files remain there.

## Commands

Each command has one focused job:

- `waybox init` starts the setup wizard, writes the TOML configuration, and creates the initial snapshot. Existing files are recorded as already known.
- `waybox settings` changes the watched directory, validates it, suggests close matches for typos, and can create a PATH launcher.
- `waybox organize` scans once, applies rules in order, moves matching files, skips collisions, and records successful moves.
- `waybox organize --dry-run` previews those moves without changing files, directories, history, or snapshots.
- `waybox watch` repeats organization at a regular interval. It is optional; stop it with `Ctrl+C`.
- `waybox status` compares the directory with `snapshot.json`, reports new, removed, and changed files, then updates the snapshot.
- `waybox undo [COUNT]` reverses recent successful moves only when doing so cannot overwrite an existing source file.

Examples:

```sh
waybox init
waybox settings
waybox organize --dry-run
waybox organize
waybox status
waybox undo
```
- `waybox init` creates an example configuration and will not overwrite one.
- `waybox organize` processes the directory once.
- `waybox organize --dry-run` previews moves without creating directories, moving files, or writing history.
- `waybox watch` repeats organization at a regular interval; use `--interval SECONDS` to change it.
- `waybox status` compares the directory with the previous snapshot and reports new, removed, and changed files. It does not move anything.
- `waybox undo [COUNT]` reverses recent successful moves, one by default.

Watch mode can be stopped cleanly with `Ctrl+C`.

## Safety

- Existing destination files are never overwritten.
- Files are never automatically deleted.
- Failed moves are not added to history.
- History is flushed to disk after each successful move.
- Undo never overwrites a file that already exists at the original source path.
- Undo skips missing or conflicting files rather than guessing.

History is readable JSON Lines stored beside the configuration by default at `~/.config/waybox/history.jsonl`. Set `state` under `[waybox]` to choose another path. The status snapshot is stored as `snapshot.json` beside the configuration and contains only relative paths, sizes, and modification times.

There is a small unavoidable boundary between completing a filesystem move and recording it. If interrupted during that boundary, the file remains safe, but the move may need manual restoration if it is not yet in history.

## Development

Run the dependency-free checks:

```sh
python verify_waybox.py
python -m py_compile waybox.py verify_waybox.py test_waybox.py
python -m pytest -q
```

## License

GPL-3.0-or-later. See `LICENSE`.

