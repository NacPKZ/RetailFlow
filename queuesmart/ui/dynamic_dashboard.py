"""Vues d'analyse du scénario joué, dans la page Analyses de RetailFlow."""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.dynamic_alerts import saturation_periods
from queuesmart.analytics.dynamic_kpi import queue_frame, register_performance
from queuesmart.analytics.dynamic_metrics import final_metrics
from queuesmart.analytics.visual_data import customer_frame
from queuesmart.exports.dynamic import csv_bytes, excel_bytes, experiment_payload
from queuesmart.ui import charts
from queuesmart.ui.dynamic_view import render_interventions, studio_results
from queuesmart.ui.presentation import cards, plot, section

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


@st.cache_data(show_spinner=False, max_entries=8)
def _workbook(tables, payload):
    return excel_bytes(tables, payload)


def render_dynamic_dashboard(base_config):
    context, reference, result = studio_results(base_config)
    config = result.config
    section("Bilan de la simulation", "Résultats synthétiques du moteur dynamique")
    st.caption(
        f"{config.name} / {config.customer_count} clients / graine {config.seed} / "
        f"{config.open_registers} caisses au départ / {len(context['actions'])} intervention(s)."
    )
    clients = customer_frame(result)
    metrics = final_metrics(result)
    queues = queue_frame(result)
    registers = register_performance(result, queues)
    abandon_rate = metrics["Taux d'abandon (%)"]
    cards(
        [
            ("Clients arrivés", str(metrics["Clients arrivés"]), "Tous les arrivants", charts.BLUE),
            ("Clients servis", str(metrics["Clients servis"]), "Services terminés", charts.TEAL),
            (
                "Abandons",
                f"{abandon_rate:.1f} %",
                f"{metrics['Abandons']} départ(s) sans service",
                charts.RED,
            ),
            (
                "Attente moyenne",
                _minutes(metrics["Attente moyenne des servis (min)"]),
                "Clients servis",
                charts.GOLD,
            ),
        ]
    )
    kpis = pd.DataFrame(metrics.items(), columns=["Indicateur", "Valeur"])
    with st.expander("Détail des indicateurs"):
        st.caption(
            f"Fenêtre de 0 à {metrics['Fin d’observation (min)']:.2f} min. "
            "Les durées de service, attentes et quantiles portent sur les services terminés. "
            "Le taux d’abandon et le niveau de service utilisent tous les arrivants."
        )
        st.dataframe(kpis.round(3), hide_index=True, width="stretch")
    view = st.radio(
        "Analyse dynamique",
        ["Flux", "Attentes", "Caisses", "Diagnostic", "Interventions", "Journal et exports"],
        horizontal=True,
    )
    if view == "Flux":
        _flow(queues)
        plot(charts.arrival_chart(clients), "dynamic_arrivals")
    elif view == "Attentes":
        _waits(clients, metrics)
    elif view == "Caisses":
        st.caption(
            "Mobilisation : minutes ouvertes ou passées à finir un service après fermeture. "
            "Le pic de file exclut le client en cours de service."
        )
        frame = registers.dropna(subset=["Occupation (%)"]).rename(columns={"Servis": "Clients"})
        figure = charts.register_load(frame)
        figure.update_xaxes(title="Part de la durée mobilisée consacrée au service")
        plot(figure, "dynamic_register_load")
        st.dataframe(registers.round(3), hide_index=True, width="stretch")
    elif view == "Diagnostic":
        _diagnostic(queues, registers, metrics)
    elif view == "Interventions":
        render_interventions(context, reference, result)
    else:
        _exports(result, context, clients, metrics, kpis, queues, registers)


def _minutes(value):
    return f"{value:.2f} min" if value is not None else "Indisponible"


def _flow(queues):
    fig = go.Figure()
    for register, frame in queues.groupby("Caisse"):
        fig.add_scatter(
            x=frame["Minute"],
            y=frame["En file"],
            name=f"Caisse {register}",
            mode="lines",
            line_shape="hv",
        )
    fig.update_xaxes(title="Minute simulée")
    fig.update_yaxes(title="Clients en attente", rangemode="tozero", dtick=1)
    plot(charts.style(fig, "Longueur des files par caisse"), "dynamic_queue_lengths")
    totals = queues.groupby("Minute", sort=False)[["En file", "En service"]].sum()
    fig = go.Figure()
    for name in totals:
        fig.add_scatter(
            x=totals.index,
            y=totals[name],
            name=name,
            mode="lines",
            line_shape="hv",
            stackgroup="present",
        )
    fig.update_xaxes(title="Minute simulée")
    fig.update_yaxes(title="Clients présents", rangemode="tozero")
    plot(charts.style(fig, "Clients présents aux caisses"), "dynamic_present")
    flow = queues.drop_duplicates("Minute")
    fig = go.Figure()
    for name in ("Arrivés", "Servis", "Abandons"):
        fig.add_scatter(
            x=flow["Minute"],
            y=flow[name],
            name=name,
            mode="lines",
            line_shape="hv",
        )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Minute simulée")
    fig.update_yaxes(title="Clients cumulés", rangemode="tozero")
    plot(charts.style(fig, "Arrivées et sorties cumulées"), "dynamic_outcomes")


