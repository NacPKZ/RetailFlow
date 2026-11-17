"""Tests de la configuration des scénarios."""

import pytest

from queuesmart.config import MAX_REGISTERS, MIN_REGISTERS, SCENARIOS, ScenarioConfig
from queuesmart.exceptions import InvalidScenarioError, QueueSmartError


def make_config(**overrides: object) -> ScenarioConfig:
    values = {
        "name": "Test",
        "customer_count": 10,
        "arrival_window_min": 20.0,
        "mean_service_time_min": 2.0,
        "open_registers": 2,
    }
    values.update(overrides)
    return ScenarioConfig(**values)


def test_valid_config_is_created() -> None:
    config = make_config()
    assert config.open_registers == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"customer_count": 0},
        {"arrival_window_min": 0.0},
        {"arrival_window_min": -5.0},
        {"mean_service_time_min": 0.1},
        {"open_registers": MIN_REGISTERS - 1},
        {"open_registers": MAX_REGISTERS + 1},
    ],
)
def test_invalid_config_raises_scenario_error(overrides: dict) -> None:
    with pytest.raises(InvalidScenarioError):
        make_config(**overrides)


def test_scenario_error_is_a_business_error_with_french_message() -> None:
    with pytest.raises(QueueSmartError, match="caisses"):
        make_config(open_registers=0)


def test_arrival_rate_per_min() -> None:
    assert make_config(customer_count=30, arrival_window_min=60.0).arrival_rate_per_min == 0.5


def test_with_registers_returns_validated_copy() -> None:
    config = make_config()
    assert config.with_registers(5).open_registers == 5
    assert config.open_registers == 2
    with pytest.raises(InvalidScenarioError):
        config.with_registers(MAX_REGISTERS + 1)


def test_with_seed_returns_copy() -> None:
    assert make_config().with_seed(7).seed == 7


def test_predefined_scenarios_are_valid_and_named() -> None:
    assert list(SCENARIOS) == ["Heures creuses", "Heures normales", "Heure de pointe"]
    for name, scenario in SCENARIOS.items():
        assert scenario.name == name
