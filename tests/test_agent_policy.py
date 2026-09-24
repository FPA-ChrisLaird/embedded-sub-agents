from __future__ import annotations

import json
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPOSITORY_ROOT / ".opencode" / "agents"
PRIMARY_AGENT = AGENTS_DIR / "embedded-engineer.md"
INSPECTION_PLUGIN = (
    REPOSITORY_ROOT / ".opencode" / "plugins" / "embedded-repository-inspection.ts"
)
SUBAGENT_NAMES = (
    "embedded-architecture-analyst",
    "embedded-c-quality-reviewer",
    "embedded-build-analyzer",
)
READ_ONLY_CODEBASE_MEMORY_TOOLS = (
    "codebase-memory-mcp_list_projects",
    "codebase-memory-mcp_index_status",
    "codebase-memory-mcp_search_graph",
    "codebase-memory-mcp_trace_path",
    "codebase-memory-mcp_get_code_snippet",
    "codebase-memory-mcp_check_index_coverage",
    "codebase-memory-mcp_query_graph",
    "codebase-memory-mcp_get_architecture",
    "codebase-memory-mcp_search_code",
    "codebase-memory-mcp_get_graph_schema",
    "codebase-memory-mcp_detect_changes",
)
PRIMARY_LOCAL_INDEX_CODEBASE_MEMORY_TOOLS = ("codebase-memory-mcp_index_repository",)
MUTATING_CODEBASE_MEMORY_TOOLS = (
    "codebase-memory-mcp_delete_project",
    "codebase-memory-mcp_manage_adr",
)
AGENT_MODELS = {
    "embedded-engineer": "github-copilot/gpt-6-sol",
    "embedded-architecture-analyst": "github-copilot/gpt-6-sol",
    "embedded-c-quality-reviewer": "github-copilot/gpt-6-sol",
    "embedded-build-analyzer": "github-copilot/gpt-6-luna",
}
GIT_INSPECTION_PERMISSION_PATTERNS = (
    "git --no-optional-locks --no-pager status*",
    "git --no-pager diff --no-ext-diff --no-textconv *",
    "git --no-pager show --no-ext-diff --no-textconv *",
    "git --no-pager log --no-ext-diff --no-textconv *",
    "git --no-pager branch --list",
    "git rev-parse *",
    "git config --get *",
    "git ls-files*",
    "git ls-tree *",
    "git worktree list*",
    "git stash list*",
    "git --no-pager blame *",
)
GIT_INSPECTION_DENIAL_PATTERNS = (
    "git * --output*",
    "git * --ext-diff*",
    "git * --textconv*",
    "git * --open-files-in-pager*",
    "*&&*",
    "*||*",
    "*;*",
    "*|*",
)


def agent_text(name: str) -> str:
    return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.split())


