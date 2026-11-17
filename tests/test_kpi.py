"""Tests des KPI sur des résultats construits à la main (valeurs connues).

Cas « une caisse saturée » : trois clients arrivent à 0 et durent 2 min.
    attentes = 0, 2, 4 ; fin = 6 ; caisse occupée 6 min sur 6.
    p90 (interpolation linéaire) = 2 + 0,8 x (4 - 2) = 3,6
"""

import pytest

from queuesmart.analytics.kpi import KpiCalculator
from tests.builders import build_result

SATURATED = [(0.0, 2.0, 1), (0.0, 2.0, 1), (0.0, 2.0, 1)]


def test_wait_statistics() -> None:
    report = KpiCalculator().compute(build_result(SATURATED, register_count=1))
    assert report.customer_count == 3
    assert report.mean_wait == pytest.approx(2.0)
    assert report.median_wait == pytest.approx(2.0)
    assert report.p90_wait == pytest.approx(3.6)
    assert report.max_wait == pytest.approx(4.0)
    assert report.share_over_threshold == 0.0


def test_threshold_is_configurable() -> None:
    report = KpiCalculator(wait_threshold_min=3.0).compute(build_result(SATURATED, 1))
    assert report.share_over_threshold == pytest.approx(1 / 3)


def test_wait_equal_to_threshold_is_not_over() -> None:
    report = KpiCalculator(wait_threshold_min=4.0).compute(build_result(SATURATED, 1))
    assert report.share_over_threshold == 0.0


def test_utilization_per_register() -> None:
    # Caisse 1 : 0 -> 4 ; caisse 2 : 1 -> 2. Fin à 4.
    result = build_result([(0.0, 4.0, 1), (1.0, 1.0, 2)], register_count=2)
    report = KpiCalculator().compute(result)
    assert report.utilization_by_register == {1: pytest.approx(1.0), 2: pytest.approx(0.25)}
    assert report.mean_utilization == pytest.approx(0.625)


def test_single_customer() -> None:
    report = KpiCalculator().compute(build_result([(1.0, 2.0, 1)], register_count=1))
    assert report.p90_wait == 0.0
    assert report.max_wait == 0.0


def test_compute_many_pools_customers() -> None:
    saturated = build_result(SATURATED, register_count=1)
    calm = build_result([(0.0, 2.0, 1)], register_count=1)
    report = KpiCalculator().compute_many([saturated, calm])
    assert report.customer_count == 4
    assert report.mean_wait == pytest.approx(1.5)  # (0 + 2 + 4 + 0) / 4
    assert report.utilization_by_register[1] == pytest.approx(1.0)


def test_compute_many_requires_results() -> None:
    with pytest.raises(ValueError):
        KpiCalculator().compute_many([])


def test_negative_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        KpiCalculator(wait_threshold_min=-1.0)
