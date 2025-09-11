import pandas as pd
import bw2data as bd
import plotly.graph_objects as go
from code_folder.helpers.constants import Chemistry
from code_folder.helpers.lca_builder import LCABuilder

PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)

db = bd.Database(DATABASE_NAME)

lca_builder = LCABuilder()
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results

# Helper: map Chemistry enum to readable label
def get_chemistry_label(chemistry):
    mapping = {
        Chemistry.BattPb: "Lead-acid",
        Chemistry.BattZn: "Zn-alkali",
        Chemistry.BattNiMH: "NiMH",
        Chemistry.BattNiCd: "NiCd",
        Chemistry.battLiNMC111: "Li-ion NMC111",
        Chemistry.battLiNMC811: "Li-ion NMC811",
        Chemistry.battLiFP_subsub: "Li-ion LFP",
        Chemistry.battLiNCA_subsub: "Li-ion NCA"
    }
    return mapping.get(chemistry.value)

# Collect data
data = []
for result in lcia_results:
    chem = result.lci.chemistry
    year = result.lci.year
    label = get_chemistry_label(chem)


    inflow = result.lci.total_inflow_amount
    total_impact_value = result.total_impact * inflow
    avoided_impact_value = result.avoided_impact * inflow

    # --- Fix signs ---
    if total_impact_value < 0:
        total_impact_value = abs(total_impact_value)
    if avoided_impact_value > 0:
        avoided_impact_value = -abs(avoided_impact_value)

    data.append({
        "year": year,
        "chemistry": label,
        "impact": total_impact_value,
        "avoided": avoided_impact_value
    })

df = pd.DataFrame(data)

# Group
grouped = df.groupby(["year", "chemistry"]).sum().reset_index()

# Filter for 2025–2050
filtered = grouped[(grouped["year"] >= 2025) & (grouped["year"] <= 2050)]

# Pivot: impacts and avoided
impact_df = filtered.pivot(index="year", columns="chemistry", values="impact").fillna(0)
avoided_df = filtered.pivot(index="year", columns="chemistry", values="avoided").fillna(0)

# Column order
column_order = [
    "Li-ion NMC111",
    "Li-ion NMC811",
    "Li-ion LFP",
    "Lead-acid",
    "Zn-alkali",
    "NiMH",
    "NiCd"
]
impact_df = impact_df[[c for c in column_order if c in impact_df.columns]]
avoided_df = avoided_df[[c for c in column_order if c in avoided_df.columns]]

# Plotly stacked bar chart
fig = go.Figure()

for i, col in enumerate(impact_df.columns):
    # Positive impact (above axis)
    fig.add_trace(go.Bar(
        x=impact_df.index.astype(str),
        y=impact_df[col],
        name=col,
        legendgroup=col,
        marker=dict(line=dict(width=0)),
    ))
    # Negative avoided impact (below axis, same color)
    fig.add_trace(go.Bar(
        x=avoided_df.index.astype(str),
        y=avoided_df[col],
        name=col,  # same name
        legendgroup=col,
        showlegend=False,  # don’t duplicate in legend
        marker=dict(line=dict(width=0)),
    ))

fig.update_layout(
    barmode="relative",
    title="Global warming potential (GWP100) - BAU scenario",
    xaxis_title="Year",
    yaxis_title="t CO₂ eq",
    legend_title="Battery type",
    bargap=0.15,
    height=600,
    width=1000
)

fig.add_hline(y=0, line_color="black", line_width=1)

fig.show()
