import matplotlib.pyplot as plt
import pandas as pd
import bw2data as bd
from code_folder.helpers.constants import Product, Route
from code_folder.helpers.lca_builder import LCABuilder
import time

import pyautogui
import time


# Helper to map family
def get_battery_family(product):
    if product.value.startswith("battLi"):
        return "li-ion"
    elif product == Product.BattPb:
        return "leadacid"
    elif product == Product.BattZn:
        return "znalkali"
    else:
        return None

# Helper to make label for li-ion by route
def get_li_ion_label(route):
    if route == Route.PYRO_HYDRO:
        return "Pyro+Hydro recycling of Li-ion battery"
    elif route == Route.PYRO_HYDRO_PRETREATMENT:
        return "Pyro+Hydro+Pretreat recycling of Li-ion battery"
    elif route == Route.HYDRO:
        return "Hydromet recycling of Li-ion battery"
    else:
        return "Other Li-ion recycling"

PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)

db = bd.Database(DATABASE_NAME)

lca_builder = LCABuilder(db)
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results

# Aggregate data
data = []

for result in lcia_results:
    chem = result.lci.product
    route = result.lci.route
    year = result.lci.year
    family = get_battery_family(chem)
    
    if family is None:
        continue

    total_impact_value = result.total_impact * result.lci.total_inflow_amount

    if family == "li-ion":
        # Further split by route
        label = get_li_ion_label(route)
    else:
        label = family

    data.append({
        "year": year,
        "label": label,
        "impact": total_impact_value
    })

# Create DataFrame
df = pd.DataFrame(data)

# Group
grouped = df.groupby(['year', 'label']).sum().reset_index()

# Pivot
pivot_df = grouped.pivot(index='year', columns='label', values='impact').fillna(0)

# Sort columns if desired (optional)
column_order = sorted(pivot_df.columns, key=lambda x: x.lower())
pivot_df = pivot_df[column_order]

# Plot
pivot_df.plot(kind='bar', stacked=True, figsize=(14, 7))

plt.ylabel('t CO2 eq')
plt.xlabel('Year')
plt.title('Global warming potential (GWP100)')
plt.legend(title='Battery type')
plt.tight_layout()
plt.show()
