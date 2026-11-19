"""Comparaison économique du moteur dynamique, indépendante de l'affichage.

Chaque capacité utilise les mêmes graines, arrivées, services et options de patience.
Les coûts sont des hypothèses de scénario. Aucune prévision de revenu n'est produite.
"""

import io
import json
import math
import zipfile
from dataclasses import asdict, dataclass

import pandas as pd

from queuesmart.analytics.dynamic_metrics import resource_frame
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine


@dataclass(frozen=True)
class DecisionAssumptions:
    hourly_cost: float = 22.0
    abandonment_cost: float = 5.0
    wait_target: float = 5.0
    service_target: float = 90.0

    def __post_init__(self):
        values = asdict(self)
        if any(not math.isfinite(v) or v < 0 for v in values.values()):
            raise ValueError("Les hypothèses doivent être finies et positives ou nulles.")
        if self.wait_target <= 0 or not 0 < self.service_target <= 100:
            raise ValueError(
                "Seuil d'attente positif et cible de service entre 0 et 100 exclus/inclus."
            )


def compare_dynamic_capacity(
    config: ScenarioConfig,
    options: DynamicOptions,
    assumptions: DecisionAssumptions,
    maximum: int = 5,
    runs: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retourne synthèse et tirages, sans appliquer les interventions de l'atelier.

    Cible robuste observée : cible de service atteinte dans CHAQUE tirage testé.
    Cette règle n'est ni une garantie sur un magasin ni un intervalle de confiance.
    Le coût intègre la mobilisation jusqu'à la dernière sortie, y compris les
    caisses fermées qui terminent un service. Aucun arrondi avant la sélection.
    """
    if config.seed is None:
        raise ValueError("Une graine explicite est nécessaire pour une comparaison appariée.")
    if type(maximum) is not int or not 1 <= maximum <= 5:
        raise ValueError("Comparer de 1 à 5 caisses.")
    if type(runs) is not int or not 1 <= runs <= 20:
        raise ValueError("Utiliser de 1 à 20 répétitions.")
    if options.register_changes or options.customer_moves or options.manual_actions:
        raise ValueError("Le laboratoire compare des capacités fixes, sans intervention.")
    engine = DynamicSimulationEngine()
    records = []
    for registers in range(1, maximum + 1):
        for index in range(runs):
            seed = config.seed + index
            result = engine.run(config.with_registers(registers).with_seed(seed), options)
            waits = pd.Series(
                [c.wait_time for c in result.customers if c.service_start is not None], dtype=float
            )
            level = 100 * sum(w <= assumptions.wait_target for w in waits) / config.customer_count
            resources = resource_frame(result)
            minutes = float(resources["Mobilisation (min)"].sum())
            labor = minutes / 60 * assumptions.hourly_cost
            loss = result.abandoned_count * assumptions.abandonment_cost
            records.append(
                {
                    "Caisses": registers,
                    "Graine": seed,
                    "Attente moyenne (min)": float(waits.mean()) if len(waits) else None,
                    "P90 servis (min)": float(waits.quantile(0.9)) if len(waits) else None,
                    "Service (%)": level,
                    "Servis": result.served_count,
                    "Abandons": result.abandoned_count,
                    "Taux d'abandon (%)": 100 * result.abandoned_count / config.customer_count,
                    "Caisse-minutes": minutes,
                    "Occupation (%)": 100 * float(resources["Service (min)"].sum()) / minutes
                    if minutes
                    else 0.0,
                    "Coût personnel (€)": labor,
                    "Coût abandons (€)": loss,
                    "Coût modélisé (€)": labor + loss,
                    "Cible atteinte": level >= assumptions.service_target,
                }
            )
    trials = pd.DataFrame(records).astype(
        {"Attente moyenne (min)": float, "P90 servis (min)": float}
    )
    summary = (
        trials.groupby("Caisses", as_index=False).mean(numeric_only=True).drop(columns="Graine")
    )
    groups = trials.groupby("Caisses")
    summary["Service minimum (%)"] = summary["Caisses"].map(groups["Service (%)"].min())
    summary["Coût min (€)"] = summary["Caisses"].map(groups["Coût modélisé (€)"].min())
    summary["Coût max (€)"] = summary["Caisses"].map(groups["Coût modélisé (€)"].max())
    summary["Tirages conformes (%)"] = summary.pop("Cible atteinte") * 100
    summary["Admissible"] = summary["Tirages conformes (%)"] == 100
    # Frontière service/coût moyen : au moins une amélioration stricte.
    summary["Pareto"] = [
        not any(
            other["Coût modélisé (€)"] <= row["Coût modélisé (€)"]
            and other["Service (%)"] >= row["Service (%)"]
            and (
                other["Coût modélisé (€)"] < row["Coût modélisé (€)"]
                or other["Service (%)"] > row["Service (%)"]
            )
            for other in summary.to_dict("records")
        )
        for row in summary.to_dict("records")
    ]
    return summary, trials


def recommend_capacity(summary: pd.DataFrame) -> int | None:
    """Coût moyen minimal parmi les capacités admissibles ; égalité : moins de caisses."""
    feasible = summary.loc[summary["Admissible"]].sort_values(["Coût modélisé (€)", "Caisses"])
    return int(feasible.iloc[0]["Caisses"]) if len(feasible) else None


def decision_report(config, options, assumptions, summary, trials) -> str:
    """Rapport Markdown reproductible, aussi lisible hors de l'application."""
    recommendation = recommend_capacity(summary)
    lines = [
        "# RetailFlow V8 : rapport de décision",
        "",
        "Simulation de files d’attente. Scénarios synthétiques.",
        "",
        "## Hypothèses",
        "",
        f"Configuration : {asdict(config)}",
        f"Options dynamiques : {asdict(options)}",
        f"Hypothèses économiques et service : {asdict(assumptions)}",
        "",
        f"Graines testées : {sorted(trials['Graine'].unique().tolist())}.",
        "",
        "## Résultats simulés",
        "",
        "| Caisses | Service moyen (%) | Minimum (%) | Abandons moyens "
        "| Coût moyen (€) | Admissible |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['Caisses']} | {row['Service (%)']:.2f} | "
            f"{row['Service minimum (%)']:.2f} | {row['Abandons']:.2f} | "
            f"{row['Coût modélisé (€)']:.2f} | {row['Admissible']} |"
        )
    lines += [
        "",
        "## Recommandation conditionnelle",
        "",
        f"{recommendation} caisses : coût moyen minimal parmi les capacités admissibles."
        if recommendation
        else "Aucune capacité testée ne respecte la cible à chaque tirage.",
        "",
        "## Méthode et limites",
        "",
        "Service : servis sous le seuil / tous les arrivants. Un abandon reste un échec.",
        "Moyenne et P90 : clients servis seulement, puis moyenne des indicateurs par tirage.",
        "Personnel : caisse-minutes mobilisées / 60 x coût horaire. "
        "Les caisses restent ouvertes jusqu'à la dernière sortie.",
        "Abandons : nombre x coût hypothétique par abandon. Aucun chiffre d'affaires réel.",
        "Les capacités partagent les mêmes graines, arrivées et services prévus. "
        "Les interventions de l'atelier sont exclues.",
        "Les étendues min/max ne sont pas des intervalles de confiance. "
        "La conformité observée n'est pas une probabilité ni une garantie future.",
        "Arrivées uniformes, services gamma, estimation d'attente avec information parfaite. "
        "Calibration terrain, pauses, compétences et coûts fixes non modélisés.",
    ]
    return "\n".join(lines) + "\n"


def decision_bundle(config, options, assumptions, summary, trials, chart_html) -> bytes:
    """Archive autonome, CSV compatibles Excel et paramètres en JSON strict."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "rapport.md", decision_report(config, options, assumptions, summary, trials)
        )
        for name, frame in [("capacites.csv", summary), ("tirages.csv", trials)]:
            archive.writestr(
                name, frame.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
            )
        archive.writestr(
            "hypotheses.json",
            json.dumps(
                {
                    "schema": "retailflow-decision/7.0",
                    "config": asdict(config),
                    "options": asdict(options),
                    "hypotheses": asdict(assumptions),
                    "maximum": int(summary["Caisses"].max()),
                    "runs": int(trials["Graine"].nunique()),
                },
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ),
        )
        archive.writestr("frontiere.html", chart_html)
    return buffer.getvalue()


def mean_wait_capacity(trials: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, int | None]:
    """Retient la plus petite capacité conforme pour chaque graine testée."""
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Le seuil d’attente doit être fini et positif ou nul.")
    waits = trials["Attente moyenne (min)"]
    summary = (
        trials.assign(conforme=waits.le(threshold))
        .groupby("Caisses", as_index=False)
        .agg(
            **{
                "Attente moyenne (min)": ("Attente moyenne (min)", "mean"),
                "Plus forte moyenne (min)": ("Attente moyenne (min)", "max"),
                "Taux d’abandon moyen (%)": ("Taux d'abandon (%)", "mean"),
                "Tirages conformes": ("conforme", "sum"),
                "Tirages": ("Graine", "count"),
            }
        )
    )
    feasible = summary.loc[summary["Tirages conformes"] == summary["Tirages"]]
    return summary, int(feasible["Caisses"].min()) if len(feasible) else None
