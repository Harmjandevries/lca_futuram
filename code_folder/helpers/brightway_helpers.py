import uuid
from collections import OrderedDict
from typing import Optional
from code_folder.helpers.constants import ExternalDatabase
import bw2data as bd

class BrightwayHelpers:
    _ecoinvent_cache = OrderedDict()
    _biosphere_cache = OrderedDict()

    @staticmethod
    def build_base_process(name: str, database_name: str, is_waste: Optional[bool] = False):
        """Create a minimal Brightway process with a production exchange.

        Returns (process_id, process_dict_fragment) suitable for Database.write.
        """
        process_id = str(uuid.uuid4())
        return process_id, {
            (database_name, process_id): {
                "name": name,
                "unit": "kilogram",
                "location": "RER",
                "reference product": name,
                "exchanges": [
                    {
                        "input": (database_name, process_id),
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
        cache_key = (name.strip(), location.strip())
        if cache_key in BrightwayHelpers._ecoinvent_cache:
            BrightwayHelpers._ecoinvent_cache.move_to_end(cache_key)
            return BrightwayHelpers._ecoinvent_cache[cache_key]
        for act in ecoinvent:
            if act["name"].strip() == name.strip() and act.get("location", "").strip() == location.strip():
                # Use the actual database name and a 2-tuple key as required by Brightway
                BrightwayHelpers._ecoinvent_cache[cache_key] = (ecoinvent.name, act["code"])
                BrightwayHelpers._ecoinvent_cache.move_to_end(cache_key)
                if len(BrightwayHelpers._ecoinvent_cache) > 50:
                    BrightwayHelpers._ecoinvent_cache.popitem(last=False)
                return BrightwayHelpers._ecoinvent_cache[cache_key]
        raise ValueError(f"Process not found: {name} @ {location}")

    @staticmethod
    def find_biosphere_key_by_name(name, biosphere: bd.Database, categories=("air", "urban air close to ground")):
        """Find (database_name, code) for a biosphere flow by exact name and categories."""
        cache_key = (name.strip(), tuple(categories))
        if cache_key in BrightwayHelpers._biosphere_cache:
            BrightwayHelpers._biosphere_cache.move_to_end(cache_key)
            return BrightwayHelpers._biosphere_cache[cache_key]
        for flow in biosphere:
            if flow["name"].strip() == name.strip() and tuple(flow["categories"]) == categories:
                # Use the actual database name for biosphere
                BrightwayHelpers._biosphere_cache[cache_key] = (biosphere.name, flow["code"])
                BrightwayHelpers._biosphere_cache.move_to_end(cache_key)
                if len(BrightwayHelpers._biosphere_cache) > 50:
                    BrightwayHelpers._biosphere_cache.popitem(last=False)
                return BrightwayHelpers._biosphere_cache[cache_key]
        raise ValueError(f"Biosphere flow not found: {name} @ {categories}")
