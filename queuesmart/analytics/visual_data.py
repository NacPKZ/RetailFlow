"""Données de visualisation calculées sans dépendre de l'interface."""

import pandas as pd

from queuesmart.config import WAIT_THRESHOLD_MIN, ScenarioConfig
from queuesmart.simulation.dynamic import DynamicResult
from queuesmart.simulation.result import SimulationResult

CUSTOMER_COLUMNS = [
    "Client",
    "Caisse",
    "Arrivée",
    "Attente",
    "Service",
    "Début",
    "Sortie",
    "Abandon",
    "Statut",
]


def customer_frame(result: SimulationResult | DynamicResult) -> pd.DataFrame:
    """Un schéma commun, avec un statut explicite pour les abandons."""
    dynamic = isinstance(result, DynamicResult)
    return pd.DataFrame(
        [
            {
                "Client": c.customer_id,
                "Caisse": c.register_id,
                "Arrivée": c.arrival_time,
                "Attente": c.wait_time,
                "Service": c.service_duration,
                "Début": c.service_start,
                "Sortie": c.departure_time if dynamic else c.service_end,
                "Abandon": c.abandoned_at if dynamic else None,
                "Statut": (
                    "Abandon"
                    if dynamic and c.abandoned_at is not None
                    else "Présent"
                    if dynamic and c.departure_time is None
                    else "Servi"
                ),
            }
            for c in result.customers
        ],
        columns=CUSTOMER_COLUMNS,
    )


def flow_frame(clients: pd.DataFrame) -> pd.DataFrame:
    """Balayage exact : état après tous les événements d'un même instant.

    Un client quittant la file entre en service ou abandonne. Les abandons ne
    sont jamais comptés comme servis. Aucun échantillonnage du temps.
    """
    events = [(0.0, 0, 0, 0, 0)]
    for row in clients.to_dict("records"):
        events.append((row["Arrivée"], 1, 0, 0, 0))
        if row["Statut"] == "Servi":
            events.append((row["Début"], -1, 1, 0, 0))
            events.append((row["Sortie"], 0, -1, 1, 0))
        elif row["Statut"] == "Abandon":
            events.append((row["Abandon"], -1, 0, 0, 1))
        elif pd.notna(row["Début"]):
            events.append((row["Début"], -1, 1, 0, 0))
    frame = pd.DataFrame(
        events, columns=["Minute", "En attente", "En service", "Servis", "Abandons"]
    )
    return frame.groupby("Minute", as_index=True).sum().cumsum().reset_index()


def register_frame(clients: pd.DataFrame, count: int, duration: float) -> pd.DataFrame:
    """Occupation rapportée à la durée totale, y compris les caisses inutilisées."""
    served = clients.loc[clients["Statut"] == "Servi"]
    rows = []
    for register in range(1, count + 1):
        part = served.loc[served["Caisse"] == register]
        rows.append(
            {
                "Caisse": register,
                "Clients": len(part),
                "Attente moyenne": float(part["Attente"].mean()) if len(part) else 0.0,
                "Occupation (%)": 100 * float(part["Service"].sum()) / duration
                if duration
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def arrival_bins(clients: pd.DataFrame, window: float = 10) -> pd.DataFrame:
    data = clients.assign(Tranche=(clients["Arrivée"] // window * window))
    return data.groupby("Tranche", as_index=False).agg(
        Clients=("Client", "count"), Attente=("Attente", "mean")
    )


def compare_capacity(
    config: ScenarioConfig, strategy: str, maximum: int, runs: int
) -> pd.DataFrame:
    """Même ensemble de graines pour chaque capacité, P90 regroupé des clients."""
    from queuesmart.analytics.comparison import run_replications
    from queuesmart.analytics.kpi import KpiCalculator
    from queuesmart.analytics.recommender import ServiceTarget
    from queuesmart.simulation.engine import SimulationEngine
    from queuesmart.simulation.strategies import build_strategy

    engine = SimulationEngine(build_strategy(strategy))
    calculator = KpiCalculator()
    rows = []
    for count in range(1, maximum + 1):
        results = run_replications(engine, config.with_registers(count), runs)
        pooled = calculator.compute_many(results)
        means = [calculator.compute(r).mean_wait for r in results]
        rows.append(
            {
                "Caisses": count,
                "Attente moyenne": pooled.mean_wait,
                "P90": pooled.p90_wait,
                "Minimum des moyennes": min(means),
                "Maximum des moyennes": max(means),
                "Sous 5 min (%)": 100 * (1 - pooled.share_over_threshold),
                "Occupation (%)": 100 * pooled.mean_utilization,
                "Objectif atteint": ServiceTarget().is_met_by(pooled),
                "Répétitions": runs,
            }
        )
    return pd.DataFrame(rows)


def service_level(clients: pd.DataFrame) -> float:
    """Part de TOUS les arrivants servis avec une attente <= seuil."""
    if clients.empty:
        return 0.0
    return (
        100 * ((clients["Statut"] == "Servi") & (clients["Attente"] <= WAIT_THRESHOLD_MIN)).mean()
    )
