import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import bw2data as bd
from helpers.constants import Chemistry

from helpers.lca_builder import LCABuilder


# Mapping battery chemistry to family
def get_battery_family(chemistry):
    if chemistry.value.startswith("battLi"):
        return "li-ion"
    elif chemistry == Chemistry.BattPb:
        return "leadacid"
    elif chemistry == Chemistry.BattZn:
        return "znalkali"
    else:
        return None  # Ignore other chemistries


PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)

db = bd.Database(DATABASE_NAME)

lca_builder = LCABuilder(db)
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results



# Aggregate impacts by year and family
data = []

for result in lcia_results:
    chem = result.lci.chemistry
    year = result.lci.year
    family = get_battery_family(chem)
    
    if family is None:
        continue  # Skip non-relevant chemistries

    # Compute total impact for this battery type in this year
    total_impact_value = result.total_impact * result.lci.total_inflow_amount

    data.append({
        "year": year,
        "family": family,
        "impact": total_impact_value
    })

# Create DataFrame
df = pd.DataFrame(data)

# Group by year and family
grouped = df.groupby(['year', 'family']).sum().reset_index()

# Pivot to wide format for stacked plot
pivot_df = grouped.pivot(index='year', columns='family', values='impact').fillna(0)

# Sort columns to desired order
pivot_df = pivot_df[['li-ion', 'leadacid', 'znalkali']].fillna(0)

# Plot
pivot_df.plot(kind='bar', stacked=True, figsize=(12, 6))

plt.ylabel('t CO2 eq')
plt.xlabel('Year')
plt.title('Global warming potential (GWP100)')
plt.legend(title='Battery type')
plt.tight_layout()
plt.show()
