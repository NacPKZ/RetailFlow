"""Composant bidirectionnel : la scène envoie des commandes au moteur Python."""

from dataclasses import asdict
from pathlib import Path

import streamlit as st
import streamlit.components.v2 as components

from queuesmart.analytics.visual_data import customer_frame, flow_frame
from queuesmart.scene.html import scene_data
from queuesmart.scene.layout import SceneLayout
from queuesmart.scene.shopping import shopping_tracks
from queuesmart.simulation.dynamic import DynamicResult

ASSETS = Path(__file__).resolve().parents[2] / "frontend_studio"
LEGACY = Path(__file__).resolve().parents[2] / "frontend_2d"


def javascript() -> str:
    sampler = (LEGACY / "animations.js").read_text(encoding="utf-8")
    sampler = sampler.replace("window.RF = window.RF || {};", "")
    scripts = [sampler] + [
        (ASSETS / name).read_text(encoding="utf-8")
        for name in ("replay.js", "painter.js", "inspector.js", "studio.js")
    ]
    return (
        "const RF = {};\n"
        + "\n".join(scripts)
        + """
export default function(component) {
  const root=component.parentElement.querySelector('.studio');
  return RF.mountStudio(root,component.data,action=>component.setTriggerValue('command',action));
}
"""
    )


studio = components.component(
    "retailflow_interactive_studio",
    html=(ASSETS / "studio.html").read_text(encoding="utf-8"),
    css=(ASSETS / "studio.css").read_text(encoding="utf-8"),
    js=javascript(),
)


@st.cache_data(show_spinner=False, max_entries=8)
def _scene_payload(result: DynamicResult) -> dict:
    """Trajectoires coûteuses, indépendantes du curseur et des messages de la session."""
    data = scene_data(result, SceneLayout(compact=True))
    flow = flow_frame(customer_frame(result))
    peak = flow.loc[flow["En attente"].idxmax()]
    data.update(
        {
            "people": {str(c.customer_id): asdict(c) for c in result.customers},
            "shopping_customers": shopping_tracks(result),
            "initially_open": result.config.open_registers,
            "scenario": result.config.name,
            "seed": result.config.seed,
            "horizon": max(e.time for e in result.events),
            "peak_time": float(peak["Minute"]),
        }
    )
    return data


def studio_payload(
    result: DynamicResult,
    run_id: str,
    revision: int,
    cursor: dict,
    feedback: str = "",
    decisions: list | None = None,
) -> dict:
    # cache_data renvoie une copie : aucune session ne partage un curseur mutable.
    data = _scene_payload(result)
    data.update(
        run_id=run_id,
        revision=revision,
        cursor=cursor,
        feedback=feedback,
        decisions=decisions or [],
    )
    return data


def render_studio(
    result: DynamicResult,
    run_id: str,
    revision: int,
    cursor: dict,
    feedback: str = "",
    decisions: list | None = None,
):
    response = studio(
        data=studio_payload(result, run_id, revision, cursor, feedback, decisions),
        key="retailflow_studio",
        on_command_change=lambda: None,
        width="stretch",
        height="content",
    )
    return response.command
