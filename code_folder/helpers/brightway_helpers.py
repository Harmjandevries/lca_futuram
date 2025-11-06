from typing import Optional, List
from .constants import SingleLCI
import uuid
from .constants import ExternalDatabase, DATABASE_NAME
import bw2data as bd

class BrightwayHelpers:
    @staticmethod
    def get_existing_process_id_by_name(lcis: List[SingleLCI], name: str) -> Optional[str]:
        """Return process UUID if a process with given name exists in any LCI, else None."""
        normalized_name = name.strip().lower()

        for lci in lcis:
            for (db_name, process_id), process_data in lci.lci_dict.items():
                if process_data["name"].strip().lower() == normalized_name:
                    return process_id  # This is the UUID you want
        return None
    
    @staticmethod
    def build_technosphere_exchange(name: str, process_id: str, amount: float):
        """Create a technosphere exchange pointing to a process in our database."""
        return {
            "input": (DATABASE_NAME, process_id),
            "name": name,
            "amount": amount,
            "unit": "kilogram",
            "type": "technosphere",
            "location": "RER"
        }
    
    @staticmethod
    def build_base_process(name: str, is_waste: Optional[bool] = False):
        """Create a minimal Brightway process with a production exchange.

        Returns (process_id, process_dict_fragment) suitable for Database.write.
        """
        process_id = str(uuid.uuid4())
        return process_id, {
            (DATABASE_NAME, process_id): {
                "name": name,
                "unit": "kilogram",
                "location": "RER",
                "reference product": name,
                "exchanges": [
                    {
                        "input": (DATABASE_NAME, process_id),
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
        """Create an exchange to an external database (ecoinvent/biosphere) with correct sign/type."""
        # Database can be ecoinvent or biosphere
        if database==ExternalDatabase.ECOINVENT:
            input = BrightwayHelpers.find_ecoinvent_key_by_name(name=process_name, ecoinvent=ecoinvent, location=location)
        if database==ExternalDatabase.BIOSPHERE:
            input = BrightwayHelpers.find_biosphere_key_by_name(name=process_name, biosphere=biosphere, categories=categories)
        return {
        "input": input,
        "name": process_name,
        "amount": amount * (1 if database==ExternalDatabase.ECOINVENT else -1) * (1 if flow_direction=='input' else -1),
        "unit": unit,
        "type": "technosphere" if database==ExternalDatabase.ECOINVENT else "biosphere",
        "location": location
    }

    @staticmethod
    def find_ecoinvent_key_by_name(name, ecoinvent: bd.Database, location):
        """Find (database_name, code) for an ecoinvent activity by exact name and location."""
        for act in ecoinvent:
            if act["name"].strip() == name.strip() and act.get("location", "").strip() == location.strip():
                # Use the actual database name and a 2-tuple key as required by Brightway
                return (ecoinvent.name, act["code"])
        raise ValueError(f"Process not found: {name} @ {location}")
    
    @staticmethod
    def find_biosphere_key_by_name(name, biosphere: bd.Database, categories=("air", "urban air close to ground")):
        """Find (database_name, code) for a biosphere flow by exact name and categories."""
        for flow in biosphere:
            if flow["name"] == name and tuple(flow["categories"]) == categories:
                # Use the actual database name for biosphere
                return (biosphere.name, flow["code"])
        raise ValueError(f"Biosphere flow not found: {name} @ {categories}")