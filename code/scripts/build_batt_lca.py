import bw2data as bd
import bw2calc as bc
import bw2io as bi
import bw_functional
from pathlib import Path
from helpers.rm_output_reader import RMOutputToLCA
from helpers.lca_builder import LCIA_allocator

# Set project
bd.projects.set_current("futuram")

# If a previous version of the database exists, remove it completely
if "batt_lci" in bd.databases:
    bd.Database("batt_lci").deregister()

db = bd.Database("batt_lci")

rm_reader = RMOutputToLCA("batt_lci",
    rm_path="data/recovery_model_outputs/25_04_batt_2025_CIR/BATT_RM_cmp_version6.csv",
    activities_path="data/recovery_model_outputs/25_04_batt_2025_CIR/NiMH_activities.json",
)

db.write(rm_reader.lca_dict)


result = LCIA_allocator().run_lca(
    database=db,
    method=("IPCC 2021", "climate change", "global warming potential (GWP100)"),
    functional_unit_trigger = rm_reader.input_lca_name,
    outputs = rm_reader.output_amounts
        )


print(result)

script_dir = Path(__file__).resolve().parent.parent.parent
bi.export.excel.write_lci_excel(
    "batt_lci", dirpath=str(script_dir / "data" / "lci_data")
)