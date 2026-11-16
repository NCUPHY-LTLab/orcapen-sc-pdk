"""The construction checks report what the caller expects, even where nothing was drawn."""

import gdsfactory as gf
from geometry_checks import construction_report

from orcapen_sc_pdk import activate

LAYER = (1, 0)
OTHER = (2, 0)


def _square(layer):
    c = gf.Component()
    c.add_polygon([(0, 0), (10, 0), (10, 10), (0, 10)], layer=layer)
    return c


def test_an_expected_layer_that_was_never_drawn_is_a_defect() -> None:
    activate()
    meant = _square(LAYER).get_region(LAYER, merge=True)
    reports = construction_report(gf.Component(), conductors={LAYER: 1}, intended={LAYER: meant})
    report = reports[LAYER]
    assert report.polygons == 0
    assert "merged: 0 polygons for 1 conductor(s)" in report.defects
    assert any("differs from the intended shape" in defect for defect in report.defects)
    assert (report.difference ^ meant).is_empty()


def test_an_expected_layer_missing_beside_a_drawn_one_is_a_defect() -> None:
    activate()
    reports = construction_report(_square(OTHER), conductors={LAYER: 1, OTHER: 1})
    assert reports[OTHER].defects == ()
    assert reports[LAYER].defects == ("merged: 0 polygons for 1 conductor(s)",)


def test_an_empty_intended_layer_matches_an_empty_build() -> None:
    activate()
    reports = construction_report(gf.Component(), intended={LAYER: gf.kdb.Region()})
    assert reports[LAYER].defects == ()
