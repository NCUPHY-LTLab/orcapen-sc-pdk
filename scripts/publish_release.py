#!/usr/bin/env python3
"""Guarded publisher for a later Human-confirmed tag workflow; never auto-discovers assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

REPO = "NCUPHY-LTLab/orcapen-sc-pdk"


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True, stderr=subprocess.PIPE).strip()


def tag_commit(tag: str) -> str:
    ref = json.loads(gh("api", f"repos/{REPO}/git/ref/tags/{tag}"))
    obj = ref["object"]
    while obj["type"] == "tag":
        obj = json.loads(gh("api", f"repos/{REPO}/git/tags/{obj['sha']}"))["object"]
    if obj["type"] != "commit":
        raise ValueError("release tag does not resolve to a commit")
    return obj["sha"]


def release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "api", "--include", f"repos/{REPO}/releases/tags/{tag}"],
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return True
    if "HTTP/2.0 404" in result.stdout or "HTTP/1.1 404" in result.stdout:
        return False
    raise RuntimeError(f"could not determine release state: {result.stderr.strip()}")


def is_eligible_pages_run(run: dict[str, str], revision: str) -> bool:
    return (
        run.get("head_sha") == revision
        and run.get("conclusion") == "success"
        and run.get("path") == ".github/workflows/pages.yml"
        and run.get("event") == "push"
        and run.get("head_branch") == "main"
    )


def package_metadata(path: Path) -> tuple[str, str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as wheel:
            names = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ValueError(f"wheel must contain one METADATA: {path}")
            raw = wheel.read(names[0]).decode("utf-8")
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            names = [name for name in archive.getnames() if name.endswith("/PKG-INFO")]
            if len(names) != 1:
                raise ValueError(f"sdist must contain one PKG-INFO: {path}")
            stream = archive.extractfile(names[0])
            if stream is None:
                raise ValueError(f"cannot read PKG-INFO: {path}")
            raw = stream.read().decode("utf-8")
    else:
        raise ValueError(f"unsupported package asset: {path.name}")
    metadata = Parser().parsestr(raw)
    return metadata.get("Name", ""), metadata.get("Version", "")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def primary_package_names(primary_rows: list[dict[str, str]]) -> tuple[str, str]:
    primary_names = [str(row.get("name", "")) for row in primary_rows]
    wheels = [name for name in primary_names if name.endswith(".whl")]
    sdists = [
        name for name in primary_names if name.endswith(".tar.gz") and name != "docs-site.tar.gz"
    ]
    if len(wheels) != 1 or len(sdists) != 1 or "docs-site.tar.gz" not in primary_names:
        raise ValueError(
            "primary asset manifest must include docs-site.tar.gz, one wheel and one sdist"
        )
    return wheels[0], sdists[0]


def publish(tag: str, assets_manifest: Path, external_manifest: Path | None = None) -> None:
    version = tag.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("tag must be vMAJOR.MINOR.PATCH")
    spec = json.loads(assets_manifest.read_text(encoding="utf-8"))
    if set(spec) != {"revision", "pagesRun", "assets"} or not isinstance(spec["assets"], list):
        raise ValueError("asset manifest requires revision, pagesRun, and explicit assets list")
    revision = spec["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("asset manifest revision must be a full Git SHA")
    main = gh("api", f"repos/{REPO}/commits/main", "--jq", ".sha")
    if main != revision or tag_commit(tag) != revision:
        raise ValueError("tag commit, main, and asset-manifest revision must match")
    if release_exists(tag):
        raise ValueError(f"release {tag} already exists")
    runs = json.loads(gh("api", f"repos/{REPO}/actions/runs/{spec['pagesRun']}"))
    if not is_eligible_pages_run(runs, revision):
        raise ValueError("referenced Pages run is not a successful exact-revision Pages run")
    artifact_data = json.loads(gh("api", f"repos/{REPO}/actions/runs/{spec['pagesRun']}/artifacts"))
    if not any(
        item.get("name") == "docs-site" and not item.get("expired")
        for item in artifact_data.get("artifacts", [])
    ):
        raise ValueError("referenced Pages run has no available docs-site artifact")
    primary_rows = spec["assets"]
    if not isinstance(primary_rows, list):
        raise ValueError("primary assets must be an explicit list")
    wheel_name, sdist_name = primary_package_names(primary_rows)
    rows = primary_rows
    if external_manifest:
        external = json.loads(external_manifest.read_text(encoding="utf-8"))
        if not isinstance(external, list) or any(
            set(row) != {"path", "name", "sha256"} for row in external
        ):
            raise ValueError("external manifest must explicitly list path, name and sha256")
        rows = rows + external
    paths: list[Path] = []
    for row in rows:
        if set(row) != {"path", "name", "sha256"}:
            raise ValueError("each asset requires explicit path, name and sha256")
        path = Path(row["path"])
        if not path.is_file() or path.name != row["name"] or checksum(path) != row["sha256"]:
            raise ValueError(f"asset missing or checksum mismatch: {path}")
        paths.append(path)
    names = [p.name for p in paths]
    if len(names) != len(set(names)) or "docs-site.tar.gz" not in names:
        raise ValueError("assets must have unique names and include docs-site.tar.gz")
    wheel = next(p for p in paths if p.name == wheel_name)
    sdist = next(p for p in paths if p.name == sdist_name)
    for package in (wheel, sdist):
        name, found_version = package_metadata(package)
        if name.lower().replace("_", "-") != "orcapen-sc-pdk" or found_version != version:
            raise ValueError(f"package metadata mismatch in {package.name}")
    with tarfile.open(next(p for p in paths if p.name == "docs-site.tar.gz"), "r:gz") as archive:
        metadata_files = [
            m
            for m in archive.getmembers()
            if m.name.endswith("/docs-release.json") or m.name == "docs-release.json"
        ]
        if len(metadata_files) != 1:
            raise ValueError("docs archive must contain one docs-release.json")
        item = archive.extractfile(metadata_files[0])
        docs = json.load(item)
    if (
        docs.get("packageVersion") != version
        or docs.get("sourceSHA") != revision
        or docs.get("languages") != ["zh-TW", "en"]
        or docs.get("pagesRun") != str(spec["pagesRun"])
    ):
        raise ValueError("documentation archive identity or language inventory mismatch")
    checksum_file = Path("SHA256SUMS")
    checksum_file.write_text("".join(f"{checksum(p)}  {p.name}\n" for p in paths), encoding="utf-8")
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            *map(str, paths),
            str(checksum_file),
            "--repo",
            REPO,
            "--verify-tag",
            "--title",
            tag,
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    parser.add_argument("assets_manifest", type=Path)
    parser.add_argument("--external-artifacts-manifest", type=Path)
    args = parser.parse_args()
    publish(args.tag, args.assets_manifest, args.external_artifacts_manifest)


if __name__ == "__main__":
    main()
