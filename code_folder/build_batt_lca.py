import bw2data as bd
from helpers.lca_builder import LCABuilder
from helpers.constants import Chemistry, Route, Scenario, Location

PROJECT_NAME = "nonbrokenproject"
DATABASE_NAME = "batt_lci"

bd.projects.set_current(PROJECT_NAME)

# If a previous version of the database exists, remove it completely
if DATABASE_NAME in bd.databases:
    bd.Database(DATABASE_NAME).deregister()
db = bd.Database(DATABASE_NAME)


chemistry_selection = [Chemistry.battLiNMC111, Chemistry.battLiNMC811, Chemistry.battLiFP_subsub, Chemistry.BattNiCd, Chemistry.BattPb, Chemistry.BattZn, Chemistry.BattNiMH]
route_selection = [Route.PYRO_HYDRO, Route.HYDRO, Route.PYRO_HYDRO_PRETREATMENT, Route.BATT_LeadAcidSorted, Route.BATT_NiCdSorted, Route.BATT_NiMHSorted, Route.BATT_ZnAlkaliSorted]
year_selection = [2010,2015,2020,2025,2030,2035,2040,2045,2050]
scenario_selection = [Scenario.BAU, Scenario.REC, Scenario.CIR]
location_selection = [Location.EU27_4]
lcia_method = ('CML v4.8 2016', 'climate change', 'global warming potential (GWP100)')


lca_builder = LCABuilder()
lca_builder.build_all_lcis(
    database=db,
    chemistry_selection=chemistry_selection,
    route_selection=route_selection,
    year_selection=year_selection,
    scenario_selection=scenario_selection,
    location_selection=location_selection
)
lca_builder.save_lcis()
lca_builder.save_database_to_excel(database=db)


lca_builder.run_lcia(database=db, lcia_method=lcia_method)
print(lca_builder.lcia_results)
lca_builder.save_lcia_results()