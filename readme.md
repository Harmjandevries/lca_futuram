# FutuRaM MFA-LCA integration

This repository builds life cycle inventories (LCIs) and runs life cycle impact assessment (LCIA) from FutuRaM-format material flow analysis (MFA) outputs and manually prepared LCA mapping sheets.

The repository contains the reusable Python code only. Input data, generated outputs, local Brightway databases, visualization code, and private Excel/CSV artifacts are intentionally excluded.

## What is included

- LCI construction from recovery model outputs.
- Brightway process and exchange helpers.
- LCIA execution helpers.
- Storage/export helpers for generated LCIs and LCIA results.
- Scenario, route, product, and method constants used by the model.

## What is not included

- FutuRaM recovery model output files.
- `lci_builder.xlsx` input workbooks.
- ecoinvent, biosphere, premise, PSILCA, or other licensed databases.
- Generated CSV, Excel, pickle, or Brightway export outputs.
- Visualization and one-off analysis scripts.

## Requirements

- Python 3.10+
- `pandas`
- Brightway packages used by your environment, including `bw2data`, `bw2calc`, and `bw2io`
- Optional: `premise`, if using `lca_futuram/premise_superstructure.py`

Brightway and ecoinvent setup is environment-specific and is not handled by this repository. The required databases must already exist in your local Brightway project before building LCIs.

## Repository structure

```text
lca_futuram/
  helpers/
    brightway_helpers.py
    constants.py
    lca_builder.py
    storage_helper.py
  premise_superstructure.py
readme.md
setup.py
pyproject.toml
```

## Expected private data layout

Input data is expected under `data/input_data/` in the project root. This folder is ignored by Git.

```text
data/
  input_data/
    shared_rm_output.csv
    scrap_processes.xlsx
    <route>/
      rm_output.csv
      lci_builder.xlsx
  output_data/
    loadable_lcis/
    loadable_lcia_results/
    bw_format_lcis/
    lcia_results_excel/
```

The route folder names must match the values in `Route` from `lca_futuram.helpers.constants`.

## MFA input

The MFA input is normally the FutuRaM recovery model output. The model expects columns including:

- `Year`
- `Scenario`
- `Stock/Flow ID`
- `Layer 1`
- `Layer 2`
- `Layer 3`
- `Layer 4`
- `Value`

The builder can read either a per-route `rm_output.csv` or a shared `data/input_data/shared_rm_output.csv`, depending on the `use_shared_rm_output` option.

## LCA builder workbook

Each route uses an `lci_builder.xlsx` workbook. Each product is represented by a sheet whose name matches a `Product` enum value.

Important columns include:

- `Stock/Flow IDs`
- `Materials`
- `Layer`
- `Linked process`
- `Categories`
- `Region`
- `LCI Flow Name`
- `Flow Direction`
- `LCI Flow Type`
- `Amount`
- `Unit`
- `Scaled by flows`
- `Recovery efficiency`

The main flow types are:

- `production`: the waste/product input to the recycling system.
- `recovered`: recovered materials that substitute background production.
- `technosphere`: external process inputs or outputs.
- `biosphere`: emissions and resource flows.

Rows can either read amounts from the recovery model using stock/flow IDs and material filters, or use fixed amounts from the `Amount` column.

## Basic usage

```python
import bw2data as bd

from lca_futuram.helpers.constants import (
    GWP_PREMISE_ONLY,
    Location,
    Product,
    PROJECT_NAME,
    Route,
    Scenario,
)
from lca_futuram.helpers.lca_builder import LCABuilder

bd.projects.set_current(PROJECT_NAME)

builder = LCABuilder(database_name="my_lca_database")
builder.build_all_lcis(
    route_selection=[Route.PYRO_HYDRO],
    product_selection=[Product.battLiNMC811],
    year_selection=[2030],
    scenario_selection=[Scenario.BAU],
    location_selection=[Location.EU27_4],
    add_scrap=False,
)

builder.run_lcia(GWP_PREMISE_ONLY)
builder.export_lcia_results_to_excel(GWP_PREMISE_ONLY)
```

## Premise superstructure

`lca_futuram/premise_superstructure.py` can create scenario databases and a superstructure database using premise. It requires:

- a configured Brightway project
- a valid source ecoinvent database
- `PREMISE_ECOINVENT_KEY` set in the environment

This step is optional and depends on your local database licenses and setup.

## Configuration note

Some environment-specific defaults, such as Brightway project names and database names, currently live in `lca_futuram.helpers.constants`. For a more reusable public package, the next improvement should be moving these values into an explicit configuration object while keeping the existing defaults for local use.

## Git hygiene

The `.gitignore` excludes private data, generated results, local setup files, and visualization/analysis artifacts. Do not commit raw input data, generated Excel outputs, or licensed database exports.
