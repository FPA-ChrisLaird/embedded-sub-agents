from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".opencode" / "skills" / "erd-knowledge" / "SKILL.md"


class ErdKnowledgeSkillTests(unittest.TestCase):
    def test_skill_is_discoverable_and_bounded(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        header = text.split("---")[1]
        self.assertIn("name: erd-knowledge", header)
        self.assertIn("description: Use for GEA Entity Reference Designator", header)
        self.assertIn("Load only for ERD-related work", header)
        self.assertNotIn(
            "erd-knowledge",
            (ROOT / ".opencode/agents/embedded-engineer.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_lookup_preserves_source_and_permission_boundaries(self) -> None:
        text = " ".join(SKILL.read_text(encoding="utf-8").split())
        for requirement in (
            "read-only lookup workflow",
            "does not authorize ERD writes",
            "On first use, ask the user",
            "reuse it without asking again",
            "only for the current session",
            "Never bypass an external-directory denial",
            "Record its HEAD revision",
            "Before finalizing, recheck HEAD",
            "Do not silently mix definitions from different revisions",
            "follow every relevant `require`",
            "sharing `.data` does not share ownership",
            "service/private meanings may vary",
            "absent file is not proof",
            "generated conveniences",
            "Do not infer wire byte order",
            "not enforced delivery or event ordering",
            "mandatory quality-reviewer delegation",
            "do not load the complete catalogue",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_skill_has_no_workstation_specific_checkout_path(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("D:\\source", text)
        self.assertNotIn("lairdc", text)
