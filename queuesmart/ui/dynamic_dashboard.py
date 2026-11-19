"""Dashboard analytique du moteur événementiel dynamique RetailFlow."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from queuesmart.analytics.dynamic_alerts import build_dynamic_alerts
from queuesmart.analytics.dynamic_comparison import (
    DynamicComparisonReport,
    compare_dynamic_register_counts,
)
from queuesmart.analytics.dynamic_kpi import DynamicKPICalculator, DynamicKPIReport
from queuesmart.analytics.dynamic_optimizer import DynamicRecommendation, recommend_by_mean_wait
from queuesmart.config import WAIT_THRESHOLD_MIN, ScenarioConfig
from queuesmart.exports.csv_export import build_dynamic_csv_exports
from queuesmart.exports.excel_export import build_dynamic_excel_export
from queuesmart.simulation.dynamic import (
    DynamicOptions,
    DynamicResult,
    DynamicSimulationEngine,
)


@st.cache_data(show_spinner="Simulation dynamique en cours…")
def _run_dynamic(config: ScenarioConfig, options: DynamicOptions) -> DynamicResult:
    return DynamicSimulationEngine().run(config, options)


@st.cache_data(show_spinner="Comparaison des configurations 1 à 5 caisses…")
def _run_comparison(
    config: ScenarioConfig, options: DynamicOptions
) -> DynamicComparisonReport:
    return compare_dynamic_register_counts(config, options, max_registers=5)


def render_dynamic_dashboard(base_config: ScenarioConfig) -> None:
    """Affiche les six zones du dashboard à partir d'un résultat dynamique unique."""
    st.header("Analytics et optimisation — moteur dynamique")
    st.caption(
        "Les chiffres sont calculés après la simulation avec DynamicSimulationEngine. "
        "Ils ne constituent pas un flux en direct ni une prévision réelle."
    )
    if base_config.open_registers > 5:
        st.warning(
            "Le moteur dynamique accepte au maximum 5 caisses. Le réglage historique "
            "supérieur à 5 n'est pas repris automatiquement."
        )

    with st.expander("Paramètres de la simulation dynamique", expanded=True):
        first, second, third = st.columns(3)
        with first:
            register_count = st.slider(
                "Caisses initialement ouvertes",
                min_value=1,
                max_value=5,
                value=min(base_config.open_registers, 5),
                key="dynamic_open_registers",
            )
            patience_enabled = st.checkbox(
                "Activer l'abandon par patience", value=True, key="dynamic_patience_enabled"
            )
            patience_min = st.number_input(
                "Patience (min)",
                min_value=0.1,
                max_value=120.0,
                value=12.0,
                step=0.5,
                disabled=not patience_enabled,
                key="dynamic_patience_min",
            )
        with second:
            switching_enabled = st.checkbox(
                "Autoriser les changements de file", value=True, key="dynamic_switching_enabled"
            )
            switching_interval = st.number_input(
                "Réévaluation (min)",
                min_value=0.1,
                max_value=30.0,
                value=1.0,
                step=0.5,
                disabled=not switching_enabled,
                key="dynamic_switching_interval",
            )
        with third:
            switching_gain = st.number_input(
                "Gain minimal pour changer (min)",
                min_value=0.0,
                max_value=30.0,
                value=1.0,
                step=0.5,
                disabled=not switching_enabled,
                key="dynamic_switching_gain",
            )
            threshold_min = st.number_input(
                "Seuil d'attente moyenne (min)",
                min_value=0.0,
                max_value=60.0,
                value=float(WAIT_THRESHOLD_MIN),
                step=0.5,
                key="dynamic_mean_wait_threshold",
            )

    config = ScenarioConfig(
        name=base_config.name,
        customer_count=base_config.customer_count,
        arrival_window_min=base_config.arrival_window_min,
        mean_service_time_min=base_config.mean_service_time_min,
        open_registers=register_count,
        seed=base_config.seed,
    )
    options = DynamicOptions(
        patience_min=float(patience_min) if patience_enabled else None,
        switching_enabled=switching_enabled,
        switching_interval_min=float(switching_interval),
        switching_gain_min=float(switching_gain),
    )

    result = _run_dynamic(config, options)
    report = DynamicKPICalculator().compute(result)
    try:
        comparison = _run_comparison(config, options)
        recommendation = recommend_by_mean_wait(comparison, float(threshold_min))
    except ValueError as error:
        comparison = None
        recommendation = None
        st.warning(f"Comparaison non disponible : {error}")

    _render_summary(report)
    summary_tab, evolution_tab, registers_tab, distribution_tab, comparison_tab, diagnosis_tab = (
        st.tabs(
            [
                "Résumé",
                "Évolution temporelle",
                "Performance caisses",
                "Distribution",
                "Comparaison",
                "Diagnostic",
            ]
        )
    )
    with summary_tab:
        _render_summary_details(report)
    with evolution_tab:
        _render_evolution(report, result)
    with registers_tab:
        _render_register_performance(report)
    with distribution_tab:
        _render_distribution(report)
    with comparison_tab:
        _render_comparison(comparison, recommendation, float(threshold_min))
    with diagnosis_tab:
        _render_diagnostic(report, result)

    _render_exports(result, report, comparison, recommendation)


