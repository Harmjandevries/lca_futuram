import pandas as pd
from typing import List, Optional
import json
import uuid


class RMOutputToLCA:

    @staticmethod
    def build_lca_from_rm(database_name: str, rm_path: str, activities_path: str):
        """
        Interpret output excel from recovery model and compute the input amount & recovered materials
        :param: product_name: Input product to the system
        :param: input_flow_ids: Flow IDs into the system
        :param output_flow_ids: Output recovered material flows
        :param output_recovered_materials: List of materials that are recovered, along with the layer for that material
        """

        mfa_df = pd.read_csv(rm_path).fillna("")
        with open(activities_path, "r") as file:
            activities = json.load(file)
        input_flow_ids = activities["input"]["flow_ids"]
        input_amount = mfa_df[
            (mfa_df["Stock/Flow ID"].isin(input_flow_ids)) & (mfa_df["Layer 2"] == "")
        ]["Value"].sum()

        lca_dict = {}

        # Add output reco flow
        for output_reco_flow in activities["output_recovered_materials"]:
            uuid_iter, dict_iter = RMOutputToLCA.build_base_process(
                output_reco_flow["lca_name"]
            )
            lca_dict.update(dict_iter)
            output_reco_flow["process_id"] = uuid_iter

        # Add output wastes flow
        for output_waste_flow in activities["output_waste_flows"]:
            uuid_iter, dict_iter = RMOutputToLCA.build_base_process(
                output_waste_flow["lca_name"]
            )
            lca_dict.update(dict_iter)
            output_waste_flow["process_id"] = uuid_iter

        # Create main activity
        main_activity_id, main_activity_dict = RMOutputToLCA.build_base_process(
            activities["input"]["lca_name"], is_waste=True
        )
        lca_dict.update(main_activity_dict)

        # Add metal exchanges
        for output_recovered_material in activities["output_recovered_materials"]:
            selection_output_flows = mfa_df[
                (
                    mfa_df[output_recovered_material["layer"]]
                    == output_recovered_material["material"]
                )
                & (mfa_df["Stock/Flow ID"].isin(output_recovered_material["flow_ids"]))
                & (
                    True
                    if output_recovered_material["layer"] == "Layer 4"
                    else mfa_df["Layer 4"] == ""
                )
            ]
            total_material = selection_output_flows["Value"].sum()
            technosphere_exchange = RMOutputToLCA.build_technosphere_exchange(
                name=output_recovered_material["lca_name"],
                process_id=output_recovered_material["process_id"],
                amount=-total_material / input_amount,
            )
            lca_dict[(database_name, main_activity_id)]["exchanges"].append(
                technosphere_exchange
            )

        # Add waste exchanges
        for output_waste_flow in activities["output_waste_flows"]:
            total_output_waste = mfa_df[
                (mfa_df["Stock/Flow ID"] == output_waste_flow["flow_id"])
                & (mfa_df["Layer 4"] != "")
            ]["Value"].sum()
            technosphere_exchange = RMOutputToLCA.build_technosphere_exchange(
                name=output_waste_flow["lca_name"],
                process_id=output_waste_flow["process_id"],
                amount=-total_output_waste / input_amount,
            )
            lca_dict[(database_name, main_activity_id)]["exchanges"].append(
                technosphere_exchange
            )

        return lca_dict

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
    def build_technosphere_exchange(name: str, process_id: str, amount: float):
        return {
            "input": ("batt_lci", process_id),
            "name": name,
            "amount": amount,
            "unit": "kilogram",
            "type": "technosphere",
        }


RMOutputToLCA.build_lca_from_rm(
    database_name="batt_lci",
    rm_path="data/recovery_model_outputs/25_04_batt_2025_CIR/BATT_RM_cmp_version6.csv",
    activities_path="data/recovery_model_outputs/25_04_batt_2025_CIR/NiMH_activities.json",
)
