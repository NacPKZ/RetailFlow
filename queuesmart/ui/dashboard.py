"""Onglet « Dashboard responsable » : KPI, graphiques, comparaisons, recommandation.

Les calculs viennent de ``queuesmart.analytics`` ; ce module ne fait qu'afficher.
Les calculs répétés (plusieurs simulations) sont mis en cache par Streamlit.
"""

from collections.abc import Mapping

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.comparison import compare_scenarios, compare_strategies, relative_gain
from queuesmart.analytics.kpi import KpiCalculator, KpiReport
from queuesmart.analytics.recommender import Recommendation, RegisterRecommender, ServiceTarget
from queuesmart.config import DEFAULT_REPLICATIONS, SCENARIOS, WAIT_THRESHOLD_MIN, ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import STRATEGIES, build_strategy
from queuesmart.ui.client_board import format_minutes

PERCENT = 100
HISTOGRAM_BINS = 30
REFERENCE_STRATEGY = "shortest_queue"  # sans écran client
SCREEN_STRATEGY = "least_wait"  # avec écran client
THRESHOLD_STYLE = {"line_dash": "dash", "line_color": "#d62728"}
HIGHLIGHT_COLOR = "#2ca02c"


def render_dashboard(config: ScenarioConfig, strategy_name: str, result: SimulationResult) -> None:
    """Tableau de bord du responsable de magasin."""
    st.subheader(
        f"{config.name} · {config.open_registers} caisses · {STRATEGIES[strategy_name].label}"
    )
    report = KpiCalculator().compute(result)
    _render_kpi_cards(report)
    _render_recommendation(config, strategy_name)
    left, right = st.columns(2)
    with left:
        _render_wait_histogram(result)
    with right:
        _render_wait_by_arrival(result)
    _render_utilization(report)
    _render_strategy_comparison(config)
    _render_scenario_comparison(strategy_name, config.seed)


# --- Calculs mis en cache ----------------------------------------------------------


@st.cache_data(show_spinner="Recherche du nombre de caisses idéal…")
def _recommendation(config: ScenarioConfig, strategy_name: str) -> Recommendation:
    engine = SimulationEngine(build_strategy(strategy_name))
    return RegisterRecommender(engine, KpiCalculator(), ServiceTarget()).recommend(config)


@st.cache_data(show_spinner="Comparaison des comportements…")
def _strategy_reports(config: ScenarioConfig) -> dict[str, KpiReport]:
    return compare_strategies(config, KpiCalculator(), DEFAULT_REPLICATIONS)


@st.cache_data(show_spinner="Comparaison des scénarios…")
def _scenario_reports(strategy_name: str, seed: int | None) -> dict[str, KpiReport]:
    scenarios = {name: scenario.with_seed(seed) for name, scenario in SCENARIOS.items()}
    return compare_scenarios(scenarios, strategy_name, KpiCalculator(), DEFAULT_REPLICATIONS)


# --- Sections ------------------------------------------------------------------------


def _render_kpi_cards(report: KpiReport) -> None:
    cards = [
        ("Attente moyenne", format_minutes(report.mean_wait)),
        ("90 % attendent moins de", format_minutes(report.p90_wait)),
        ("Attente maximale", format_minutes(report.max_wait)),
        (f"Clients > {WAIT_THRESHOLD_MIN:g} min", f"{report.share_over_threshold:.0%}"),
        ("Occupation des caisses", f"{report.mean_utilization:.0%}"),
    ]
    for column, (label, value) in zip(st.columns(len(cards)), cards, strict=True):
        column.metric(label, value)


def _render_recommendation(config: ScenarioConfig, strategy_name: str) -> None:
    st.markdown("### Combien de caisses ouvrir ?")
    recommendation = _recommendation(config, strategy_name)
    _recommendation_message(recommendation, config.open_registers)
    st.plotly_chart(_recommendation_chart(recommendation))
    st.caption(
        f"Cible : 90 % des clients attendent au plus "
        f"{format_minutes(recommendation.target.max_p90_wait_min)} et au plus "
        f"{recommendation.target.max_share_over_threshold:.0%} dépassent ce seuil. "
        f"Moyenne sur {DEFAULT_REPLICATIONS} simulations par nombre de caisses."
    )


def _recommendation_message(recommendation: Recommendation, open_registers: int) -> None:
    recommended = recommendation.recommended_registers
    if recommended is None:
        st.error("Même avec toutes les caisses ouvertes, la cible de service n'est pas atteinte.")
    elif recommended == open_registers:
        st.success(f"Recommandation : {recommended} caisses. Votre choix actuel est le bon.")
    else:
        st.warning(
            f"Recommandation : {recommended} caisses (vous en avez ouvert {open_registers})."
        )


