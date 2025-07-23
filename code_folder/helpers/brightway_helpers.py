from typing import Optional, List
from helpers.constants import SingleLCI
import uuid
from helpers.constants import ExternalDatabase
import bw2data as bd

class BrightwayHelpers:
    @staticmethod
    def get_existing_process_id_by_name(lcis: List[SingleLCI], name: str) -> Optional[str]:
        """
        Checks if a process with the given name exists in any of the lci_dicts in lcis.
        Returns its process ID (code) if found, else None.
        """
        normalized_name = name.strip().lower()

        for lci in lcis:
            for (db_name, process_id), process_data in lci.lci_dict.items():
                if process_data["name"].strip().lower() == normalized_name:
                    return process_id  # This is the UUID you want
        return None
    
    @staticmethod
    def build_technosphere_exchange(name: str, process_id: str, amount: float):
        return {
            "input": ("batt_lci", process_id),
            "name": name,
            "amount": amount,
            "unit": "kilogram",
            "type": "technosphere",
            "location": "RER"
        }
    
    @staticmethod
    def build_base_process(name: str, is_waste: Optional[bool] = False):
        process_id = str(uuid.uuid4())
        return process_id, {
            ("batt_lci", process_id): {
                "name": name,
                "unit": "kilogram",
                "location": "RER",
                "reference product": name,
                "exchanges": [
                    {
                        "input": ("batt_lci", process_id),
                        "name": name,
                        "amount": 1 if not is_waste else -1,
                        "unit": "kilogram",
                        "type": "production",
                    },
                ],
            }
        }
    
    @staticmethod
    def build_external_exchange(database: ExternalDatabase, biosphere: bd.Database, ecoinvent: bd.Database, process_name: str, amount: float, unit: str, flow_direction:str, location: str, categories: tuple):
        # Database can be ecoinvent or biosphere
        if database==ExternalDatabase.ECOINVENT:
            input = BrightwayHelpers.get_ecoinvent_key_by_name(name=process_name, ecoinvent=ecoinvent, location=location)
        if database==ExternalDatabase.BIOSPHERE:
            input = BrightwayHelpers.get_biosphere_key_by_name(name=process_name, biosphere=biosphere, categories=categories)
        return {
        "input": input,
        "name": process_name,
        "amount": amount * (1 if database==ExternalDatabase.ECOINVENT else -1) * (1 if flow_direction=='input' else -1),
        "unit": unit,
        "type": "technosphere" if database==ExternalDatabase.ECOINVENT else "biosphere",
        "location": location
    }

    @staticmethod
    def get_ecoinvent_key_by_name(name, ecoinvent: bd.Database, location):
        for act in ecoinvent:
            if act["name"].strip() == name.strip() and act.get("location", "").strip() == location.strip():
                return ("ecoinvent", act["code"],location)
        raise ValueError(f"Process not found: {name} @ {location}")
    
    @staticmethod
    def get_biosphere_key_by_name(name, biosphere: bd.Database, categories=("air", "urban air close to ground")):
        for flow in biosphere:
            if flow["name"] == name and tuple(flow["categories"]) == categories:
                return ("biosphere", flow["code"])
        raise ValueError(f"Biosphere flow not found: {name} @ {categories}")