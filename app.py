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
from queuesmart.ui.decision_lab import render_decision_lab, render_mean_wait
from queuesmart.ui.dynamic_dashboard import render_dynamic_dashboard
from queuesmart.ui.dynamic_view import render_dynamic, studio_parameters
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


def hero(config: ScenarioConfig) -> None:
    st.markdown(
        '<div class="rf-hero"><div><div class="rf-eyebrow">FILES D’ATTENTE EN SUPERMARCHÉ</div>'
        '<h1>RetailFlow<span style="color:#e6bd76">.</span></h1>'
        "<p>Observer les files, comprendre les pics et tester les décisions.</p></div>"
        f'<div class="rf-context"><b>{escape(config.name)}</b><br>{config.customer_count} clients '
        f"/ {config.open_registers} caisses<br>Graine {config.seed} "
        "</div></div>",
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


def overview(config: ScenarioConfig, result: SimulationResult) -> None:
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
    for title, text in describe_result(result)[:2]:
        st.markdown(f"**{title}.** {text}")
    st.caption(f"{config.open_registers} caisses / {result.end_time:.1f} minutes de simulation")


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


def _record_navigation():
    target = st.session_state.get("navigation", "Accueil")
    previous = st.session_state.get("active_page", "Accueil")
    if target != previous:
        history = st.session_state.setdefault("page_history", [])
        history.append(previous)
        st.session_state["page_history"] = history[-20:]
    st.session_state["active_page"] = target


def _navigate(target):
    st.session_state["navigation"] = target
    _record_navigation()


def _back():
    history = st.session_state.get("page_history", [])
    target = history.pop() if history else "Accueil"
    st.session_state.update(navigation=target, active_page=target, page_history=history)


def main() -> None:
    st.set_page_config(
        page_title="RetailFlow V8 | Aide à la décision",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    theme()
    destination = st.session_state.pop("studio_navigation_request", None)
    if destination == "back":
        _back()
    elif destination in ("Analyses", "Optimisation"):
        _navigate(destination)
    config, strategy_name = render_sidebar()
    back, home, heading = st.columns([1, 1, 4])
    back.button(
        "← Retour",
        on_click=_back,
        width="stretch",
        disabled=not st.session_state.get("page_history"),
    )
    home.button("⌂ Accueil", on_click=_navigate, args=("Accueil",), width="stretch")
    heading.markdown(
        '<div class="rf-topbrand">RetailFlow <span>Simulation et aide à la décision</span></div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navigation",
        ["Accueil", "Simulation", "Analyses", "Optimisation", "Méthodologie"],
        horizontal=True,
        label_visibility="collapsed",
        index=0,
        key="navigation",
        on_change=_record_navigation,
    )
    if page == "Simulation":
        st.markdown(
            '<div class="rf-lab-head"><strong>RetailFlow <small>V8.0</small></strong>'
            "<span>Aide à la décision / Prototype de simulation</span></div>",
            unsafe_allow_html=True,
        )
    if page == "Accueil":
        hero(config)
        st.subheader("Simulation et optimisation des files d'attente en supermarché")
        st.write(
            "RetailFlow permet de simuler les flux de clients, d'analyser la congestion "
            "et de comparer différentes configurations de caisses afin d'éclairer "
            "les décisions opérationnelles."
        )
        for col, label, target in zip(
            st.columns(3),
            ["Lancer une simulation", "Explorer les analyses", "Comprendre la méthode"],
            ["Simulation", "Analyses", "Méthodologie"],
            strict=True,
        ):
            col.button(
                label,
                on_click=_navigate,
                args=(target,),
                width="stretch",
            )
        st.markdown(
            '<ol class="rf-steps"><li>Configurer le scénario</li><li>Observer le pic</li>'
            "<li>Mesurer les effets</li><li>Choisir une capacité</li></ol>",
            unsafe_allow_html=True,
        )
        st.write(
            "Comparez l'attente et le niveau de service au coût hypothétique des caisses. "
            "Les abandons comptent comme des échecs de service. Les scénarios sont "
            "synthétiques et reproductibles, sans calibration sur un magasin réel."
        )
        st.info(
            "Démonstration : dans Simulation, choisissez Soutenance reproductible, "
            "puis Voir le pic. Le laboratoire permet ensuite de tester +20 % de clients."
        )
    elif page == "Méthodologie":
        st.subheader("Méthode et limites")
        st.markdown(
            "Arrivées uniformes, services gamma, files FIFO par caisse. "
            "Le moteur dynamique ajoute patience, abandons et changements de file. "
            "Une fermeture laisse finir le service en cours. "
            "La vitesse du dessin ne modifie aucun calcul."
        )
        st.markdown(
            "Le niveau de service dynamique utilise tous les arrivants. "
            "Moyenne et percentiles des attentes portent sur les clients servis. "
            "Les capacités partagent les mêmes graines et les mêmes clients. "
            "Le laboratoire économique exige la cible de service à chaque réplication. "
            "L’objectif d’attente moyenne utilise le pire des tirages et affiche les abandons."
        )
        st.markdown(
            "Coûts hypothétiques, information parfaite sur les services simulés, "
            "parcours de courses illustratifs. La projection à cinq minutes extrapole "
            "la tendance récente. Aucun résultat ne constitue une prévision terrain."
        )
        with st.expander("Suivre un client dans le moteur"):
            st.markdown(
                '<ol class="rf-steps"><li>Arrivée en caisse</li>'
                "<li>Affectation et file FIFO</li><li>Service ou abandon</li>"
                "<li>Sortie et mise à jour des KPI</li></ol>",
                unsafe_allow_html=True,
            )
            st.write(
                "En cas de fermeture, les clients en attente rejoignent une caisse ouverte. "
                "Le client en cours de service termine son passage à la même caisse."
            )
    elif page == "Simulation":
        with st.expander("Comprendre le simulateur et préparer une décision"):
            a, b, c = st.columns(3)
            a.markdown(
                "**1. Observer**\n\nLancez la scène, visitez le pic et inspectez les files. "
                "Les compteurs et graphiques suivent les événements calculés par Python."
            )
            b.markdown(
                "**2. Tester**\n\nOuvrez une caisse ou réaffectez un client. "
                "Le moteur valide l'action puis recalcule le futur avec la même clientèle."
            )
            c.markdown(
                "**3. Décider**\n\nConsultez Interventions pour mesurer l'effet de vos actions. "
                "Optimisation compare capacités, coûts et qualité "
                "sur plusieurs graines."
            )
            st.caption(
                "Scénarios synthétiques, sans données de magasin réel. Les courses sont "
                "illustratives. Les projections de tendance et coûts reposent sur des hypothèses "
                "explicites. La vitesse de lecture ne change aucun résultat de simulation."
            )
        simulation(config, run_simulation(config, strategy_name))
    elif page == "Analyses":
        st.title("Analyses")
        mode = st.radio("Moteur analysé", ["Dynamique", "FIFO historique"], horizontal=True)
        if mode == "Dynamique":
            render_dynamic_dashboard(config)
        else:
            st.caption("Simulation FIFO historique, sans abandon ni changement de file.")
            result = run_simulation(config, strategy_name)
            clients = customer_frame(result)
            with st.expander("Synthèse FIFO"):
                overview(config, result)
            analytics(result, clients)
    elif page == "Optimisation":
        st.title("Optimisation")
        objective = st.radio(
            "Objectif de capacité",
            ["Niveau de service et coût", "Seuil d’attente moyenne"],
            horizontal=True,
        )
        dynamic_config, options = studio_parameters(config)
        st.caption(
            f"{dynamic_config.name} / {dynamic_config.customer_count} clients / "
            f"première graine {dynamic_config.seed}. Réglages de l’atelier dans Simulation."
        )
        if objective == "Niveau de service et coût":
            render_decision_lab(dynamic_config, options)
        else:
            render_mean_wait(dynamic_config, options)
        with st.expander("Comparateur FIFO historique"):
            comparison(config, strategy_name, customer_frame(run_simulation(config, strategy_name)))
    st.markdown(
        '<div class="rf-foot">RetailFlow / Simulation / Données synthétiques / '
        "Ouvre la barre du graphique pour zoomer ou exporter une image.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
