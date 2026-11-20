"""Barre latérale : scénario prédéfini puis ajustements par l'utilisateur."""

import streamlit as st

from queuesmart.config import (
    DEFAULT_SEED,
    MAX_ARRIVAL_WINDOW_MIN,
    MAX_CUSTOMER_COUNT,
    MAX_MEAN_SERVICE_TIME_MIN,
    MAX_REGISTERS,
    MIN_ARRIVAL_WINDOW_MIN,
    MIN_REGISTERS,
    MIN_SERVICE_TIME_MIN,
    SCENARIOS,
    ScenarioConfig,
)
from queuesmart.exceptions import InvalidScenarioError
from queuesmart.simulation.strategies import STRATEGIES

ARRIVAL_WINDOW_STEP_MIN = 5.0
SERVICE_TIME_STEP_MIN = 0.1


def render_sidebar() -> tuple[ScenarioConfig, str]:
    """Affiche les saisies et renvoie (scénario validé, nom du comportement client).

    Si les saisies sont incohérentes, affiche un message clair et arrête la page.
    """
    with st.sidebar:
        st.header("Paramètres")
        preset = SCENARIOS[st.selectbox("Scénario prédéfini", list(SCENARIOS))]
        st.caption("Ajustements (préremplis par le scénario)")
        values = _adjustment_inputs(preset)
        strategy_name = _strategy_input()
        seed = st.number_input("Graine aléatoire", min_value=0, value=DEFAULT_SEED, step=1)
    return _validated_config(preset.name, values, int(seed)), strategy_name


def _adjustment_inputs(preset: ScenarioConfig) -> dict[str, float]:
    """Widgets préremplis. La clé contient le nom du scénario : changer de
    scénario remet donc les widgets à ses valeurs."""
    key = preset.name
    return {
        "customer_count": st.slider(
            "Nombre de clients", 1, MAX_CUSTOMER_COUNT, preset.customer_count, key=f"n-{key}"
        ),
        "arrival_window_min": st.slider(
            "Durée d'arrivée des clients (min)", MIN_ARRIVAL_WINDOW_MIN, MAX_ARRIVAL_WINDOW_MIN,
            preset.arrival_window_min, step=ARRIVAL_WINDOW_STEP_MIN, format="%.0f",
            key=f"window-{key}",
        ),
        "open_registers": st.slider(
            "Caisses ouvertes", MIN_REGISTERS, MAX_REGISTERS, preset.open_registers,
            key=f"registers-{key}",
        ),
        "mean_service_time_min": st.slider(
            "Temps moyen de passage en caisse (min)", MIN_SERVICE_TIME_MIN,
            MAX_MEAN_SERVICE_TIME_MIN, preset.mean_service_time_min,
            step=SERVICE_TIME_STEP_MIN, format="%.1f", key=f"service-{key}",
        ),
    }


def _strategy_input() -> str:
    return st.radio(
        "Comportement des clients",
        list(STRATEGIES),
        format_func=lambda name: STRATEGIES[name].label,
        help="Sans écran, les clients prennent la file la plus courte. "
        "Avec l'écran client, ils suivent l'attente estimée la plus faible.",
    )


def _validated_config(name: str, values: dict[str, float], seed: int) -> ScenarioConfig:
    try:
        return ScenarioConfig(name=name, seed=seed, **values)
    except InvalidScenarioError as error:
        st.error(f"Paramètres invalides : {error}")
        st.stop()
