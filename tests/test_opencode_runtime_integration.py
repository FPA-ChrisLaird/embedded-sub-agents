"""Opt-in OpenCode tool tests using isolated, local fixtures."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
from threading import Thread

OPENCODE_DIR = Path(__file__).resolve().parents[1] / ".opencode"
PLUGIN = Path("plugins/embedded-repository-inspection/index.ts")
MODEL = "runtime-fixture/smoke"
MCP_SERVER = "codebase-memory-mcp"
MCP_FIXTURE_TOOLS = ("search_graph", "index_repository", "delete_project")
SPECIALISTS = (
    "embedded-architecture-analyst",
    "embedded-c-quality-reviewer",
    "embedded-build-analyzer",
)
FIRST = "echo opencode-shell-guard-first"
SECOND = "echo opencode-shell-guard-second"
COMPOUND = f"{FIRST}; {SECOND}"


class FixtureModel(BaseHTTPRequestHandler):
    """Serve a deterministic response to the standalone test runtime."""

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        delta, finish = self.reply(request)
        choices = [
            {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None},
            {"index": 0, "delta": delta, "finish_reason": None},
            {"index": 0, "delta": {}, "finish_reason": finish},
        ]
        chunks = [
            {
                "object": "chat.completion.chunk",
                "id": "chatcmpl-runtime-fixture",
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

    def reply(self, request: dict) -> tuple[dict, str]:
        raise NotImplementedError


class ShellFixtureModel(FixtureModel):
    """Return two fixed, harmless calls; do not contact a real provider."""

    def reply(self, request: dict) -> tuple[dict, str]:
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
            return delta, "tool_calls"
        return {"content": "Shell guard fixture"}, "stop"


class CatalogFixtureModel(FixtureModel):
    """Record the model-visible catalog without issuing any tool calls."""

    def reply(self, request: dict) -> tuple[dict, str]:
        self.server.requests.put(request)
        return {"content": "Catalog fixture"}, "stop"


@contextmanager
def fixture_model(handler: type[FixtureModel]):
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        server.requests = Queue()
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()


def run_fixture(
    root: Path, binary: str, port: int, agent: str, profile: str, **config: object
) -> list[dict]:
    agents = root / ".opencode/agents"
    agents.mkdir(parents=True)
    (agents / f"{agent}.md").write_text(profile, encoding="utf-8")
    fixture_config = {
        "default_agent": agent,
        "model": MODEL,
        "agents": {"title": {"disabled": True}},
        "policies": [
            {"action": "provider.use", "resource": "*", "effect": "deny"},
            {
                "action": "provider.use",
                "resource": "runtime-fixture",
                "effect": "allow",
            },
        ],
        "providers": {
            "runtime-fixture": {
                "package": "@opencode/ai/providers/openai-compatible",
                "settings": {
                    "baseURL": f"http://127.0.0.1:{port}/v1",
                    "apiKey": "local-fixture-only",
                },
                "models": {"smoke": {"capabilities": {"tools": True}}},
            },
        },
        **config,
    }
    (agents.parent / "opencode.json").write_text(
        json.dumps(fixture_config), encoding="utf-8"
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
            agent,
            "--model",
            MODEL,
            "Run the local test fixture.",
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
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


@unittest.skipUnless(
    os.environ.get("OPENCODE_SMOKE_TEST") == "1", "requires OpenCode V2"
)
class OpenCodeRuntimeIntegrationTests(unittest.TestCase):
    def opencode_binary(self) -> str:
        binary = shutil.which("opencode")
        self.assertIsNotNone(binary, "install OpenCode V2 or unset OPENCODE_SMOKE_TEST")
        assert binary is not None
        return binary

    def test_real_shell_tool_allows_single_command_and_blocks_compound(self) -> None:
        profile = (
            "---\nmode: primary\npermissions:\n"
            '  - { action: "*", resource: "*", effect: deny }\n'
            f'  - {{ action: shell, resource: "{FIRST}", effect: allow }}\n'
            f'  - {{ action: shell, resource: "{SECOND}", effect: allow }}\n'
            "---\nRun only the harmless shell fixture.\n"
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            fixture_model(ShellFixtureModel) as server,
        ):
            root = Path(directory)
            plugin = root / ".opencode" / PLUGIN
            plugin.parent.mkdir(parents=True)
            shutil.copyfile(OPENCODE_DIR / PLUGIN, plugin)
            events = run_fixture(
                root,
                self.opencode_binary(),
                server.server_port,
                "embedded-engineer",
                profile,
            )

        calls = [
            event["part"]["state"]
            for event in events
            if event.get("part", {}).get("tool") == "shell"
            and event["part"]["state"]["status"] in {"completed", "error"}
        ]

        self.assertEqual(len(calls), 2, calls)
        single, compound = calls
        self.assertEqual(single["input"]["command"], FIRST)
        self.assertEqual(single["status"], "completed")
        self.assertIn("opencode-shell-guard-first", single["output"])
        self.assertEqual(compound["input"]["command"], COMPOUND)
        self.assertEqual(compound["status"], "error")
        self.assertIn("Shell composition is disabled", compound["error"])

    def test_specialists_discover_only_allowlisted_mcp_tools_without_execute(
        self,
    ) -> None:
        # Leave codemode unset to exercise OpenCode's default exposure.
        mcp = {
            "servers": {
                MCP_SERVER: {
                    "type": "local",
                    "command": [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--mcp-catalog",
                    ],
                }
            }
        }
        binary = self.opencode_binary()
        with (
            tempfile.TemporaryDirectory() as directory,
            fixture_model(CatalogFixtureModel) as server,
        ):
            for agent in SPECIALISTS:
                with self.subTest(agent=agent):
                    profile = (OPENCODE_DIR / "agents" / f"{agent}.md").read_text(
                        encoding="utf-8"
                    )
                    # The CLI requires a primary profile; keep permissions intact.
                    run_fixture(
                        Path(directory) / agent,
                        binary,
                        server.server_port,
                        agent,
                        profile.replace("mode: subagent", "mode: primary", 1),
                        mcp=mcp,
                    )
                    self.assertFalse(
                        server.requests.empty(), "model fixture received no request"
                    )
                    request = server.requests.get_nowait()
                    expected_prompt = profile.split("---", 2)[2].strip().splitlines()[0]
                    self.assertIn(
                        expected_prompt,
                        json.dumps(request["messages"], ensure_ascii=False),
                    )
                    self.assertTrue(server.requests.empty())
                    names = {tool["function"]["name"] for tool in request["tools"]}
                    self.assertIn("read", names)
                    self.assertNotIn("execute", names)
                    self.assertEqual(
                        {"codebase-memory-mcp_search_graph"},
                        {name for name in names if name.startswith(MCP_SERVER + "_")},
                    )


def mcp_catalog_fixture() -> None:
    """Expose names only; never execute a requested MCP tool."""
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        response = {"jsonrpc": "2.0", "id": request["id"]}
        match request["method"]:
            case "initialize":
                response["result"] = {
                    "protocolVersion": request["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "local-catalog-fixture", "version": "1"},
                }
            case "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": name,
                            "description": "Catalog fixture only",
                            "inputSchema": {"type": "object"},
                        }
                        for name in MCP_FIXTURE_TOOLS
                    ]
                }
            case "ping":
                response["result"] = {}
            case _:
                response["error"] = {
                    "code": -32601,
                    "message": "Catalog fixture does not execute tools",
                }
        print(json.dumps(response), flush=True)


if __name__ == "__main__" and sys.argv[1:] == ["--mcp-catalog"]:
    mcp_catalog_fixture()
