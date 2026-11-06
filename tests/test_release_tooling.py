from __future__ import annotations

import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "assemble_docs_release", ROOT / "scripts/assemble_docs_release.py"
)
ASSEMBLER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(ASSEMBLER)
PUBLISH_SPEC = importlib.util.spec_from_file_location(
    "publish_release", ROOT / "scripts/publish_release.py"
)
PUBLISHER = importlib.util.module_from_spec(PUBLISH_SPEC)
assert PUBLISH_SPEC.loader
PUBLISH_SPEC.loader.exec_module(PUBLISHER)


class ReleaseToolingTests(unittest.TestCase):
    def test_initial_release_manifests_and_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "site"
            (current / "en").mkdir(parents=True)
            (current / "index.html").write_text("繁體中文")
            (current / "en/index.html").write_text("English")
            output = root / "assembled"
            ASSEMBLER.assemble(current, output, "1.0.0", "a" * 40, "1234", None)
            expected = {
                "mode": "title",
                "versions": [{"label": "1.0.0", "root": "/", "latest": True}],
            }
            self.assertEqual(json.loads((output / "askr-versions.json").read_text()), expected)
            expected_en = {
                "mode": "title",
                "versions": [{"label": "1.0.0", "root": "/", "latest": True}],
            }
            self.assertEqual(
                json.loads((output / "en/askr-versions.json").read_text()), expected_en
            )
            meta = json.loads((output / "docs-release.json").read_text())
            self.assertEqual(
                meta,
                {
                    "packageVersion": "1.0.0",
                    "sourceSHA": "a" * 40,
                    "languages": ["zh-TW", "en"],
                    "pagesRun": "1234",
                },
            )

    def test_reject_archive_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                info = tarfile.TarInfo("../escape")
                info.size = 1
                tf.addfile(info, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                ASSEMBLER.extract_site(archive, root / "out")

    def test_nested_version_snapshots_are_not_copied_forward(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "current"
            (current / "en").mkdir(parents=True)
            (current / "index.html").write_text("current 1.0.2")
            (current / "en/index.html").write_text("current en")

            old_one = root / "one"
            (old_one / "en").mkdir(parents=True)
            (old_one / "index.html").write_text("release 1.0.1")
            (old_one / "en/index.html").write_text("release 1.0.1 en")
            (old_one / "v1.0.0/en").mkdir(parents=True)
            (old_one / "v1.0.0/index.html").write_text("nested release 1.0.0")
            (old_one / "v1.0.0/en/index.html").write_text("nested release 1.0.0 en")
            archive_one = root / "one.tar.gz"
            with tarfile.open(archive_one, "w:gz") as tf:
                for path in old_one.rglob("*"):
                    tf.add(path, arcname=path.relative_to(old_one))

            old_zero = root / "zero"
            (old_zero / "en").mkdir(parents=True)
            (old_zero / "index.html").write_text("release 1.0.0")
            (old_zero / "en/index.html").write_text("release 1.0.0 en")
            archive_zero = root / "zero.tar.gz"
            with tarfile.open(archive_zero, "w:gz") as tf:
                tf.add(old_zero / "index.html", arcname="index.html")
                tf.add(old_zero / "en/index.html", arcname="en/index.html")

            history = root / "history.json"
            history.write_text(
                json.dumps(
                    [
                        {
                            "version": "1.0.1",
                            "archive": str(archive_one),
                            "home": "https://example.test/v1.0.1/",
                            "english_home": "https://example.test/v1.0.1/en/",
                        },
                        {
                            "version": "1.0.0",
                            "archive": str(archive_zero),
                            "home": "https://example.test/v1.0.0/",
                            "english_home": "https://example.test/v1.0.0/en/",
                        },
                    ]
                )
            )
            output = root / "assembled"
            ASSEMBLER.assemble(current, output, "1.0.2", "a" * 40, None, history)

            self.assertEqual((output / "v1.0.1/index.html").read_text(), "release 1.0.1")
            self.assertFalse((output / "v1.0.1/v1.0.0").exists())
            self.assertEqual((output / "v1.0.0/index.html").read_text(), "release 1.0.0")

    def test_nested_version_snapshot_paths_are_still_checked_for_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                info = tarfile.TarInfo("v1.0.0/../../escape")
                info.size = 1
                tf.addfile(info, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                ASSEMBLER.extract_site(archive, root / "out")

    def test_requires_both_language_homepages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "site"
            current.mkdir()
            (current / "index.html").write_text("only root")
            with self.assertRaisesRegex(ValueError, "en/index.html"):
                ASSEMBLER.assemble(current, root / "out", "1.0.0", "b" * 40, None, None)

    def test_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "site"
            current.mkdir()
            output = root / "out"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                ASSEMBLER.assemble(current, output, "1.0.0", "c" * 40, None, None)

    def test_wheel_metadata_is_read_from_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "orcapen_sc_pdk-1.0.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as zf:
                zf.writestr(
                    "orcapen_sc_pdk-1.0.0.dist-info/METADATA",
                    "Name: orcapen-sc-pdk\nVersion: 1.0.0\n\n",
                )
            self.assertEqual(PUBLISHER.package_metadata(wheel), ("orcapen-sc-pdk", "1.0.0"))

    def test_sdist_metadata_is_read_from_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            sdist = Path(temporary) / "orcapen_sc_pdk-1.0.0.tar.gz"
            with tarfile.open(sdist, "w:gz") as tf:
                data = b"Name: orcapen-sc-pdk\nVersion: 1.0.0\n\n"
                info = tarfile.TarInfo("orcapen_sc_pdk-1.0.0/PKG-INFO")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            self.assertEqual(PUBLISHER.package_metadata(sdist), ("orcapen-sc-pdk", "1.0.0"))

    def test_external_tarball_is_not_mistaken_for_primary_sdist(self):
        primary = [
            {"name": "docs-site.tar.gz"},
            {"name": "orcapen_sc_pdk-1.0.0-py3-none-any.whl"},
            {"name": "orcapen_sc_pdk-1.0.0.tar.gz"},
        ]
        self.assertEqual(
            PUBLISHER.primary_package_names(primary), (primary[1]["name"], primary[2]["name"])
        )

    def test_pages_run_must_be_successful_main_push(self):
        run = {
            "head_sha": "f" * 40,
            "conclusion": "success",
            "path": ".github/workflows/pages.yml",
            "event": "push",
            "head_branch": "main",
        }
        self.assertTrue(PUBLISHER.is_eligible_pages_run(run, "f" * 40))
        for field, bad_value in (
            ("event", "workflow_dispatch"),
            ("head_branch", "feature"),
            ("conclusion", "failure"),
        ):
            with self.subTest(field=field):
                self.assertFalse(
                    PUBLISHER.is_eligible_pages_run({**run, field: bad_value}, "f" * 40)
                )

    def test_large_asset_hashes_in_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset = Path(temporary) / "asset.bin"
            asset.write_bytes(b"x" * (2 * 1024 * 1024))
            self.assertEqual(len(PUBLISHER.checksum(asset)), 64)

    def test_history_manifest_uses_language_specific_routes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "current"
            (current / "en").mkdir(parents=True)
            (current / "index.html").write_text("current zh")
            (current / "en/index.html").write_text("current en")
            previous = root / "previous"
            (previous / "en").mkdir(parents=True)
            (previous / "index.html").write_text("old zh")
            (previous / "en/index.html").write_text("old en")
            archive = root / "old.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(previous / "index.html", arcname="index.html")
                tf.add(previous / "en/index.html", arcname="en/index.html")
            history = root / "history.json"
            history.write_text(
                json.dumps(
                    [
                        {
                            "version": "1.0.0",
                            "archive": str(archive),
                            "home": "https://example.test/",
                            "english_home": "https://example.test/en/",
                        }
                    ]
                )
            )
            output = root / "out"
            ASSEMBLER.assemble(current, output, "1.1.0", "d" * 40, None, history)
            en_entries = json.loads((output / "en/askr-versions.json").read_text())["versions"]
            self.assertEqual(
                en_entries[1]["href"], "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/v1.0.0/en/"
            )
            old_en = json.loads((output / "v1.0.0/en/askr-versions.json").read_text())["versions"]
            self.assertEqual(
                old_en,
                [
                    {"label": "1.0.0", "root": "/", "latest": True},
                    {"label": "1.1.0", "href": "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/en/"},
                ],
            )

    def test_rejects_non_numeric_or_non_older_history_version(self):
        for invalid_version in ("../../escape", "1.1.0"):
            with self.subTest(version=invalid_version), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                current = root / "current"
                (current / "en").mkdir(parents=True)
                (current / "index.html").write_text("zh")
                (current / "en/index.html").write_text("en")
                archive = root / "old.tar.gz"
                archive.touch()
                history = root / "history.json"
                history.write_text(
                    json.dumps(
                        [
                            {
                                "version": invalid_version,
                                "archive": str(archive),
                                "home": "https://example.test/",
                                "english_home": "https://example.test/en/",
                            }
                        ]
                    )
                )
                with self.assertRaises(ValueError):
                    ASSEMBLER.assemble(current, root / "out", "1.1.0", "e" * 40, None, history)


if __name__ == "__main__":
    unittest.main()
