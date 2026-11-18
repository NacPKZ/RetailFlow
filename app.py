"""RetailFlow : une entrée pour la scène dynamique et l'analyse FIFO."""

import json
from dataclasses import asdict
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.comparison import compare_strategies
from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.analytics.narrative import describe_result
from queuesmart.analytics.visual_data import compare_capacity, customer_frame, register_frame
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import STRATEGIES, build_strategy
from queuesmart.ui import charts
from queuesmart.ui.client_screen import render_client_screen
from queuesmart.ui.dynamic_view import render_dynamic
from queuesmart.ui.presentation import cards, plot, section, theme
from queuesmart.ui.sidebar import render_sidebar
from queuesmart.ui.store_view import render_store_view


@st.cache_data(show_spinner="Calcul du scénario...")
def run_simulation(config: ScenarioConfig, strategy_name: str) -> SimulationResult:
    return SimulationEngine(build_strategy(strategy_name)).run(config)


@st.cache_data(show_spinner="Comparaison sur plusieurs graines...")
def capacity(config: ScenarioConfig, strategy: str, maximum: int, runs: int) -> pd.DataFrame:
    return compare_capacity(config, strategy, maximum, runs)


@st.cache_data(show_spinner="Comparaison des comportements...")
def strategies(config: ScenarioConfig, runs: int):
    return compare_strategies(config, KpiCalculator(), runs)


def hero(config: ScenarioConfig, strategy_name: str) -> None:
    st.markdown(
        '<div class="rf-hero"><div><div class="rf-eyebrow">LE BON FLUX. AU BON MOMENT.</div>'
        '<h1>RetailFlow<span style="color:#e6bd76">.</span></h1>'
        "<p>Observer les files, comprendre les pics et tester les décisions.</p></div>"
        f'<div class="rf-context"><b>{escape(config.name)}</b><br>{config.customer_count} clients '
        f"/ {config.open_registers} caisses<br>Graine {config.seed} "
        f"/ {escape(STRATEGIES[strategy_name].label)}</div></div>",
        unsafe_allow_html=True,
    )


def kpis(result: SimulationResult) -> None:
    report = KpiCalculator().compute(result)
    level = 100 * (1 - report.share_over_threshold)
    cards(
        [
            (
                "Clients simulés",
                str(report.customer_count),
                "Tous les parcours sont terminés",
                charts.BLUE,
            ),
            (
                "Attente moyenne",
                f"{report.mean_wait:.2f} min",
                "De l'arrivée au début du service",
                charts.BLUE,
            ),
            ("Attente P90", f"{report.p90_wait:.2f} min", "90e percentile interpolé", charts.GOLD),
            (
                "Attente ≤ 5 min",
                f"{level:.1f} %",
                "Objectif : au moins 90 % des clients",
                charts.TEAL if level >= 90 else charts.RED,
            ),
        ]
    )


def overview(config: ScenarioConfig, result: SimulationResult, clients: pd.DataFrame) -> None:
    kpis(result)
    report = KpiCalculator().compute(result)
    if report.share_over_threshold <= 0.10 and report.p90_wait <= 5:
        st.success(
            "Objectif atteint sur ce tirage : au moins 90 % des clients attendent 5 min ou moins."
        )
    else:
        st.warning(
            "Objectif non atteint sur ce tirage. Compare les capacités pour tester plus de caisses."
        )
    section(
        "Le rythme du magasin",
        "La hauteur montre les clients présents. Le doré représente la file d'attente.",
    )
    plot(charts.congestion(clients), "overview_flow")
    left, right = st.columns([1.25, 1])
    with left:
        plot(charts.wait_scatter(clients), "overview_scatter")
        st.caption(
            "Une couleur par caisse. Survole un point pour examiner le client ; "
            "clique sur une légende pour filtrer."
        )
    with right:
        plot(charts.wait_histogram(clients), "overview_histogram")
        st.caption(
            "Vert : tranches sous le seuil de 5 min. Rose : tranches au-delà. Les "
            "données sont simulées."
        )
    for title, text in describe_result(result)[:2]:
        st.markdown(f"**{title}.** {text}")
    section(
        "Repères", f"{config.open_registers} caisses / {result.end_time:.1f} minutes de simulation"
    )
    left, right = st.columns(2)
    with left:
        plot(
            charts.register_load(register_frame(clients, config.open_registers, result.end_time)),
            "overview_load",
        )
    with right:
        plot(charts.wait_ecdf(clients), "overview_ecdf")


