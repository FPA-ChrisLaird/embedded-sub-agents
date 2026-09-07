from __future__ import annotations

import json
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPOSITORY_ROOT / ".opencode" / "agents"
PRIMARY_AGENT = AGENTS_DIR / "embedded-engineer.md"
SUBAGENT_NAMES = (
    "embedded-architecture-analyst",
    "embedded-c-quality-reviewer",
    "embedded-build-analyzer",
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

        self.assertEqual(1, config["subagent_depth"])


if __name__ == "__main__":
    unittest.main()
