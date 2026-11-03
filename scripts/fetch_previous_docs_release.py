#!/usr/bin/env python3
"""Fetch only explicitly listed older docs archives and verify their release checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = "NCUPHY-LTLab/orcapen-sc-pdk"
DOCS_ASSET = "docs-site.tar.gz"
CHECKSUM_ASSET = "SHA256SUMS"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_rows(rows: object, current_version: str) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise ValueError("release history must be a JSON array")
    current = tuple(int(part) for part in current_version.split("."))
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"version", "tag", "asset", "sha256"}:
            raise ValueError("history entries require exactly version, tag, asset and sha256")
        version = row["version"]
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError(f"invalid history version: {version!r}")
        if tuple(int(part) for part in version.split(".")) >= current:
            raise ValueError(f"history version must be older than {current_version}: {version}")
        if version in seen:
            raise ValueError(f"duplicate history version: {version}")
        seen.add(version)
        if row["tag"] != f"v{version}" or row["asset"] != DOCS_ASSET:
            raise ValueError(f"history release must use tag v{version} and {DOCS_ASSET}")
        if not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError(f"invalid SHA-256 for release {version}")
        validated.append({key: str(row[key]) for key in ("version", "tag", "asset", "sha256")})
    return validated


def fetch(tag: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    subprocess.run(
        [
            "gh",
            "release",
            "download",
            tag,
            "--repo",
            REPO,
            "--pattern",
            DOCS_ASSET,
            "--pattern",
            CHECKSUM_ASSET,
            "--dir",
            str(destination),
        ],
        check=True,
    )


def checksum_entry(checksums: Path, asset: str) -> str:
    matches = []
    for line in checksums.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and fields[1].lstrip(" *") == asset:
            matches.append(fields[0])
    if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{64}", matches[0]):
        raise ValueError(f"{CHECKSUM_ASSET} must contain exactly one valid checksum for {asset}")
    return matches[0]


def fetch_history(
    source_manifest: Path, current_version: str, destination: Path, output_manifest: Path
) -> None:
    rows = validate_rows(json.loads(source_manifest.read_text(encoding="utf-8")), current_version)
    if output_manifest.exists():
        raise FileExistsError(f"refusing to overwrite generated manifest: {output_manifest}")
    result: list[dict[str, str]] = []
    for row in rows:
        version_dir = destination / f"v{row['version']}"
        fetch(row["tag"], version_dir)
        archive = version_dir / DOCS_ASSET
        checksum_file = version_dir / CHECKSUM_ASSET
        if not archive.is_file() or not checksum_file.is_file():
            raise FileNotFoundError(
                f"release {row['tag']} did not provide both required docs assets"
            )
        advertised = checksum_entry(checksum_file, DOCS_ASSET)
        actual = sha256(archive)
        if advertised != row["sha256"] or actual != advertised:
            raise ValueError(f"docs archive checksum mismatch for release {row['tag']}")
        base = f"https://ncuphy-ltlab.github.io/orcapen-sc-pdk/v{row['version']}/"
        result.append(
            {
                "version": row["version"],
                "archive": str(archive.resolve()),
                "home": base,
                "english_home": base + "en/",
            }
        )
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "history_manifest", type=Path, help="committed JSON array of exact release assets"
    )
    parser.add_argument("destination", type=Path)
    parser.add_argument("--current-version", required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    args = parser.parse_args()
    fetch_history(
        args.history_manifest, args.current_version, args.destination, args.output_manifest
    )


if __name__ == "__main__":
    main()
