import uuid
from typing import Optional
from code_folder.helpers.constants import ExternalDatabase
import bw2data as bd

class BrightwayHelpers:
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
    def build_external_exchange(
        database: ExternalDatabase,
        biosphere: bd.Database,
        ecoinvent: bd.Database,
        scrap: bd.Database,
        process_name: str,
        amount: float,
        unit: str,
        flow_direction: str,
        location: str,
        categories: tuple,
        reference_product: Optional[str] = None,
    ):
        """Create an exchange to an external database (ecoinvent/biosphere) with correct sign/type."""
        # Database can be ecoinvent or biosphere
        if database == ExternalDatabase.ECOINVENT:
            input = BrightwayHelpers.find_external_db_key_by_name(
                name=process_name,
                database=ecoinvent,
                location=location,
                reference_product=reference_product,
            )
        if database == ExternalDatabase.SCRAP:
            input = BrightwayHelpers.find_external_db_key_by_name(
                name=process_name,
                database=scrap,
                location=location,
                reference_product=reference_product,
            )
        if database == ExternalDatabase.BIOSPHERE:
            input = BrightwayHelpers.find_biosphere_key_by_name(name=process_name, biosphere=biosphere, categories=categories)
        return {
        "input": input,
        "name": process_name,
        "amount": amount * (1 if database in [ExternalDatabase.ECOINVENT,ExternalDatabase.SCRAP] else -1) * (1 if flow_direction == "input" else -1),
        "unit": unit,
        "type": "technosphere" if database in [ExternalDatabase.ECOINVENT,ExternalDatabase.SCRAP] else "biosphere",
        "location": location
    }

    @staticmethod
    def find_external_db_key_by_name(name, database: bd.Database, location, reference_product: Optional[str] = None):
        """Find (database_name, code) for an ecoinvent activity by exact name/location and optional reference product."""
        matches = [
            act for act in database
            if act["name"].strip() == name.strip() and act.get("location", "").strip() == location.strip()
        ]

        if not matches:
            raise ValueError(f"Process not found: {name} @ {location}")

        if len(matches)>1:
            print(f"Warning: Multiple processes found for {name} @ {location}. Using reference product ({reference_product}) to disambiguate.")
            filtered = [
                act for act in matches
                if str(act.get("reference product", "")).strip() == reference_product.strip()
            ]
            if filtered:
                matches = filtered
            else:
                available = ", ".join(sorted({str(act.get("reference product", "")) for act in matches}))
                raise ValueError(
                    f"Process not found: {name} @ {location} with reference product '{reference_product}'. "
                    f"Available reference products: {available}"
                )

        if len(matches) == 1:
            act = matches[0]
            return (database.name, act["code"])

        raise ValueError(
            f"Multiple processes found for {name} @ {location}. "
            "Provide a reference product to disambiguate."
        )
    
    @staticmethod
    def find_biosphere_key_by_name(name, biosphere: bd.Database, categories=("air", "urban air close to ground")):
        """Find (database_name, code) for a biosphere flow by exact name and categories."""
        for flow in biosphere:
            if flow["name"].strip() == name.strip() and tuple(flow["categories"]) == categories:
                # Use the actual database name for biosphere
                return (biosphere.name, flow["code"])
        raise ValueError(f"Biosphere flow not found: {name} @ {categories}")