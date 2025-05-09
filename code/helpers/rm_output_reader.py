import pandas as pd
from typing import List, Optional
import json
import uuid


class RMOutputToLCA:
    """
    Responsible for turning MFA output into LCA readable data
    """
    def __init__(self, database_name: str, rm_path: str, activities_path: str):
        self.database_name = database_name
        self.mfa_df = pd.read_csv(rm_path).fillna("")
        with open(activities_path, "r") as file:
            activities = json.load(file)
        self.activities = activities
        self.output_amounts = {}
        self.input_lca_name = self.activities["input"]["lca_name"]
        self.lca_dict = self.build_lca_from_rm()


    def build_lca_from_rm(self):
        """
        Interpret output excel from recovery model and compute the input amount & recovered materials
        :param: product_name: Input product to the system
        :param: input_flow_ids: Flow IDs into the system
        :param output_flow_ids: Output recovered material flows
        :param output_recovered_materials: List of materials that are recovered, along with the layer for that material
        """
        input_flow_ids = self.activities["input"]["flow_ids"]
        input_amount = self.mfa_df[
            (self.mfa_df["Stock/Flow ID"].isin(input_flow_ids)) & (self.mfa_df["Layer 2"] == "")
        ]["Value"].sum()

        lca_dict = {}

        # Add output reco flow
        for output_reco_flow in self.activities["output_recovered_materials"]:
            uuid_iter, dict_iter = RMOutputToLCA.build_base_process(
                output_reco_flow["lca_name"]
            )
            lca_dict.update(dict_iter)
            output_reco_flow["process_id"] = uuid_iter

        # Add output wastes flow
        for output_waste_flow in self.activities["output_waste_flows"]:
            uuid_iter, dict_iter = RMOutputToLCA.build_base_process(
                output_waste_flow["lca_name"]
            )
            lca_dict.update(dict_iter)
            output_waste_flow["process_id"] = uuid_iter

        # Create main activity
        main_activity_id, main_activity_dict = RMOutputToLCA.build_base_process(
            self.activities["input"]["lca_name"], is_waste=True
        )
        lca_dict.update(main_activity_dict)

        # Add metal exchanges
        for output_recovered_material in self.activities["output_recovered_materials"]:
            selection_output_flows = self.mfa_df[
                (
                    self.mfa_df[output_recovered_material["layer"]]
                    == output_recovered_material["material"]
                )
                & (self.mfa_df["Stock/Flow ID"].isin(output_recovered_material["flow_ids"]))
                & (
                    True
                    if output_recovered_material["layer"] == "Layer 4"
                    else self.mfa_df["Layer 4"] == ""
                )
            ]
            total_material = selection_output_flows["Value"].sum()
            technosphere_exchange = RMOutputToLCA.build_technosphere_exchange(
                name=output_recovered_material["lca_name"],
                process_id=output_recovered_material["process_id"],
                amount=-total_material / input_amount,
            )
            lca_dict[(self.database_name, main_activity_id)]["exchanges"].append(
                technosphere_exchange
            )
            self.output_amounts[output_recovered_material["material"]] = total_material / input_amount

        # Add waste exchanges
        for output_waste_flow in self.activities["output_waste_flows"]:
            total_output_waste = self.mfa_df[
                (self.mfa_df["Stock/Flow ID"] == output_waste_flow["flow_id"])
                & (self.mfa_df["Layer 4"] != "")
            ]["Value"].sum()
            technosphere_exchange = RMOutputToLCA.build_technosphere_exchange(
                name=output_waste_flow["lca_name"],
                process_id=output_waste_flow["process_id"],
                amount=-total_output_waste / input_amount,
            )
            lca_dict[(self.database_name, main_activity_id)]["exchanges"].append(
                technosphere_exchange
            )

        # Add additional exchanges
        for add_exchange in self.activities["additional_exchanges"]:
            add_exchange["input"] = tuple(add_exchange["input"])
            lca_dict[(self.database_name, main_activity_id)]["exchanges"].append(
                add_exchange
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
            "location": "RER"
        }


# RMOutputToLCA("batt_lci").build_lca_from_rm(
#     rm_path="data/recovery_model_outputs/25_04_batt_2025_CIR/BATT_RM_cmp_version6.csv",
#     activities_path="data/recovery_model_outputs/25_04_batt_2025_CIR/NiMH_activities.json",
# )
