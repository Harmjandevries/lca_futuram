import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px


material_colors = {
            'Co': '#1f77b4',
            'Ni': '#ff7f0e',
            'Cu': '#2ca02c',
            'Li': '#d62728',
            'Al': '#9467bd',
            'AlAndAlAlloys': '#8c564b',
            'ferrousMetals': '#e377c2',
            'Mn': '#7f7f7f',
            'ni': '#ff7f0e',
            'co': '#1f77b4',
            'pb': '#bcbd22',
            'sb': '#17becf',
            'cd': '#bc82bd',
            'copper': '#2ca02c',
            'iron': '#7f7f7f',
            'nickel sulfate': '#1f77b4',
            'cobalt sulfate': '#ff7f0e',
            'aluminum scrap': '#9467bd',
            'lithium carbonate': '#d62728',
            'lead-antimony alloy': '#bcbd22',
            'ferronickel alloy': '#17becf',
            'special high grade zinc': '#f7b6d2',
            'silver': '#c49c94',
            'ferrous scrap': '#8c564b',
        }

names_map = {
    "lithium nickel-manganese-cobalt 111":"Lithium-Ion battery (NMC111)",
    "sorted nickel-metal hybride": "Nickel-Metal hybride battery",
    "sorted lead acid": "Lead Acid battery",
    "sorted znalkali": "Zinc-based batteries"
}


class PlotHelper():
    def __init__(self):
        pass
    @staticmethod
    def plot_allocated_lcia_plotly(results, per_input=True):
        # If per input, its per input kg, if false, per output kg

        # Convert results into long-format dataframe
        rows = []
        for waste_input in results:
            if not per_input:
                scaling_factor = sum([impact_per_material['amount'] for impact_per_material in results[waste_input][0]])
            else:
                scaling_factor = 1
            battery_name = waste_input.replace(" - input cutoff","").replace(" battery waste", "")
            if battery_name in names_map:
                battery_name = names_map[battery_name]
            label = battery_name
            materials = [impact_per_material['material'] for impact_per_material in results[waste_input][0]]
            impacts = [impact_per_material['impacts']/scaling_factor for impact_per_material in results[waste_input][0]]
            total = results[waste_input][1]/scaling_factor
            
            sum_impacts = sum(impacts)
            remaining = total - sum_impacts
            if remaining > 0:
                rows.append({'Battery': label, 'Material': 'Other', 'Impact': remaining})
            
            for mat, imp in zip(materials, impacts):
                rows.append({'Battery': label, 'Material': mat, 'Impact': imp})

        df = pd.DataFrame(rows)

        # Assign colors, include 'Other' as lightgrey
        all_materials = df.sort_values("Impact",ascending=False)['Material'].unique()
        color_discrete_map = {mat: material_colors.get(mat, 'grey') for mat in all_materials}
        color_discrete_map['Other'] = 'lightgrey'

        # Plot using plotly express
        title = "Global warming potential for 1kg of input material" if per_input else "Global warming potential for 1kg of recovered mixed materials - allocated by price"
        fig = px.bar(df, 
                     x='Battery', 
                     y='Impact', 
                     color='Material',
                     color_discrete_map=color_discrete_map,
                     title=title,
                     labels={'Impact': 'GWP (kg CO₂ eq)'})

        fig.update_layout(barmode='stack', legend_title_text='Material')
        fig.show()