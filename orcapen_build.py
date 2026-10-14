"""Generate offline usage resources for uv_build without importing the PDK.

Only docs/examples and project metadata are inputs. This is a build backend,
not an installed resource discovery API or an MCP dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import tomllib
from pathlib import Path, PurePosixPath

import uv_build
from uv_build import (
    build_editable as build_editable,
)
from uv_build import (
    get_requires_for_build_editable as get_requires_for_build_editable,
)
from uv_build import (
    get_requires_for_build_sdist as get_requires_for_build_sdist,
)
from uv_build import (
    get_requires_for_build_wheel as get_requires_for_build_wheel,
)
from uv_build import (
    prepare_metadata_for_build_editable as prepare_metadata_for_build_editable,
)
from uv_build import (
    prepare_metadata_for_build_wheel as prepare_metadata_for_build_wheel,
)


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", value):
        raise ValueError("Knowledge resource requires a relative POSIX path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Knowledge resource path contains an unsafe segment")
    return PurePosixPath(value)


def _generate() -> None:
    root = Path(__file__).resolve().parent
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    inventory = tomllib.loads((root / "docs/usage/resources.toml").read_text(encoding="utf-8"))[
        "resources"
    ]
    if project["name"] != "orcapen-sc-pdk" or not inventory:
        raise ValueError("Knowledge bundle requires OrcaPen metadata and declared resources")

    resources = []
    contents = {}
    seen_ids = set()
    for item in sorted(inventory, key=lambda row: row["id"]):
        if set(item) != {"id", "kind", "title", "summary", "status", "source"}:
            raise ValueError("Knowledge inventory entry has unexpected fields")
        if not all(isinstance(value, str) and value.strip() for value in item.values()):
            raise ValueError("Knowledge inventory fields must be nonempty strings")
        resource_id = item["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", resource_id):
            raise ValueError("Invalid knowledge resource ID")
        _relative_path(resource_id)
        relative = _relative_path(item["source"])
        source = root / relative
        if any(path.is_symlink() for path in [source, *source.parents] if path != root):
            raise ValueError("Knowledge source must not use symlinks")
        if resource_id in seen_ids or str(relative) in contents:
            raise ValueError("Duplicate knowledge resource ID or source path")
        data = source.read_bytes()
        data.decode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        seen_ids.add(resource_id)
        contents[str(relative)] = data
        resources.append(
            {
                "id": resource_id,
                "kind": item["kind"],
                "title": item["title"],
                "summary": item["summary"],
                "status": item["status"],
                "path": str(relative),
                "content_sha256": digest,
                "provenance": {"source_ref": str(relative), "source_sha256": digest},
            }
        )

    manifest = {
        "schema_version": "1.0",
        "distribution": project["name"],
        "distribution_version": project["version"],
        "resources": resources,
    }
    manifest["bundle_id"] = "sha256:" + hashlib.sha256(_canonical(manifest)).hexdigest()
    destination = root / "orcapen_sc_pdk/_agent_knowledge"
    if destination.is_symlink():
        raise ValueError("Generated knowledge directory must not be a symlink")
    with tempfile.TemporaryDirectory(prefix="orcapen-knowledge-") as directory:
        staged = Path(directory) / "bundle"
        staged.mkdir()
        for relative, data in contents.items():
            output = staged / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        (staged / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
        # This directory is generated, ignored package data; discard stale resources.
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(staged, destination)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _generate()
    return uv_build.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    _generate()
    return uv_build.build_sdist(sdist_directory, config_settings)