def _waits(clients, metrics):
    served = clients.loc[clients["Statut"] == "Servi"]
    if len(served):
        a, b, c, d = st.columns(4)
        a.metric("Médiane", _minutes(metrics["Médiane des servis (min)"]))
        b.metric("P90", _minutes(metrics["P90 des servis (min)"]))
        c.metric("P95", _minutes(metrics["P95 des servis (min)"]))
        d.metric("Maximum", _minutes(metrics["Attente maximale des servis (min)"]))
        st.caption(
            "La moyenne est sensible aux attentes longues. Le P90 et le P95 situent "
            "respectivement les 90e et 95e percentiles des attentes des clients servis."
        )
        left, right = st.columns(2)
        with left:
            plot(charts.wait_histogram(served), "dynamic_histogram")
        with right:
            plot(charts.wait_ecdf(served), "dynamic_ecdf")
    else:
        st.info("Aucun service terminé sur cette fenêtre.")
    st.caption(
        "Le nuage inclut les temps avant abandon. La carte rattache le parcours "
        "à la dernière caisse, même après un changement de file."
    )
    plot(charts.wait_scatter(clients), "dynamic_scatter")
    plot(charts.wait_heatmap(clients, 5), "dynamic_heatmap")


def _diagnostic(queues, registers, metrics):
    st.caption("Seuils de diagnostic modifiables pour ce scénario synthétique.")
    a, b, c = st.columns(3)
    queue_limit = a.number_input("Clients en file à partir de", 1, 100, 5)
    wait_limit = b.number_input("P90 des servis à partir de (min)", 0.5, 120.0, 5.0, 0.5)
    abandon_limit = c.number_input("Abandon à partir de (%)", 1, 100, 10)
    periods = saturation_periods(queues, queue_limit)
    p90 = metrics["P90 des servis (min)"]
    abandoned = metrics["Taux d'abandon (%)"]
    if p90 is not None and p90 >= wait_limit:
        st.warning(f"P90 de {_minutes(p90)}, pour un seuil de {wait_limit:g} min.")
    if abandoned >= abandon_limit:
        st.warning(f"{abandoned:.1f} % d’abandons, pour un seuil de {abandon_limit:g} %.")
    if periods:
        st.warning(f"{len(periods)} période(s) avec au moins {queue_limit} clients en file.")
        st.dataframe(pd.DataFrame(periods).round(3), hide_index=True, width="stretch")
    else:
        st.info("Aucune période de saturation selon le seuil de file choisi.")
    with st.expander("Écarts d’occupation et sous-utilisation"):
        low = st.slider("Occupation faible sous (%)", 0, 100, 30)
        spread = st.slider("Écart d’occupation à partir de (points)", 1, 100, 30)
        active = registers.dropna(subset=["Occupation (%)"])
        light = active.loc[active["Occupation (%)"] < low, "Caisse"].tolist()
        delta = active["Occupation (%)"].max() - active["Occupation (%)"].min()
        if light:
            st.info("Occupation faible pour les caisses " + ", ".join(map(str, light)) + ".")
        if delta >= spread:
            st.warning(f"Écart maximal de {delta:.1f} points entre les caisses mobilisées.")
        st.caption("Comparez les temps de mobilisation avant d’interpréter les écarts.")


def _exports(result, context, clients, metrics, kpis, queues, registers):
    events = pd.DataFrame(
        result.events_as_dicts(),
        columns=[
            "time",
            "type",
            "customer_id",
            "register_id",
            "target_register_id",
            "queue_position",
        ],
    )
    events["Événement"] = events["type"].map(EVENT_LABELS)
    selected = st.multiselect("Types d'événements", list(EVENT_LABELS.values()))
    display = events if not selected else events.loc[events["Événement"].isin(selected)]
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption(
        "Les exports couvrent le scénario complet, y compris les événements filtrés à l’écran."
    )
    tables = {
        "Résumé KPI": kpis,
        "Caisses": registers,
        "Clients": clients,
        "Événements": events,
        "Files": queues,
    }
    for column, label, name, filename in zip(
        st.columns(4),
        ("CSV clients", "CSV indicateurs", "CSV événements", "CSV files"),
        ("Clients", "Résumé KPI", "Événements", "Files"),
        ("clients_dynamiques", "indicateurs", "evenements", "files"),
        strict=True,
    ):
        column.download_button(
            label,
            csv_bytes(tables[name]),
            f"retailflow_{filename}.csv",
            "text/csv",
            width="stretch",
            on_click="ignore",
        )
    payload = experiment_payload(result, metrics, context["actions"])
    a, b = st.columns(2)
    a.download_button(
        "Classeur Excel",
        _workbook(tables, payload),
        "retailflow_analyse.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        on_click="ignore",
    )
    b.download_button(
        "Paramètres et bilan (JSON)",
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        "retailflow_experience.json",
        "application/json",
        width="stretch",
        on_click="ignore",
    )
