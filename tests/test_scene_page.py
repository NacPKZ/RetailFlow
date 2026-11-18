"""La page HTML de la scène est autonome, et le banc dynamique l'affiche sans erreur."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from queuesmart.config import ScenarioConfig
from queuesmart.scene.html import DATA_MARKER, SCRIPT_ORDER, SCRIPTS_MARKER, build_scene_html
from queuesmart.simulation.dynamic import DynamicSimulationEngine

DEMO_PATH = Path(__file__).resolve().parent.parent / "dynamic_demo.py"


def test_scene_page_embeds_all_modules_and_data() -> None:
    result = DynamicSimulationEngine().run(ScenarioConfig("Page", 20, 10.0, 2.0, 2, seed=1))
    page = build_scene_html(result)
    assert SCRIPTS_MARKER not in page and DATA_MARKER not in page
    assert page.count("window.RF = window.RF || {};") == len(SCRIPT_ORDER)
    data = page.split("RF.mountScene(document.getElementById(\"rf-scene\"), ")[1].split(");")[0]
    assert len(json.loads(data)["customers"]) == 20


def test_dynamic_demo_renders_with_scene() -> None:
    app = AppTest.from_file(str(DEMO_PATH), default_timeout=60).run()
    assert not app.exception
    assert any(header.value == "Scène 2D" for header in app.subheader)
