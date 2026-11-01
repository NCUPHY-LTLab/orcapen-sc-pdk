#!/usr/bin/env python3
"""Assemble Askr version manifests and metadata around rendered docs and real releases."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
from pathlib import Path, PurePosixPath


def safe_member(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {name}")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"archive path escapes destination: {name}")
    return target


def extract_site(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            target = safe_member(destination, member.name)
            if member.issym() or member.islnk():
                link = (target.parent / member.linkname).resolve()
                if not link.is_relative_to(destination.resolve()):
                    raise ValueError(f"archive link escapes destination: {member.name}")
                raise ValueError("documentation archives may not contain links")
            parts = PurePosixPath(member.name).parts
            if parts and re.fullmatch(r"v\d+\.\d+\.\d+", parts[0]):
                continue
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tf.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot read archive member: {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def manifest(versions: list[dict[str, object]]) -> dict[str, object]:
    return {"mode": "title", "versions": versions}


def write_manifests(root: Path, version: str, history: list[dict[str, str]]) -> None:
    for language, language_root in (("zh", root), ("en", root / "en")):
        if not (language_root / "index.html").is_file():
            raise ValueError(
                f"required language homepage is missing: {language_root / 'index.html'}"
            )
        if language == "en":
            entries = [{"label": version, "root": "/", "latest": True}]
            entries.extend(
                {
                    "label": old["version"],
                    "href": f"https://ncuphy-ltlab.github.io/orcapen-sc-pdk/v{old['version']}/en/",
                }
                for old in history
            )
        else:
            entries = [{"label": version, "root": "/", "latest": True}]
            entries.extend(
                {"label": old["version"], "root": f"/v{old['version']}/"} for old in history
            )
        entries.sort(
            key=lambda row: tuple(int(x) for x in str(row["label"]).split(".")), reverse=True
        )
        (language_root / "askr-versions.json").write_text(
            json.dumps(manifest(entries), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    # Every preserved version gets a standalone archive-local manifest. Its
    # older choices point to fixed release homes rather than guessed snapshots.
    for old in history:
        old_root = root / f"v{old['version']}"
        if not (old_root / "index.html").is_file() or not (old_root / "en/index.html").is_file():
            raise ValueError(
                f"historical release {old['version']} is not a complete bilingual site"
            )
        for language, lang_root in (("zh", old_root), ("en", old_root / "en")):
            nested = [{"label": old["version"], "root": "/", "latest": True}]
            current_home = (
                "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/en/"
                if language == "en"
                else "https://ncuphy-ltlab.github.io/orcapen-sc-pdk/"
            )
            nested.append({"label": version, "href": current_home})
            home_key = "english_home" if language == "en" else "home"
            nested.extend(
                {"label": newer["version"], "href": newer[home_key]}
                for newer in history
                if newer["version"] != old["version"]
            )
            (lang_root / "askr-versions.json").write_text(
                json.dumps(manifest(nested), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )


def assemble(
    current: Path,
    output: Path,
    version: str,
    source_sha: str,
    pages_run: str | None,
    history_manifest: Path | None,
) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be numeric semantic major.minor.patch")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source SHA must be a full lowercase Git SHA")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    shutil.copytree(current, output)
    history: list[dict[str, str]] = []
    if history_manifest:
        rows = json.loads(history_manifest.read_text(encoding="utf-8"))
        current_tuple = tuple(int(part) for part in version.split("."))
        seen_versions: set[str] = set()
        seen_archives: set[Path] = set()
        for row in rows:
            old = str(row["version"])
            if (
                not re.fullmatch(r"\d+\.\d+\.\d+", old)
                or tuple(int(part) for part in old.split(".")) >= current_tuple
            ):
                raise ValueError(
                    f"history version must be a stable version older than {version}: {old}"
                )
            if old in seen_versions:
                raise ValueError(f"duplicate history version: {old}")
            seen_versions.add(old)
            archive = Path(row["archive"]).resolve()
            if archive in seen_archives:
                raise ValueError(f"duplicate history archive: {archive}")
            seen_archives.add(archive)
            if not archive.is_file():
                raise FileNotFoundError(archive)
            if not row.get("home") or not row.get("english_home"):
                raise ValueError("each historical release needs fixed home and english_home URLs")
            extract_site(archive, output / f"v{old}")
            history.append(
                {"version": old, "home": str(row["home"]), "english_home": str(row["english_home"])}
            )
    write_manifests(output, version, history)
    release = {"packageVersion": version, "sourceSHA": source_sha, "languages": ["zh-TW", "en"]}
    if pages_run:
        release["pagesRun"] = pages_run
    (output / "docs-release.json").write_text(
        json.dumps(release, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--pages-run")
    parser.add_argument("--history-manifest", type=Path)
    args = parser.parse_args()
    assemble(
        args.current,
        args.output,
        args.version,
        args.source_sha,
        args.pages_run,
        args.history_manifest,
    )


if __name__ == "__main__":
    main()
