#!/usr/bin/env python3
"""Package an explicitly selected set of local public example artifacts."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

PART_SIZE_LIMIT = 1900 * 1024 * 1024
PART_COPY_CHUNK = 1024 * 1024
PUBLIC_MANIFEST = "MANIFEST.json"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class PackageError(ValueError):
    """The selection or requested output is unsafe or inconsistent."""


@dataclass
class SelectedFile:
    source: Path
    member: str
    sha256: str
    executable: bool
    stream: BinaryIO
    size: int


class _HashingReader:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.digest.update(data)
        return data


def _member_name(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PackageError("member must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise PackageError(f"unsafe archive member path: {value!r}")
    normalized = path.as_posix()
    if normalized != value or normalized == PUBLIC_MANIFEST:
        raise PackageError(f"invalid or reserved archive member path: {value!r}")
    return normalized


def _load_selection(selection_path: Path) -> tuple[str, str, str, list[SelectedFile]]:
    try:
        document = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read selection JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise PackageError("selection must be a JSON object")
    identifiers = []
    for key in ("package", "run_id", "kind"):
        value = document.get(key)
        if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value) or "--" in value:
            raise PackageError(
                f"{key} must use letters, digits, dot, underscore, or hyphen; '--' is reserved"
            )
        identifiers.append(value)
    rows = document.get("files")
    if not isinstance(rows, list) or not rows:
        raise PackageError("files must be a nonempty explicit list")

    selected: list[SelectedFile] = []
    names: set[str] = set()
    sources: set[str] = set()
    try:
        for row in rows:
            if not isinstance(row, dict):
                raise PackageError("each files entry must be an object")
            source_value = row.get("source")
            expected = row.get("sha256")
            if not isinstance(source_value, str) or not Path(source_value).is_absolute():
                raise PackageError("each source must be an absolute path")
            if not isinstance(expected, str) or not HASH_RE.fullmatch(expected):
                raise PackageError("each sha256 must be 64 lowercase hexadecimal characters")
            member = _member_name(row.get("member"))
            if member in names:
                raise PackageError(f"duplicate archive member: {member}")
            names.add(member)
            source = Path(source_value)
            if str(source) in sources:
                raise PackageError(f"duplicate source path: {source}")
            sources.add(str(source))
            try:
                path_info = os.lstat(source)
            except OSError as exc:
                raise PackageError(f"cannot inspect source file: {source}") from exc
            if stat.S_ISLNK(path_info.st_mode):
                raise PackageError(f"source is a symlink: {source}")
            if not stat.S_ISREG(path_info.st_mode):
                raise PackageError(f"source is not a regular file: {source}")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            try:
                descriptor = os.open(source, flags)
            except OSError as exc:
                raise PackageError(f"cannot open source file: {source}") from exc
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                os.close(descriptor)
                raise PackageError(f"source is not a regular file: {source}")
            stream = os.fdopen(descriptor, "rb")
            digest = hashlib.sha256()
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
            if digest.hexdigest() != expected:
                stream.close()
                raise PackageError(f"SHA256 mismatch for selected source: {source}")
            stream.seek(0)
            selected.append(
                SelectedFile(
                    source=source,
                    member=member,
                    sha256=expected,
                    executable=row.get("runner") is True,
                    stream=stream,
                    size=info.st_size,
                )
            )
    except Exception:
        for item in selected:
            item.stream.close()
        raise
    return identifiers[0], identifiers[1], identifiers[2], selected


def _tar_info(name: str, size: int, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.type = tarfile.REGTYPE
    return info


def _write_archive(
    path: Path, package: str, run_id: str, kind: str, files: list[SelectedFile]
) -> None:
    manifest = {
        "package": package,
        "run_id": run_id,
        "kind": kind,
        "files": [
            {"member": item.member, "sha256": item.sha256, "bytes": item.size} for item in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with path.open("xb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                archive.addfile(
                    _tar_info(PUBLIC_MANIFEST, len(manifest_bytes), 0o644),
                    _bytes(manifest_bytes),
                )
                for item in files:
                    item.stream.seek(0)
                    hashing_reader = _HashingReader(item.stream)
                    archive.addfile(
                        _tar_info(
                            item.member,
                            item.size,
                            0o755 if item.executable else 0o644,
                        ),
                        hashing_reader,
                    )
                    if hashing_reader.digest.hexdigest() != item.sha256:
                        raise PackageError(f"source changed while packaging: {item.source}")


def _bytes(value: bytes) -> BinaryIO:
    from io import BytesIO

    return BytesIO(value)


def _digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _split_archive(archive: Path, output: Path, max_part_size: int) -> dict[str, object]:
    if max_part_size <= 0:
        raise PackageError("part size must be positive")
    archive_hash, archive_size = _digest_file(archive)
    if archive_size <= max_part_size:
        final = output / archive.name
        archive.rename(final)
        return {"archive": final.name, "sha256": archive_hash, "bytes": archive_size, "parts": []}

    parts = []
    with archive.open("rb") as source:
        index = 1
        remaining_archive = archive_size
        while remaining_archive:
            part_name = f"{archive.name}.part{index:03d}"
            part_path = output / part_name
            part_digest = hashlib.sha256()
            part_size = 0
            with part_path.open("xb") as destination:
                remaining_part = min(max_part_size, remaining_archive)
                while remaining_part:
                    chunk = source.read(min(PART_COPY_CHUNK, remaining_part))
                    if not chunk:
                        raise PackageError("archive ended unexpectedly while splitting")
                    destination.write(chunk)
                    part_digest.update(chunk)
                    chunk_size = len(chunk)
                    part_size += chunk_size
                    remaining_part -= chunk_size
                    remaining_archive -= chunk_size
            parts.append({"name": part_name, "sha256": part_digest.hexdigest(), "bytes": part_size})
            index += 1
    archive.unlink()
    return {"archive": archive.name, "sha256": archive_hash, "bytes": archive_size, "parts": parts}


def package_selection(
    selection_path: Path, output_dir: Path, *, part_size: int = PART_SIZE_LIMIT
) -> dict[str, object]:
    package, run_id, kind, files = _load_selection(selection_path)
    if output_dir.exists() or output_dir.is_symlink():
        for item in files:
            item.stream.close()
        raise PackageError("output directory already exists")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()
    archive_name = f"{package}--{run_id}--{kind}.tar.gz"
    temporary_archive = output_dir / archive_name
    try:
        _write_archive(temporary_archive, package, run_id, kind, files)
        archive_record = _split_archive(temporary_archive, output_dir, part_size)
        sidecar = {
            "package": package,
            "run_id": run_id,
            "kind": kind,
            "archive": archive_record,
        }
        (output_dir / "package_manifest.json").write_text(
            json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return sidecar
    except Exception:
        shutil.rmtree(output_dir)
        raise
    finally:
        for item in files:
            item.stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path, help="explicit local selection JSON")
    parser.add_argument("output_dir", type=Path, help="new output directory")
    args = parser.parse_args()
    try:
        record = package_selection(args.selection, args.output_dir)
    except (PackageError, OSError, tarfile.TarError) as exc:
        parser.error(str(exc))
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
