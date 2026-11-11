from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent


class DocumentationOwnershipTests(unittest.TestCase):
    def test_navigation_docs_do_not_duplicate_model_and_step_values(self) -> None:
        for name in ("README.md", "PLAN.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(path=name):
                self.assertNotRegex(text, r"GPT-\d|github-copilot/gpt-|steps:\s*\d")
                self.assertIn(".opencode/agents/", text)
                self.assertIn(".opencode/opencode.json", text)

    def test_local_documentation_links_resolve(self) -> None:
        for name in (
            "README.md",
            "PLAN.md",
            "docs/workplans/Embedded-Subagent-Pilot-Charter.md",
        ):
            path = ROOT / name
            for target in re.findall(
                r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")
            ):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(path=name, target=target):
                    self.assertTrue((path.parent / target.split("#")[0]).exists())
