"""Parcours Streamlit du laboratoire et export reproductible."""

from test_app import run_app


def _lab():
    app = run_app()
    next(w for w in app.radio if w.label == "Analyse de la scène").set_value(
        "Laboratoire de décision"
    ).run()
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
