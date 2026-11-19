"""Parcours Streamlit du laboratoire et export reproductible."""

from test_app import run_app, select_page


def _lab():
    app = select_page(run_app(), "Optimisation")
    assert not app.exception
    return app


def test_decision_lab_evaluation_exports_and_invalidation():
    app = _lab()
    next(b for b in app.button if b.label == "Évaluer le compromis coût / service").click().run()
    assert not app.exception
    signature, (summary, trials) = app.session_state["decision_lab_result"]
    assert len(summary) == 5 and len(trials) == 25
    assert signature[2].hourly_cost == 22
    assert any("Recommandation conditionnelle" in s.value for s in app.success)
    app.sidebar.selectbox[0].select("Heure de pointe").run()
    assert not app.exception
    assert any("Relancez l'évaluation" in i.value for i in app.info)


def test_sensitivity_changes_volume_only():
    app = _lab()
    next(b for b in app.button if b.label == "Évaluer le compromis coût / service").click().run()
    next(b for b in app.button if b.label == "Tester la sensibilité au volume").click().run()
    assert not app.exception
    _, rows = app.session_state["decision_sensitivity"]
    assert [r["Clients"] for r in rows] == [40, 50, 60]
    assert len({r["Caisses"] for r in rows}) == 1


def test_mean_wait_objective_reports_abandonment():
    app = _lab()
    next(w for w in app.radio if w.label == "Objectif de capacité").set_value(
        "Seuil d’attente moyenne"
    ).run()
    next(b for b in app.button if b.label == "Tester le seuil d’attente").click().run()
    assert not app.exception
    assert any("Taux d’abandon moyen" in notice.value for notice in app.success)