class AgentPolicyTests(unittest.TestCase):
    def test_pilot_has_exactly_the_primary_and_three_analysis_agents(self) -> None:
        self.assertEqual(
            {
                "embedded-engineer.md",
                *(f"{name}.md" for name in SUBAGENT_NAMES),
            },
            {path.name for path in AGENTS_DIR.glob("*.md")},
        )

    def test_primary_can_delegate_only_to_declared_analysis_agents(self) -> None:
        primary_text = PRIMARY_AGENT.read_text(encoding="utf-8")

        self.assertIn('"*": deny', primary_text)
        for name in SUBAGENT_NAMES:
            self.assertIn(f'"{name}": allow', primary_text)
        self.assertNotIn("embedded-c-implementer", primary_text)

    def test_primary_defaults_to_one_focused_subagent(self) -> None:
        primary_text = normalized(PRIMARY_AGENT.read_text(encoding="utf-8"))

        self.assertIn("Do not delegate routine work by default.", primary_text)
        self.assertIn("use one subagent.", primary_text)
        self.assertIn(
            (
                "Use two or three only for explicitly independent, "
                "cross-cutting questions;"
            ),
            primary_text,
        )
        self.assertIn("at most three non-overlapping subagents", primary_text)

    def test_primary_allows_trusted_external_skill_directory_only(self) -> None:
        primary_text = PRIMARY_AGENT.read_text(encoding="utf-8")

        self.assertIn('"C:\\\\Users\\\\lairdc\\\\.agents\\\\**": allow', primary_text)
        self.assertIn('"*": ask', primary_text)

    def test_analysis_agents_are_read_only_and_cannot_delegate(self) -> None:
        for name in SUBAGENT_NAMES:
            with self.subTest(agent=name):
                text = agent_text(name)
                self.assertIn("mode: subagent", text)
                self.assertIn("  edit: deny", text)
                self.assertIn("  task: deny", text)

    def test_analysis_agents_keep_the_configured_step_limits(self) -> None:
        expected_step_limits = {
            "embedded-architecture-analyst": 20,
            "embedded-c-quality-reviewer": 60,
            "embedded-build-analyzer": 12,
        }

        for name, steps in expected_step_limits.items():
            with self.subTest(agent=name):
                self.assertIn(f"steps: {steps}", agent_text(name))

    def test_agents_use_github_copilot_models(self) -> None:
        for name, model in AGENT_MODELS.items():
            with self.subTest(agent=name):
                text = agent_text(name)
                self.assertIn(f"model: {model}", text)
                self.assertNotIn("model: litellm/", text)

    def test_codebase_memory_permissions_allow_only_primary_local_indexing(
        self,
    ) -> None:
        for name in ("embedded-engineer", *SUBAGENT_NAMES):
            with self.subTest(agent=name):
                text = agent_text(name)
                for tool in READ_ONLY_CODEBASE_MEMORY_TOOLS:
                    self.assertIn(f'"{tool}": allow', text)
                for tool in PRIMARY_LOCAL_INDEX_CODEBASE_MEMORY_TOOLS:
                    if name == "embedded-engineer":
                        self.assertIn(f'"{tool}": allow', text)
                    else:
                        self.assertNotIn(f'"{tool}": allow', text)
                for tool in MUTATING_CODEBASE_MEMORY_TOOLS:
                    self.assertNotIn(f'"{tool}": allow', text)
                self.assertNotIn('"codebase-memory-mcp_*": allow', text)

    def test_pr_scoped_analysis_agents_can_load_pr_check(self) -> None:
        for name in SUBAGENT_NAMES:
            with self.subTest(agent=name):
                text = agent_text(name)
                self.assertIn('"pr-check": allow', text)

    def test_all_agents_preserve_github_and_git_non_mutation_policy(self) -> None:
        for name in ("embedded-engineer", *SUBAGENT_NAMES):
            with self.subTest(agent=name):
                text = normalized(agent_text(name))
                self.assertIn("Do not mutate GitHub resources", text)
                self.assertIn("non-mutating Git inspection commands", text)

    def test_shared_plugin_allows_bounded_git_inspection_commands(self) -> None:
        plugin_text = INSPECTION_PLUGIN.read_text(encoding="utf-8")

        for pattern in GIT_INSPECTION_PERMISSION_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(f'"{pattern}": "allow"', plugin_text)

    def test_shared_plugin_denies_composition_and_unsafe_git_output(self) -> None:
        plugin_text = INSPECTION_PLUGIN.read_text(encoding="utf-8")

        for pattern in GIT_INSPECTION_DENIAL_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(f'"{pattern}": "deny"', plugin_text)

    def test_quality_reviewer_keeps_persistent_data_coverage_policy(self) -> None:
        reviewer_text = normalized(agent_text("embedded-c-quality-reviewer"))

        self.assertIn("enumerate all writers", reviewer_text)
        self.assertIn(
            "Include a coverage summary of writer, trigger, marker", reviewer_text
        )
        self.assertIn("risk requiring confirmation", reviewer_text)

    def test_primary_requires_evidence_and_current_pr_head_before_mutation(
        self,
    ) -> None:
        primary_text = normalized(PRIMARY_AGENT.read_text(encoding="utf-8"))

        self.assertIn(
            "Report a bug only when source, tests, runtime traces", primary_text
        )
        self.assertIn(
            "A state reachable only in isolation is a hypothesis, not a finding.",
            primary_text,
        )
        self.assertIn("re-fetch its head SHA and review status", primary_text)

    def test_project_configuration_keeps_single_subagent_level(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / ".opencode" / "opencode.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual("embedded-engineer", config["default_agent"])
        self.assertEqual(1, config["subagent_depth"])


if __name__ == "__main__":
    unittest.main()
