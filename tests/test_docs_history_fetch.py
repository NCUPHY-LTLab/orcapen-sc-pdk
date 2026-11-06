from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fetch_previous_docs_release", ROOT / "scripts/fetch_previous_docs_release.py"
)
FETCHER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(FETCHER)


class DocsHistoryFetchTests(unittest.TestCase):
    def test_empty_initial_history_writes_empty_manifest_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            source.write_text("[]")
            output = root / "prepared.json"
            with patch.object(FETCHER.subprocess, "run") as run:
                FETCHER.fetch_history(source, "1.0.0", root / "assets", output)
            run.assert_not_called()
            self.assertEqual(json.loads(output.read_text()), [])

    def test_exact_release_docs_asset_checksum_produces_assembler_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_bytes = b"audited older documentation archive"
            digest = hashlib.sha256(archive_bytes).hexdigest()
            source = root / "source.json"
            source.write_text(
                json.dumps(
                    [
                        {
                            "version": "0.9.0",
                            "tag": "v0.9.0",
                            "asset": "docs-site.tar.gz",
                            "sha256": digest,
                        }
                    ]
                )
            )
            output = root / "prepared.json"

            def fake_download(command, check):
                destination = Path(command[command.index("--dir") + 1])
                (destination / "docs-site.tar.gz").write_bytes(archive_bytes)
                (destination / "SHA256SUMS").write_text(f"{digest}  docs-site.tar.gz\n")

            with patch.object(FETCHER.subprocess, "run", side_effect=fake_download) as run:
                FETCHER.fetch_history(source, "1.0.0", root / "assets", output)
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--pattern") + 1], "docs-site.tar.gz")
            prepared = json.loads(output.read_text())
            self.assertEqual(prepared[0]["version"], "0.9.0")
            self.assertEqual(Path(prepared[0]["archive"]).read_bytes(), archive_bytes)
            self.assertEqual(
                prepared[0]["home"], "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/v0.9.0/"
            )
            self.assertEqual(prepared[0]["english_home"], prepared[0]["home"] + "en/")

    def test_invalid_or_duplicate_entries_fail_before_network(self):
        invalid_rows = [
            [
                {
                    "version": "../escape",
                    "tag": "v../escape",
                    "asset": "docs-site.tar.gz",
                    "sha256": "0" * 64,
                }
            ],
            [
                {
                    "version": "1.0.0",
                    "tag": "v1.0.0",
                    "asset": "docs-site.tar.gz",
                    "sha256": "0" * 64,
                }
            ],
            [
                {
                    "version": "0.9.0",
                    "tag": "v0.9.0",
                    "asset": "docs-site.tar.gz",
                    "sha256": "0" * 64,
                },
                {
                    "version": "0.9.0",
                    "tag": "v0.9.0",
                    "asset": "docs-site.tar.gz",
                    "sha256": "0" * 64,
                },
            ],
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            for rows in invalid_rows:
                source.write_text(json.dumps(rows))
                with patch.object(FETCHER.subprocess, "run") as run, self.assertRaises(ValueError):
                    FETCHER.fetch_history(source, "1.0.0", root / "assets", root / "prepared.json")
                run.assert_not_called()

    def test_checksum_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.json"
            source.write_text(
                json.dumps(
                    [
                        {
                            "version": "0.9.0",
                            "tag": "v0.9.0",
                            "asset": "docs-site.tar.gz",
                            "sha256": "0" * 64,
                        }
                    ]
                )
            )

            def fake_download(command, check):
                destination = Path(command[command.index("--dir") + 1])
                (destination / "docs-site.tar.gz").write_bytes(b"wrong")
                (destination / "SHA256SUMS").write_text(f"{'1' * 64}  docs-site.tar.gz\n")

            with (
                patch.object(FETCHER.subprocess, "run", side_effect=fake_download),
                self.assertRaisesRegex(ValueError, "checksum mismatch"),
            ):
                FETCHER.fetch_history(source, "1.0.0", root / "assets", root / "prepared.json")


if __name__ == "__main__":
    unittest.main()
