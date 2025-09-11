# Battery Recycling LCA

This repository builds life cycle inventories (LCIs) and runs impact assessment using the FutuRaM-format MFA data as input, together with manually collected LCA data.

## Requirements

- Python 3.10+
- `brightway2` (`bw2data`, `bw2calc`)
- `pandas`

## Preparing input data

Two steps are required for preparing the input data:

### Defining routes and products

In the constants.py file, define the recycling 
All data are read from the `data` directory in the project root. The folder structure is:

```
data/
├─ input_data/
│  ├─ <route>/
│  │  ├─ rm_output.csv
│  │  └─ lci_builder.xlsx
└─ prices/prices.json
```

### Routes and products

Route folders must be named after the values in `helpers/constants.py`. Examples include `BATT_LIBToPyro1`, `Batt_LIBToPyrolysis2`, `BATT_LeadAcidSorted` and others. Each Excel workbook requires one sheet per product. Valid product sheet names are: `battLiNMC111`, `battLiNMC811`, `battLiFP_subsub`, `battLiNCA_subsub`, `battPb`, `battZn`, `battNiMH`, and `battNiCd`.

### `rm_output.csv`

Comma‑separated table used to scale flows. Required columns:

- `Year` – integer year of the scenario.
- `Scenario` – one of `OBS`, `BAU`, `REC`, or `CIR`.
- `Stock/Flow ID` – identifiers matching the Excel file.
- `Layer 1` .. `Layer 4` – hierarchical material labels.
- `Value` – numeric amount of the flow.

Additional `Layer` columns can be present and are referenced in the Excel file.

### `lci_builder.xlsx`

Workbook containing the LCI definition. Each sheet corresponds to a product and must include the following columns:

- `LCI Flow Type` – `production` for the main activity or blank for others.
- `LCI Flow Name` – name of the activity or exchange.
- `Stock/Flow IDs` – comma separated list of IDs appearing in `rm_output.csv`.
- `Materials` – comma separated list linked to the chosen `Layer`.
- `Layer` – number of the layer column in `rm_output.csv` used for scaling.
- `Flow Direction` – `input`, `output`, or `recovered`.
- `Linked process` – external process in the format `DATABASE:process name` (e.g. `ECOINVENT:market for copper`).
- `Region` – region code such as `RER`.
- `Unit` – measurement unit.
- `Categories` – comma separated Brightway categories.
- Optional: `Scaled by flows`, `Amount`, `Element to compound ratio`.

At least one row must have `LCI Flow Type` set to `production` to define the main activity. Rows with `Flow Direction` set to `recovered` describe recovered materials and generate avoided impact exchanges.

## Running the model

1. Import the required external databases (ecoinvent and biosphere) into a Brightway project.
2. Place input files and `prices/prices.json` as described above.
3. Execute the builder script:

```bash
python code_folder/build_batt_lca.py
```

The script creates a new Brightway database, constructs LCIs for all scenarios, runs a climate‑change LCIA, and saves the results under `data/output_data`.