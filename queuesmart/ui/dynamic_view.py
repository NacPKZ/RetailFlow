"""Atelier interactif, analyses et comparaison au scénario témoin."""

import hashlib
import json
import uuid
from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from queuesmart.analytics.dynamic_metrics import final_metrics, paired_metrics, resource_frame
from queuesmart.analytics.interventions import apply_interventions, validate_intervention
from queuesmart.analytics.narrative import compare_results, describe_result
from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.ui import charts
from queuesmart.ui.decision_lab import render_decision_lab
from queuesmart.ui.presentation import cards, plot, section
from queuesmart.ui.studio_component import render_studio

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


@st.cache_data(show_spinner="Calcul de la simulation...", max_entries=64)
def run_dynamic(config: ScenarioConfig, options: DynamicOptions):
    return DynamicSimulationEngine().run(config, options)


def _refresh():
    from streamlit.errors import StreamlitAPIException

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def _controls(config: ScenarioConfig) -> tuple[ScenarioConfig, DynamicOptions]:
    with st.expander("Réglages de l'atelier et défis d'affluence"):
        situation = st.selectbox(
            "Situation à explorer",
            [
                "Paramètres latéraux",
                "Affluence soutenue",
                "Pic du samedi",
                "Soutenance reproductible",
            ],
        )
        if situation == "Affluence soutenue":
            config = replace(
                config,
                name=situation,
                customer_count=80,
                arrival_window_min=60.0,
                mean_service_time_min=1.6,
                open_registers=3,
            )
        elif situation == "Pic du samedi":
            config = replace(
                config,
                name=situation,
                customer_count=110,
                arrival_window_min=60.0,
                mean_service_time_min=1.7,
                open_registers=4,
            )
        elif situation == "Soutenance reproductible":
            config = replace(
                config,
                name=situation,
                customer_count=110,
                arrival_window_min=60.0,
                mean_service_time_min=1.7,
                open_registers=2,
                seed=42,
            )
            st.caption(
                "Profil dérivé du Pic du samedi, avec deux caisses et graine 42. "
                "Conservez patience 12 min, abandons et rééquilibrage activés "
                "pour reproduire le scénario de secours documenté."
            )
        if config.open_registers > 5:
            st.info("L'atelier représente 5 caisses. La capacité historique reste inchangée.")
        a, b, c = st.columns(3)
        registers = a.slider(
            "Caisses initiales de la scène",
            1,
            5,
            min(config.open_registers, 5),
            key=f"studio_registers_{situation}",
        )
        patience = b.slider("Patience avant abandon (min)", 1, 60, 12)
        abandon = c.checkbox("Abandons autorisés", value=True)
        switches = c.checkbox("Rééquilibrage automatique des files", value=True)
        st.caption(
            "Un client réaffecté à la souris garde sa nouvelle file jusqu'au service "
            "ou à une fermeture de caisse. L'arrivée et la patience sont conservées."
        )
    return replace(config, name=config.name, open_registers=registers), DynamicOptions(
        patience_min=patience if abandon else None,
        switching_enabled=switches,
    )


def _context(config: ScenarioConfig, options: DynamicOptions) -> dict:
    signature = hashlib.sha256(
        json.dumps({"config": asdict(config), "options": asdict(options)}, sort_keys=True).encode()
    ).hexdigest()[:20]
    if st.session_state.get("studio_context", {}).get("run_id") != signature:
        st.session_state["studio_context"] = {
            "run_id": signature,
            "actions": [],
            "cursor": {},
            "feedback": "",
            "last_id": None,
        }
    return st.session_state["studio_context"]


