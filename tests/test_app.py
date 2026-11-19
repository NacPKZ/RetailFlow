"""Tests d'intégration de l'interface RetailFlow V4 avec Streamlit AppTest."""

import itertools
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from queuesmart.config import SCENARIOS
from queuesmart.simulation.strategies import STRATEGIES

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
APP_TIMEOUT_S = 60
CASES = list(itertools.product(SCENARIOS, STRATEGIES))
PAGES = ["Accueil", "Simulation", "Analyses", "Optimisation", "Méthodologie"]


def run_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=APP_TIMEOUT_S).run()
    return select_page(app, "Simulation")


def select_page(app: AppTest, page: str) -> AppTest:
    navigation = next(widget for widget in app.radio if widget.label == "Navigation")
    page = {"Analyse": "Analyses", "Comparaison": "Optimisation", "Vue d'ensemble": "Accueil"}.get(
        page, page
    )
    navigation.set_value(page).run()
    return app


@pytest.mark.parametrize(("scenario", "strategy"), CASES)
def test_every_scenario_and_behaviour_renders(scenario: str, strategy: str) -> None:
    app = run_app()
    app.sidebar.selectbox[0].select(scenario).run()
    app.sidebar.radio[0].set_value(strategy).run()
    assert not app.exception
    navigation = next(widget for widget in app.radio if widget.label == "Navigation")
    assert list(navigation.options) == PAGES


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_exception(page: str) -> None:
    app = select_page(run_app(), page)
    assert not app.exception


def test_simulation_contains_store_and_customer_tabs() -> None:
    app = select_page(run_app(), "Simulation")
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Magasin", "Écran client"]


def test_unknown_customer_shows_a_warning_not_a_traceback() -> None:
    app = select_page(run_app(), "Simulation")
    journey_input = next(
        widget for widget in app.number_input if widget.label == "Numéro du client"
    )
    journey_input.set_value(9999).run()
    assert not app.exception
    assert any("Aucun client n°9999" in warning.value for warning in app.warning)


def test_back_and_home_navigation():
    app = run_app()
    select_page(app, "Analyses")
    select_page(app, "Méthodologie")
    next(b for b in app.button if b.label == "← Retour").click().run()
    assert app.session_state["navigation"] == "Analyses"
    next(b for b in app.button if b.label == "← Retour").click().run()
    assert app.session_state["navigation"] == "Simulation"
    next(b for b in app.button if b.label == "⌂ Accueil").click().run()
    assert app.session_state["navigation"] == "Accueil"
    assert not app.exception