def _recommendation_chart(recommendation: Recommendation) -> go.Figure:
    reports = recommendation.reports_by_register_count
    figure = px.line(
        x=list(reports), y=[report.p90_wait for report in reports.values()], markers=True,
        labels={"x": "Nombre de caisses ouvertes", "y": "Attente du 90e percentile (min)"},
    )
    figure.add_hline(y=recommendation.target.max_p90_wait_min, annotation_text="Cible",
                     **THRESHOLD_STYLE)
    recommended = recommendation.recommended_registers
    if recommended is not None:
        figure.add_scatter(x=[recommended], y=[reports[recommended].p90_wait], mode="markers",
                           marker={"size": 18, "color": HIGHLIGHT_COLOR, "symbol": "star"},
                           name="Recommandé", showlegend=False)
    return figure


def _render_wait_histogram(result: SimulationResult) -> None:
    st.markdown("#### Répartition des attentes")
    figure = px.histogram(
        x=[customer.wait_time for customer in result.customers], nbins=HISTOGRAM_BINS,
        labels={"x": "Attente (min)", "count": "Clients"},
    )
    figure.add_vline(x=WAIT_THRESHOLD_MIN, annotation_text="Seuil", **THRESHOLD_STYLE)
    figure.update_layout(yaxis_title="Nombre de clients")
    st.plotly_chart(figure)


def _render_wait_by_arrival(result: SimulationResult) -> None:
    st.markdown("#### Attente selon l'heure d'arrivée")
    figure = px.scatter(
        x=[customer.arrival_time for customer in result.customers],
        y=[customer.wait_time for customer in result.customers],
        color=[f"Caisse {customer.register_id}" for customer in result.customers],
        labels={"x": "Arrivée (min depuis l'ouverture)", "y": "Attente (min)", "color": ""},
    )
    figure.add_hline(y=WAIT_THRESHOLD_MIN, **THRESHOLD_STYLE)
    st.plotly_chart(figure)


def _render_utilization(report: KpiReport) -> None:
    st.markdown("#### Occupation de chaque caisse")
    rates = report.utilization_by_register
    figure = px.bar(
        x=[f"Caisse {register_id}" for register_id in rates],
        y=[rate * PERCENT for rate in rates.values()],
        labels={"x": "", "y": "Occupation (%)"}, range_y=[0, PERCENT],
    )
    st.plotly_chart(figure)


def _render_strategy_comparison(config: ScenarioConfig) -> None:
    st.markdown("### Gain apporté par l'écran client")
    reports = _strategy_reports(config)
    before, after = reports[REFERENCE_STRATEGY], reports[SCREEN_STRATEGY]
    mean_column, p90_column = st.columns(2)
    mean_column.metric("Attente moyenne avec écran", format_minutes(after.mean_wait),
                       f"-{relative_gain(before.mean_wait, after.mean_wait):.0%}", "inverse")
    p90_column.metric("90e percentile avec écran", format_minutes(after.p90_wait),
                      f"-{relative_gain(before.p90_wait, after.p90_wait):.0%}", "inverse")
    labelled = {STRATEGIES[name].label: report for name, report in reports.items()}
    _render_comparison(labelled, "Comportement")


def _render_scenario_comparison(strategy_name: str, seed: int | None) -> None:
    st.markdown("### Comparaison des scénarios prédéfinis")
    st.caption("Chaque scénario avec son nombre de caisses par défaut.")
    _render_comparison(_scenario_reports(strategy_name, seed), "Scénario")


def _render_comparison(reports: Mapping[str, KpiReport], category: str) -> None:
    """Tableau + barres (attente moyenne et p90) pour comparer plusieurs rapports."""
    table = _reports_table(reports, category)
    st.dataframe(table, hide_index=True)
    figure = px.bar(
        table, x=category, y=["Attente moyenne (min)", "p90 (min)"], barmode="group",
        labels={"value": "Minutes", "variable": ""},
    )
    st.plotly_chart(figure)


def _reports_table(reports: Mapping[str, KpiReport], category: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            category: name,
            "Attente moyenne (min)": round(report.mean_wait, 2),
            "p90 (min)": round(report.p90_wait, 2),
            "Attente max (min)": round(report.max_wait, 2),
            f"Clients > {WAIT_THRESHOLD_MIN:g} min (%)": round(
                report.share_over_threshold * PERCENT, 1
            ),
            "Occupation (%)": round(report.mean_utilization * PERCENT, 1),
        }
        for name, report in reports.items()
    )
