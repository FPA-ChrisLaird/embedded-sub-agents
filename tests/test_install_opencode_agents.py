from __future__ import annotations

import importlib.util
import contextlib
import io
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
    def test_decoded_legacy_references_fail_before_copies_or_backup(self) -> None:
        for content in (
            r'{"plugins":["./plugins/embedded-repository-inspection\u002ets"]}',
            r'{"plugin":["./plugins/\u0065mbedded-repository-inspection.ts"]}',
            '// unmatched comment quote "\n'
            r'{"plugins":["./plugins/embedded-repository-inspection\u002ets",],}',
            '/* unmatched quote " */\n'
            r'{"plugins":["./plugins/embedded-repository-inspection\u002ets"]}',
        ):
            with self.subTest(
                content=content
            ), tempfile.TemporaryDirectory() as directory:
                config_dir = Path(directory)
                legacy = config_dir / INSTALLER.LEGACY_PLUGIN
                legacy.parent.mkdir()
                legacy.write_bytes(b"old managed plugin")
                config = config_dir / "opencode.jsonc"
                config.write_text(content, encoding="utf-8-sig")
                before = {
                    p: p.read_bytes() for p in config_dir.rglob("*") if p.is_file()
                }

                with self.assertRaisesRegex(
                    ValueError, "Update the legacy plugin reference"
                ):
                    INSTALLER.install(REPOSITORY_ROOT, config_dir)

                self.assertEqual(
                    before,
                    {p: p.read_bytes() for p in config_dir.rglob("*") if p.is_file()},
                )

    def test_commented_raw_legacy_reference_remains_conservatively_rejected(
        self,
    ) -> None:
        self.assertTrue(
            INSTALLER.mentions_legacy_plugin(
                '// "./plugins/embedded-repository-inspection.ts"\n{}'
            )
        )
        self.assertFalse(
            INSTALLER.mentions_legacy_plugin(
                '// comment with "unbalanced quote\n{"plugins":["./plugins/unrelated"]}'
            )
        )

    def test_mid_suite_copy_failure_preserves_legacy_and_retry_converges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory)
            legacy = config_dir / INSTALLER.LEGACY_PLUGIN
            legacy.parent.mkdir()
            legacy.write_bytes(b"old plugin")
            calls = 0
            real_copy = INSTALLER.copy_atomically

            def failing_copy(source, target):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("mid-suite failure")
                real_copy(source, target)

            with mock.patch.object(
                INSTALLER, "copy_atomically", side_effect=failing_copy
            ):
                with self.assertRaisesRegex(OSError, "mid-suite failure"):
                    INSTALLER.install(REPOSITORY_ROOT, config_dir)
            self.assertEqual(b"old plugin", legacy.read_bytes())
            self.assertFalse(legacy.with_suffix(".ts.v1-backup").exists())

            INSTALLER.install(REPOSITORY_ROOT, config_dir)

            self.assertFalse(legacy.exists())
            for source, target in INSTALLER.MANAGED_FILES:
                self.assertEqual(
                    (REPOSITORY_ROOT / source).read_bytes(),
                    (config_dir / target).read_bytes(),
                )
            self.assertTrue(
                all(
                    line.startswith("unchanged ")
                    for line in INSTALLER.install(REPOSITORY_ROOT, config_dir)
                )
            )

    def test_v2_plugin_directory_is_an_explicit_managed_file(self) -> None:
        self.assertIn(
            (
                Path(".opencode/plugins/embedded-repository-inspection/index.ts"),
                Path("plugins/embedded-repository-inspection/index.ts"),
            ),
            INSTALLER.MANAGED_FILES,
        )

    def test_upgrade_backs_up_only_legacy_plugin_and_preserves_configuration(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory)
            legacy = config_dir / INSTALLER.LEGACY_PLUGIN
            legacy.parent.mkdir()
            legacy.write_text("customized V1 plugin", encoding="utf-8")
            existing_backup = legacy.with_suffix(".ts.v1-backup")
            existing_backup.write_text("earlier backup", encoding="utf-8")
            config = config_dir / "opencode.jsonc"
            config.write_text('// user config\n{"providers": {}}', encoding="utf-8")
            unrelated = legacy.parent / "custom.ts"
            unrelated.write_text("unrelated plugin", encoding="utf-8")
            before_config = config.read_bytes()

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir)

            self.assertEqual(len(INSTALLER.MANAGED_FILES) + 1, len(results))
            self.assertFalse(legacy.exists())
            self.assertEqual(
                "customized V1 plugin",
                legacy.with_suffix(".ts.v1-backup.1").read_text(),
            )
            self.assertEqual("earlier backup", existing_backup.read_text())
            self.assertEqual(before_config, config.read_bytes())
            self.assertEqual("unrelated plugin", unrelated.read_text())
            self.assertTrue(
                all(
                    line.startswith("unchanged ")
                    for line in INSTALLER.install(REPOSITORY_ROOT, config_dir)
                )
            )

    def test_explicit_legacy_reference_fails_before_any_installation(self) -> None:
        for filename in ("opencode.json", "opencode.jsonc"):
            with self.subTest(
                filename=filename
            ), tempfile.TemporaryDirectory() as directory:
                config_dir = Path(directory)
                config = config_dir / filename
                config.write_text(
                    '{"plugin": ["./plugins/embedded-repository-inspection.ts"]}',
                    encoding="utf-8",
                )
                before = config.read_bytes()
                with self.assertRaisesRegex(
                    ValueError, "Update the legacy plugin reference"
                ):
                    INSTALLER.install(REPOSITORY_ROOT, config_dir)
                self.assertEqual([config], list(config_dir.iterdir()))
                self.assertEqual(before, config.read_bytes())

    def test_v1_upgrade_dry_run_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory)
            legacy = config_dir / INSTALLER.LEGACY_PLUGIN
            legacy.parent.mkdir()
            legacy.write_bytes(b"old plugin")

            results = INSTALLER.install(REPOSITORY_ROOT, config_dir, dry_run=True)

            self.assertTrue(results[-1].startswith("backup "))
            self.assertEqual(
                [legacy], [p for p in config_dir.rglob("*") if p.is_file()]
            )
            self.assertEqual(b"old plugin", legacy.read_bytes())

    def test_missing_source_does_not_retire_legacy_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "config" / INSTALLER.LEGACY_PLUGIN
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"old plugin")
            with self.assertRaises(FileNotFoundError):
                INSTALLER.install(root / "missing", root / "config")
            self.assertEqual(b"old plugin", legacy.read_bytes())

    def test_failed_legacy_backup_reports_failure_and_retry_converges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory)
            legacy = config_dir / INSTALLER.LEGACY_PLUGIN
            legacy.parent.mkdir()
            legacy.write_bytes(b"old plugin")
            with mock.patch.object(
                Path, "rename", side_effect=OSError("backup failed")
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(
                    output
                ):
                    result = INSTALLER.main(["--config-dir", str(config_dir)])
            self.assertEqual(1, result)
            self.assertIn("Installation failed", output.getvalue())
            self.assertNotIn("reloads configuration", output.getvalue())
            self.assertEqual(b"old plugin", legacy.read_bytes())
            INSTALLER.install(REPOSITORY_ROOT, config_dir)
            self.assertFalse(legacy.exists())

    def test_atomic_copy_failure_preserves_existing_file_and_cleans_temporary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source", root / "target"
            source.write_bytes(b"new")
            target.write_bytes(b"old")
            with mock.patch.object(
                Path, "replace", side_effect=OSError("replace failed")
            ):
                with self.assertRaises(OSError):
                    INSTALLER.copy_atomically(source, target)
            self.assertEqual(b"old", target.read_bytes())
            self.assertEqual({source, target}, set(root.iterdir()))

    def test_erd_skill_is_an_explicit_managed_file(self) -> None:
        self.assertIn(
            (
                Path(".opencode/skills/erd-knowledge/SKILL.md"),
                Path("skills/erd-knowledge/SKILL.md"),
            ),
            INSTALLER.MANAGED_FILES,
        )

    def test_android_skill_is_an_explicit_managed_file_installed_before_agents(
        self,
    ) -> None:
        self.assertEqual(
            (
                Path(".opencode/skills/android-device-workflow/SKILL.md"),
                Path("skills/android-device-workflow/SKILL.md"),
            ),
            INSTALLER.MANAGED_FILES[0],
        )

    def test_missing_android_skill_fails_before_updating_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory) / "repository"
            config_dir = Path(temporary_directory) / "opencode"
            for source, _ in INSTALLER.MANAGED_FILES[1:]:
                path = repository_root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                INSTALLER.install(repository_root, config_dir)

            self.assertFalse(config_dir.exists())

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
