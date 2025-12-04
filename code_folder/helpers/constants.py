"""Shared constants, enums, data paths, and simple data classes used across the project."""

from enum import Enum
from dataclasses import dataclass
from pathlib import Path

PROJECT_NAME = "premise"
ECOINVENT_NAME = "ecoinvent-3.11-cutoff"
SUPERSTRUCTURE_NAME = "scenario_superstructure"
BIOSPHERE_NAME = "biosphere3"

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



class ExternalDatabase(Enum):
    ECOINVENT="ECOINVENT"
    BIOSPHERE="BIOSPHERE"

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
    total_impact: float # impact of 1kg of recycling
    avoided_impact: float
    lci: SingleLCI
    # impact_per_element: dict