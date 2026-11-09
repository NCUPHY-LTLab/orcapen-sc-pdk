from pathlib import Path

from orcapen_sc_pdk.config import PATH
from orcapen_sc_pdk.pdk import write_layer_properties


def test_bundled_lyp_matches_layers_yaml(tmp_path: Path) -> None:
    written = write_layer_properties(tmp_path / "orcapen.lyp")

    assert written.read_text() == PATH.lyp.read_text()
