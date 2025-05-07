import bw2io as bi
import bw2data as bd
import bw2calc as bc
import pandas as pd
from pathlib import Path


def get_total_material(mfa_df_input: pd.DataFrame, flow_id: str) -> float:
    mfa_df_flow = mfa_df_input[mfa_df_input["Stock/Flow ID"] == flow_id]
    for layer in [col for col in mfa_df_flow.columns if col.startswith("Layer")]:
        blank_mask = mfa_df_flow[layer].astype(str).str.strip() == ""
        if blank_mask.any():
            return mfa_df_flow.loc[blank_mask, "Value"].sum()
    return mfa_df_flow["Value"].sum()


bd.projects.set_current("futuram")

# Create or clear the database
if "test_weee_lci" in bd.databases:
    bd.Database("test_weee_lci").deregister()
db = bd.Database("test_weee_lci")

mfa_df = pd.read_csv(
    "data/recovery_model_outputs/21_03_weee_cat1/recovery_model_output.csv"
).fillna("")
activities_df = pd.read_csv(
    "data/recovery_model_outputs/21_03_weee_cat1/activities.csv"
)
activities_df["total_material"] = activities_df["Stock/Flow ID"].apply(
    lambda flow_id: get_total_material(mfa_df_input=mfa_df, flow_id=flow_id)
)

mfa_df[
    (mfa_df["Stock/Flow ID"] == "WEEE_mechRec2_Landfill") & (mfa_df["Layer 4"] == "")
]

db_data = {
    # FLOW: Collected e-waste
    ("test_weee_lci", "WEEE_categ_mechRec1"): {
        "name": "Sorted category-1 e-waste",
        "unit": "kilogram",
        "type": "processwithreferenceproduct",
        "location": "RER",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_categ_mechRec1"),
                "amount": 1.0,
                "type": "production",
                "unit": "kilogram",
            }
        ],
    },
    # PROCESS: Dismantling
    ("test_weee_lci", "dismantling_categ1"): {
        "name": "Dismantling of category-1 e-waste",
        "unit": "kilogram",
        "type": "processwithreferenceproduct",
        "location": "RER",
        "reference product": "Dismantled category-1 e-waste",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_categ_mechRec1"),
                "amount": 1.0,
                "type": "technosphere",
                "unit": "kilogram",
            },
            {
                "input": ("test_weee_lci", "dismantling_categ1"),
                "amount": 0.99297,
                "type": "production",
                "unit": "kilogram",
                "name": "Dismantled category-1 e-waste",
            },
            {
                "input": ("ecoinvent", "c9417d9413057b8082458955d9edc16a"),
                "amount": 0.00075133,
                "type": "technosphere",
                "unit": "kilogram",
                "name": "Used refrigerant R12 for treatment",
            },
        ],
    },
    # PROCESS: Comminution
    ("test_weee_lci", "comminution_categ1"): {
        "name": "Comminution of dismantled category-1 e-waste",
        "unit": "kilogram",
        "type": "processwithreferenceproduct",
        "location": "RER",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_AlScrap"),
                "amount": 0.032669,
                "type": "production",
                "unit": "kilogram",
            },
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_CuScrap"),
                "amount": 0.02918641,
                "type": "production",
                "unit": "kilogram",
            },
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_ferrousScrap"),
                "amount": 0.4889,
                "type": "production",
                "unit": "kilogram",
            },
            {
                "input": ("test_weee_lci", "dismantling_categ1"),
                "amount": 1.0,
                "type": "technosphere",
                "unit": "kilogram",
                "name": "Dismantled category-1 e-waste",
            },
            {
                "input": ("ecoinvent", "e814b362fff46e86d498a1156e70c266"),
                "amount": 0.0000000008,
                "type": "technosphere",
                "unit": "unit",
                "name": "market for mechanical treatment facility, waste electric and electronic equipment",
            },
            {
                "input": ("ecoinvent", "7e7c1abdd9ad21d357446c35317721a5"),
                "amount": 0.066,
                "type": "technosphere",
                "unit": "kilowatt hour",
                "name": "market group for electricity, medium voltage",
            },
            {
                "input": ("ecoinvent", "bd0428d4d6f4dea8e3035d9b3356e04b"),
                "amount": 0.4901,
                "type": "technosphere",
                "unit": "kilogram",
                "name": "treatment of waste plastic, mixture, municipal incineration",
            },
        ],
    },
    ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_AlScrap"): {
        "name": "Aluminum scrap",
        "unit": "kilogram",
        "location": "RER",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_AlScrap"),
                "amount": 1.0,
                "type": "production",
                "unit": "kilogram",
            }
        ],
    },
    ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_CuScrap"): {
        "name": "Copper scrap",
        "unit": "kilogram",
        "location": "RER",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_CuScrap"),
                "amount": 1.0,
                "type": "production",
                "unit": "kilogram",
            }
        ],
    },
    # FLOW: Ferrous scrap
    ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_ferrousScrap"): {
        "name": "Ferrous scrap",
        "unit": "kilogram",
        "location": "RER",
        "exchanges": [
            {
                "input": ("test_weee_lci", "WEEE_2RM_mechRec2Smelter_ferrousScrap"),
                "amount": 1.0,
                "type": "production",
                "unit": "kilogram",
            }
        ],
    },
}

db.write(db_data)

script_dir = Path(__file__).resolve().parent.parent
bi.export.write_lci_excel(
    "test_weee_lci", dirpath=str(script_dir / "data" / "lci_data")
)
