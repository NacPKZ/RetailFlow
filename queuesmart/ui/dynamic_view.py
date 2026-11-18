"""Scène et analyses du même résultat dynamique, intégrées à l'application."""

import json
from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.ui import charts
from queuesmart.ui.presentation import cards, plot, section
from queuesmart.ui.scene_view import render_scene_2d

EVENT_LABELS = {
    "customer_arrived": "Arrivée",
    "queue_joined": "Entrée dans une file",
    "service_started": "Début de service",
    "customer_departed": "Client servi et sorti",
    "queue_switched": "Changement de file",
    "customer_abandoned": "Abandon",
    "register_opened": "Ouverture de caisse",
    "register_closed": "Fermeture de caisse",
}


@st.cache_data(show_spinner="Préparation de la scène et des événements...")
def run_dynamic(config: ScenarioConfig, options: DynamicOptions):
    return DynamicSimulationEngine().run(config, options)


def render_dynamic(config: ScenarioConfig) -> None:
    st.caption(
        "Moteur dynamique : abandons, changements de file et caisses programmées. "
        "Le comportement historique de la barre latérale ne s'applique pas ici : "
        "choix par attente estimée."
    )
    with st.expander("Paramètres de la scène", expanded=config.open_registers > 5):
        st.caption(
            f"Base : {config.customer_count} clients / "
            f"arrivées sur {config.arrival_window_min:g} min / "
            f"service moyen {config.mean_service_time_min:g} min / graine {config.seed}."
        )
        if config.open_registers > 5:
            st.info(
                "La scène représente 5 caisses. Choisis ci-dessous la capacité dynamique ; "
                "les analyses historiques conservent leur propre capacité."
            )
        a, b, c = st.columns(3)
        registers = a.slider("Caisses initiales de la scène", 1, 5, min(config.open_registers, 5))
        patience = b.slider("Patience avant abandon (min)", 1, 60, 12)
        switches = c.checkbox("Changements de file", value=True)
        abandon = c.checkbox("Abandons autorisés", value=True)
        a, b, c = st.columns(3)
        action = a.selectbox("Action programmée", ["Aucune", "Ouvrir", "Fermer"])
        rid = b.selectbox("Caisse concernée", [1, 2, 3, 4, 5], index=4, disabled=action == "Aucune")
        minute = c.number_input(
            "Minute du changement", min_value=0.0, value=10.0, disabled=action == "Aucune"
        )
    dynamic_config = replace(config, name="Scène dynamique", open_registers=registers)
    changes = () if action == "Aucune" else ((float(minute), rid, action == "Ouvrir"),)
    options = DynamicOptions(
        patience_min=patience if abandon else None,
        switching_enabled=switches,
        register_changes=changes,
    )
    result = run_dynamic(dynamic_config, options)
    data = customer_frame(result)
    cards(
        [
            ("Clients arrivés", str(len(data)), "Total du scénario dynamique", charts.BLUE),
            ("Clients servis", str(result.served_count), "Passages terminés", charts.TEAL),
            ("Abandons", str(result.abandoned_count), "Départs sans être servis", charts.RED),
            (
                "Servis avec attente ≤ 5 min",
                f"{service_level(data):.1f} %",
                "Part de tous les clients arrivés",
                charts.GOLD,
            ),
        ]
    )
    st.subheader("Scène 2D")
    st.caption("Lecture, pause, vitesse et suivi. Les décisions sont calculées en Python.")
    render_scene_2d(result)
    if changes and not any(e.type in ("register_opened", "register_closed") for e in result.events):
        st.info(
            "L'action programmée n'a produit aucun changement : caisse déjà dans cet "
            "état ou dernière caisse ouverte."
        )
    section(
        "Comprendre ce scénario",
        "Ces graphiques utilisent exactement les événements de la scène ci-dessus.",
    )
    view = st.radio(
        "Analyse de la scène", ["Flux", "Attentes", "Journal et exports"], horizontal=True
    )
    if view == "Flux":
        plot(charts.congestion(data), "dynamic_flow")
        plot(charts.cumulative_flow(data), "dynamic_outcomes")
    elif view == "Attentes":
        plot(charts.wait_scatter(data), "dynamic_scatter")
        served = data.loc[data["Statut"] == "Servi"]
        if len(served):
            plot(charts.wait_histogram(served), "dynamic_histogram")
            st.caption(
                f"Distribution : {len(served)} clients servis uniquement. "
                f"Attente moyenne des servis : {result.mean_wait_served:.2f} min. "
                "Le nuage inclut aussi les abandons, identifiables au survol."
            )
        else:
            st.info("Aucun client servi dans ce scénario.")
    else:
        events = pd.DataFrame(result.events_as_dicts())
        events["Événement"] = events["type"].map(EVENT_LABELS)
        selected = st.multiselect("Types d'événements", list(EVENT_LABELS.values()))
        display = events if not selected else events.loc[events["Événement"].isin(selected)]
        st.dataframe(
            display.rename(
                columns={
                    "time": "Minute",
                    "customer_id": "Client",
                    "register_id": "Caisse",
                    "target_register_id": "Caisse destination",
                }
            ).drop(columns="type"),
            hide_index=True,
            width="stretch",
        )
        a, b, c = st.columns(3)
        a.download_button(
            "Événements (CSV)",
            events.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            "retailflow_evenements.csv",
            "text/csv",
        )
        b.download_button(
            "Clients (CSV)",
            data.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            "retailflow_clients_dynamiques.csv",
            "text/csv",
        )
        payload = {"configuration": asdict(dynamic_config), "options": asdict(options)}
        c.download_button(
            "Paramètres (JSON)",
            json.dumps(payload, ensure_ascii=False, indent=2),
            "retailflow_dynamique.json",
            "application/json",
        )
    st.caption(
        "Les trajets sont une représentation visuelle. Une fermeture termine le "
        "client en cours puis réaffecte la file. "
        "La dernière caisse ouverte reste disponible. Les actions sont programmées avant le calcul."
    )
