"""Fixtures partagées par les tests."""

import pytest

from queuesmart.config import ScenarioConfig


@pytest.fixture
def small_config() -> ScenarioConfig:
    return ScenarioConfig("Petit", 40, 30.0, 2.0, 3, seed=1)
