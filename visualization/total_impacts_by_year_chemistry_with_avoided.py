import matplotlib.pyplot as plt
import pandas as pd
import bw2data as bd
from helpers.constants import Chemistry
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
        Chemistry.battLiFP_subsub: "Li-ion LFP"
    }
    return mapping.get(chemistry, "Other")

# Collect data
data = []
for result in lcia_results:
    chem = result.lci.chemistry
    year = result.lci.year
    label = get_chemistry_label(chem)

    if label == "Other":
        continue

    inflow = result.lci.total_inflow_amount
    total_impact_value = result.total_impact * inflow
    avoided_impact_value = result.avoided_impact * inflow   # <-- new

    data.append({
        "year": year,
        "chemistry": label,
        "impact": total_impact_value,
        "avoided": -avoided_impact_value   # make negative so it goes below axis
    })

df = pd.DataFrame(data)

# Group
grouped = df.groupby(["year", "chemistry"]).sum().reset_index()

# Filter (years >= 2025 and odd numbers)
filtered = grouped[(grouped["year"] >= 2025) & (grouped["year"] % 2 == 1)]

# Pivot: impacts
impact_df = filtered.pivot(index="year", columns="chemistry", values="impact").fillna(0)
avoided_df = filtered.pivot(index="year", columns="chemistry", values="avoided").fillna(0)

# Sort columns
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

# Plot stacked bars: impacts above, avoided below
fig, ax = plt.subplots(figsize=(14, 7))

impact_df.plot(kind="bar", stacked=True, ax=ax, position=1, width=0.8)
avoided_df.plot(kind="bar", stacked=True, ax=ax, position=1, width=0.8)

ax.set_ylabel("t CO₂ eq")
ax.set_xlabel("Year")
ax.set_title("Global warming potential (GWP100) - BAU scenario")

ax.axhline(0, color="black", linewidth=1)
ax.legend(title="Battery type")
plt.tight_layout()
plt.show()
