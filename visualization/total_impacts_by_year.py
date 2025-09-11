import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import bw2data as bd
from code_folder.helpers.constants import Product

from code_folder.helpers.lca_builder import LCABuilder


# Mapping battery product to family
def get_battery_family(product):
    if product.value.startswith("battLi"):
        return "li-ion"
    elif product == Product.BattPb:
        return "leadacid"
    elif product == Product.BattZn:
        return "znalkali"
    else:
        return None  # Ignore other products


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
    chem = result.lci.product
    year = result.lci.year
    family = get_battery_family(chem)
    
    if family is None:
        continue  # Skip non-relevant products

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
