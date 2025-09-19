# Battery Recycling LCA

This repository builds life cycle inventories (LCIs) and runs impact assessment using the FutuRaM-format MFA data as input, together with manually collected LCA data.

## Requirements

- Python 3.10+
- `brightway2` (`bw2data`, `bw2calc`)
- `pandas`

## Preparing input data

Three steps are required for preparing the lca: defining parameters, creating an MFA file, and creating the LCA file.

All data are read from the `data` directory in the project root. The folder structure is:

```
data/
├─ input_data/
│  ├─ <route>/
│  │  ├─ rm_output.csv
│  │  └─ lci_builder.xlsx
```

### MFA data input
The MFA data is created in the FutuRaM format from the recovery model, see the recovery model github for information on how to obtain these files. The file _rm_output.csv_ is simply the output of the recovery model as-is. To make the code faster, you can pre-emptively make a selection of only the relevant flows you wish to analyse. Required columns are Year, Scenario, Stock/Flow ID, Layer 1-4 and Value.

### LCA data input
lci_builder.xlsx defines how the Life Cycle Inventory will be constructed from the recovery model. Every row represents an LCI exchange. Exchanges can be read from the recovery model, or defined independently if the recovery model does not provide information (such as for electricity). There are 5 possible ways to define a row:
1. The production exchange: This is the input of products to the recycling system and has 'LCI Flow Type' column set to 'production'. It is the input amount for the recovery model, which the code will read and scale to 1 for the LCI.
2. The recovered materials: This is the set of materials or elements that are recovered by recycling and substituted with new materials. The the 'LCI Flow Type'  column is set to 'recovered'. The code will read the recovered amount for each year/scenario from the recovery model and scale the recovered output in the LCI accordingly.
3. Technosphere exchanges: This has the 'LCI Flow Type' column set to ' technosphere'. These can be:
   1. read from the recovery model. In this case the recovery model flow needs to be defined.
   2. predefined per kg of input material, in this case the amount per kg of input is set in the 'Amount' column. 
4. Biosphere exchanges: This has the 'LCI Flow Type' set to 'biosphere'. The amount is defined per kg of input material.

For all rows, either of the following is defined:
- If the amount needs to be read from the recovery model, `Stock/Flow IDs`, `Materials` and `Layer` need to be defined.
- If the amount is defined from external sources, `Amount` and `Scaled by flows` needs to be defined, and above columns are empty.

Columns:
- `Stock/Flow IDs` – Stock/Flow ID to be read (for 1, 2, 3i)
- `Materials` – Selection of materials to be read from the RM
- `Layer` – Layer to read the materials from in the RM, for example 3 for materials, 4 for elements
- `Linked process` – ecoinvent/biosphere process to link to this exchange (for 3/4). Put the name of the database in front of the semicolon and the exchange after.
- `Categories` – category, for biosphere exchanges only
- `Region` – ecoinvent/biosphere region, for 2-4 only 
- `LCI Flow Name` – desired name for this flow in the LCI
- `Flow Direction` – direction of the flow in the recycling system (e.g. input for the product waste, electricity, reagents, output for emissions, slag)
- `LCI Flow Type` – see section above
- `Amount` – amount per kg of input product, only defined if not present in recovery model (3ii, 4)
- `Unit` – unit for the ecoinvent/biosphere exchange
- `Scaled by flows` - for flows where we know the amount from an external source, we know the amount _per_ amount of a different flow. For example, we know the electricity use per amount of input material, or we know the amount of produced slag per nickel output. This column contains the Stock/Flow ID that the column needs to be scaled by.
- `Recovery efficiency` - for recovered materials, defines how well recovered materials replace the market product. For example, if recovered nickel sulfate replaces new nickel sulfate at a 80% efficiency on the market, the recovery efficiency 0.8. Default value is 1.


### Defining parameters

In the file _constants.py_ the following things need to be defined:
- **PROJECT_NAME**: name of the brightway project
- **DATABASE_NAME**: name of the brightway database
- **Route**: defines all the possible recycling routes. Values need to match the Stock/Flow ID from the input data.
- **Product**: defines all the possible products that are tracked through the recycling system. Matches with the 'Layer 1' values from the input data.


## Running the model

1. Import the required external databases (ecoinvent and biosphere) into a Brightway project.
2. Define the constants and inputs file
3. Run the build_all_lcis() method
4. Run the run_lcia() method