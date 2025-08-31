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
PRICES_FILE = DATA_FOLDER / "prices/prices.json"
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
    


class Chemistry(Enum):
    BattPb="battPb"
    BattZn="battZn"
    BattNiMH="battNiMH"
    BattNiCd="battNiCd"
    battLiNMC111="battLiNMC111"
    battLiNMC811="battLiNMC811"
    battLiFP_subsub="battLiFP_subsub"

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
    chemistry:Chemistry
    scenario: Scenario
    location: Location
    year:int
    
    lci_dict: dict
    main_activity_flow_name: str
    total_inflow_amount: int
    output_amounts_alloy: dict
    output_amounts_element: dict

@dataclass
class SingleLCIAResult:
    """Class that holds all information for an LCIA"""
    total_impact: int # impact of 1kg of recycling
    impact_per_alloy: dict
    lci: SingleLCI
    # impact_per_element: dict