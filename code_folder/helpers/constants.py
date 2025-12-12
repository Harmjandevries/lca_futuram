"""Shared constants, enums, data paths, and simple data classes used across the project."""

from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

PROJECT_NAME = "premise"
ECOINVENT_NAME = "ecoinvent-3.11-cutoff"
SUPERSTRUCTURE_NAME = "scenario_superstructure"
BIOSPHERE_NAME = "biosphere3"
SCRAP_DATABASE_NAME = "scrap"
SCENARIO_MAP  = {
    # Adjust mappings as needed
    "BAU": {"model": "image", "pathway": "SSP2-L"},            # or "SSP2-Base"
    "REC": {"model": "remind", "pathway": "SSP2-PkBudg1000"},
    "CIR": {"model": "remind", "pathway": "SSP2-PkBudg650"},
}
SCENARIO_DATABASE_YEARS = [2020, 2030, 2040, 2050]

class Route(Enum):
    PYRO_HYDRO = "BATT_LIBToPyro1"
    ELV = "ELV"
    PYRO_HYDRO_PRETREATMENT = "BATT_LIBToPyrolysis4"
    HYDRO = "Batt_LIBToPyrolysis2"
    DIRECT = "BATT_LIBToDirectRecycling"
    BATT_NiCdSorted = "BATT_NiCdSorted"
    BATT_LeadAcidSorted = "BATT_LeadAcidSorted"
    BATT_ZnAlkaliSorted = "BATT_ZnAlkaliSorted"
    BATT_EVInspectedReuse = "BATT_EVInspectedReuse"
    BATT_NiMHSorted = "BATT_NiMHSorted"
    BATT_2RM_dismantlingToSmelter = "BATT_2RM_dismantlingToSmelter"
    WEEE = "WEEE"


class Product(Enum):
    BattPb = "battPb"
    BattZn = "battZn"
    BattNiMH = "battNiMH"
    BattNiCd = "battNiCd"
    battLiNMC111 = "battLiNMC111"
    battLiCO_subsub = "battLiCO_subsub"
    battLiMO_subsub = "battLiMO_subsub"
    battLiNMC811 = "battLiNMC811"
    battLiFP_subsub = "battLiFP_subsub"
    battLiNCA_subsub = "battLiNCA_subsub"
    battPackXEV = "battPackXEV"	
    WEEE_Cat1 = "WEEE_Cat1"
    WEEE_Cat2 = "WEEE_Cat2"
    WEEE_Cat3 = "WEEE_Cat3"
    WEEE_Cat4a = "WEEE_Cat4a"
    WEEE_Cat4b = "WEEE_Cat4b"
    WEEE_Cat4c = "WEEE_Cat4c"
    WEEE_Cat5 = "WEEE_Cat5"
    WEEE_Cat6 = "WEEE_Cat6"
    elvBEV = "elvBEV"
    elvDiesel = "elvDiesel"
    elvHEV = "elvHEV"
    elvLPG = "elvLPG"
    elvNG = "elvNG"
    elvOther = "elvOther" 
    elvPetrol = "elvPetrol"


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FOLDER = PROJECT_ROOT / "data"
SCRAP_PROCESSES_FILE = PROJECT_ROOT / "data" / "input_data" / "scrap_processes.xlsx"

SUPPORTED_YEARS_OBS = range(2010, 2025)
SUPPORTED_YEARS_SCENARIO = range(2025, 2051)
INPUT_DATA_FOLDER = DATA_FOLDER / "input_data"
LOADABLE_LCI_DATA_FOLDER = DATA_FOLDER / "output_data/loadable_lcis"
LOADABLE_LCIA_RESULTS_DATA_FOLDER = DATA_FOLDER / "output_data/loadable_lcia_results"
BW_FORMAT_LCIS_DATA_FOLDER = DATA_FOLDER / "output_data/bw_format_lcis"
LCIA_RESULTS_EXCEL_FOLDER = DATA_FOLDER / "output_data/lcia_results_excel"

