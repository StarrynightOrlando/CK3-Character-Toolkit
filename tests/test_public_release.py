import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from bridge import core


class PublicReleaseTests(unittest.TestCase):
    def test_author_docs_and_release_tools_are_distributed_without_local_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "LICENSE.md", "THIRD_PARTY_NOTICES.md",
                         "docs/SUPPORTED_TYPES.md", "tools/prepare_public_release.py",
                         ".github/workflows/check.yml"):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("public")
            (root / "settings.local.json").write_text("private")
            with patch.object(core, "ROOT", root):
                with zipfile.ZipFile(core.public_zip()) as archive:
                    self.assertIn("README.md", archive.namelist())
                    self.assertIn("docs/SUPPORTED_TYPES.md", archive.namelist())
                    self.assertIn(".github/workflows/check.yml", archive.namelist())
                    self.assertNotIn("settings.local.json", archive.namelist())

    def test_full_runtime_shader_cannot_be_hidden_in_public_source_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bridge").mkdir()
            (root / "bridge/copied.shader").write_text("game-derived content")
            with patch.object(core, "ROOT", root):
                with self.assertRaises(core.BridgeError):
                    core.public_zip()

    def test_local_profile_cannot_be_hidden_in_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "examples").mkdir()
            (root / "examples/profile.local.json").write_text("private")
            with patch.object(core, "ROOT", root):
                with self.assertRaises(core.BridgeError):
                    core.public_zip()
