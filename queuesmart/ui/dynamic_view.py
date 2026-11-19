"""Atelier interactif, analyses et comparaison au scénario témoin."""

import hashlib
import json
import uuid
from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from queuesmart.analytics.dynamic_metrics import paired_metrics, resource_frame
from queuesmart.analytics.interventions import apply_interventions, validate_intervention
from queuesmart.analytics.narrative import compare_results
from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.ui import charts
from queuesmart.ui.presentation import plot, section
from queuesmart.ui.studio_component import render_studio


@st.cache_data(show_spinner="Calcul de la simulation...", max_entries=64)
def run_dynamic(config: ScenarioConfig, options: DynamicOptions):
    return DynamicSimulationEngine().run(config, options)


def _refresh():
    from streamlit.errors import StreamlitAPIException

    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


PROFILES = {
    "Paramètres latéraux": {},
    "Affluence soutenue": dict(
        customer_count=80,
        arrival_window_min=60.0,
        mean_service_time_min=1.6,
        open_registers=3,
    ),
    "Pic du samedi": dict(
        customer_count=110,
        arrival_window_min=60.0,
        mean_service_time_min=1.7,
        open_registers=4,
    ),
    "Soutenance reproductible": dict(
        customer_count=110,
        arrival_window_min=60.0,
        mean_service_time_min=1.7,
        open_registers=2,
        seed=42,
    ),
}


def _settings():
    return st.session_state.get(
        "studio_settings", (None, "Paramètres latéraux", None, 12, True, True)
    )


def studio_parameters(config: ScenarioConfig) -> tuple[ScenarioConfig, DynamicOptions]:
    saved_capacity_key, situation, registers, patience, abandon, switches = _settings()
    profile = replace(config, **PROFILES[situation])
    capacity_key = _capacity_key(config, situation)
    if saved_capacity_key != capacity_key:
        registers = min(profile.open_registers, 5)
    if PROFILES[situation]:
        profile = replace(profile, name=situation)
    return replace(profile, open_registers=registers), DynamicOptions(
        patience_min=patience if abandon else None, switching_enabled=switches
    )


def _capacity_key(config, situation):
    # Les profils fixent leur capacité initiale, les réglages latéraux la pilotent sinon.
    return (
        situation,
        None if PROFILES[situation] else (config.name, config.open_registers),
    )


def studio_results(config: ScenarioConfig):
    config, base_options = studio_parameters(config)
    context = _context(config, base_options)
    reference = run_dynamic(config, base_options)
    options = apply_interventions(base_options, context["actions"])
    return context, reference, run_dynamic(config, options) if context["actions"] else reference


def _controls(config: ScenarioConfig) -> None:
    capacity_key, situation, registers, patience, abandon, switches = _settings()
    with st.expander("Réglages de l'atelier et défis d'affluence"):
        situation = st.selectbox(
            "Situation à explorer",
            list(PROFILES),
            index=list(PROFILES).index(situation),
            key="studio_profile",
        )
        current_key = _capacity_key(config, situation)
        profile = replace(config, **PROFILES[situation])
        if situation == "Soutenance reproductible":
            st.caption(
                "Pic du samedi avec deux caisses et graine 42. Conservez une patience "
                "de 12 min, les abandons et le rééquilibrage pour reproduire la démonstration."
            )
        if profile.open_registers > 5:
            st.info("L’atelier représente au maximum cinq caisses.")
        a, b, c = st.columns(3)
        registers = a.slider(
            "Caisses initiales de la scène",
            1,
            5,
            registers if capacity_key == current_key else min(profile.open_registers, 5),
            key=f"studio_registers_{current_key}",
        )
        patience = b.slider("Patience avant abandon (min)", 1, 60, patience, key="studio_patience")
        abandon = c.checkbox("Abandons autorisés", value=abandon, key="studio_abandon")
        switches = c.checkbox(
            "Rééquilibrage automatique des files", value=switches, key="studio_switches"
        )
        st.session_state["studio_settings"] = (
            current_key,
            situation,
            registers,
            patience,
            abandon,
            switches,
        )
        st.caption(
            "Un client réaffecté à la souris garde sa nouvelle file jusqu'au service "
            "ou à une fermeture de caisse. L'arrivée et la patience sont conservées."
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
    _controls(config)
    context, _, result = studio_results(config)
    config = result.config
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
    a, b = st.columns(2)
    if a.button("Analyser ce scénario", width="stretch"):
        st.session_state["studio_navigation_request"] = "Analyses"
        st.rerun(scope="app")
    if b.button("Comparer les capacités", width="stretch"):
        st.session_state["studio_navigation_request"] = "Optimisation"
        st.rerun(scope="app")


def render_interventions(context: dict, reference, result) -> None:
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
