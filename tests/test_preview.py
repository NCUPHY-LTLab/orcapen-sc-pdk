from pathlib import Path

import gdsfactory as gf
import pytest

import orcapen_sc_pdk.preview as preview


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Record viewer calls instead of reaching VS Code or KLayout."""

    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(gf.Component, "show", lambda self, **_: calls.append("klayout"))
    monkeypatch.setattr(
        preview.subprocess, "run", lambda command, **_: calls.append(" ".join(command))
    )
    return calls


def test_klayout_preview_writes_one_gds_per_factory(opened: list[str]) -> None:
    gds_path = preview.show("taper", viewer="klayout")

    assert gds_path == Path("build/gds/taper.gds")
    assert gds_path.is_file()
    assert opened == ["klayout"]


def test_auto_preview_opens_gds_in_gdsfactoryplus_when_available(
    opened: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(preview, "gdsfactoryplus_is_available", lambda: True)

    preview.show("taper")

    assert opened == ["code --reuse-window build/gds/taper.gds"]


def test_gdsfactoryplus_is_unavailable_outside_a_vscode_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TERM_PROGRAM", raising=False)

    assert not preview.gdsfactoryplus_is_available()
