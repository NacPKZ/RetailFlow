"""Parcours des nouvelles vues et invalidation des comparaisons périmées."""

import pytest
from streamlit.testing.v1 import AppTest
from test_app import APP_PATH, run_app, select_page


def choose(app: AppTest, label: str, value: str) -> AppTest:
    next(w for w in app.radio if w.label == label).set_value(value).run()
    assert not app.exception
    return app


@pytest.mark.parametrize("view", ["Attentes", "Caisses", "Flux", "Clients"])
def test_analysis_subviews(view):
    choose(select_page(run_app(), "Analyse"), "Analyse détaillée", view)


@pytest.mark.parametrize("view", ["Flux", "Attentes", "Journal et exports"])
def test_dynamic_subviews(view):
    app = select_page(run_app(), "Simulation")
    choose(app, "Analyse de la scène", view)
    assert any("Clients arrivés" in m.value for m in app.markdown)


def test_capacity_comparison_is_invalidated_when_scenario_changes():
    app = select_page(run_app(), "Comparaison")
    next(b for b in app.button if b.label == "Comparer les configurations").click().run()
    assert not app.exception
    assert any("Capacité minimale observée" in s.value for s in app.success)
    app.sidebar.selectbox[0].select("Heure de pointe").run()
    assert not app.exception
    assert any("paramètres ont changé" in s.value for s in app.info)


def test_empty_filter_is_a_message():
    app = select_page(run_app(), "Analyse")
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("Choisis au moins une caisse" in s.value for s in app.info)


def test_single_customer_is_valid_in_all_analysis_views():
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    app.sidebar.slider[0].set_value(1).run()
    select_page(app, "Analyse")
    for view in ["Attentes", "Caisses", "Flux", "Clients"]:
        choose(app, "Analyse détaillée", view)
