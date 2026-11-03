from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.package_example_artifacts import PackageError, package_selection


class PackageExampleArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "input.bin"
        self.source.write_bytes(b"selected payload\x00\x01")
        self.selection = self.root / "selection.json"
        self.output = self.root / "out"
        self.document = {
            "package": "example-pdk",
            "run_id": "run-001",
            "kind": "public-result",
            "files": [
                {
                    "source": str(self.source),
                    "member": "data/result.bin",
                    "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                }
            ],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_selection(self) -> None:
        self.selection.write_text(json.dumps(self.document), encoding="utf-8")

    def test_archive_roundtrip_hash_and_normalized_headers(self) -> None:
        self.write_selection()
        package_selection(self.selection, self.output)
        archive_path = self.output / "example-pdk--run-001--public-result.tar.gz"
        with tarfile.open(archive_path, "r:gz") as archive:
            manifest = json.load(archive.extractfile("MANIFEST.json"))
            member = archive.getmember("data/result.bin")
            self.assertEqual(archive.extractfile(member).read(), self.source.read_bytes())
            self.assertEqual(member.mode, 0o644)
            self.assertEqual(member.mtime, 0)
            self.assertEqual(member.uid, 0)
            self.assertEqual(member.gid, 0)
            self.assertEqual(member.uname, "")
            self.assertEqual(member.gname, "")
        self.assertEqual(manifest["run_id"], "run-001")
        self.assertEqual(manifest["files"][0]["member"], "data/result.bin")
        sidecar = json.loads((self.output / "package_manifest.json").read_text())
        self.assertEqual(
            sidecar["archive"]["sha256"],
            hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        )

    def test_declared_runner_keeps_executable_mode(self) -> None:
        self.document["files"][0]["runner"] = True
        self.document["files"][0]["member"] = "bin/run.sh"
        self.write_selection()
        package_selection(self.selection, self.output)
        with tarfile.open(
            self.output / "example-pdk--run-001--public-result.tar.gz", "r:gz"
        ) as archive:
            self.assertEqual(archive.getmember("bin/run.sh").mode, 0o755)

    def test_archive_name_uses_selection_identifiers(self) -> None:
        self.write_selection()
        first = package_selection(self.selection, self.output)
        second_output = self.root / "second"
        self.document["run_id"] = "run-002"
        self.write_selection()
        second = package_selection(self.selection, second_output)
        self.assertNotEqual(first["archive"]["archive"], second["archive"]["archive"])
        self.assertEqual(
            first["archive"]["archive"],
            "example-pdk--run-001--public-result.tar.gz",
        )

    def test_long_member_path_uses_pax_headers(self) -> None:
        member = f"{'d' * 130}/{'f' * 130}.bin"
        self.document["files"][0]["member"] = member
        self.write_selection()
        package_selection(self.selection, self.output)
        archive_path = self.output / "example-pdk--run-001--public-result.tar.gz"
        with tarfile.open(archive_path, "r:gz") as archive:
            member_info = archive.getmember(member)
            self.assertEqual(archive.extractfile(member_info).read(), self.source.read_bytes())
            self.assertEqual(member_info.mtime, 0)
            self.assertEqual(member_info.uid, 0)
            self.assertEqual(member_info.gid, 0)
            self.assertEqual(member_info.uname, "")
            self.assertEqual(member_info.gname, "")

    def test_tampered_source_is_rejected(self) -> None:
        self.document["files"][0]["sha256"] = "0" * 64
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "SHA256 mismatch"):
            package_selection(self.selection, self.output)
        self.assertFalse(self.output.exists())

    def test_unsafe_and_duplicate_members_are_rejected(self) -> None:
        for member in ("../escape", "/absolute", "a/../../escape"):
            self.document["files"][0]["member"] = member
            self.write_selection()
            with self.subTest(member=member), self.assertRaises(PackageError):
                package_selection(self.selection, self.output)
            self.assertFalse(self.output.exists())
        self.document["files"][0]["member"] = "data/result.bin"
        self.document["files"].append(dict(self.document["files"][0]))
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "duplicate archive member"):
            package_selection(self.selection, self.output)

    def test_symlink_and_nonregular_sources_are_rejected(self) -> None:
        link = self.root / "link.bin"
        link.symlink_to(self.source)
        self.document["files"][0]["source"] = str(link)
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "symlink"):
            package_selection(self.selection, self.output)
        self.document["files"][0]["source"] = str(self.root)
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "regular file"):
            package_selection(self.selection, self.output)

    def test_fifo_source_is_rejected_without_blocking(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO fixtures require POSIX")
        fifo = self.root / "input.fifo"
        os.mkfifo(fifo)
        self.document["files"][0]["source"] = str(fifo)
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "regular file"):
            package_selection(self.selection, self.output)

    def test_source_changed_after_prevalidation_is_rejected(self) -> None:
        self.write_selection()
        from scripts import package_example_artifacts

        original_addfile = tarfile.TarFile.addfile

        def change_selected_source(
            archive: tarfile.TarFile, tarinfo: tarfile.TarInfo, fileobj=None
        ):
            if tarinfo.name == "data/result.bin":
                self.source.write_bytes(b"changed after validation")
            return original_addfile(archive, tarinfo, fileobj)

        with patch.object(
            package_example_artifacts.tarfile.TarFile,
            "addfile",
            change_selected_source,
        ):
            with self.assertRaisesRegex(PackageError, "source changed while packaging"):
                package_selection(self.selection, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_rejected(self) -> None:
        self.output.mkdir()
        self.write_selection()
        with self.assertRaisesRegex(PackageError, "already exists"):
            package_selection(self.selection, self.output)

    def test_small_injected_parts_join_back_to_original_archive(self) -> None:
        self.document["files"][0]["member"] = "data/large.bin"
        self.source.write_bytes(os.urandom(2048))
        self.document["files"][0]["sha256"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.write_selection()
        record = package_selection(self.selection, self.output, part_size=128)
        parts = record["archive"]["parts"]
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(part["bytes"] <= 128 for part in parts))
        joined = b"".join((self.output / part["name"]).read_bytes() for part in parts)
        self.assertEqual(hashlib.sha256(joined).hexdigest(), record["archive"]["sha256"])
        temp_archive = self.root / "joined.tar.gz"
        temp_archive.write_bytes(joined)
        with tarfile.open(temp_archive, "r:gz") as archive:
            self.assertEqual(archive.extractfile("data/large.bin").read(), self.source.read_bytes())


if __name__ == "__main__":
    unittest.main()
