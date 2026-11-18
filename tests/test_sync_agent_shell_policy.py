from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "sync_agent_shell_policy", ROOT / "scripts/sync_agent_shell_policy.py"
)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class SyncAgentShellPolicyTests(unittest.TestCase):
    def test_render_preserves_non_generated_header_and_entire_body(self) -> None:
        header = (
            "\nmode: subagent\npermissions:\n"
            '  - { action: read, resource: "*", effect: allow }\n'
        )
        body = "\nKeep this complete prompt.\n---\nIncluding Markdown separators.\n"
        original = "---" + header + "---" + body
        rules = [{"action": "shell", "resource": "*", "effect": "deny"}]

        rendered = GENERATOR.render(original, rules)

        self.assertTrue(rendered.startswith("---" + header + GENERATOR.BEGIN))
        self.assertTrue(rendered.endswith("---" + body))
        self.assertEqual(rendered, GENERATOR.render(rendered, rules))
        updated = GENERATOR.render(
            rendered,
            [{"action": "shell", "resource": "echo approved", "effect": "allow"}],
        )
        self.assertNotIn('action: shell, resource: "*"', updated)
        self.assertEqual(1, updated.count(GENERATOR.BEGIN))
        self.assertTrue(updated.endswith("---" + body))

    def test_cli_check_does_not_write_and_write_converges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            path = agents / "embedded-test.md"
            original = "---\npermissions:\n---\nNever change this prompt.\n"
            path.write_text(original, encoding="utf-8")
            policy = {
                "embedded-test": {
                    "permissions": [
                        {"action": "shell", "resource": "*", "effect": "deny"}
                    ]
                }
            }
            with mock.patch.object(GENERATOR, "AGENTS", agents), mock.patch.object(
                GENERATOR, "shell_policy", return_value=policy
            ), contextlib.redirect_stdout(io.StringIO()):
                with mock.patch("sys.argv", ["sync_agent_shell_policy.py"]):
                    self.assertEqual(1, GENERATOR.main())
                self.assertEqual(original, path.read_text(encoding="utf-8"))
                with mock.patch("sys.argv", ["sync_agent_shell_policy.py", "--write"]):
                    self.assertEqual(0, GENERATOR.main())
                expected = GENERATOR.render(
                    original, policy["embedded-test"]["permissions"]
                )
                self.assertEqual(expected, path.read_text(encoding="utf-8"))
                with mock.patch("sys.argv", ["sync_agent_shell_policy.py"]):
                    self.assertEqual(0, GENERATOR.main())
