"""Assemble la page HTML autonome de la scène (modules JS + données JSON).

Aucune dépendance à Streamlit : la même page sert au composant Streamlit, aux
tests dans le navigateur et à un export autonome pour la démo.
"""

import json
from pathlib import Path

from queuesmart.scene.layout import SceneLayout
from queuesmart.scene.timeline import SceneTimelineBuilder
from queuesmart.simulation.dynamic import DynamicResult

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend_2d"
# Ordre de chargement : chaque module n'utilise que ceux chargés avant lui.
SCRIPT_ORDER = ("animations.js", "event_player.js", "characters.js", "map.js", "scene.js")
SCRIPTS_MARKER = "/*__RF_SCRIPTS__*/"
DATA_MARKER = "/*__RF_DATA__*/"


def scene_data(result: DynamicResult, layout: SceneLayout | None = None) -> dict:
    """Trajectoires et états des caisses, prêts à être rejoués par le navigateur."""
    layout = layout or SceneLayout()
    data = SceneTimelineBuilder(layout).build(result).to_dict(layout)
    data["events"] = result.events_as_dicts()
    return data


def build_scene_html(result: DynamicResult) -> str:
    """Page HTML complète et autonome (aucun fichier externe à charger)."""
    template = (FRONTEND_DIR / "scene.html").read_text(encoding="utf-8")
    scripts = "\n".join((FRONTEND_DIR / name).read_text(encoding="utf-8") for name in SCRIPT_ORDER)
    data = json.dumps(scene_data(result), ensure_ascii=False).replace("</", "<\\/")
    return template.replace(SCRIPTS_MARKER, scripts).replace(DATA_MARKER, data)
