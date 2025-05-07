import pandas as pd
from typing import List
import json
from rm_output_reader import RMOutputReader

with open(
    "data/recovery_model_outputs/25_04_batt_2025_CIR/NiMH_activities.json", "r"
) as file:
    NiMH_activities = json.load(file)


RMOutputReader(
    "data/recovery_model_outputs/25_04_batt_2025_CIR/BATT_RM_cmp_version6.csv"
).process_product(
    input_flow_ids=NiMH_activities["input_flow_ids"],
    output_flow_ids=NiMH_activities["output_flow_ids"],
    output_recovered_materials=NiMH_activities["output_recovered_materials"],
    output_waste_flows=NiMH_activities["output_waste_flows"],
)


{
    "input_flow_ids": ["BATT_NiMHSorted"],
    "output_flow_ids": ["BATT_2RM_therRecNiMH", "BATT_2RM_mechRecNiMH"],
    "output_recovered_materials": [
        {"material": "ferrousMetals", "layer": "Layer 3"},
        {"material": "Ni", "layer": "Layer 4"},
    ],
    "output_waste_flows": ["BATT_slagsAndSludgesNiMH_REC", "BATT_slagsAndSludgesNiMH"],
}