def _render_summary(report: DynamicKPIReport) -> None:
    st.subheader("Résumé des résultats")
    cards = [
        ("Clients arrivés", str(report.arrival_count)),
        ("Clients servis", str(report.served_count)),
        ("Clients abandonnés", str(report.abandoned_count)),
        ("Attente moyenne des servis", _format_minute(report.mean_wait_served_min)),
        ("P95 des attentes des servis", _format_minute(report.p95_wait_served_min)),
        ("Taux d'abandon", _format_percent(report.abandonment_rate)),
        ("Débit", _format_rate(report.throughput_served_per_min)),
    ]
    columns = st.columns(4)
    for index, (label, value) in enumerate(cards):
        columns[index % len(columns)].metric(label, value)


def _render_summary_details(report: DynamicKPIReport) -> None:
    st.markdown("#### Dictionnaire des principaux indicateurs")
    rows = [
        (
            "Attente moyenne des servis", report.mean_wait_served_min,
            "min", "service_start - arrival_time",
        ),
        (
            "Médiane des attentes des servis", report.median_wait_served_min,
            "min", "Médiane des attentes des servis",
        ),
        (
            "P90 des attentes des servis", report.p90_wait_served_min,
            "min", "Quantile linéaire inclusif",
        ),
        (
            "P95 des attentes des servis", report.p95_wait_served_min,
            "min", "Quantile linéaire inclusif",
        ),
        (
            "Attente maximale des servis", report.max_wait_served_min,
            "min", "Maximum des attentes des servis",
        ),
        (
            "Durée moyenne de service", report.mean_service_duration_served_min,
            "min", "Moyenne(service_duration), servis uniquement",
        ),
        (
            "Temps total moyen dans le système", report.mean_total_time_served_min,
            "min", "Moyenne(departure_time - arrival_time), servis uniquement",
        ),
        (
            "Temps total cumulé des servis", report.total_time_served_customer_min,
            "client-min", "Somme(departure_time - arrival_time)",
        ),
        (
            "Temps moyen avant abandon", report.mean_time_before_abandonment_min,
            "min", "Moyenne(abandoned_at - arrival_time), abandons uniquement",
        ),
        ("Taux d'abandon", report.abandonment_rate, "%", "Abandons / arrivées"),
        ("Débit", report.throughput_served_per_min, "clients/min", "Servis / durée observée"),
    ]
    frame = pd.DataFrame(rows, columns=["Indicateur", "Valeur", "Unité", "Définition"])
    st.dataframe(frame, width="stretch", hide_index=True)
    st.caption(
        "Les attentes des clients servis et les temps avant abandon sont deux populations "
        "distinctes. Une valeur indisponible reste vide (N/A), jamais remplacée par zéro."
    )


def _render_evolution(report: DynamicKPIReport, result: DynamicResult) -> None:
    st.markdown("#### Longueur des files par caisse")
    queue_frame = pd.DataFrame(
        {
            "Minute simulée": point.time_min,
            "Caisse": f"Caisse {point.register_id}",
            "Clients en attente": point.waiting_count,
            "Caisse ouverte": "Oui" if point.is_open else "Non",
        }
        for point in report.queue_timeline
    )
    if not queue_frame.empty:
        figure = px.line(
            queue_frame,
            x="Minute simulée",
            y="Clients en attente",
            color="Caisse",
            markers=True,
            hover_data=["Caisse ouverte"],
        )
        figure.update_layout(yaxis_title="Clients en attente (hors service)", legend_title="Caisse")
        for event in result.events:
            if event.type in {"register_opened", "register_closed"}:
                label = "Ouverture" if event.type == "register_opened" else "Fermeture"
                figure.add_vline(
                    x=event.time,
                    line_dash="dot",
                    annotation_text=f"{label} caisse {event.register_id}",
                )
        st.plotly_chart(figure, width="stretch")
    else:
        st.info("Aucun événement disponible pour reconstruire les files.")

    st.markdown("#### Conservation des flux")
    flow_frame = pd.DataFrame(
        {
            "Minute simulée": point.time_min,
            "Arrivés": point.arrived_count,
            "Services terminés": point.completed_count,
            "Abandons": point.abandoned_count,
            "En attente": point.waiting_count,
            "En service": point.in_service_count,
            "Présents": point.present_count,
        }
        for point in report.flow_timeline
    )
    if not flow_frame.empty:
        figure = px.line(
            flow_frame,
            x="Minute simulée",
            y=["Arrivés", "Services terminés", "Abandons", "Présents"],
            markers=True,
        )
        figure.update_layout(yaxis_title="Nombre de clients", legend_title="État")
        st.plotly_chart(figure, width="stretch")
        if all(point.is_conserved for point in report.flow_timeline):
            st.success("Conservation des flux vérifiée à chaque instant observé.")
        else:
            st.error("La conservation des flux n'est pas vérifiée pour au moins un instant.")


