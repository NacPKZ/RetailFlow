"""Fabriques Plotly communes aux deux moteurs, sans rendu Streamlit."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from queuesmart.analytics.visual_data import arrival_bins, flow_frame
from queuesmart.config import WAIT_THRESHOLD_MIN

NAVY = "#162C46"
BLUE = "#3979CE"
TEAL = "#148778"
GOLD = "#BD8B32"
RED = "#C35465"
PALETTE = [BLUE, TEAL, GOLD, "#8A69B5", "#D27145", "#527D8F", "#AF578C", "#5967AC"]
PLOT_CONFIG = {
    "displaylogo": False,
    "scrollZoom": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "RetailFlow_graphique"},
}


def style(fig: go.Figure, title: str, height: int = 370) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, x=0, font=dict(size=19)),
        height=height,
        margin=dict(l=24, r=26, t=82, b=55),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", size=14, color=NAVY),
        colorway=PALETTE,
        separators=", ",
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor=NAVY, font_color="white", font_size=14),
        transition=dict(duration=300),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, automargin=True, title_standoff=14)
    fig.update_yaxes(gridcolor="#EDF1F5", zeroline=False, automargin=True, title_standoff=12)
    return fig


def wait_target(fig: go.Figure, horizontal: bool = True) -> None:
    args = dict(
        line_color=GOLD,
        line_dash="dash",
        line_width=1.5,
        annotation_text="Seuil : 5 min",
        annotation_font_size=12,
    )
    if horizontal:
        fig.add_hrect(y0=0, y1=WAIT_THRESHOLD_MIN, fillcolor=TEAL, opacity=0.045, line_width=0)
        fig.add_hline(y=WAIT_THRESHOLD_MIN, annotation_position="top right", **args)
    else:
        fig.add_vline(x=WAIT_THRESHOLD_MIN, annotation_position="top right", **args)


def wait_scatter(clients: pd.DataFrame, x: str = "Arrivée") -> go.Figure:
    fig = go.Figure()
    for rid, part in clients.groupby("Caisse", sort=True):
        label = f"Caisse {int(rid)}"
        fig.add_trace(
            go.Scatter(
                x=part[x],
                y=part["Attente"],
                mode="markers",
                name=label,
                marker=dict(
                    size=9,
                    color=PALETTE[(int(rid) - 1) % len(PALETTE)],
                    opacity=0.8,
                    line=dict(width=1, color="white"),
                ),
                customdata=part[["Client", "Service", "Statut"]].to_numpy(),
                hovertemplate=(
                    "Client %{customdata[0]}<br>" + x + " : %{x:.2f} min<br>"
                    "Attente : %{y:.2f} min<br>Service prévu : %{customdata[1]:.2f} min"
                    "<br>%{customdata[2]}<extra>" + label + "</extra>"
                ),
            )
        )
    wait_target(fig)
    fig.update_xaxes(
        title="Minute d'arrivée" if x == "Arrivée" else "Durée de service prévue (min)"
    )
    fig.update_yaxes(title="Attente avant service ou abandon (min)", rangemode="tozero")
    return style(
        fig, "Quand l'attente s'accumule" if x == "Arrivée" else "Service prévu et attente", 420
    )


def wait_histogram(clients: pd.DataFrame) -> go.Figure:
    waits = clients["Attente"].dropna().to_numpy(dtype=float)
    upper = max(6.0, float(waits.max()) if len(waits) else 0.0)
    edges = np.linspace(0, upper, min(25, max(6, int(np.sqrt(len(waits))) + 1)))
    edges = np.unique(np.append(edges, WAIT_THRESHOLD_MIN))
    centers = (edges[1:] + edges[:-1]) / 2
    fig = go.Figure()
    for selected, label, color in [
        (waits[waits <= WAIT_THRESHOLD_MIN], "Attente ≤ 5 min", TEAL),
        (waits[waits > WAIT_THRESHOLD_MIN], "Attente > 5 min", RED),
    ]:
        counts, _ = np.histogram(selected, bins=edges)
        fig.add_bar(
            x=centers,
            y=counts,
            width=np.diff(edges) * 0.91,
            name=label,
            marker_color=color,
            customdata=np.column_stack((edges[:-1], edges[1:])),
            hovertemplate="%{customdata[0]:.2f} à %{customdata[1]:.2f} min"
            "<br>%{y} clients<extra>" + label + "</extra>",
        )
    fig.update_layout(barmode="stack")
    wait_target(fig, False)
    fig.update_xaxes(title="Attente (min)", range=[-0.15, upper + 0.5])
    fig.update_yaxes(title="Nombre de clients", rangemode="tozero")
    return style(fig, "Comment se répartissent les attentes")


def wait_ecdf(clients: pd.DataFrame) -> go.Figure:
    waits = np.sort(clients["Attente"].dropna().to_numpy(dtype=float))
    values, counts = np.unique(waits, return_counts=True)
    fig = go.Figure(
        go.Scatter(
            x=values,
            y=np.cumsum(counts) / max(1, len(waits)) * 100,
            mode="lines",
            line=dict(color=BLUE, width=3, shape="hv"),
            fill="tozeroy",
            fillcolor="rgba(57,121,206,.08)",
            hovertemplate="%{y:.1f} % des clients<br>attendent au plus %{x:.2f} min<extra></extra>",
        )
    )
    fig.add_hline(y=90, line_color=TEAL, line_dash="dot", annotation_text="90 % des clients")
    wait_target(fig, False)
    fig.update_xaxes(title="Attente maximale considérée (min)", rangemode="tozero")
    fig.update_yaxes(title="Part cumulée des clients", range=[0, 105], ticksuffix=" %")
    return style(fig, "Quelle part des clients attend moins longtemps ?")


def congestion(clients: pd.DataFrame) -> go.Figure:
    data = flow_frame(clients)
    fig = go.Figure()
    for name, color in [("En service", BLUE), ("En attente", GOLD)]:
        fig.add_trace(
            go.Scatter(
                x=data["Minute"],
                y=data[name],
                name=name,
                mode="lines",
                stackgroup="clients",
                line=dict(color=color, width=1.8, shape="hv"),
                hovertemplate="%{y} clients<extra>" + name + "</extra>",
            )
        )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Temps depuis l'ouverture (min)")
    fig.update_yaxes(title="Clients présents", rangemode="tozero")
    return style(fig, "La congestion, minute par minute", 390)


def cumulative_flow(clients: pd.DataFrame) -> go.Figure:
    data = flow_frame(clients)
    fig = go.Figure()
    for name, color in [("Servis", TEAL), ("Abandons", RED)]:
        fig.add_trace(
            go.Scatter(
                x=data["Minute"],
                y=data[name],
                name=name,
                mode="lines",
                line=dict(color=color, width=3, shape="hv"),
            )
        )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Temps depuis l'ouverture (min)")
    fig.update_yaxes(title="Clients cumulés", rangemode="tozero")
    return style(fig, "Les sorties du magasin")


def register_load(registers: pd.DataFrame) -> go.Figure:
    labels = [f"Caisse {i}" for i in registers["Caisse"]]
    fig = go.Figure(
        go.Bar(
            y=labels,
            x=[100] * len(labels),
            orientation="h",
            marker_color="#EFF3F8",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            y=labels,
            x=registers["Occupation (%)"],
            orientation="h",
            marker_color=[PALETTE[(int(i) - 1) % len(PALETTE)] for i in registers["Caisse"]],
            text=[f"{v:.0f} %" for v in registers["Occupation (%)"]],
            textposition="auto",
            customdata=registers[["Clients", "Attente moyenne"]].to_numpy(),
            hovertemplate=(
                "%{y}<br>Occupation : %{x:.1f} %<br>%{customdata[0]} clients servis"
                "<br>Attente moyenne : %{customdata[1]:.2f} min<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_layout(barmode="overlay", bargap=0.45)
    fig.update_xaxes(
        title="Part de la durée totale consacrée au service", range=[0, 105], ticksuffix=" %"
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, "Comment la charge est répartie", max(330, len(labels) * 42 + 120))


def service_timeline(clients: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    served = clients.loc[clients["Statut"] == "Servi"]
    for rid, part in served.groupby("Caisse"):
        fig.add_trace(
            go.Bar(
                y=[f"Caisse {int(rid)}"] * len(part),
                x=part["Service"],
                base=part["Début"],
                orientation="h",
                width=0.65,
                name=f"Caisse {int(rid)}",
                showlegend=False,
                marker=dict(
                    color=PALETTE[(int(rid) - 1) % len(PALETTE)], line_color="white", line_width=0.6
                ),
                customdata=part[["Client", "Début", "Sortie", "Attente"]].to_numpy(),
                hovertemplate=(
                    "Client %{customdata[0]:.0f}<br>Service : %{customdata[1]:.2f} à "
                    "%{customdata[2]:.2f} min<br>Attente : %{customdata[3]:.2f} min<extra></extra>"
                ),
            )
        )
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Temps depuis l'ouverture (min)")
    fig.update_yaxes(title="", autorange="reversed", showgrid=False)
    return style(fig, "Les passages en caisse, à leur durée réelle", 400)


def wait_heatmap(clients: pd.DataFrame, count: int) -> go.Figure:
    data = clients.assign(Tranche=(clients["Arrivée"] // 10 * 10).astype(int))
    bins = list(range(0, int(data["Tranche"].max()) + 10, 10))
    grid = data.pivot_table(index="Caisse", columns="Tranche", values="Attente", aggfunc="mean")
    grid = grid.reindex(index=range(1, count + 1), columns=bins)
    fig = go.Figure(
        go.Heatmap(
            z=grid.to_numpy(),
            x=[f"{b} à {b + 10}" for b in bins],
            y=[f"Caisse {i}" for i in grid.index],
            colorscale=[[0, "#ECF4FA"], [0.4, "#6C9AC7"], [0.75, "#D1AC65"], [1, RED]],
            zmin=0,
            colorbar=dict(title="min", thickness=12),
            xgap=3,
            ygap=3,
            hoverongaps=False,
            hovertemplate="%{y}<br>Arrivées : %{x} min<br>Attente moyenne : %{z:.2f} "
            "min<extra></extra>",
        )
    )
    fig.update_xaxes(title="Tranche d'arrivée (min)")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, "Où se concentrent les attentes ?", 370)


def arrival_chart(clients: pd.DataFrame) -> go.Figure:
    data = arrival_bins(clients)
    fig = go.Figure(
        go.Bar(
            x=data["Tranche"],
            y=data["Clients"],
            width=8,
            marker_color=BLUE,
            text=data["Clients"],
            textposition="outside",
            hovertemplate="Tranche commençant à %{x} min<br>%{y} arrivants<extra></extra>",
        )
    )
    fig.update_xaxes(title="Début de tranche de 10 min")
    fig.update_yaxes(title="Clients arrivés", rangemode="tozero")
    return style(fig, "L'affluence pendant la simulation")


def capacity_chart(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["Caisses"],
            y=data["Maximum des moyennes"],
            mode="lines",
            line_width=0,
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["Caisses"],
            y=data["Minimum des moyennes"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(57,121,206,.13)",
            line_width=0,
            name="Étendue des moyennes observées",
            hoverinfo="skip",
        )
    )
    for name, color in [("Attente moyenne", BLUE), ("P90", GOLD)]:
        fig.add_trace(
            go.Scatter(
                x=data["Caisses"],
                y=data[name],
                name=name,
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker_size=9,
                hovertemplate="%{y:.2f} min<extra>" + name + "</extra>",
            )
        )
    feasible = data.loc[data["Objectif atteint"]]
    if len(feasible):
        row = feasible.iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["Caisses"]],
                y=[row["P90"]],
                mode="markers",
                name="Capacité minimale observée",
                marker=dict(size=18, symbol="star", color=TEAL),
            )
        )
    wait_target(fig)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Nombre de caisses ouvertes", dtick=1)
    fig.update_yaxes(title="Attente (min)", rangemode="tozero")
    return style(fig, "Combien de caisses pour atteindre l'objectif ?", 440)
