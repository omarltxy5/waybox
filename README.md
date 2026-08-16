# Waybox

A tiny, local-first file router for your filesystem.

Drop files into one directory. Waybox moves them to destinations you define with explicit rules.

No AI. No cloud. No database. No account. No guessing.

## Why Waybox?

Your Downloads folder becomes a landfill because apparently every application on your computer believes its files belong there.

Waybox gives you one controlled drop directory:

<pre>
~/Downloads
    │
    ▼
  Waybox
    │
    ├── Documents  →  ~/Documents
    ├── Images     →  ~/Pictures
    └── Archives   →  ~/Archives
</pre>

Rules are explicit and predictable. If a file doesn't match a rule, Waybox leaves it alone.

## Features

- Explicit file-routing rules
- Interactive setup
- One-shot organization
- Detects new, changed, and removed files with snapshots
- Optional continuous watch mode
- Dry-run support
- Move history
- Conservative undo
- Never overwrites existing files
- Never automatically deletes files
- Local-only
- Dependency-free at runtime
- Cross-platform
- Human-readable TOML configuration

## Quick start

Requires Python 3.11+.

Clone the repository:

    git clone https://github.com/omarltxy5/waybox.git
    cd waybox

Initialize Waybox:

    python waybox.py init

The setup wizard asks where your files live and which types you want Waybox to organize.

You can select individual categories or use:

    all

to enable every supported file type.

Preview what would happen:

    python waybox.py organize --dry-run

Then organize the files:

    python waybox.py organize

## Everyday use

Check what changed since Waybox last checked the directory:

    waybox status

Example:

    Waybox
    ~/Downloads

    3 new files:

      + invoice.pdf
      + screenshot.png
      + archive.zip

Organize matching files:

    waybox organize

Undo the most recent move:

    waybox undo

Undo several moves:

    waybox undo 3

For continuous organization:

    waybox watch

Watch mode is optional. Waybox can detect changes using its local snapshot without running continuously.

## Configuration

Waybox uses a small TOML configuration file.

Example:

    [waybox]
    directory = "~/Downloads"

    [[rule]]
    extension = ".pdf"
    destination = "~/Documents/PDF"

    [[rule]]
    extension = ".png"
    destination = "~/Pictures"

    [[rule]]
    extension = ".zip"
    destination = "~/Archives"

Rules are evaluated from top to bottom.

You can edit the configuration manually after running `waybox init`.

The default configuration location is:

    ~/.config/waybox/config.toml

You can override the configuration location with the `WAYBOX_CONFIG` environment variable.

## Safety

Waybox is deliberately conservative.

It will:

- never overwrite an existing destination file
- never automatically delete files
- leave unmatched files alone
- support dry-run before moving anything
- record successful moves
- refuse unsafe undo operations

A move is only added to history after the filesystem operation succeeds.

If something looks wrong, use:

    waybox organize --dry-run

before actually moving anything.

## Snapshots

Waybox keeps a small local snapshot of the configured directory.

The snapshot stores file metadata rather than file contents:

- relative path
- file size
- modification time

This allows:

    waybox status

to detect what changed since the previous check without requiring Waybox to run continuously.

The snapshot is not a backup and does not contain copies of your files.

## Settings

Run:

    waybox settings

to change the configured directory and manage local Waybox settings.

## Installing as a command

For development, running:

    python waybox.py ...

is enough.

Waybox also includes PATH setup through its settings interface so it can be invoked directly as:

    waybox organize

## Project philosophy

Waybox intentionally does less.

It does not try to classify your files with AI, synchronize them to the cloud, build a database of your filesystem, or replace your file manager.

You define the rules. Waybox follows them.

## Development

Run the verification suite:

    python verify_waybox.py

Run the tests:

    python -m pytest

Check compilation:

    python -m py_compile waybox.py test_waybox.py verify_waybox.py

## License

Waybox is free and open-source software licensed under the GNU General Public License v3.0 or later.

See [LICENSE](LICENSE).