def _render_register_performance(report: DynamicKPIReport) -> None:
    st.markdown("#### Indicateurs par caisse")
    frame = pd.DataFrame(
        {
            "Caisse": register.register_id,
            "Servis": register.served_count,
            "Attente moyenne des servis (min)": register.mean_wait_served_min,
            "Temps de service (min)": register.total_service_time_min,
            "Temps ouverte (min)": register.open_time_min,
            "Temps disponible effectif (min)": register.available_time_min,
            "Occupation (%)": (
                register.utilization_rate * 100
                if register.utilization_rate is not None
                else None
            ),
            "Pic de file (clients en attente)": register.peak_queue_length,
        }
        for register in report.registers
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    left, right = st.columns(2)
    with left:
        figure = px.bar(
            frame,
            x="Caisse",
            y="Occupation (%)",
            title="Occupation des caisses",
            range_y=[0, 100],
        )
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(
            frame,
            x="Caisse",
            y="Servis",
            title="Nombre de clients servis par caisse",
        )
        st.plotly_chart(figure, width="stretch")
    st.caption(
        "Le temps disponible effectif comprend les périodes d'ouverture et la fin d'un service "
        "déjà commencé qui se poursuit après une fermeture."
    )


def _render_distribution(report: DynamicKPIReport) -> None:
    st.markdown("#### Distribution des attentes des clients servis")
    if report.served_waits_min:
        figure = px.histogram(
            x=report.served_waits_min,
            nbins=25,
            labels={"x": "Attente avant service (min)", "y": "Clients servis"},
        )
        for value, label in (
            (report.median_wait_served_min, "Médiane"),
            (report.p90_wait_served_min, "P90"),
            (report.p95_wait_served_min, "P95"),
        ):
            if value is not None:
                figure.add_vline(x=value, line_dash="dash", annotation_text=label)
        st.plotly_chart(figure, width="stretch")
    else:
        st.info("Aucun client servi : la distribution des attentes n'est pas disponible.")

    st.markdown("#### Arrivée et délai avant issue")
    customer_frame = pd.DataFrame(report.customer_rows)
    if not customer_frame.empty:
        customer_frame["Délai avant issue (min)"] = customer_frame.apply(
            lambda row: (
                row["wait_served_min"]
                if pd.notna(row["wait_served_min"])
                else row["time_before_abandonment_min"]
            ),
            axis=1,
        )
        figure = px.scatter(
            customer_frame,
            x="arrival_time_min",
            y="Délai avant issue (min)",
            color="outcome",
            hover_data=["customer_id", "register_id"],
            labels={
                "arrival_time_min": "Arrivée (min depuis l'ouverture)",
                "outcome": "Issue",
            },
        )
        st.plotly_chart(figure, width="stretch")
    st.caption(
        "L'histogramme porte uniquement sur les clients servis. Le nuage de points distingue "
        "les attentes des servis des temps passés avant abandon."
    )


def _render_comparison(
    comparison: DynamicComparisonReport | None,
    recommendation: DynamicRecommendation | None,
    threshold_min: float,
) -> None:
    st.markdown("#### Comparaison contrôlée de 1 à 5 caisses")
    if comparison is None or recommendation is None:
        st.info("La comparaison n'est pas disponible pour les paramètres actuels.")
        return
    rows = [vars(row) for row in comparison.rows]
    frame = pd.DataFrame(rows).rename(
        columns={
            "register_count": "Caisses",
            "served_count": "Servis",
            "abandoned_count": "Abandons",
            "abandonment_rate": "Taux d'abandon",
            "mean_wait_served_min": "Attente moyenne des servis (min)",
            "p95_wait_served_min": "P95 (min)",
            "absolute_gain_vs_previous_min": "Gain absolu vs précédent (min)",
            "relative_gain_vs_previous": "Gain relatif vs précédent",
        }
    )
    st.dataframe(frame, width="stretch", hide_index=True)

    figure = px.line(
        frame,
        x="Caisses",
        y="Attente moyenne des servis (min)",
        markers=True,
        title="Nombre de caisses et attente moyenne des clients servis",
    )
    figure.add_hline(y=threshold_min, line_dash="dash", annotation_text="Seuil choisi")
    if recommendation.recommended_registers is not None:
        selected = frame.loc[frame["Caisses"] == recommendation.recommended_registers]
        if not selected.empty and pd.notna(selected.iloc[0]["Attente moyenne des servis (min)"]):
            figure.add_scatter(
                x=selected["Caisses"],
                y=selected["Attente moyenne des servis (min)"],
                mode="markers",
                marker={"size": 15, "symbol": "star"},
                name="Première configuration conforme",
            )
    st.plotly_chart(figure, width="stretch")
    st.metric("Recommandation", recommendation.message)
    st.caption(
        "Règle appliquée : plus petit nombre de caisses dont l'attente moyenne des servis "
        "est inférieure ou égale au seuil. Les abandons sont affichés séparément. "
        "Il ne s'agit pas d'une optimisation économique complète."
    )


def _render_diagnostic(report: DynamicKPIReport, result: DynamicResult) -> None:
    st.markdown("#### Seuils d'alerte configurables")
    first, second, third, fourth = st.columns(4)
    with first:
        max_queue = st.number_input(
            "File trop longue (clients)", 1, 50, 5, key="dynamic_alert_queue"
        )
    with second:
        max_estimated_wait = st.number_input(
            "Attente estimée excessive (min)",
            0.1,
            60.0,
            5.0,
            0.5,
            key="dynamic_alert_wait",
        )
    with third:
        abandonment_limit = st.slider(
            "Taux d'abandon élevé (%)", 0, 100, 10, key="dynamic_alert_abandon"
        )
    with fourth:
        occupancy_limit = st.slider(
            "Occupation soutenue (%)", 0, 100, 85, key="dynamic_alert_occupancy"
        )

    alerts = build_dynamic_alerts(
        report,
        max_queue=int(max_queue),
        max_estimated_wait_min=float(max_estimated_wait),
        abandonment_limit=abandonment_limit / 100,
        occupancy_limit=occupancy_limit / 100,
    )
    if alerts:
        st.dataframe(pd.DataFrame(alerts), width="stretch", hide_index=True)
    else:
        st.success("Aucune alerte ne dépasse les seuils sélectionnés.")
    st.caption(
        "Les alertes sont reconstruites après la simulation. Elles ne sont pas des notifications "
        "en direct et chaque dépassement continu est regroupé en une seule période."
    )

    st.markdown("#### Tableaux filtrables des clients et événements")
    customer_frame = pd.DataFrame(report.customer_rows)
    if not customer_frame.empty:
        outcomes = sorted(customer_frame["outcome"].dropna().unique().tolist())
        selected_outcomes = st.multiselect(
            "Filtrer les clients par issue",
            outcomes,
            default=outcomes,
            key="dynamic_customer_filter",
        )
        st.dataframe(
            customer_frame.loc[customer_frame["outcome"].isin(selected_outcomes)],
            width="stretch",
            hide_index=True,
        )

    event_frame = pd.DataFrame(
        [
            {"Ordre d'origine": index, **event.to_dict()}
            for index, event in enumerate(result.events)
        ]
    )
    if not event_frame.empty:
        event_types = sorted(event_frame["type"].dropna().unique().tolist())
        selected_types = st.multiselect(
            "Filtrer les événements par type",
            event_types,
            default=event_types,
            key="dynamic_event_filter",
        )
        st.dataframe(
            event_frame.loc[event_frame["type"].isin(selected_types)],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Aucun événement à afficher.")


def _render_exports(
    result: DynamicResult,
    report: DynamicKPIReport,
    comparison: DynamicComparisonReport | None,
    recommendation: DynamicRecommendation | None,
) -> None:
    st.subheader("Exports et traçabilité")
    csv_exports = build_dynamic_csv_exports(result, report, comparison)
    columns = st.columns(5)
    for column, (filename, content) in zip(columns, csv_exports.items(), strict=True):
        column.download_button(
            f"CSV {filename.removesuffix('.csv')}",
            data=content,
            file_name=filename,
            mime="text/csv",
            width="stretch",
        )
    excel_bytes = build_dynamic_excel_export(result, report, comparison, recommendation)
    st.download_button(
        "Télécharger le classeur Excel complet",
        data=excel_bytes,
        file_name="retailflow_analytics_dynamique.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        "Les exports conservent les unités, les populations, la graine, les hypothèses, "
        "le seuil et la date de génération. La version du moteur est indiquée comme "
        "non déclarée dans le dépôt lorsqu'aucune version n'est disponible."
    )


def _format_minute(value: float | None) -> str:
    return f"{value:.2f} min" if value is not None else "N/A"


def _format_percent(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "N/A"


def _format_rate(value: float | None) -> str:
    return f"{value:.3f} client/min" if value is not None else "N/A"
