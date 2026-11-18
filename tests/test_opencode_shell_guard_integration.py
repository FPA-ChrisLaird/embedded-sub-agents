"""Opt-in test of the actual OpenCode shell tool, using a local model fixture."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

PLUGIN = (
    Path(__file__).resolve().parents[1]
    / ".opencode/plugins/embedded-repository-inspection/index.ts"
)
FIRST = "echo opencode-shell-guard-first"
SECOND = "echo opencode-shell-guard-second"
COMPOUND = f"{FIRST}; {SECOND}"


class FixtureModel(BaseHTTPRequestHandler):
    """Return two fixed, harmless calls; do not contact a real provider."""

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        shell_offered = any(
            tool.get("function", {}).get("name") == "shell"
            for tool in request.get("tools", [])
        )
        prior_calls = sum(message["role"] == "tool" for message in request["messages"])
        if shell_offered and prior_calls < 2:
            command = (FIRST, COMPOUND)[prior_calls]
            delta = {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": f"call_shell_fixture_{prior_calls}",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": json.dumps({"command": command}),
                        },
                    }
                ]
            }
            finish = "tool_calls"
        else:
            delta, finish = {"content": "Shell guard fixture"}, "stop"

        choices = [
            {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None},
            {"index": 0, "delta": delta, "finish_reason": None},
            {"index": 0, "delta": {}, "finish_reason": finish},
        ]
        chunks = [
            {
                "object": "chat.completion.chunk",
                "id": "chatcmpl-shell-fixture",
                "model": "smoke",
                "created": 0,
                "choices": [choice],
            }
            for choice in choices
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        encoded = (body + "data: [DONE]\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_fixture(root: Path, binary: str, port: int) -> list[dict]:
    opencode = root / ".opencode"
    plugin = opencode / "plugins/embedded-repository-inspection/index.ts"
    plugin.parent.mkdir(parents=True)
    shutil.copyfile(PLUGIN, plugin)
    (opencode / "opencode.json").write_text(
        json.dumps(
            {
                "default_agent": "embedded-engineer",
                "model": "shell-fixture/smoke",
                "providers": {
                    "shell-fixture": {
                        "package": "@opencode/ai/providers/openai-compatible",
                        "settings": {
                            "baseURL": f"http://127.0.0.1:{port}/v1",
                            "apiKey": "local-fixture-only",
                        },
                        "models": {"smoke": {"capabilities": {"tools": True}}},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    agents = opencode / "agents"
    agents.mkdir()
    (agents / "embedded-engineer.md").write_text(
        "---\nmode: primary\npermissions:\n"
        '  - { action: "*", resource: "*", effect: deny }\n'
        f'  - {{ action: shell, resource: "{FIRST}", effect: allow }}\n'
        f'  - {{ action: shell, resource: "{SECOND}", effect: allow }}\n'
        "---\nRun only the harmless shell fixture.\n",
        encoding="utf-8",
    )
    # A Git hook can export the original repository's directory and index.
    # The standalone process must discover the scratch project instead.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("OPENCODE_", "GIT_"))
    }
    env.update(
        PWD=str(root),
        XDG_CONFIG_HOME=str(root / "config"),
        XDG_DATA_HOME=str(root / "data"),
        XDG_STATE_HOME=str(root / "state"),
        OPENCODE_DB=":memory:",
    )
    result = subprocess.run(
        [
            binary,
            "--standalone",
            "run",
            "--archived",
            "--format",
            "json",
            "--agent",
            "embedded-engineer",
            "--model",
            "shell-fixture/smoke",
            "Run the shell guard fixture.",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=75,
    )
    if result.returncode:
        raise AssertionError(f"OpenCode failed:\n{result.stdout}\n{result.stderr}")
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return [
        event["part"]["state"]
        for event in events
        if event.get("part", {}).get("tool") == "shell"
        and event["part"]["state"]["status"] in {"completed", "error"}
    ]


@unittest.skipUnless(
    os.environ.get("OPENCODE_SMOKE_TEST") == "1", "requires OpenCode V2"
)
class ShellGuardIntegrationTests(unittest.TestCase):
    def test_real_shell_tool_allows_single_command_and_blocks_compound(self) -> None:
        binary = shutil.which("opencode")
        self.assertIsNotNone(binary, "install OpenCode V2 or unset OPENCODE_SMOKE_TEST")
        assert binary is not None
        with tempfile.TemporaryDirectory() as directory, ThreadingHTTPServer(
            ("127.0.0.1", 0), FixtureModel
        ) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                calls = run_fixture(Path(directory), binary, server.server_port)
            finally:
                server.shutdown()
                thread.join()

        self.assertEqual(len(calls), 2, calls)
        single, compound = calls
        self.assertEqual(single["input"]["command"], FIRST)
        self.assertEqual(single["status"], "completed")
        self.assertIn("opencode-shell-guard-first", single["output"])
        self.assertEqual(compound["input"]["command"], COMPOUND)
        self.assertEqual(compound["status"], "error")
        self.assertIn("Shell composition is disabled", compound["error"])
