import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px


results = {
    'lithium nickel-manganese-cobalt 111 battery waste - input cutoff': (
    [
        {'material': 'cobalt sulfate', 'amount': 0.05581311, 'impacts': 1.68956650},
        {'material': 'nickel sulfate', 'amount': 0.06528687, 'impacts': 0.98817735},
        {'material': 'copper', 'amount': 0.05597680, 'impacts': 0.76253470},
        {'material': 'aluminum scrap', 'amount': 0.08488098, 'impacts': 0.32118809},
        {'material': 'lithium carbonate', 'amount': 0.00205252, 'impacts': 0.03728022},
        {'material': 'ferrous scrap', 'amount': 0.05578485, 'impacts': 0.02110889}
    ],
    3.819855755205896
), 
            
            'sorted lead acid battery waste': ([{'material': 'lead-antimony alloy', 'amount': 0.6122129500846486, 'impacts': 0.3497265133831404}], 0.3497265133831404), 'sorted nickel-metal hybride battery waste': ([{'material': 'ferronickel alloy', 'amount': 0.3649173097513201, 'impacts': 0.2914441598969587}, {'material': 'ferrous scrap', 'amount': 0.23616657923862214, 'impacts': 0.002773769823314213}], 0.29421792972027294), 'sorted znalkali battery waste': ([{'material': 'special high grade zinc', 'amount': 0.1698763288377611, 'impacts': 0.45645556699545375}], 0.45645556699545375)}


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
        all_materials = df['Material'].unique()
        color_discrete_map = {mat: material_colors.get(mat, 'grey') for mat in all_materials}
        color_discrete_map['Other'] = 'lightgrey'

        # Define custom material stacking order
        preferred_order = [
            'nickel sulfate',
            'cobalt sulfate',
            'copper',
            'aluminum scrap',
            'lithium carbonate',
            'lead-antimony alloy',
            'special high grade zinc',
            'ferronickel alloy',
            'ferrous scrap',  # <-- place ferrous scrap after ferronickel alloy so it's stacked above
            'Other',
            'silver',

        ]

        # Ensure all present materials are included
        present_materials = [mat for mat in preferred_order if mat in df['Material'].unique()]
        # Add any missing ones at the end
        present_materials += [mat for mat in df['Material'].unique() if mat not in present_materials]

        # Plot using plotly express
        title = "Global warming potential for 1kg of input material" if per_input else "Global warming potential for 1kg of recovered mixed materials - allocated by price"
        fig = px.bar(df, 
                    x='Battery', 
                    y='Impact', 
                    color='Material',
                    color_discrete_map=color_discrete_map,
                    category_orders={"Material": present_materials},
                    title=title,
                    labels={'Impact': 'GWP (kg CO₂ eq)'})

        fig.update_layout(barmode='stack', legend_title_text='Material')
        fig.show()



PlotHelper.plot_allocated_lcia_plotly(results, per_input=False)