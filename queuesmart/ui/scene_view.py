"""Rendu de la scène autonome, avec hauteur ajustée au contenu."""

import streamlit as st

from queuesmart.scene.html import build_scene_html
from queuesmart.simulation.dynamic import DynamicResult


def render_scene_2d(result: DynamicResult) -> None:
    """La scène adapte sa hauteur au bureau comme au mobile."""
    st.iframe(build_scene_html(result), height="content", alt="Magasin animé RetailFlow")
