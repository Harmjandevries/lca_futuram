import bw2data as bd
import bw2calc as bc
import bw2io as bi
import bw_functional
from pathlib import Path
from helpers.rm_output_reader import RMOutputToLCA

# Set project
bd.projects.set_current("futuram")

# If a previous version of the database exists, remove it completely
if "batt_lci" in bd.databases:
    bd.Database("batt_lci").deregister()

db = bd.Database("batt_lci")

db_data = RMOutputToLCA.build_lca_from_rm(
    database_name="batt_lci",
    rm_path="data/recovery_model_outputs/25_04_batt_2025_CIR/BATT_RM_cmp_version6.csv",
    activities_path="data/recovery_model_outputs/25_04_batt_2025_CIR/NiMH_activities.json",
)


db_data = {
    ("batt_lci", "5299f521-3b05-4ebd-ae02-3fd54e23d994"): {
        "name": "recovered ferrous scrap",
        "unit": "kilogram",
        "location": "RER",
        "reference product": "recovered ferrous scrap",
        "exchanges": [
            {
                "input": ("batt_lci", "5299f521-3b05-4ebd-ae02-3fd54e23d994"),
                "name": "recovered ferrous scrap",
                "amount": 1,
                "unit": "kilogram",
                "type": "production",
            }
        ],
    },
    ("batt_lci", "5e404637-d154-4b40-b482-42030e3f2bdd"): {
        "name": "recovered nickel",
        "unit": "kilogram",
        "location": "RER",
        "reference product": "recovered nickel",
        "exchanges": [
            {
                "input": ("batt_lci", "5e404637-d154-4b40-b482-42030e3f2bdd"),
                "name": "recovered nickel",
                "amount": 1,
                "unit": "kilogram",
                "type": "production",
            }
        ],
    },
    ("batt_lci", "076c9af2-f2b6-47b1-ba90-87c9e40e3113"): {
        "name": "nickel-metal hybride battery recovery slag 2",
        "unit": "kilogram",
        "location": "RER",
        "reference product": "nickel-metal hybride battery recovery slag 2",
        "exchanges": [
            {
                "input": ("batt_lci", "076c9af2-f2b6-47b1-ba90-87c9e40e3113"),
                "name": "nickel-metal hybride battery recovery slag 2",
                "amount": 1,
                "unit": "kilogram",
                "type": "production",
            }
        ],
    },
    ("batt_lci", "f3e14ff1-4e03-4f47-8ed3-ca7fe48f05a7"): {
        "name": "nickel-metal hybride battery recovery slag",
        "unit": "kilogram",
        "location": "RER",
        "reference product": "nickel-metal hybride battery recovery slag",
        "exchanges": [
            {
                "input": ("batt_lci", "f3e14ff1-4e03-4f47-8ed3-ca7fe48f05a7"),
                "name": "nickel-metal hybride battery recovery slag",
                "amount": 1,
                "unit": "kilogram",
                "type": "production",
            }
        ],
    },
    ("batt_lci", "369c0dd3-5bd8-43dc-8ab2-ac3200f366f7"): {
        "name": "nickel-metal hybride battery waste",
        "unit": "kilogram",
        "location": "RER",
        "reference product": "nickel-metal hybride battery waste",
        "exchanges": [
            {
                "input": ("batt_lci", "369c0dd3-5bd8-43dc-8ab2-ac3200f366f7"),
                "name": "nickel-metal hybride battery waste",
                "amount": -1,
                "unit": "kilogram",
                "type": "production",
            },
            {
                "input": ("batt_lci", "5299f521-3b05-4ebd-ae02-3fd54e23d994"),
                "name": "recovered ferrous scrap",
                "amount": -0.5083601468312615,
                "unit": "kilogram",
                "type": "technosphere",
            },
            {
                "input": ("batt_lci", "5e404637-d154-4b40-b482-42030e3f2bdd"),
                "name": "recovered nickel",
                "amount": -0.2535257812778481,
                "unit": "kilogram",
                "type": "technosphere",
            },
            {
                "input": ("batt_lci", "076c9af2-f2b6-47b1-ba90-87c9e40e3113"),
                "name": "nickel-metal hybride battery recovery slag 2",
                "amount": -0.10917230148300938,
                "unit": "kilogram",
                "type": "technosphere",
            },
            {
                "input": ("batt_lci", "f3e14ff1-4e03-4f47-8ed3-ca7fe48f05a7"),
                "name": "nickel-metal hybride battery recovery slag",
                "amount": -0.0,
                "unit": "kilogram",
                "type": "technosphere",
            },
            # {
            #     "input": ("ecoinvent", "7e7c1abdd9ad21d357446c35317721a5"),
            #     "amount": 0.066,
            #     "type": "technosphere",
            #     "unit": "kilowatt hour",
            #     "name": "market group for electricity, medium voltage",
            # },
        ],
    },
}


db.write(db_data)


method = ("IPCC 2021", "climate change", "global warming potential (GWP100)")


input_process = next(
    (act for act in db if "nickel-metal hybride battery waste" in act["name"].lower())
)
functional_unit = {input_process: -1}

# Perform LCA
lca = bc.LCA(functional_unit, method)
lca.lci()
lca.lcia()

# Show result
print(
    f"Climate impact (GWP100) for 1 kg nicd processing from NiCd recycling: {lca.score:.4f} kg CO₂-eq"
)


script_dir = Path(__file__).resolve().parent.parent.parent
bi.export.excel.write_lci_excel(
    "batt_lci", dirpath=str(script_dir / "data" / "lci_data")
)
