#!/usr/bin/env python3
"""Install the embedded OpenCode agents, safety plugin, and on-demand skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

PRIMARY_AGENT = Path("agents/embedded-engineer.md")
MANAGED_FILES = (
    (
        Path(".opencode") / "skills" / "android-device-workflow" / "SKILL.md",
        Path("skills") / "android-device-workflow" / "SKILL.md",
    ),
    (
        Path(".opencode") / "skills" / "erd-knowledge" / "SKILL.md",
        Path("skills") / "erd-knowledge" / "SKILL.md",
    ),
    (Path(".opencode") / PRIMARY_AGENT, PRIMARY_AGENT),
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
        Path(".opencode/plugins/embedded-repository-inspection/index.ts"),
        Path("plugins/embedded-repository-inspection/index.ts"),
    ),
)
LEGACY_PLUGIN = Path("plugins/embedded-repository-inspection.ts")
ERD_RULE_ANCHOR = (
    b"  # Optional local ERD checkout rules are inserted here by the installer."
)
ERD_RULE_COMMENT = (
    b"  # Machine-local ERD checkout: keep this after the external directory catch-all."
)
EXTERNAL_DIRECTORY_DEFAULT = (
    b'  - { action: external_directory, resource: "*", effect: ask }'
)
EDIT_DEFAULT = b'  - { action: edit, resource: "*", effect: allow }'


def mentions_legacy_plugin(text: str) -> bool:
    """Find raw mentions and decoded JSON strings, ignoring JSONC comment syntax."""
    if LEGACY_PLUGIN.name in text:
        return True
    # Match complete strings OR comments, so quotes inside a comment cannot
    # consume the beginning of a real configuration string. Do not rewrite or
    # otherwise interpret user configuration. JSONC still uses JSON strings.
    tokens = re.finditer(r'"(?:[^"\\]|\\.)*"|//[^\r\n]*|/\*[\s\S]*?\*/', text)
    for token in tokens:
        if not token.group().startswith('"'):
            continue
        try:
            value = json.loads(token.group())
        except json.JSONDecodeError:
            continue
        if LEGACY_PLUGIN.name in value:
            return True
    return False


def preflight_upgrade(config_dir: Path) -> tuple[Path, Path] | None:
    """Reject stale explicit references and plan a non-destructive V1 backup."""
    # Do not rewrite user-owned JSONC or risk dropping unrelated settings.
    # Conservatively include commented references in this manual migration check.
    for name in ("opencode.json", "opencode.jsonc"):
        config_path = config_dir / name
        if config_path.is_file() and mentions_legacy_plugin(
            config_path.read_text(encoding="utf-8-sig")
        ):
            raise ValueError(
                f"Update the legacy plugin reference in {config_path} before "
                "installing: use plugins with the directory "
                "./plugins/embedded-repository-inspection (no .ts), or remove "
                "the entry to use automatic discovery. Preserve other settings; "
                "the installer does not rewrite user configuration."
            )

    legacy = config_dir / LEGACY_PLUGIN
    is_symlink = legacy.is_symlink()
    if not is_symlink and not legacy.exists():
        return None
    if is_symlink or not legacy.is_file():
        raise ValueError(f"Expected a regular legacy plugin file: {legacy}")
    backup = legacy.with_suffix(".ts.v1-backup")
    number = 1
    while backup.exists() or backup.is_symlink():
        backup = legacy.with_suffix(f".ts.v1-backup.{number}")
        number += 1
    return legacy, backup


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


def render_erd_rules(source: bytes, checkout: Path) -> bytes:
    """Render the primary profile for one exact, canonical checkout directory."""
    canonical = checkout.expanduser().resolve(strict=True)
    path = canonical.as_posix()
    if (
        canonical == canonical.parent
        or any(character in path for character in "*?\\")
        or not path.isprintable()
    ):
        raise ValueError(f"ERD checkout requires a literal, non-root path: {canonical}")
    if not (canonical / "README.md").is_file() or not (canonical / "erd").is_dir():
        raise ValueError(f"Expected README.md and erd/ in ERD checkout: {canonical}")
    lines = source.splitlines(keepends=True)
    anchors = [
        i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == ERD_RULE_ANCHOR
    ]
    if len(anchors) != 1 or not lines[anchors[0]].endswith(b"\n"):
        raise ValueError("Expected exactly one ERD rules anchor in the primary profile")
    anchor = anchors[0]
    profile_lines = source.splitlines()
    if (
        not profile_lines[0] == b"---"
        or b"---" not in profile_lines[1:]
        or anchor >= profile_lines.index(b"---", 1)
        or any(
            profile_lines.count(rule) != 1 or profile_lines.index(rule) >= anchor
            for rule in (EXTERNAL_DIRECTORY_DEFAULT, EDIT_DEFAULT)
        )
    ):
        raise ValueError("ERD rules anchor must follow the primary permission defaults")
    newline = b"\r\n" if lines[anchor].endswith(b"\r\n") else b"\n"
    resource = json.dumps(f"{path}/*", ensure_ascii=False)
    entries = [
        f"  - {{ action: {action}, resource: {resource}, effect: {effect} }}".encode(
            "utf-8"
        )
        for action, effect in (("external_directory", "allow"), ("edit", "deny"))
    ]
    lines.insert(anchor + 1, newline.join((ERD_RULE_COMMENT, *entries, b"")))
    return b"".join(lines)


def copy_atomically(
    source_path: Path, target_path: Path, *, rendered: bytes | None = None
) -> None:
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
            if rendered is None:
                with source_path.open("rb") as source_file:
                    shutil.copyfileobj(source_file, temporary_file)
            else:
                temporary_file.write(rendered)

        shutil.copystat(source_path, temporary_path)
        temporary_path.replace(target_path)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def install(
    repository_root: Path,
    config_dir: Path,
    dry_run: bool = False,
    *,
    erd_checkout: Path | None = None,
    clear_erd_checkout: bool = False,
) -> list[str]:
    """Install managed files and return their status messages."""
    sources = managed_sources(repository_root)
    legacy_backup = preflight_upgrade(config_dir)
    primary = config_dir / PRIMARY_AGENT
    if erd_checkout is not None and clear_erd_checkout:
        raise ValueError("Choose --erd-checkout or --clear-erd-checkout, not both")
    if erd_checkout is not None:
        primary_source = next(
            source for source, target in sources if target == PRIMARY_AGENT
        )
        if primary.parent.resolve() == primary_source.parent.resolve() or (
            primary.exists() and primary.samefile(primary_source)
        ):
            raise ValueError("Cannot render local ERD rules into the source profile")
        rendered = render_erd_rules(primary_source.read_bytes(), erd_checkout)
    else:
        rendered = None
        if (
            not clear_erd_checkout
            and primary.is_file()
            and ERD_RULE_COMMENT in primary.read_bytes().splitlines()
        ):
            raise ValueError(
                "The installed profile has local ERD rules. Pass --erd-checkout PATH "
                "to keep them or --clear-erd-checkout to remove them."
            )
    results: list[str] = []
    for source_path, target_relative_path in sources:
        target_path = config_dir / target_relative_path
        content = rendered if target_relative_path == PRIMARY_AGENT else None
        unchanged = (
            files_match(source_path, target_path)
            if content is None
            else target_path.is_file() and target_path.read_bytes() == content
        )
        if unchanged:
            results.append(f"unchanged {target_path}")
            continue

        action = "install" if not target_path.exists() else "update"
        results.append(f"{action} {target_path}")
        if not dry_run:
            if content is None:
                copy_atomically(source_path, target_path)
            else:
                copy_atomically(source_path, target_path, rendered=content)

    if legacy_backup is not None:
        legacy, backup = legacy_backup
        results.append(f"backup {legacy} -> {backup}")
        if not dry_run:
            legacy.rename(backup)

    return results


def nonempty_path(value: str) -> Path:
    if not value:
        raise argparse.ArgumentTypeError("expected a non-empty ERD checkout path")
    return Path(value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the embedded OpenCode agents, plugin, and skills globally."
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
    erd = parser.add_mutually_exclusive_group()
    erd.add_argument(
        "--erd-checkout",
        type=nonempty_path,
        metavar="PATH",
        help="Allow primary-agent ERD lookups and deny editor writes in this checkout",
    )
    erd.add_argument(
        "--clear-erd-checkout",
        action="store_true",
        help="Install the stock primary profile, removing its local ERD rules",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, script_path: Path | None = None) -> int:
    args = parse_args(argv)
    repository_root = source_root(script_path or Path(__file__))
    config_dir = args.config_dir.expanduser()

    try:
        results = install(
            repository_root,
            config_dir,
            args.dry_run,
            erd_checkout=args.erd_checkout,
            clear_erd_checkout=args.clear_erd_checkout,
        )
    except (OSError, ValueError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)

    if args.dry_run:
        print("Dry run only; no files were changed.")
    else:
        print("OpenCode reloads configuration automatically; use /reload if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