@st.fragment
def render_dynamic(config: ScenarioConfig) -> None:
    stage = st.container()
    config, base_options = _controls(config)
    context = _context(config, base_options)
    reference = run_dynamic(config, base_options)
    options = apply_interventions(base_options, context["actions"])
    result = run_dynamic(config, options)
    st.caption(
        f"{config.name} / {config.customer_count} clients / "
        f"{config.open_registers} caisses initiales / "
        f"graine {config.seed}. Pilotage par attente estimée, puis vos interventions."
    )
    with stage:
        action = render_studio(
            result,
            context["run_id"],
            len(context["actions"]),
            context["cursor"],
            context["feedback"],
            [
                asdict(o) | {"action": asdict(context["actions"][o.index])}
                for o in result.action_outcomes
            ],
        )
    if action and action.get("id") != context["last_id"]:
        context["last_id"] = action.get("id")
        if action.get("run_id") == context["run_id"] and action.get("revision") == len(
            context["actions"]
        ):
            if action.get("kind") == "navigate":
                st.session_state["studio_navigation_request"] = "back"
                st.rerun(scope="app")
            try:
                if len(context["actions"]) >= 100:
                    raise ValueError(
                        "100 interventions maximum. Annulez ou recommencez l'expérience."
                    )
                intervention = validate_intervention(result, action)
                context["actions"].append(intervention)
                context["feedback"] = (
                    f"Caisse {intervention.register_id} "
                    f"{'ouverte' if intervention.opened else 'fermée'} "
                    f"à {intervention.time:.2f} min."
                    if intervention.kind == "register"
                    else (
                        f"Client {intervention.customer_id} réaffecté "
                        f"à la caisse {intervention.register_id}."
                    )
                )
            except ValueError as error:
                context["feedback"] = str(error)
            context["cursor"] = {
                "token": uuid.uuid4().hex,
                "time": action.get("time", 0),
                "revision": len(context["actions"]),
                "followed": action.get("followed"),
            }
            _refresh()
    a, b, c = st.columns([1, 1, 2])
    if a.button(
        "Annuler la dernière intervention", disabled=not context["actions"], width="stretch"
    ):
        removed = context["actions"].pop()
        context["cursor"] = {
            "time": removed.time,
            "revision": len(context["actions"]),
            "token": uuid.uuid4().hex,
        }
        context["feedback"] = "La dernière intervention a été annulée."
        _refresh()
    if b.button("Réinitialiser l'expérience", disabled=not context["actions"], width="stretch"):
        context.update(
            actions=[],
            cursor={"time": 0, "revision": 0, "token": uuid.uuid4().hex},
            feedback="Expérience réinitialisée.",
        )
        _refresh()
    c.caption(
        f"{len(context['actions'])} intervention(s). "
        "Les actions recalculent le futur avec la même clientèle."
    )
    section(
        "Ce que raconte la simulation",
        "Bilan final du scénario, distinct des compteurs en direct de l'atelier.",
    )
    data = customer_frame(result)
    cards(
        [
            ("Clients arrivés", str(len(data)), "Tous les arrivants du scénario", charts.BLUE),
            ("Clients servis", str(result.served_count), "Passages terminés", charts.TEAL),
            ("Abandons", str(result.abandoned_count), "Départs sans être servis", charts.RED),
            (
                "Servis avec attente ≤ 5 min",
                f"{service_level(data):.1f} %",
                "Part de tous les arrivants",
                charts.GOLD,
            ),
        ]
    )
    served_waits = data.loc[data["Statut"] == "Servi", "Attente"]
    if len(served_waits):
        st.caption(
            f"Attentes des servis : moyenne {served_waits.mean():.2f} min, "
            f"médiane {served_waits.median():.2f} min, "
            f"P90 {served_waits.quantile(0.9):.2f} min, "
            f"P95 {served_waits.quantile(0.95):.2f} min."
        )
    for title, text in describe_result(result):
        st.markdown(f"**{title}.** {text}")
    view = st.radio(
        "Analyse de la scène",
        ["Flux", "Attentes", "Interventions", "Laboratoire de décision", "Journal et exports"],
        horizontal=True,
    )
    if view == "Flux":
        plot(charts.congestion(data), "dynamic_flow")
        plot(charts.cumulative_flow(data), "dynamic_outcomes")
        plot(charts.arrival_chart(data), "dynamic_arrivals")
    elif view == "Attentes":
        st.caption(
            "La caisse désigne la dernière affectation du client. Son attente couvre "
            "tout le parcours aux caisses, y compris les éventuels changements de file. "
            "La heatmap associe cette attente à la caisse finale, sans attribuer "
            "tout ce temps à cette seule caisse."
        )
        plot(charts.wait_scatter(data), "dynamic_scatter")
        served = data.loc[data["Statut"] == "Servi"]
        if len(served):
            left, right = st.columns(2)
            with left:
                plot(charts.wait_histogram(served), "dynamic_histogram")
            with right:
                plot(charts.wait_ecdf(served), "dynamic_ecdf")
            st.caption(
                "Histogramme et courbe cumulée : clients servis seulement. "
                "Le nuage inclut aussi les abandons, identifiables au survol."
            )
        plot(charts.wait_heatmap(data, 5), "dynamic_heatmap")
    elif view == "Interventions":
        _render_interventions(context, reference, result)
    elif view == "Laboratoire de décision":
        render_decision_lab(config, base_options)
    else:
        _exports(config, options, result, context)


