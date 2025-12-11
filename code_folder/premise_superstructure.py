import os
from typing import Dict, List
import bw2data as bw
from premise import NewDatabase  # type: ignore
from code_folder.helpers.constants import (
    PROJECT_NAME,
    ECOINVENT_NAME,
    SUPERSTRUCTURE_NAME,
    SCENARIO_SPECS,
    SCENARIO_YEARS,
    Scenario,
)


def _derive_ecoinvent_version(db_name: str) -> str:
    # Best-effort extraction like "ecoinvent-3.12-cutoff" -> "3.12"
    try:
        parts = db_name.split("-")
        for p in parts:
            if p.replace(".", "").isdigit():
                return p
    except Exception:
        pass
    # Fallback; adjust if your EI version differs
    return "3.12"


def build_superstructure_db() -> None:

    ecoinvent_key = os.environ.get("PREMISE_ECOINVENT_KEY")
    if not ecoinvent_key:
        raise RuntimeError(
            "Environment variable PREMISE_ECOINVENT_KEY is not set. "
            "Set it to your ecoinvent decryption key and re-run."
        )

    bw.projects.set_current(PROJECT_NAME)

    source_db = ECOINVENT_NAME
    source_version = _derive_ecoinvent_version(ECOINVENT_NAME)

    scenarios: List[Dict[str, object]] = []
    for scenario, spec in SCENARIO_SPECS.items():
        if scenario not in {Scenario.BAU, Scenario.REC, Scenario.CIR}:
            continue
        for year in SCENARIO_YEARS:
            scenarios.append({"model": spec["model"], "pathway": spec["pathway"], "year": year})

    ndb = NewDatabase(
        scenarios=scenarios,
        source_db=source_db,
        source_version=source_version,
        key=ecoinvent_key,
        keep_source_db_uncertainty=False,
        keep_imports_uncertainty=False,
        use_absolute_efficiency=False,
    )

    # Update all sectors for a comprehensive superstructure
    ndb.update()

    # Single superstructure database with scenario-difference file
    super_name = SUPERSTRUCTURE_NAME
    ndb.write_superstructure_db_to_brightway(name=super_name)


if __name__ == "__main__":
    build_superstructure_db()
