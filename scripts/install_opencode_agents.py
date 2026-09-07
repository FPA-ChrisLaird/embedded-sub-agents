#!/usr/bin/env python3
"""Install the embedded OpenCode agents and their shared safety plugin."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MANAGED_FILES = (
    (
        Path(".opencode") / "agents" / "embedded-engineer.md",
        Path("agents") / "embedded-engineer.md",
    ),
    (
        Path(".opencode") / "agents" / "embedded-architecture-analyst.md",
        Path("agents") / "embedded-architecture-analyst.md",
    ),
    (
        Path(".opencode") / "agents" / "embedded-c-quality-reviewer.md",
        Path("agents") / "embedded-c-quality-reviewer.md",
    ),
    (
        Path(".opencode") / "agents" / "embedded-build-analyzer.md",
        Path("agents") / "embedded-build-analyzer.md",
    ),
    (
        Path(".opencode") / "plugins" / "embedded-repository-inspection.ts",
        Path("plugins") / "embedded-repository-inspection.ts",
    ),
)


def default_config_dir() -> Path:
    """Return OpenCode's XDG-compatible global configuration directory."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "opencode"
    return Path.home() / ".config" / "opencode"


def source_root(script_path: Path) -> Path:
    """Return the repository root for an installer located in scripts/."""
    return script_path.resolve().parent.parent


def managed_sources(repository_root: Path) -> list[tuple[Path, Path]]:
    """Return verified source files paired with their config-relative targets."""
    sources: list[tuple[Path, Path]] = []
    missing: list[Path] = []

    for source_relative_path, target_relative_path in MANAGED_FILES:
        source_path = repository_root / source_relative_path
        if not source_path.is_file():
            missing.append(source_path)
        else:
            sources.append((source_path, target_relative_path))

    if missing:
        missing_paths = "\n".join(f"  {path}" for path in missing)
        raise FileNotFoundError(
            f"Missing required OpenCode suite source files:\n{missing_paths}"
        )

    return sources


def files_match(source_path: Path, target_path: Path) -> bool:
    """Return whether a target already has identical content to its source."""
    return (
        target_path.is_file() and source_path.read_bytes() == target_path.read_bytes()
    )


def copy_atomically(source_path: Path, target_path: Path) -> None:
    """Copy a file through a sibling temporary file to avoid partial targets."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            with source_path.open("rb") as source_file:
                shutil.copyfileobj(source_file, temporary_file)

        shutil.copystat(source_path, temporary_path)
        temporary_path.replace(target_path)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def install(
    repository_root: Path, config_dir: Path, dry_run: bool = False
) -> list[str]:
    """Install managed files and return their status messages."""
    results: list[str] = []
    for source_path, target_relative_path in managed_sources(repository_root):
        target_path = config_dir / target_relative_path
        if files_match(source_path, target_path):
            results.append(f"unchanged {target_path}")
            continue

        action = "install" if not target_path.exists() else "update"
        results.append(f"{action} {target_path}")
        if not dry_run:
            copy_atomically(source_path, target_path)

    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the embedded OpenCode agents and safety plugin globally."
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=default_config_dir(),
        help="OpenCode configuration directory (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, script_path: Path | None = None) -> int:
    args = parse_args(argv)
    repository_root = source_root(script_path or Path(__file__))
    config_dir = args.config_dir.expanduser()

    try:
        results = install(repository_root, config_dir, args.dry_run)
    except (FileNotFoundError, OSError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)

    if args.dry_run:
        print("Dry run only; no files were changed.")
    else:
        print("Restart OpenCode to load the installed agents and plugin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