def _render_interventions(context: dict, reference, result) -> None:
    section(
        "L'effet de vos décisions",
        "Même graine, mêmes arrivants, mêmes services prévus. Seules vos actions diffèrent.",
    )
    changes = compare_results(reference, result)
    a, b, c = st.columns(3)
    a.metric(
        "Servis avec attente ≤ 5 min",
        f"{service_level(customer_frame(result)):.1f} %",
        f"{changes['Niveau de service (points)']:+.1f} points",
    )
    b.metric("Clients servis", result.served_count, f"{changes['Clients servis']:+.0f}")
    c.metric(
        "Abandons", result.abandoned_count, f"{changes['Abandons']:+.0f}", delta_color="inverse"
    )
    plot(
        charts.intervention_comparison(customer_frame(reference), customer_frame(result)),
        "intervention_comparison",
    )
    if context["actions"]:
        st.write(
            f"Dans cette simulation, vos interventions changent l'attente cumulée de "
            f"{changes['Attente totale (min)']:+.2f} min, les clients servis de "
            f"{changes['Clients servis']:+.0f} et les abandons de {changes['Abandons']:+.0f}. "
            "Une attente plus courte ne suffit pas à conclure si les abandons augmentent."
        )
        rows = [
            {
                "Minute": outcome.time,
                "Action": "Réaffecter"
                if action.kind == "move"
                else ("Ouvrir" if action.opened else "Fermer"),
                "Caisse": action.register_id,
                "Client": action.customer_id,
                "Avant": outcome.before,
                "Après": outcome.after,
                "Résultat du recalcul": outcome.reason,
            }
            for outcome in result.action_outcomes
            for action in [context["actions"][outcome.index]]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        skipped = sum(not o.applied for o in result.action_outcomes)
        if skipped:
            st.warning(
                f"{skipped} décision(s) devenue(s) impossible(s) après recalcul. "
                "Consultez le journal avant de conclure sur leur effet."
            )
    else:
        st.info(
            "Cliquez sur une caisse ou réaffectez un client "
            "pour comparer votre expérience au témoin."
        )

    st.dataframe(pd.DataFrame(paired_metrics(reference, result)), hide_index=True, width="stretch")
    st.caption(
        "Bilan final apparié, effet combiné de toutes les décisions. Les écarts sont en minutes, "
        "clients ou points de pourcentage selon la ligne. Moyenne et P90 : servis seulement. "
        "Niveau de service : tous les arrivants. Occupation : service / durée mobilisée "
        "(caisse ouverte ou terminant un client), jusqu'à la dernière sortie. "
        "La mobilisation indique le coût en capacité. Une hausse de l'occupation n'est pas "
        "un gain en soi. Une seule graine ne permet pas de généraliser. "
        "L'effet individuel d'une décision n'est pas isolé par cette comparaison."
    )
    with st.expander("Vérifier les ressources mobilisées par caisse"):
        st.dataframe(resource_frame(result), hide_index=True, width="stretch")


def _exports(config, options, result, context) -> None:
    events = pd.DataFrame(result.events_as_dicts())
    events["Événement"] = events["type"].map(EVENT_LABELS)
    selected = st.multiselect("Types d'événements", list(EVENT_LABELS.values()))
    display = events if not selected else events.loc[events["Événement"].isin(selected)]
    st.dataframe(display, hide_index=True, width="stretch")
    a, b, c = st.columns(3)
    a.download_button(
        "Événements (CSV)",
        events.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        "retailflow_evenements.csv",
        "text/csv",
    )
    b.download_button(
        "Clients (CSV)",
        customer_frame(result).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        "retailflow_clients_dynamiques.csv",
        "text/csv",
    )
    payload = {
        "schema": "retailflow-experience/7.0",
        "perimetre": "Bilan final du moteur dynamique, temps en minutes",
        "indicateurs_finaux": final_metrics(result),
        "resultats_interventions": [asdict(o) for o in result.action_outcomes],
        "configuration": asdict(config),
        "options": asdict(options),
        "interventions": [asdict(a) for a in context["actions"]],
    }
    c.download_button(
        "Expérience (JSON)",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "retailflow_experience.json",
        "application/json",
    )
