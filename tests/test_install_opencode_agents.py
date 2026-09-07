from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_PATH = REPOSITORY_ROOT / "scripts" / "install_opencode_agents.py"
SPEC = importlib.util.spec_from_file_location("install_opencode_agents", INSTALLER_PATH)
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class InstallOpenCodeAgentsTests(unittest.TestCase):
    def test_installs_all_managed_files_with_identical_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory) / "opencode"

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir)

            self.assertEqual(len(INSTALLER.MANAGED_FILES), len(results))
            for source_relative_path, target_relative_path in INSTALLER.MANAGED_FILES:
                self.assertEqual(
                    (REPOSITORY_ROOT / source_relative_path).read_bytes(),
                    (config_dir / target_relative_path).read_bytes(),
                )

    def test_rerun_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory) / "opencode"
            INSTALLER.install(REPOSITORY_ROOT, config_dir)

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir)

            self.assertTrue(all(result.startswith("unchanged ") for result in results))

    def test_replaces_outdated_managed_file_without_touching_unrelated_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory) / "opencode"
            outdated_agent = config_dir / "agents" / "embedded-engineer.md"
            unrelated_agent = config_dir / "agents" / "custom-agent.md"
            outdated_agent.parent.mkdir(parents=True)
            outdated_agent.write_text("outdated", encoding="utf-8")
            unrelated_agent.write_text("custom", encoding="utf-8")

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir)

            self.assertIn(f"update {outdated_agent}", results)
            self.assertEqual(
                (
                    REPOSITORY_ROOT / ".opencode" / "agents" / "embedded-engineer.md"
                ).read_text(encoding="utf-8"),
                outdated_agent.read_text(encoding="utf-8"),
            )
            self.assertEqual("custom", unrelated_agent.read_text(encoding="utf-8"))

    def test_dry_run_does_not_create_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory) / "opencode"

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir, dry_run=True)

            self.assertEqual(len(INSTALLER.MANAGED_FILES), len(results))
            self.assertFalse(config_dir.exists())

    def test_missing_source_fails_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory) / "repository"
            repository_root.mkdir()
            config_dir = Path(temporary_directory) / "opencode"

            with self.assertRaises(FileNotFoundError):
                INSTALLER.install(repository_root, config_dir)

            self.assertFalse(config_dir.exists())

    def test_xdg_config_home_is_used_when_set(self) -> None:
        with mock.patch.dict(
            "os.environ", {"XDG_CONFIG_HOME": "/tmp/config"}, clear=True
        ):
            self.assertEqual(
                Path("/tmp/config/opencode"), INSTALLER.default_config_dir()
            )


if __name__ == "__main__":
    unittest.main()
