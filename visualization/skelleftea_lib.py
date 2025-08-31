import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px


results = {
    'lithium iron phosphate battery waste pretreatment - input cutoff': ([{'material': 'copper', 'amount': 0.082428524, 'impacts': 2.643752418520388}, {'material': 'aluminum scrap', 'amount': 0.091984187, 'impacts': 0.8195093863883064}, {'material': 'ferrous scrap', 'amount': 0.055776958, 'impacts': 0.04969304194120489}, {'material': 'lithium carbonate', 'amount': 0.001102228, 'impacts': 0.047136077001061594}], 3.5600909238509604),
    
    'lithium nickel-manganese-cobalt 811 battery waste pretreatment - input cutoff': ([{'material': 'nickel sulfate', 'amount': 0.13862575799999996, 'impacts': 2.416215040727233}, {'material': 'copper', 'amount': 0.05668642799999998, 'impacts': 0.8892282482223197}, {'material': 'cobalt sulfate', 'amount': 0.014852547999999997, 'impacts': 0.5177529831176567}, {'material': 'aluminum scrap', 'amount': 0.08871955799999999, 'impacts': 0.3865903666443291}, {'material': 'lithium carbonate', 'amount': 0.0018167809999999995, 'impacts': 0.037999289378017}, {'material': 'ferrous scrap', 'amount': 0.05577695799999999, 'impacts': 0.024304488355910592}], 4.272090416445466),
    
    'lithium nickel-manganese-cobalt 111 battery waste pretreatment - input cutoff': ([{'material': 'cobalt sulfate', 'amount': 0.05581311467198838, 'impacts': 1.6895665078412467}, {'material': 'nickel sulfate', 'amount': 0.06528687139804025, 'impacts': 0.9881773483179962}, {'material': 'copper', 'amount': 0.055976799836712894, 'impacts': 0.7625347026273271}, {'material': 'aluminum scrap', 'amount': 0.08488098135648157, 'impacts': 0.32118809372903656}, {'material': 'lithium carbonate', 'amount': 0.0020525234731219163, 'impacts': 0.03728021563167034}, {'material': 'ferrous scrap', 'amount': 0.05578485267235019, 'impacts': 0.021108887058619193}], 3.819855755205896),

    'lithium iron phosphate battery waste - input cutoff': ([{'material': 'copper', 'amount': 0.081905985, 'impacts': 5.331324968881209}, {'material': 'lithium carbonate', 'amount': 0.001715088, 'impacts': 0.1488485687295995}, {'material': 'ferrous scrap', 'amount': 0.079908595, 'impacts': 0.1444809245325317}], 5.624654462143341),

    'lithium nickel-manganese-cobalt 811 battery waste - input cutoff': ([{'material': 'nickel sulfate', 'amount': 0.16132496899999998, 'impacts': 3.268637116084463}, {'material': 'copper', 'amount': 0.05632707599999998, 'impacts': 1.0271286283569612}, {'material': 'cobalt sulfate', 'amount': 0.016788258999999996, 'impacts': 0.6803004745265319}, {'material': 'lithium carbonate', 'amount': 0.0027459599999999995, 'impacts': 0.06676372663886858}], 5.042829945606825),

    'lithium nickel-manganese-cobalt 111 battery waste - input cutoff': ([{'material': 'cobalt sulfate', 'amount': 0.063087157094472, 'impacts': 2.304986601596292}, {'material': 'nickel sulfate', 'amount': 0.07597724029904712, 'impacts': 1.3879728377466454}, {'material': 'copper', 'amount': 0.05562194661788536, 'impacts': 0.914505129508742}, {'material': 'lithium carbonate', 'amount': 0.0030706225545039136, 'impacts': 0.06731395903060357}], 4.674778527882283)
}



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
    'lithium iron phosphate battery waste - input cutoff': "LFP - no pt",
    'lithium nickel-manganese-cobalt 811 battery waste - input cutoff': "NMC811 - no pt",
    'lithium nickel-manganese-cobalt 111 battery waste - input cutoff': "NMC111 - no pt",
    'lithium iron phosphate battery waste pretreatment - input cutoff': "LFP - pt",
    'lithium nickel-manganese-cobalt 111 battery waste pretreatment - input cutoff': "NMC111 - pt",
    'lithium nickel-manganese-cobalt 811 battery waste pretreatment - input cutoff': "NMC811 - pt",
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

            if waste_input in names_map:
                battery_name = names_map[waste_input]

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
        desired_material_order = [
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
        desired_battery_order = [
            "LFP - no pt",
            "NMC111 - no pt",
            "NMC811 - no pt",
            "LFP - pt",
            "NMC111 - pt",
            "NMC811 - pt"
        ]

        # Ensure all present materials are included
        present_materials = [mat for mat in desired_material_order if mat in df['Material'].unique()]
        # Add any missing ones at the end
        present_materials += [mat for mat in df['Material'].unique() if mat not in present_materials]

        # Plot using plotly express
        title = "Global warming potential for 1kg of input material" if per_input else "GWP for 1kg of recovered mixed materials - allocated by price"
        fig = px.bar(df, 
                    x='Battery', 
                    y='Impact', 
                    color='Material',
                    color_discrete_map=color_discrete_map,
                    category_orders={
                        "Material": present_materials,
                        "Battery": desired_battery_order  # <-- control here
                    },
                    title=title,
                    labels={'Impact': 'GWP (kg CO₂ eq)'})

        fig.update_layout(barmode='stack', legend_title_text='Material')
        fig.show()



PlotHelper.plot_allocated_lcia_plotly(results, per_input=False)