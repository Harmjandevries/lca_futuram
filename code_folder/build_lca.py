"""Entry point to build LCIs/LCIA and export results using Brightway.

Configure selections below and run to (re)create the project database,
build LCIs, export to Excel, and compute LCIA.
"""
import os

# Workarounds for native library crashes on Windows (MKL/Numba/OpenMP)
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import bw2data as bd
from code_folder.helpers.lca_builder import LCABuilder
from code_folder.helpers.constants import Product, Route, Scenario, Location, PROJECT_NAME


def main():
    bd.projects.set_current(PROJECT_NAME)

    database_name = "batt"
    PRODUCT_SELECTION = [Product.battLiNMC111, Product.battLiCO_subsub, Product.battLiFP_subsub, Product.battLiNMC811,Product.battLiMO_subsub, Product.battLiNCA_subsub,Product.BattNiCd, Product.BattNiMH, Product.BattPb, Product.BattZn]
    ROUTE_SELECTION = [Route.BATT_EVInspectedReuse, Route.BATT_LeadAcidSorted, Route.BATT_ZnAlkaliSorted, Route.BATT_NiCdSorted, Route.BATT_NiMHSorted, Route.DIRECT, Route.PYRO_HYDRO, Route.HYDRO, Route.PYRO_HYDRO_PRETREATMENT]
    YEAR_SELECTION = [2010, 2015, 2020, 2025, 2030, 2035, 2040, 2045, 2050]
    SCENARIO_SELECTION = [Scenario.CIR, Scenario.OBS, Scenario.BAU, Scenario.REC]
    LOCATION_SELECTION = [Location.EU27_4]

    # If a previous version of the database exists, remove it completely
    if database_name in bd.databases:
        bd.Database(database_name).deregister()
    db = bd.Database(database_name)


    lcia_method = ('CML v4.8 2016', 'climate change', 'global warming potential (GWP100)')


    lca_builder = LCABuilder(database_name=database_name)
    lca_builder.build_all_lcis(
        product_selection=PRODUCT_SELECTION,
        route_selection=ROUTE_SELECTION,
        year_selection=YEAR_SELECTION,
        scenario_selection=SCENARIO_SELECTION,
        location_selection=LOCATION_SELECTION
    )
    lca_builder.save_lcis()
    lca_builder.save_database_to_excel()


    lca_builder.run_lcia(lcia_method=lcia_method)
    lca_builder.save_lcia_results()


if __name__ == "__main__":
    # Only executed when run as a script
    main()