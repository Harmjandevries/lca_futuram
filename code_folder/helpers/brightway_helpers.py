import uuid
from collections import OrderedDict
from typing import Optional
from code_folder.helpers.constants import (
    ExternalDatabase,
    Scenario,
    SCENARIO_DATABASE_YEARS,
    SCRAP_DATABASE_NAME,
)
import bw2data as bd

class BrightwayHelpers:
    _ecoinvent_cache: OrderedDict = OrderedDict()
    _biosphere_cache: OrderedDict = OrderedDict()

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
        cache_key = (database.name, name.strip(), location.strip(), reference_product.strip() if reference_product else None)
        if cache_key in BrightwayHelpers._ecoinvent_cache:
            BrightwayHelpers._ecoinvent_cache.move_to_end(cache_key)
            return BrightwayHelpers._ecoinvent_cache[cache_key]

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
            result = (database.name, act["code"])
            BrightwayHelpers._ecoinvent_cache[cache_key] = result
            if len(BrightwayHelpers._ecoinvent_cache) > 150:
                BrightwayHelpers._ecoinvent_cache.popitem(last=False)
            return result

        raise ValueError(
            f"Multiple processes found for {name} @ {location}. "
            "Provide a reference product to disambiguate."
        )
    
    @staticmethod
    def find_biosphere_key_by_name(name, biosphere: bd.Database, categories=("air", "urban air close to ground")):
        """Find (database_name, code) for a biosphere flow by exact name and categories."""
        cache_key = (biosphere.name, name.strip(), tuple(categories))
        if cache_key in BrightwayHelpers._biosphere_cache:
            BrightwayHelpers._biosphere_cache.move_to_end(cache_key)
            return BrightwayHelpers._biosphere_cache[cache_key]

        for flow in biosphere:
            if flow["name"].strip() == name.strip() and tuple(flow["categories"]) == categories:
                # Use the actual database name for biosphere
                result = (biosphere.name, flow["code"])
                BrightwayHelpers._biosphere_cache[cache_key] = result
                if len(BrightwayHelpers._biosphere_cache) > 50:
                    BrightwayHelpers._biosphere_cache.popitem(last=False)
                return result
        raise ValueError(f"Biosphere flow not found: {name} @ {categories}")

    def resolve_scenario_db_name(
    scenario: Scenario,
    year: int,
) -> str:
        """Map a scenario/year to the closest available scenario database name.

        Scenario OBS is mapped to the BAU series. The year is rounded to the
        nearest value in ``available_years`` (ties resolved toward the earlier
        year).
        """

        scenario_name = Scenario.BAU.value if scenario == Scenario.OBS else scenario.value
        closest_year = min(SCENARIO_DATABASE_YEARS, key=lambda candidate: (abs(candidate - year), candidate))
        return f"{scenario_name}_{closest_year}"

    @staticmethod
    def resolve_scrap_db_name(
        scenario: Scenario,
        year: int,
    ) -> str:
        """Return the scrap DB name for a scenario/year combo."""
        scenario_name = Scenario.BAU.value if scenario == Scenario.OBS else scenario.value
        closest_year = min(SCENARIO_DATABASE_YEARS, key=lambda candidate: (abs(candidate - year), candidate))
        return f"{SCRAP_DATABASE_NAME}_{scenario_name}_{year}"
