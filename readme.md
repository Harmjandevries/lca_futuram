# Battery Recycling LCA

This repository builds life cycle inventories (LCIs) and runs impact assessment using the FutuRaM-format MFA data as input, together with manually collected LCA data.

## Requirements

- Python 3.10+
- `brightway2` (`bw2data`, `bw2calc`)
- `pandas`

## Preparing input data

Three steps are required for preparing the lca: defining the database name, defining recycling routes and products, and adding data.

The database and project name in brightway can simply be set in constants.py under the PROJECT_NAME and DATABASE_NAME variables.

### Defining routes and products

In the constants.py file, define the 'Route' and 'Product' parameters. The values for these need to coincide with respectively the 'Layer 1' and the 'Stock/Flow ID' for the input flow that you want to consider.

### Input data
All data are read from the `data` directory in the project root. The folder structure is:

```
data/
├─ input_data/
│  ├─ <route>/
│  │  ├─ rm_output.csv
│  │  └─ lci_builder.xlsx
```

rm_output.csv is simply the output of the recovery model as-is. To make the code faster, you can pre-emptively make a selection of only the relevant flows you wish to analyse. Required columns are Year, Scenario, Stock/Flow ID, Layer 1-4 and Value.

lci_builder.xlsx defines how the Life Cycle Inventory will be constructed from the recovery model. Every row represents an LCI exchange. Exchanges can be read from the recovery model, or defined independently if the recovery model does not provide information (such as for electricity). There are 5 possible ways to define a row:
1. Input product flow: This has 'LCI Flow Type' column set to 'production'. It is the input amount for the recovery model, which the code will read and scale to 1 for the LCI.
2. Recovered outputs: This has the 'LCI Flow Type'  column set to 'recovered'. The code will read the recovered amount for each year/scenario from the recovery model and scale the recovered output in the LCI accordingly.
3. Technosphere exchanges: This has the 'LCI Flow Type' column set to ' technosphere'. These can be:
   1. read from the recovery model. In this case the recovery model flow needs to be defined.
   2. predefined per kg of input material, in this case the amount per kg of input is set in the 'Amount' column. 
4. Biosphere exchanges: This has the 'LCI Flow Type' set to 'biosphere'. The amount is defined per kg of input material.

Columns:
- `Stock/Flow IDs` – Stock/Flow ID to be read (for 1, 2, 3i)
- `Materials` – Selection of materials to be read from the RM
- `Layer` – Layer to read the materials from in the RM, for example 3 for materials, 4 for elements
- `Linked process` – ecoinvent/biosphere process to link to this exchange (for 3/4). Put the name of the database in front of the semicolon and the exchange after.
- `Categories` – category, for biosphere exchanges only
- `Region` – ecoinvent/biosphere region, for 3/4 only 
- `LCI Flow Name` – desired name for this flow in the LCI
- `Flow Direction` – direction of the flow in the recycling system (e.g. input for the product waste, electricity, reagents, output for emissions, slag)
- `LCI Flow Type` – see section above
- `Amount` – amount per kg of input product, only defined if not present in recovery model (3ii, 4)
- `Unit` – unit for the ecoinvent/biosphere exchange
- `Scaled by flows` - edge case for batteries, not relevant
- `Recovery efficiency` - for recovered materials, defines how well recovered materials replace the market product. For example, if recovered nickel sulfate replaces new nickel sulfate at a 80% efficiency on the market, put 0.8.

## Running the model

1. Import the required external databases (ecoinvent and biosphere) into a Brightway project.
2. Define the constants and inputs file
3. Run the build_all_lcis() method
4. Run the run_lcia() method