def simulation(config: ScenarioConfig, result: SimulationResult) -> None:
    tab_scene, tab_client = st.tabs(["Magasin", "Écran client"])
    with tab_scene:
        with st.expander("Modes d'affichage"):
            mode = st.radio(
                "Vue du magasin", ["Scène 2D dynamique", "Rejeu FIFO historique"], horizontal=True
            )
        if mode == "Scène 2D dynamique":
            render_dynamic(config)
        else:
            render_store_view(result)
    with tab_client:
        st.caption(
            "Panneau du moteur FIFO historique, selon le comportement choisi dans la "
            "barre latérale."
        )
        render_client_screen(result)


def analytics(result: SimulationResult, clients: pd.DataFrame) -> None:
    section(
        "Explorer les performances",
        "Chaque vue répond à une question. Les durées sont exprimées en minutes.",
    )
    selected = st.multiselect(
        "Caisses à analyser",
        list(range(1, result.config.open_registers + 1)),
        default=list(range(1, result.config.open_registers + 1)),
    )
    data = clients.loc[clients["Caisse"].isin(selected)]
    if data.empty:
        st.info("Choisis au moins une caisse ayant reçu un client.")
        return
    st.caption(
        f"Périmètre filtré : {len(data)} clients sur {len(clients)}. "
        "Les graphiques ci-dessous suivent ce filtre."
    )
    choice = st.radio(
        "Analyse détaillée", ["Attentes", "Caisses", "Flux", "Clients"], horizontal=True
    )
    if choice == "Attentes":
        plot(charts.wait_scatter(data), "analysis_scatter")
        left, right = st.columns(2)
        with left:
            plot(charts.wait_histogram(data), "analysis_histogram")
        with right:
            plot(charts.wait_ecdf(data), "analysis_ecdf")
        plot(charts.wait_heatmap(data, result.config.open_registers), "analysis_heatmap")
        st.caption(
            "Carte : moyenne par caisse et tranche d'arrivée de 10 min. Une case vide"
            " signifie qu'aucun client n'est présent dans ce groupe."
        )
    elif choice == "Caisses":
        frame = register_frame(data, result.config.open_registers, result.end_time)
        frame = frame.loc[frame["Caisse"].isin(selected)]
        plot(charts.register_load(frame), "analysis_load")
        plot(charts.service_timeline(data), "analysis_timeline")
        st.dataframe(frame.round(2), hide_index=True, width="stretch")
    elif choice == "Flux":
        plot(charts.congestion(data), "analysis_flow")
        plot(charts.arrival_chart(data), "analysis_arrivals")
        plot(charts.wait_scatter(data, "Service"), "analysis_service")
        st.caption(
            "Le nuage de points ne démontre pas un effet causal de la durée de "
            "service sur l'attente."
        )
    else:
        selected_id = st.selectbox("Client à examiner", data["Client"].tolist())
        row = data.loc[data["Client"] == selected_id].iloc[0]
        cards(
            [
                ("Caisse", str(int(row["Caisse"])), "Caisse d'affectation", charts.BLUE),
                ("Attente", f"{row['Attente']:.2f} min", "Avant le début du service", charts.GOLD),
                ("Service", f"{row['Service']:.2f} min", "Durée du passage en caisse", charts.TEAL),
            ]
        )
        st.info(
            f"Arrivée à {row['Arrivée']:.2f} min, service à {row['Début']:.2f} min, "
            f"sortie à {row['Sortie']:.2f} min."
        )
        st.dataframe(data.round(2), hide_index=True, width="stretch")


