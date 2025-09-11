from enum import Enum
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FOLDER = PROJECT_ROOT / "data"

SUPPORTED_YEARS_OBS = range(2010, 2025)
SUPPORTED_YEARS_SCENARIO = range(2025, 2051)
INPUT_DATA_FOLDER = DATA_FOLDER / "input_data"
LOADABLE_LCI_DATA_FOLDER = DATA_FOLDER / "output_data/loadable_lcis"
LOADABLE_LCIA_RESULTS_DATA_FOLDER = DATA_FOLDER / "output_data/loadable_lcia_results"
BW_FORMAT_LCIS_DATA_FOLDER = DATA_FOLDER / "output_data/bw_format_lcis"
ECOINVENT_NAME = "ecoinvent"
BIOSPHERE_NAME = "biosphere"


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

class Route(Enum):
    PYRO_HYDRO="BATT_LIBToPyro1"
    PYRO_HYDRO_PRETREATMENT = "BATT_LIBToPyrolysis4"
    HYDRO = "Batt_LIBToPyrolysis2"
    BATT_NiCdSorted="BATT_NiCdSorted"
    BATT_LeadAcidSorted="BATT_LeadAcidSorted"
    BATT_ZnAlkaliSorted="BATT_ZnAlkaliSorted"
    BATT_NiMHSorted="BATT_NiMHSorted"
    


class Product(Enum):
    BattPb="battPb"
    BattZn="battZn"
    BattNiMH="battNiMH"
    BattNiCd="battNiCd"
    battLiNMC111="battLiNMC111"
    battLiNMC811="battLiNMC811"
    battLiFP_subsub="battLiFP_subsub"
    battLiNCA_subsub="battLiNCA_subsub"


route_lci_names = {
    Route.PYRO_HYDRO: "Pyrometallurgical+Hydrometallurgical recycling of ",
    Route.BATT_LeadAcidSorted: "Pyrometallurgical recycling of ",
    Route.PYRO_HYDRO_PRETREATMENT: "Pretreatment+Pyrometallurgical+Hydrometallurgical recycling of ",
    Route.BATT_NiMHSorted: "Recycling of",
    Route.BATT_NiCdSorted: "Recycling of",
    Route.BATT_ZnAlkaliSorted: "Recycling of",
    Route.HYDRO: "Hydrometallurgical recycling of"
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
    avoided_impacts_flow_name: str # LCI name of the recovered materials process
    total_inflow_amount: int #total amount of recycled material, (we need to multiply the impacts with this, to get total impact)
    output_amounts_alloy: dict # amount of each alloy
    output_amounts_element: dict # amount of each element

@dataclass
class SingleLCIAResult:
    """Class that holds all information for an LCIA"""
    total_impact: float # impact of 1kg of recycling
    avoided_impact: float
    lci: SingleLCI
    # impact_per_element: dict