LCIA_METHODS = [
    ('EF v3.0', 'climate change', 'global warming potential (GWP100)'),
    ('EF v3.0', 'ozone depletion', 'ozone depletion potential (ODP)'),
    ('EF v3.0', 'human toxicity: carcinogenic', 'comparative toxic unit for human (CTUh)'),
    ('EF v3.0', 'human toxicity: non-carcinogenic', 'comparative toxic unit for human (CTUh)'),
    ('EF v3.0', 'particulate matter formation', 'impact on human health'),
    ('EF v3.0', 'ionising radiation: human health', 'human exposure efficiency relative to u235'),
    ('EF v3.0', 'photochemical oxidant formation: human health', 'tropospheric ozone concentration increase'),
    ('EF v3.0', 'acidification', 'accumulated exceedance (AE)'),
    ('EF v3.0', 'eutrophication: terrestrial', 'accumulated exceedance (AE)'),
    ('EF v3.0', 'eutrophication: freshwater', 'fraction of nutrients reaching freshwater end compartment (P)'),
    ('EF v3.0', 'eutrophication: marine', 'fraction of nutrients reaching marine end compartment (N)'),
    ('EF v3.0', 'ecotoxicity: freshwater', 'comparative toxic unit for ecosystems (CTUe)'),
    ('EF v3.0', 'land use', 'soil quality index'),
    ('EF v3.0', 'water use', 'user deprivation potential (deprivation-weighted water consumption)'),
    ('EF v3.0', 'energy resources: non-renewable', 'abiotic depletion potential (ADP): fossil fuels'),
    ('EF v3.0', 'material resources: metals/minerals', 'abiotic depletion potential (ADP): elements (ultimate reserves)')
]

class ExternalDatabase(Enum):
    ECOINVENT="ECOINVENT"
    BIOSPHERE="BIOSPHERE"
    SCRAP="SCRAP"

class Scenario(Enum):
    OBS="OBS"
    BAU="BAU"
    REC="REC"
    CIR="CIR"

class Location(Enum):
    EU27_4="EU27+4"



route_lci_names = {
    Route.PYRO_HYDRO: "Pyrometallurgical+Hydrometallurgical recycling of ",
    Route.BATT_LeadAcidSorted: "Pyrometallurgical recycling of ",
    Route.PYRO_HYDRO_PRETREATMENT: "Pretreatment+Pyrometallurgical+Hydrometallurgical recycling of ",
    Route.BATT_NiMHSorted: "Recycling of",
    Route.BATT_NiCdSorted: "Recycling of",
    Route.BATT_ZnAlkaliSorted: "Recycling of",
    Route.BATT_EVInspectedReuse: "Refurbishment of ",
    Route.HYDRO: "Hydrometallurgical recycling of",
    Route.WEEE: "Dismantling and shredding of ",
    Route.DIRECT: "Direct recycling of ",
    Route.ELV: "Dismantling and shredding of ",
    Route.BATT_2RM_dismantlingToSmelter: "Dismantling and shredding of "
}

@dataclass
class SingleLCI:
    """Class that holds all information for an LCI"""
    route: Route
    product:Product
    scenario: Scenario
    location: Location
    year:int
    
    lci_dict: dict # lci for the impacts of the recycling process
    main_activity_flow_name: str # name of the recycled material inflow to the lci_dict
    avoided_impacts_flow_name: str # LCI name of the avoided impacts activity
    total_inflow_amount: int #total amount of recycled material, (we need to multiply the impacts with this, to get total impact)

@dataclass
class SingleLCIAResult:
    """Class that holds all information for an LCIA"""
    total_impacts: Dict[str, float] # impact of 1kg of recycling
    avoided_impacts: Dict[str, float]
    lci: SingleLCI
    # impact_per_element: dict