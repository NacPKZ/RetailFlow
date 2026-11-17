"""Tests du générateur de clients."""

import statistics

import pytest

from queuesmart.config import MIN_SERVICE_TIME_MIN, ScenarioConfig
from queuesmart.simulation.generator import CustomerGenerator

STATISTICAL_TOLERANCE = 0.05  # 5 % d'écart toléré sur un grand échantillon


def test_generates_requested_number_of_customers(small_config: ScenarioConfig) -> None:
    assert len(CustomerGenerator(small_config).generate()) == small_config.customer_count


def test_customers_are_sorted_by_arrival_with_ids_from_one(small_config: ScenarioConfig) -> None:
    customers = CustomerGenerator(small_config).generate()
    arrivals = [customer.arrival_time for customer in customers]
    assert arrivals == sorted(arrivals)
    assert [customer.customer_id for customer in customers] == list(range(1, 41))


def test_values_stay_within_bounds(small_config: ScenarioConfig) -> None:
    for customer in CustomerGenerator(small_config).generate():
        assert 0.0 <= customer.arrival_time <= small_config.arrival_window_min
        assert customer.service_duration >= MIN_SERVICE_TIME_MIN
        assert not customer.is_served


def test_same_seed_gives_same_customers(small_config: ScenarioConfig) -> None:
    generator = CustomerGenerator(small_config)
    assert generator.generate() == generator.generate()
    assert CustomerGenerator(small_config).generate() == generator.generate()


def test_different_seed_gives_different_customers(small_config: ScenarioConfig) -> None:
    other = CustomerGenerator(small_config.with_seed(2)).generate()
    assert other != CustomerGenerator(small_config).generate()


def test_mean_service_time_is_respected_on_large_sample() -> None:
    config = ScenarioConfig("Grand", 5000, 60.0, 2.0, 3, seed=3)
    durations = [customer.service_duration for customer in CustomerGenerator(config).generate()]
    assert statistics.fmean(durations) == pytest.approx(2.0, rel=STATISTICAL_TOLERANCE)
