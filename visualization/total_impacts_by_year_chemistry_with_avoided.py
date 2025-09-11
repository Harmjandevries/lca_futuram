import pandas as pd
import plotly.express as px
import bw2data as bd
from code_folder.helpers.constants import Product
from code_folder.helpers.lca_builder import LCABuilder

PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)
db = bd.Database(DATABASE_NAME)

chosen_scenario="CIR"
lca_builder = LCABuilder()
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results

for result in lcia_results:
    if result.lci.product.value=="battZn":
        result.avoided_impact = 0.48

# Helper: map Product enum to readable label (fallback to enum name if unknown)
def get_product_label(product):
    mapping = {
        Product.BattPb: "Lead-acid",
        Product.BattZn: "Zn-alkali",
        Product.BattNiMH: "NiMH",
        Product.BattNiCd: "NiCd",
        Product.battLiNMC111: "Li-ion NMC (high Co)",
        Product.battLiNMC811: "Li-ion NMC (low Co)",
        Product.battLiFP_subsub: "Li-ion LFP",
        product.battLiNCA_subsub: "Li-ion NCA"
    }
    # If not in mapping, use the enum's name or string repr to ensure it's included
    return mapping.get(product, getattr(product, "name", str(product)))

# Collect data
rows = []
for result in lcia_results:
    chem_label = get_product_label(result.lci.product)
    year = int(result.lci.year)
    if result.lci.scenario.value!=chosen_scenario:
        continue

    inflow = result.lci.total_inflow_amount
    total_impact_value = result.total_impact * inflow
    avoided_impact_value = result.avoided_impact * inflow  # positive by definition here

    rows.append({
        "year": year,
        "product": chem_label,
        "impact": float(total_impact_value),
        "avoided": -float(avoided_impact_value),  # make negative so it goes below axis
    })

df = pd.DataFrame(rows)

# Group (sum across same year/product if needed)
grouped = df.groupby(["year", "product"], as_index=False).sum()

# Filter to years 2020–2050 that are actually present (no odd-only restriction)
present_years = sorted(y for y in grouped["year"].unique() if 2020 <= y <= 2050)
filtered = grouped[grouped["year"].isin(present_years)].copy()

# Ensure ALL products present in the dataset are included (even if zero for a year)
all_chems = sorted(filtered["product"].unique())

# Create a complete grid of (year, product)
complete_index = pd.MultiIndex.from_product([present_years, all_chems], names=["year", "product"])
completed = (
    filtered.set_index(["year", "product"])
    .reindex(complete_index, fill_value=0)
    .reset_index()
)

# Long-form for Plotly (stacked bars with positives and negatives)
long_df = pd.melt(
    completed,
    id_vars=["year", "product"],
    value_vars=["impact", "avoided"],
    var_name="impact_type",
    value_name="value",
)

# Column (legend) order – include any extra products that weren't in the original order
preferred_order = [
    "Li-ion NCA",
    "Li-ion NMC (high Co)",
    "Li-ion NMC (low Co)",
    "Li-ion LFP",
    "Lead-acid",
    "Zn-alkali",
    "NiMH",
    "NiCd",
]
# Add any remaining products (e.g., previously unmapped) at the end, preserving discovery order
remaining = [c for c in all_chems if c not in preferred_order]
product_order = [c for c in preferred_order if c in all_chems] + remaining

# Plot
fig = px.bar(
    long_df,
    x="year",
    y="value",
    color="product",
    category_orders={
        "year": present_years,
        "product": product_order,
    },
)

# Stacked positives/negatives around zero
fig.update_layout(
    barmode="relative",
    title=f"Global warming potential (GWP100) - {chosen_scenario} scenario",
    xaxis_title="Year",
    yaxis_title="t CO₂ eq",
    legend_title_text="Battery type",
)

# Draw axis line at y=0
fig.add_hline(y=0, line_width=1, line_color="black")

# Improve hover labels
fig.update_traces(hovertemplate="Year=%{x}<br>%{legendgroup}: %{y:.2f} t CO₂ eq<extra></extra>")

fig.show()
