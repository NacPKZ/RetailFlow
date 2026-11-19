"""Tests A07, A08 et A10 de la comparaison et de l'optimiseur dynamiques."""

import pytest

from queuesmart.analytics.dynamic_comparison import (
    DynamicComparisonReport,
    DynamicComparisonRow,
    compare_dynamic_register_counts,
)
from queuesmart.analytics.dynamic_optimizer import recommend_by_mean_wait
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions


def make_config(seed=42):
    return ScenarioConfig("Comparaison", 35, 30.0, 2.0, 3, seed=seed)


def make_report(means):
    rows = tuple(
        DynamicComparisonRow(
            register_count=register_count,
            served_count=20 if mean is not None else 0,
            abandoned_count=0 if mean is not None else 20,
            abandonment_rate=0.0 if mean is not None else 1.0,
            mean_wait_served_min=mean,
            p95_wait_served_min=mean,
            absolute_gain_vs_previous_min=None,
            relative_gain_vs_previous=None,
        )
        for register_count, mean in enumerate(means, start=1)
    )
    return DynamicComparisonReport(
        base_config=make_config(),
        options=DynamicOptions(patience_min=None, switching_enabled=False),
        rows=rows,
        results_by_register_count={},
        reports_by_register_count={},
    )


def test_comparison_uses_the_same_generated_customers_for_one_to_five_registers():
    config = make_config()
    options = DynamicOptions(patience_min=None, switching_enabled=False)

    comparison = compare_dynamic_register_counts(config, options)

    assert [row.register_count for row in comparison.rows] == [1, 2, 3, 4, 5]
    reference = comparison.results_by_register_count[1].customers
    for result in comparison.results_by_register_count.values():
        assert [
            (customer.customer_id, customer.arrival_time, customer.service_duration)
            for customer in result.customers
        ] == [
            (customer.customer_id, customer.arrival_time, customer.service_duration)
            for customer in reference
        ]


def test_a07_no_configuration_meets_threshold_returns_empty_recommendation():
    recommendation = recommend_by_mean_wait(make_report([8.0, 6.0, 4.0]), threshold_min=2.0)

    assert recommendation.recommended_registers is None
    assert recommendation.message == "aucune configuration conforme"


def test_a08_smallest_configuration_is_selected_when_several_meet_threshold():
    recommendation = recommend_by_mean_wait(make_report([5.0, 3.0, 2.5, 2.0, 1.5]), 3.0)

    assert recommendation.recommended_registers == 2
    assert recommendation.mean_wait_by_register_count[2] == 3.0


def test_missing_mean_wait_is_never_considered_compliant():
    recommendation = recommend_by_mean_wait(make_report([None, 1.0, 0.5]), 2.0)

    assert recommendation.recommended_registers == 2


def test_a10_unseeded_scenarios_are_refused_as_non_comparable():
    with pytest.raises(ValueError, match="graine fixe"):
        compare_dynamic_register_counts(
            make_config(seed=None),
            DynamicOptions(patience_min=None, switching_enabled=False),
        )


def test_a10_scheduled_register_changes_are_refused_as_non_comparable():
    options = DynamicOptions(
        patience_min=None,
        switching_enabled=False,
        register_changes=((10.0, 5, True),),
    )

    with pytest.raises(ValueError, match="calendrier de caisses"):
        compare_dynamic_register_counts(make_config(), options)


def test_dynamic_comparison_rejects_more_than_five_registers():
    with pytest.raises(ValueError, match="1 et 5"):
        compare_dynamic_register_counts(make_config(), max_registers=6)