def comparison(config: ScenarioConfig, strategy_name: str, clients: pd.DataFrame) -> None:
    section(
        "Tester une décision",
        "Même clientèle et mêmes graines pour comparer les capacités équitablement.",
    )
    st.caption(
        "Moteur FIFO historique, sans abandon ni intervention dynamique. "
        f"Scénario {config.name}, {config.customer_count} clients, "
        f"arrivées sur {config.arrival_window_min:g} min, service moyen "
        f"{config.mean_service_time_min:g} min, comportement {strategy_name}. "
        "Les configurations utilisent les mêmes graines. Cette recommandation ne remplace "
        "pas une validation avec le moteur dynamique et ses hypothèses."
    )
    with st.form("capacity_form"):
        left, right = st.columns(2)
        maximum = left.slider("Nombre maximal de caisses à comparer", 2, 8, 8)
        runs = right.select_slider("Répétitions par capacité", options=[5, 10, 20], value=20)
        submitted = st.form_submit_button(
            "Comparer les configurations", type="primary", width="stretch"
        )
    signature = (config, strategy_name, maximum, runs)
    if submitted:
        st.session_state["capacity_result"] = (
            signature,
            capacity(config, strategy_name, maximum, runs),
        )
    cached = st.session_state.get("capacity_result")
    if cached is not None and cached[0] == signature:
        frame = cached[1]
        feasible = frame.loc[frame["Objectif atteint"]]
        if len(feasible):
            minimum = int(feasible.iloc[0]["Caisses"])
            st.success(
                f"Capacité minimale observée : {minimum} caisses sur {runs} répétitions. "
                "P90 ≤ 5 min et au moins 90 % des clients avec une attente ≤ 5 min."
            )
        else:
            st.warning("Aucune capacité testée ne respecte les deux critères de service.")
        plot(charts.capacity_chart(frame), "capacity_chart")
        st.caption(
            "La bande représente le minimum et le maximum des attentes moyennes "
            "observées selon les graines. "
            "Ce n'est pas un intervalle de confiance. P90 et part sous le seuil : "
            "tous les clients des répétitions regroupés."
        )
        st.dataframe(frame.round(2), hide_index=True, width="stretch")
        st.download_button(
            "Exporter la comparaison (CSV)",
            frame.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            "retailflow_comparaison.csv",
            "text/csv",
        )
    elif cached is not None:
        st.info("Les paramètres ont changé. Relance la comparaison pour actualiser les résultats.")
    else:
        st.info(
            "Lance la comparaison pour rechercher la plus petite capacité respectant l'objectif."
        )
    with st.expander("Comparer les comportements avec et sans écran client"):
        if st.button("Calculer le gain de l'écran"):
            reports = strategies(config, 20)
            st.session_state["screen_comparison"] = (config, reports)
        screen = st.session_state.get("screen_comparison")
        if screen is not None and screen[0] == config:
            reports = screen[1]
            fig = go.Figure()
            for name, color in [("Attente moyenne", charts.BLUE), ("P90", charts.GOLD)]:
                values = [
                    r.mean_wait if name == "Attente moyenne" else r.p90_wait
                    for r in reports.values()
                ]
                fig.add_bar(
                    x=[STRATEGIES[k].label for k in reports],
                    y=values,
                    name=name,
                    marker_color=color,
                )
            fig.update_yaxes(title="Minutes", rangemode="tozero")
            plot(charts.style(fig, "Les comportements, sur 20 graines identiques"), "screen_chart")
            before, after = reports["shortest_queue"].mean_wait, reports["least_wait"].mean_wait
            if before:
                change = (after - before) / before * 100
                st.caption(
                    f"Variation de l'attente moyenne avec l'écran : {change:+.1f} %. "
                    "Une valeur positive signifie une dégradation."
                )
            else:
                st.caption("Attente de référence nulle : variation relative non définie.")
    section("Emporter les résultats", "CSV pour Excel, paramètres pour reproduire le scénario")
    a, b = st.columns(2)
    a.download_button(
        "Exporter les clients (CSV)",
        clients.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        "retailflow_clients.csv",
        "text/csv",
        width="stretch",
    )
    b.download_button(
        "Exporter les paramètres (JSON)",
        json.dumps(
            {"configuration": asdict(config), "strategie": strategy_name},
            ensure_ascii=False,
            indent=2,
        ),
        "retailflow_parametres.json",
        "application/json",
        width="stretch",
    )
    with st.expander("Méthode et limites"):
        st.write(
            "Arrivées uniformes et durées de service gamma. Le moteur historique "
            "conserve les clients dans leur file jusqu'au service."
        )
        st.write(
            "L'écran connaît les durées de service simulées : c'est une hypothèse "
            "d'information parfaite. Les résultats ne sont pas une prévision réelle."
        )
        st.write(
            "Le P90 est interpolé. La recommandation teste les deux critères : P90 ≤ "
            "5 min et part au-delà de 5 min ≤ 10 %."
        )


def main() -> None:
    st.set_page_config(
        page_title="RetailFlow | Simulateur",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    theme()
    config, strategy_name = render_sidebar()
    result = run_simulation(config, strategy_name)
    page = st.radio(
        "Navigation",
        ["Vue d'ensemble", "Simulation", "Analyse", "Comparaison"],
        horizontal=True,
        label_visibility="collapsed",
        index=1,
    )
    if page == "Simulation":
        st.markdown(
            '<div class="rf-lab-head"><strong>RetailFlow.</strong>'
            "<span>Observer. Intervenir. Comprendre.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        hero(config, strategy_name)
    if page != "Simulation":
        st.markdown(
            '<div class="rf-source"><b>Moteur FIFO historique</b> / sans abandon ni '
            "changement de file / "
            "graphiques calculés sur le même scénario</div>",
            unsafe_allow_html=True,
        )
    clients = customer_frame(result)
    if page == "Vue d'ensemble":
        overview(config, result, clients)
    elif page == "Simulation":
        simulation(config, result)
    elif page == "Analyse":
        analytics(result, clients)
    else:
        comparison(config, strategy_name, clients)
    st.markdown(
        '<div class="rf-foot">RetailFlow / Projet universitaire / Données synthétiques / '
        "Ouvre la barre du graphique pour zoomer ou exporter une image.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
