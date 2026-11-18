#!/usr/bin/env python3
"""Render native shell permissions from the shared policy, without a server.

OpenCode's file-based agent config can load after a user plugin transform.
Checked-in native rules keep the policy effective regardless of that order,
including when the runtime plugin is missing or fails to load.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".opencode/agents"
PLUGIN = ROOT / ".opencode/plugins/embedded-repository-inspection/index.ts"
BEGIN = "  # BEGIN generated shell policy (scripts/sync_agent_shell_policy.py)"
END = "  # END generated shell policy"


def shell_policy() -> dict:
    agents = {
        path.stem: {"permissions": []} for path in sorted(AGENTS.glob("embedded-*.md"))
    }
    result = subprocess.run(
        ["node", str(ROOT / "scripts/evaluate_inspection_plugin.mjs"), str(PLUGIN)],
        input=json.dumps(agents),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def render(text: str, rules: list[dict]) -> str:
    opening, header, body = text.split("---", 2)
    if BEGIN in header:
        before, generated = header.split(BEGIN, 1)
        _, after = generated.split(END, 1)
        header = before + after.lstrip("\n")
    lines = [BEGIN]
    for rule in rules:
        resource = json.dumps(rule["resource"])
        lines.append(
            f"  - {{ action: shell, resource: {resource}, effect: {rule['effect']} }}"
        )
    lines.append(END)
    return (
        opening + "---" + header.rstrip("\n") + "\n" + "\n".join(lines) + "\n---" + body
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update generated rules.")
    args = parser.parse_args()
    different = False
    for name, agent in shell_policy().items():
        path = AGENTS / f"{name}.md"
        current = path.read_text(encoding="utf-8")
        expected = render(current, agent["permissions"])
        if expected != current:
            different = True
            print(f"{'update' if args.write else 'outdated'} {path}")
            if args.write:
                path.write_text(expected, encoding="utf-8", newline="\n")
    if different and not args.write:
        print("Run python scripts/sync_agent_shell_policy.py --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
