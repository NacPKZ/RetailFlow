"""Laboratoire de capacité dynamique et hypothèses économiques explicites."""

from dataclasses import replace

import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.decision_lab import (
    DecisionAssumptions,
    compare_dynamic_capacity,
    decision_bundle,
    decision_report,
    recommend_capacity,
)
from queuesmart.ui import charts
from queuesmart.ui.presentation import plot, section


@st.cache_data(show_spinner="Simulation des capacités et des graines...", max_entries=16)
def _compare(config, options, assumptions, maximum, runs):
    return compare_dynamic_capacity(config, options, assumptions, maximum, runs)


@st.cache_data(show_spinner=False, max_entries=8)
def _bundle(*args):
    return decision_bundle(*args)


def render_decision_lab(config, base_options):
    section("Laboratoire de décision", "Capacité, qualité de service et coûts hypothétiques")
    st.caption(
        "Moteur dynamique de l'atelier, avec la même patience et le même rééquilibrage. "
        "Comparaison de capacités fixes, sans vos interventions. Arrivées et services "
        "identiques entre capacités pour chaque graine. Données synthétiques."
    )
    with st.form("decision_lab"):
        a, b, c = st.columns(3)
        hourly = a.number_input("Coût horaire par caisse (€)", 0.0, 200.0, 22.0, 1.0)
        loss = b.number_input("Coût hypothétique par abandon (€)", 0.0, 200.0, 5.0, 1.0)
        maximum = c.slider("Capacité maximale à tester", 1, 5, 5)
        wait = a.number_input("Seuil d'attente (min)", 0.5, 30.0, 5.0, 0.5)
        target = b.slider("Cible : servis sous le seuil (%)", 50, 100, 90)
        runs = c.select_slider("Graines par capacité", options=[5, 10, 20], value=5)
        submitted = st.form_submit_button("Évaluer le compromis coût / service", type="primary")
    assumptions = DecisionAssumptions(hourly, loss, wait, target)
    signature = (config, base_options, assumptions, maximum, runs)
    if submitted:
        st.session_state["decision_lab_result"] = (signature, _compare(*signature))
    cached = st.session_state.get("decision_lab_result")
    if cached is None:
        st.info(
            "Choisissez vos hypothèses puis lancez l'évaluation. Aucun coût réel n'est importé."
        )
        return
    if cached[0] != signature:
        st.info(
            "Les paramètres ont changé. Relancez l'évaluation pour actualiser la recommandation."
        )
        return
    summary, trials = cached[1]
    st.caption(
        f"Dernier calcul : {config.customer_count} clients, "
        f"{assumptions.hourly_cost:g} €/h par caisse, "
        f"{assumptions.abandonment_cost:g} € par abandon, "
        f"cible {assumptions.service_target:g} % servis en {assumptions.wait_target:g} min "
        f"ou moins, {runs} graines. Modifiez puis validez le formulaire pour recalculer."
    )
    recommended = recommend_capacity(summary)
    if recommended:
        st.success(
            f"Recommandation conditionnelle : {recommended} caisses. Coût moyen minimal parmi "
            f"les capacités atteignant la cible sur chacune des {runs} graines testées."
        )
    else:
        st.warning("Aucune capacité testée ne respecte la cible sur chacune des graines.")
    figure = go.Figure()
    for pareto, label, color in [
        (False, "Configurations dominées", charts.BLUE),
        (True, "Frontière coût / service", charts.TEAL),
    ]:
        data = summary.loc[summary["Pareto"] == pareto]
        figure.add_scatter(
            x=data["Coût modélisé (€)"],
            y=data["Service (%)"],
            mode="markers+text",
            text=[f"{n} caisses" for n in data["Caisses"]],
            textposition="top center",
            name=label,
            marker={"size": 14, "color": color},
            customdata=data[["Caisses", "Service minimum (%)", "Abandons"]],
            hovertemplate="%{customdata[0]} caisses<br>Coût moyen : %{x:.2f} €"
            "<br>Service moyen : %{y:.1f} %<br>Service minimum : %{customdata[1]:.1f} %"
            "<br>Abandons moyens : %{customdata[2]:.1f}<extra></extra>",
        )
    figure.add_hline(y=target, line_dash="dash", line_color=charts.GOLD)
    figure.update_xaxes(title="Coût modélisé moyen (€)", rangemode="tozero")
    figure.update_yaxes(title="Servis sous le seuil / arrivants (%)", range=[0, 105])
    plot(charts.style(figure, "Le coût de la qualité de service"), "decision_frontier")
    st.dataframe(summary.round(2), hide_index=True, width="stretch")
    st.caption(
        "Moyennes sur les tirages. P90 : moyenne des P90 des servis par tirage. "
        "Service minimum : moins bon tirage observé. Pareto : aucune autre configuration "
        "n'offre un service moyen au moins égal à coût moyen inférieur ou égal, avec "
        "une amélioration stricte. Min/max sont des étendues observées."
    )
    with st.expander("Détail par graine et méthode de calcul"):
        st.dataframe(trials.round(3), hide_index=True, width="stretch")
        st.write(
            "Personnel = mobilisation réelle des caisses en minutes / 60 x coût horaire. "
            "Une caisse fermée terminant son client reste mobilisée. Le scénario s'arrête "
            "à la dernière sortie. Coût d'abandon = abandons x hypothèse unitaire. "
            "Aucun coût fixe, pause, marge réelle ni revenu futur n'est modélisé."
        )
        st.write(
            "La conformité sur toutes les graines testées n'est pas une garantie future. "
            "L'information parfaite sur les services simulés favorise le choix de file. "
            "Une utilisation opérationnelle demanderait une calibration terrain."
        )
    report = decision_report(config, base_options, assumptions, summary, trials)
    bundle = _bundle(
        config,
        base_options,
        assumptions,
        summary,
        trials,
        figure.to_html(include_plotlyjs=True, full_html=True),
    )
    a, b = st.columns(2)
    a.download_button(
        "Dossier de décision (ZIP)",
        bundle,
        "retailflow_decision.zip",
        "application/zip",
        width="stretch",
    )
    b.download_button(
        "Rapport de simulation (Markdown)",
        report,
        "retailflow_decision.md",
        "text/markdown",
        width="stretch",
    )
    with st.expander("Sensibilité au volume de clients : -20 %, référence, +20 %"):
        st.caption(
            "Le volume seul varie. Chaque niveau est simulé sur les mêmes graines. "
            "Entre niveaux de volume, la clientèle générée peut changer."
        )
        sensitivity_key = (signature, recommended or maximum)
        if st.button("Tester la sensibilité au volume"):
            records = []
            for factor in [0.8, 1.0, 1.2]:
                variant = replace(
                    config, customer_count=max(1, round(config.customer_count * factor))
                )
                frame, _ = _compare(
                    variant, base_options, assumptions, recommended or maximum, runs
                )
                row = frame.iloc[-1].to_dict()
                row["Volume relatif"] = f"{factor:.0%}"
                row["Clients"] = variant.customer_count
                records.append(row)
            st.session_state["decision_sensitivity"] = (sensitivity_key, records)
        saved = st.session_state.get("decision_sensitivity")
        if saved and saved[0] == sensitivity_key:
            st.dataframe(saved[1], hide_index=True, width="stretch")
