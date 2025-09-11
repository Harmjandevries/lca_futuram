import matplotlib.pyplot as plt
import pandas as pd
import bw2data as bd
from code_folder.helpers.constants import Product

from code_folder.helpers.lca_builder import LCABuilder

PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)

db = bd.Database(DATABASE_NAME)

lca_builder = LCABuilder()
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results

# Helper: map Product enum to readable label
def get_product_label(product):
    mapping = {
        Product.BattPb: "Lead-acid",
        Product.BattZn: "Zn-alkali",
        Product.BattNiMH: "NiMH",
        Product.BattNiCd: "NiCd",
        Product.battLiNMC111: "Li-ion NMC111",
        Product.battLiNMC811: "Li-ion NMC811",
        Product.battLiFP_subsub: "Li-ion LFP"
    }
    return mapping.get(product, "Other")

# Aggregate data
data = []

for result in lcia_results:
    chem = result.lci.product
    year = result.lci.year

    label = get_product_label(chem)
    
    # Skip if not in our mapping
    if label == "Other":
        continue

    # Compute total impact
    total_impact_value = result.total_impact * result.lci.total_inflow_amount

    data.append({
        "year": year,
        "product": label,
        "impact": total_impact_value
    })

# Create DataFrame
df = pd.DataFrame(data)

# Group by year and product
grouped = df.groupby(['year', 'product']).sum().reset_index()

# Filter years >= 2025 and only even steps (2025, 2027, ...)
filtered = grouped[(grouped['year'] >= 2025) & (grouped['year'] % 2 == 1)]

# Pivot to wide format
pivot_df = filtered.pivot(index='year', columns='product', values='impact').fillna(0)

# Optional: sort columns in custom order if desired
column_order = [
    "Li-ion NMC111", 
    "Li-ion NMC811", 
    "Li-ion LFP", 
    "Lead-acid", 
    "Zn-alkali", 
    "NiMH", 
    "NiCd"
]
pivot_df = pivot_df[[col for col in column_order if col in pivot_df.columns]]

# Plot
pivot_df.plot(kind='bar', stacked=True, figsize=(14, 7))

plt.ylabel('t CO2 eq')
plt.xlabel('Year')
plt.title('Global warming potential (GWP100) - BAU scenario')
plt.legend(title='Battery type')
plt.tight_layout()
plt.show()
