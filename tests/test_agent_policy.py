from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPOSITORY_ROOT / ".opencode" / "agents"
PRIMARY_AGENT = AGENTS_DIR / "embedded-engineer.md"
ANDROID_SKILL = (
    REPOSITORY_ROOT / ".opencode" / "skills" / "android-device-workflow" / "SKILL.md"
)
INSPECTION_PLUGIN = (
    REPOSITORY_ROOT / ".opencode/plugins/embedded-repository-inspection/index.ts"
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
    "embedded-engineer": "github-copilot/gpt-6.2-sol",
    "embedded-architecture-analyst": "github-copilot/gpt-6.1-sol",
    "embedded-c-quality-reviewer": "github-copilot/gpt-6.1-sol",
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


def frontmatter(name: str) -> dict:
    return yaml.safe_load(agent_text(name).split("---", 2)[1])


def permission(rules: list[dict], action: str, resource: str = "*") -> str:
    """Model the documented V2 whole-value *, ? matcher and last-match rule.

    These fixtures use normalized paths. Shell's special trailing ' *' form
    also matches the command with no arguments. This is not a shell scanner.
    """

    def matches(pattern: str, value: str) -> bool:
        expression = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
        return re.fullmatch(expression, value, re.DOTALL) is not None

    effect = "ask"
    for rule in rules:
        pattern = rule["resource"]
        resource_match = matches(pattern, resource)
        if action == "shell" and pattern.endswith(" *"):
            resource_match |= matches(pattern[:-2], resource)
        if matches(rule["action"], action) and resource_match:
            effect = rule["effect"]
    return effect


def run_plugin(agents: dict, *options: str) -> dict:
    result = subprocess.run(
        [
            "node",
            str(REPOSITORY_ROOT / "scripts/evaluate_inspection_plugin.mjs"),
            str(INSPECTION_PLUGIN),
            *options,
        ],
        input=json.dumps(agents),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


class AgentPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transformed = run_plugin({name: frontmatter(name) for name in AGENT_MODELS})

    def test_todo_is_enabled_and_analysis_agents_remain_denied(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / ".opencode/opencode.json").read_text(encoding="utf-8")
        )
        self.assertIs(True, config["experimental"]["todo"])
        for name in AGENT_MODELS:
            with self.subTest(agent=name):
                expected = "allow" if name == "embedded-engineer" else "deny"
                self.assertEqual(
                    expected, permission(frontmatter(name)["permissions"], "todowrite")
                )

    def test_native_shell_rules_match_shared_policy_without_a_loaded_plugin(
        self,
    ) -> None:
        generated = run_plugin({name: {"permissions": []} for name in AGENT_MODELS})
        for name in AGENT_MODELS:
            self.assertEqual(
                generated[name]["permissions"],
                [r for r in frontmatter(name)["permissions"] if r["action"] == "shell"],
            )
            native = frontmatter(name)["permissions"]
            self.assertEqual("allow", permission(native, "shell", "gh repo view a/b"))
            self.assertEqual("deny", permission(native, "shell", "make flash"))
            self.assertEqual(
                "ask" if name == "embedded-engineer" else "deny",
                permission(native, "shell", "make all"),
            )

    def test_generated_shell_policy_is_current(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(REPOSITORY_ROOT / "scripts/sync_agent_shell_policy.py"),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )

    def test_frontmatter_is_entirely_native_v2(self) -> None:
        native_fields = {"description", "mode", "model", "steps", "permissions"}
        for name in AGENT_MODELS:
            with self.subTest(agent=name):
                agent = frontmatter(name)
                self.assertLessEqual(agent.keys(), native_fields)
                self.assertIsInstance(agent["permissions"], list)
                for rule in agent["permissions"]:
                    self.assertEqual({"action", "resource", "effect"}, rule.keys())
                    self.assertIn(rule["effect"], {"allow", "ask", "deny"})
                    self.assertNotIn(
                        rule["action"], {"bash", "task", "lsp", "doom_loop", "list"}
                    )
                    self.assertFalse(rule["action"].startswith("codebase_memory_mcp_"))

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

        rules = frontmatter("embedded-engineer")["permissions"]
        for name in SUBAGENT_NAMES:
            self.assertEqual("allow", permission(rules, "subagent", name))
        self.assertEqual("deny", permission(rules, "subagent", "general"))
        self.assertEqual("deny", permission(rules, "subagent", "unknown"))
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
        rules = frontmatter("embedded-engineer")["permissions"]
        self.assertEqual(
            "allow",
            permission(rules, "external_directory", "C:/Users/lairdc/.agents/*"),
        )
        self.assertEqual("ask", permission(rules, "external_directory", "D:/other/*"))

    def test_analysis_agents_are_read_only_and_cannot_delegate(self) -> None:
        for name in SUBAGENT_NAMES:
            with self.subTest(agent=name):
                agent = frontmatter(name)
                self.assertEqual("subagent", agent["mode"])
                for action in ("edit", "subagent", "external_directory", "question"):
                    self.assertEqual("deny", permission(agent["permissions"], action))

    def test_reads_keep_secret_denials_after_general_allow(self) -> None:
        for name in AGENT_MODELS:
            rules = frontmatter(name)["permissions"]
            self.assertEqual("allow", permission(rules, "read", "src/main.c"))
            for path in (".env", "app.env.local", "a.pem", "a.key", "a.p12", "a.pfx"):
                self.assertEqual("deny", permission(rules, "read", path), (name, path))
        self.assertEqual(
            "allow", permission(frontmatter("embedded-engineer")["permissions"], "edit")
        )

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
                rules = frontmatter(name)["permissions"]
                for tool in READ_ONLY_CODEBASE_MEMORY_TOOLS:
                    self.assertEqual("allow", permission(rules, tool))
                for tool in PRIMARY_LOCAL_INDEX_CODEBASE_MEMORY_TOOLS:
                    expected = "allow" if name == "embedded-engineer" else "deny"
                    self.assertEqual(expected, permission(rules, tool))
                for tool in MUTATING_CODEBASE_MEMORY_TOOLS:
                    self.assertNotEqual("allow", permission(rules, tool))
                self.assertNotIn("codebase-memory-mcp_*", [r["action"] for r in rules])

    def test_agents_keep_role_specific_reasoning_variants(self) -> None:
        for name in AGENT_MODELS:
            with self.subTest(agent=name):
                variant = "medium" if name == "embedded-build-analyzer" else "xhigh"
                self.assertEqual(
                    f"{AGENT_MODELS[name]}#{variant}", frontmatter(name)["model"]
                )

    def test_project_defaults_to_sol_6_2_with_xhigh_reasoning(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / ".opencode" / "opencode.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual("github-copilot/gpt-6.2-sol", config["model"])
        model = config["providers"]["github-copilot"]["models"]["gpt-6.2-sol"]
        self.assertEqual("xhigh", model["settings"]["reasoningEffort"])
        self.assertNotIn("provider", config)
        self.assertNotIn("plugin", config)
        self.assertNotIn("subagent_depth", config)
        self.assertEqual(
            ["./plugins/embedded-repository-inspection"], config["plugins"]
        )

    def test_pr_scoped_analysis_agents_can_load_pr_check(self) -> None:
        for name in SUBAGENT_NAMES:
            with self.subTest(agent=name):
                rules = frontmatter(name)["permissions"]
                self.assertEqual("allow", permission(rules, "skill", "pr-check"))
                self.assertEqual("allow", permission(rules, "skill", "access-github"))
                self.assertEqual("deny", permission(rules, "skill", "other"))

    def test_all_agents_preserve_github_and_git_non_mutation_policy(self) -> None:
        for name in SUBAGENT_NAMES:
            with self.subTest(agent=name):
                text = normalized(agent_text(name))
                self.assertIn("Do not mutate GitHub resources", text)
                self.assertIn("non-mutating Git inspection commands", text)

        primary_text = normalized(agent_text("embedded-engineer"))
        self.assertIn("an explicit human request to post, approve", primary_text)
        self.assertIn("plugin's separate permission prompt", primary_text)
        self.assertIn("never treat a read-only request as authorization", primary_text)
        self.assertIn("non-mutating Git inspection commands", primary_text)

    def test_shared_plugin_prompts_primary_for_api_writes_and_denies_subagents(
        self,
    ) -> None:
        flags = (
            "-XPOST",
            "-X POST",
            "--method=POST",
            "--method POST",
            "-fbody=test",
            "-f body=test",
            "-Fbody=test",
            "-F body=test",
            "--raw-field=body=test",
            "--raw-field body=test",
            "--field=body=test",
            "--field body=test",
            "--input=body.json",
            "--input body.json",
        )
        for name, agent in self.transformed.items():
            expected = "ask" if name == "embedded-engineer" else "deny"
            for flag in flags:
                command = f"gh api repos/owner/repo/pulls/1/comments {flag}"
                self.assertEqual(
                    expected, permission(agent["permissions"], "shell", command)
                )
            for query_flag in ("-f", "-F", "--raw-field", "--field"):
                prefix = f"gh api graphql --paginate {query_flag}"
                for query, effect in (
                    ("query='{ repository { name } }'", "allow"),
                    ("query='mutation { addComment { id } }'", expected),
                    ("query=@request.graphql", expected),
                ):
                    self.assertEqual(
                        effect,
                        permission(agent["permissions"], "shell", f"{prefix} {query}"),
                    )

    def test_plugin_effective_shell_policy_for_all_four_roles(self) -> None:
        for name, agent in self.transformed.items():
            rules = agent["permissions"]
            default = "ask" if name == "embedded-engineer" else "deny"
            for command in ("make all", "make clean", "adb devices", "git add file.c"):
                self.assertEqual(
                    default, permission(rules, "shell", command), (name, command)
                )
            for command in (
                "gh repo view owner/repo",
                "gh api repos/owner/repo/pulls/1",
                "git --no-optional-locks --no-pager status --short --branch",
                "git --no-pager diff --no-ext-diff --no-textconv",
                "git --no-pager branch --list",
                "git rev-parse HEAD",
                "git ls-files",
                "git worktree list",
            ):
                self.assertEqual(
                    "allow", permission(rules, "shell", command), (name, command)
                )
            for command in (
                "git --no-pager diff --no-ext-diff --no-textconv --output=result.patch",
                "git --no-pager diff --no-ext-diff --no-textconv --ext-diff",
                "git --no-pager show --no-ext-diff --no-textconv --textconv",
                "git --no-pager log --no-ext-diff --no-textconv --open-files-in-pager",
                "make flash",
                "make program",
                "make package",
                "make release",
                "openocd",
                "jlink",
                "pyocd",
                "st-flash",
                "dfu-util",
                "avrdude",
                "nrfjprog",
            ):
                self.assertEqual(
                    "deny", permission(rules, "shell", command), (name, command)
                )

    def test_shell_hook_checks_complete_input_for_all_four_roles(self) -> None:
        run_plugin(
            {name: {"permissions": []} for name in AGENT_MODELS}, "--check-shell-hook"
        )

    def test_plugin_ignores_absent_agents_and_preserves_unrelated_policy(self) -> None:
        unrelated = {
            "permissions": [{"action": "*", "resource": "*", "effect": "deny"}]
        }
        self.assertEqual({"custom": unrelated}, run_plugin({"custom": unrelated}))
        # A disabled agent is absent from the V2 agent editor, not recreated.
        self.assertEqual({}, run_plugin({}))
        custom = {
            "permissions": [
                {"action": "edit", "resource": "*", "effect": "deny"},
                {"action": "shell", "resource": "echo approved", "effect": "allow"},
            ]
        }
        result = run_plugin({"embedded-engineer": custom})["embedded-engineer"]
        self.assertEqual(custom["permissions"], result["permissions"][:2])
        self.assertEqual(
            "allow", permission(result["permissions"], "shell", "echo approved")
        )
        self.assertEqual("deny", permission(result["permissions"], "edit"))
        self.assertNotIn(
            {"action": "shell", "resource": "*", "effect": "ask"}, result["permissions"]
        )

    def test_shared_plugin_allows_bounded_git_inspection_commands(self) -> None:
        plugin_text = INSPECTION_PLUGIN.read_text(encoding="utf-8")

        for pattern in GIT_INSPECTION_PERMISSION_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(f'"{pattern}": "allow"', plugin_text)

    def test_shared_plugin_retains_shell_resource_denials(self) -> None:
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

    def test_primary_build_cleanup_requires_approval_and_target_inspection(
        self,
    ) -> None:
        plugin_text = INSPECTION_PLUGIN.read_text(encoding="utf-8")
        primary_text = normalized(agent_text("embedded-engineer"))

        self.assertNotIn('"* clean*": "deny"', plugin_text)
        self.assertIn('"embedded-engineer": "ask"', plugin_text)
        for name in SUBAGENT_NAMES:
            self.assertIn(f'"{name}": "deny"', plugin_text)
        for pattern in ("*flash*", "*program*", "* package*", "* release*"):
            self.assertIn(f'"{pattern}": "deny"', plugin_text)
        self.assertIn(
            "Build cleanup such as `make clean` requires explicit human approval",
            primary_text,
        )
        self.assertIn("prior inspection of the target", primary_text)
        self.assertIn("Other destructive targets remain prohibited", primary_text)

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

    def test_android_details_are_loaded_only_on_demand(self) -> None:
        primary_text = normalized(agent_text("embedded-engineer"))
        skill_text = ANDROID_SKILL.read_text(encoding="utf-8")

        self.assertIn("load `android-device-workflow`", primary_text)
        self.assertIn("If unavailable, stop device work", primary_text)
        self.assertIn("Do not load it for non-Android work", primary_text)
        self.assertIn("shell-approval-gated", primary_text)
        self.assertIn("Analysis subagents must not run ADB", primary_text)
        self.assertNotIn("shell am start", primary_text)
        self.assertNotIn("adb logcat", primary_text)
        self.assertIn("name: android-device-workflow", skill_text.split("---")[1])
        self.assertIn("description: Use for Android APK builds", skill_text)
        self.assertIn("UI automation", skill_text)

    def test_android_skill_permits_approved_non_release_apk_builds(self) -> None:
        skill_text = normalized(ANDROID_SKILL.read_text(encoding="utf-8"))

        self.assertIn("inspected, approval-gated local build tasks", skill_text)
        self.assertIn("gradlew assembleDebug", skill_text)
        self.assertIn("task dependencies", skill_text)
        self.assertIn(
            "package/release targets, publishing, and distribution remain prohibited",
            skill_text,
        )
        self.assertIn(
            "does not authorize device access, installation, or launch", skill_text
        )

    def test_primary_adb_workflow_is_scoped_and_approval_gated(self) -> None:
        primary_text = normalized(ANDROID_SKILL.read_text(encoding="utf-8"))
        plugin_text = INSPECTION_PLUGIN.read_text(encoding="utf-8")

        self.assertIn(
            "explicit human authorization and shell permission approval", primary_text
        )
        self.assertIn("pull or push APKs and log files", primary_text)
        self.assertIn("install or update APKs", primary_text)
        self.assertIn("read or capture logs with `adb logcat`", primary_text)
        self.assertIn("use `adb -s <serial>`", primary_text)
        self.assertIn(
            "explain replacement effects before writes or installs", primary_text
        )
        self.assertIn("not authorization for arbitrary shell execution", primary_text)
        self.assertIn(
            "Analysis subagents must not run ADB or access devices", primary_text
        )
        self.assertIn("do not bypass plugin denials", primary_text)
        self.assertNotIn(
            "Never flash or program firmware, access a device", primary_text
        )
        self.assertNotIn('"adb *": "allow"', plugin_text)
        self.assertIn('"embedded-engineer": "ask"', plugin_text)
        for name in SUBAGENT_NAMES:
            self.assertIn(f'"{name}": "deny"', plugin_text)

    def test_primary_reuses_bounded_adb_authorization_without_waiving_prompts(
        self,
    ) -> None:
        primary_text = normalized(ANDROID_SKILL.read_text(encoding="utf-8"))

        self.assertIn("for the current session", primary_text)
        self.assertIn("without repeated conversational confirmation", primary_text)
        self.assertIn("Reconfirm if the device, task, transfer paths", primary_text)
        self.assertIn("authorization is revoked or unclear", primary_text)
        self.assertIn("does not waive shell permission prompts", primary_text)

    def test_primary_can_launch_only_the_authorized_installed_app(self) -> None:
        primary_text = normalized(ANDROID_SKILL.read_text(encoding="utf-8"))

        self.assertIn("launch the approved installed app", primary_text)
        self.assertIn(
            "explicit authorization covering the app and device", primary_text
        )
        self.assertIn("shell am start -n <package>/<activity>", primary_text)
        self.assertIn("without unapproved intent arguments", primary_text)
        self.assertIn(
            "Installing an APK alone does not authorize launching it", primary_text
        )
        self.assertIn(
            "obtain confirmation of those effects before launching", primary_text
        )

    def test_project_configuration_keeps_single_subagent_level(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / ".opencode" / "opencode.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual("embedded-engineer", config["default_agent"])
        self.assertEqual(1, config["experimental"]["subagent_depth"])

    def test_incomplete_subagents_resume_by_v2_session_id(self) -> None:
        self.assertIn("`sessionID`", agent_text("embedded-engineer"))
        self.assertNotIn("`task_id`", agent_text("embedded-engineer"))


if __name__ == "__main__":
    unittest.main()
