"""Composant Streamlit de la scène 2D : affiche la page produite par ``scene.html``."""

import streamlit.components.v1 as components

from queuesmart.scene.html import build_scene_html
from queuesmart.simulation.dynamic import DynamicResult

SCENE_HEIGHT_PX = 1100  # canvas 24 x 20 cases sur 1100 px de large + commandes + légende


def render_scene_2d(result: DynamicResult) -> None:
    """Rejoue dans le navigateur les événements d'une simulation déjà terminée."""
    components.html(build_scene_html(result), height=SCENE_HEIGHT_PX)
