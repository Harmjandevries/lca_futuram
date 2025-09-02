import pandas as pd
import plotly.express as px
from helpers.constants import Route, Scenario, Chemistry
from helpers.lca_builder import LCABuilder
import bw2data as bd

# ---- Setup ----
PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"
bd.projects.set_current(PROJECT_NAME)

db = bd.Database(DATABASE_NAME)

lca_builder = LCABuilder()
lca_builder.load_latest_lcia_results()
lcia_results = lca_builder.lcia_results

# ---- Select only desired chemistries, routes, year, scenario ----
desired_chemistries = [Chemistry.battLiNMC111, Chemistry.battLiNMC811, Chemistry.battLiFP_subsub, Chemistry.battLiNCA_subsub, Chemistry.BattZn, Chemistry.BattPb, Chemistry.BattNiCd, Chemistry.BattNiMH]
desired_routes = [Route.HYDRO, Route.PYRO_HYDRO, Route.PYRO_HYDRO_PRETREATMENT, Route.BATT_ZnAlkaliSorted, Route.BATT_LeadAcidSorted, Route.BATT_NiMHSorted, Route.BATT_NiCdSorted]
selected_year = 2030
selected_scenario = Scenario.BAU

lcia_results_selection = [
    res for res in lcia_results
    if res.lci.chemistry in desired_chemistries
    and res.lci.route in desired_routes
    and res.lci.year == selected_year
    and res.lci.scenario == selected_scenario
]

# ---- Define colors ----
material_colors = {
    'nickel sulfate': '#1f77b4',
    'cobalt sulfate': '#ff7f0e',
    'copper': '#2ca02c',
    'aluminum scrap': '#9467bd',
    'lithium carbonate': '#d62728',
    'ferrous scrap': '#8c564b',
    'graphite': '#7f7f7f',
    'manganese sulfate': '#bcbd22',
    'lead-antimony alloy': "#af8c8c",       # dark gray metallic for lead
    'special high grade zinc': '#aec7e8',   # light bluish-gray for zinc
    'silver': '#c0c0c0',                    # silver/light gray
    'ferronickel alloy': "#be5f32",     
}

# ---- Define route and chemistry names ----
chemistry_labels = {
    Chemistry.battLiFP_subsub: "LFP",
    Chemistry.battLiNMC111: "NMC111",
    Chemistry.battLiNMC811: "NMC811",
    Chemistry.BattZn: "Zinc-based",
    Chemistry.BattPb: "Lead-acid",
    Chemistry.BattNiMH: "Nickel-metal hybride",
    Chemistry.BattNiCd: "Nickel-cadmium"
}

route_labels = {
    Route.HYDRO: "Hydro",
    Route.PYRO_HYDRO: "PyroHydro",
    Route.PYRO_HYDRO_PRETREATMENT: "PyroHydroPt",
    Route.BATT_ZnAlkaliSorted: "Zinc refining process chain",
    Route.BATT_LeadAcidSorted: "Pyromet",
    Route.BATT_NiCdSorted: "Pyromet",
    Route.BATT_NiMHSorted: "Pyromet"
}

rows = []

for res in lcia_results_selection:
    chem = chemistry_labels[res.lci.chemistry]
    route = route_labels[res.lci.route]
    battery_label = f"{chem} - {route}"

    total = res.total_impact  # Already per kg input
    materials = res.impact_per_alloy

    # For zinc batteries: merge silver into special high grade zinc
    if res.lci.chemistry == Chemistry.BattZn:
        zinc_impact = 0.0
        other_materials = []
        for m in materials:
            mat_name = m['material']
            imp = m['impacts']
            if mat_name == 'special high grade zinc':
                zinc_impact += imp
            elif mat_name == 'silver':
                zinc_impact += imp
            else:
                other_materials.append(m)
        
        # Add combined zinc
        rows.append({'Battery': battery_label, 'Material': 'special high grade zinc', 'GWP100 (kg CO2 eq)': zinc_impact})
        
        # Add remaining materials
        sum_impacts = zinc_impact + sum(m['impacts'] for m in other_materials)
        for m in other_materials:
            rows.append({'Battery': battery_label, 'Material': m['material'], 'GWP100 (kg CO2 eq)': m['impacts']})
        
    else:
        sum_impacts = sum(m['impacts'] for m in materials)
        for m in materials:
            rows.append({'Battery': battery_label, 'Material': m['material'], 'GWP100 (kg CO2 eq)': m['impacts']})

    remaining = total - sum_impacts
    if remaining > 0:
        rows.append({'Battery': battery_label, 'Material': 'Other', 'GWP100 (kg CO2 eq)': remaining})


df = pd.DataFrame(rows)

# ---- Color map (include Other) ----
color_discrete_map = {mat: material_colors.get(mat, 'grey') for mat in df['Material'].unique()}
color_discrete_map['Other'] = 'lightgrey'

# ---- Sort materials for stacking ----
desired_material_order = [
    'nickel sulfate',
    'cobalt sulfate',
    'manganese sulfate',
    'copper',
    'aluminum scrap',
    'lithium carbonate',
    'graphite',
    'ferrous scrap',
    'Other'
]

# ---- Sort battery order ----
desired_battery_order = [
    "LFP - Hydro", "NMC111 - Hydro", "NMC811 - Hydro",
    "LFP - PyroHydro", "NMC111 - PyroHydro", "NMC811 - PyroHydro",
    "LFP - PyroHydroPt", "NMC111 - PyroHydroPt", "NMC811 - PyroHydroPt"
]

# ---- Plot ----
fig = px.bar(df,
             x='Battery',
             y='GWP100 (kg CO2 eq)',
             color='Material',
             color_discrete_map=color_discrete_map,
             category_orders={
                 "Material": desired_material_order,
                 "Battery": desired_battery_order
             },
             title="Global warming potential (GWP100) per kg input (2030 BAU)")

fig.update_layout(barmode='stack', legend_title_text='Material')
fig.show()
