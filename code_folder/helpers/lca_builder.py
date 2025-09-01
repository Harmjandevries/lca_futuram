import pandas as pd
from typing import List
import json
from .constants import PRICES_FILE, SingleLCI, SingleLCIAResult, ExternalDatabase,  Location, Scenario, Route, Chemistry, INPUT_DATA_FOLDER, route_lci_names, SUPPORTED_YEARS_OBS, SUPPORTED_YEARS_SCENARIO
import bw2data as bd
from dataclasses import dataclass
import bw2calc as bc
from .brightway_helpers import BrightwayHelpers
from .storage_helper import StorageHelper


class LCABuilder:
    """
    Responsible for building an LCA using the lca_builder and RM output files.
    """
    def __init__(self):
        # Setup BW databases
        self.ecoinvent = bd.Database("ecoinvent")
        self.biosphere = bd.Database("biosphere")
        with open(PRICES_FILE, "r") as file:
            self.prices = json.load(file)

        self.lcis: List[SingleLCI] = []
        self.lcia_results: List[SingleLCIAResult] = []

    def build_all_lcis(self,
                  database: bd.Database,
                  route_selection:List[Route],
                  chemistry_selection: List[Chemistry],
                  year_selection=List[int],
                  scenario_selection=List[Scenario],
                  location_selection=List[Location],
                  ):
        for route in route_selection:

            for chemistry in chemistry_selection:
                for year in year_selection:
                    for scenario in scenario_selection:
                        # Filter scenarios for relevant years
                        if (scenario == Scenario.OBS and year not in SUPPORTED_YEARS_OBS) or \
                        (scenario in [Scenario.BAU, Scenario.CIR, Scenario.REC] and year not in SUPPORTED_YEARS_SCENARIO):
                            continue
                        for location in location_selection:
                            lci = self.build_lci_for_route(database=database, route=route, chemistry=chemistry,year=year,scenario=scenario,location=location)
                            if lci:
                                self.lcis.append(lci)
                                print(f"Finished LCI for route: {route.value}, scenario: {scenario.value}, chemistry: {chemistry.value}, year: {year}, location: {location.value}")


        # Adds all the lci_dict together in a big dict
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        database.write(big_dict)

    def build_lci_for_route(self, database: bd.Database, route:Route, chemistry:Chemistry, year: int, scenario:Scenario, location:Location):
        input_folder = INPUT_DATA_FOLDER / route.value

        mfa_df = pd.read_csv(input_folder / "rm_output.csv").fillna("")
        if chemistry.value in pd.ExcelFile( input_folder / "lci_builder.xlsx").sheet_names:
            lci_builder_df = pd.read_excel(
                input_folder / "lci_builder.xlsx",
                sheet_name=chemistry.value,
                dtype={"Layer": str}
            ).fillna("")
        else:
            return

        mfa_df = mfa_df[
            (mfa_df["Year"] == year) &
            (mfa_df["Scenario"] == scenario.value)
            ]

        lci_dict = {}
        output_amounts_alloy = {}
        output_amounts_element = {}
        
        # Build main activity
        main_activity_row = lci_builder_df[lci_builder_df["LCI Flow Type"]=="production"]
        main_activity_flow_name = f"{route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        main_activity_id, main_activity_dict = BrightwayHelpers.build_base_process(
            name=main_activity_flow_name,
            is_waste=True
        )
        lci_dict.update(main_activity_dict)
        input_flow_ids = [m.strip() for m in main_activity_row.iloc[0]['Stock/Flow IDs'].split(',')]
        product_list = [] if not main_activity_row["Materials"].iloc[0] else [m.strip() for m in main_activity_row["Materials"].iloc[0].split(',')]
        input_amount = self.get_flow_amount(mfa_df=mfa_df, flows_list=input_flow_ids, product_list=product_list, layer="")

        # Build avoided impact activity
        avoided_impacts_flow_name =  f"avoided impacts for {route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        avoided_impacts_activity_id, avoided_impacts_dict = BrightwayHelpers.build_base_process(
            name=avoided_impacts_flow_name,
            is_waste=False
        )
        lci_dict.update(avoided_impacts_dict)


        # Build recovered metal activities
        output_recovered_material_rows = lci_builder_df[
            (lci_builder_df["Flow Direction"]=="recovered")
        ]
        for _, output_reco_row in output_recovered_material_rows.iterrows():
            material_list = [m.strip() for m in output_reco_row["Materials"].split(',')]
            flows_list = [m.strip() for m in output_reco_row["Stock/Flow IDs"].split(',')]

            process_name = output_reco_row['LCI Flow Name']
            existing_id = BrightwayHelpers.get_existing_process_id_by_name(lcis=self.lcis, name=process_name)

            if existing_id:
                process_id = existing_id
            else:
                process_id, process_dict = BrightwayHelpers.build_base_process(process_name)
                lci_dict.update(process_dict)
           
            total_material = self.get_flow_amount(mfa_df=mfa_df, flows_list=flows_list, product_list=product_list, material_list=material_list, layer=str(output_reco_row["Layer"]))
            technosphere_exchange = BrightwayHelpers.build_technosphere_exchange(
                name=output_reco_row["LCI Flow Name"],
                process_id=process_id,
                amount=-total_material / input_amount,
            )
            lci_dict[(database.name, main_activity_id)]["exchanges"].append(
                technosphere_exchange
            )
            output_amounts_alloy[output_reco_row['LCI Flow Name']] = total_material / input_amount
            for i in range(0, len(material_list)):
                material = material_list[i]
                layer = output_reco_row["Layer"].split(",")[i] if "," in output_reco_row["Layer"] else output_reco_row["Layer"]
                amount = self.get_flow_amount(mfa_df=mfa_df, flows_list=flows_list, product_list=product_list, material_list=[material],layer=layer)
                if material not in output_amounts_element:
                    output_amounts_element[material] = amount / input_amount
                else:
                    output_amounts_element[material] += amount / input_amount

            linked_process_database, linked_process_name = tuple(output_reco_row['Linked process'].split(':'))
            linked_process_database = ExternalDatabase(linked_process_database.upper())

            avoided_impact_exchange = BrightwayHelpers.build_external_exchange(
                database=linked_process_database,
                ecoinvent=self.ecoinvent,
                biosphere=self.biosphere,
                process_name=linked_process_name,
                location=output_reco_row["Region"] if output_reco_row["Region"] else "RER",
                amount=total_material / input_amount,
                flow_direction="output",
                categories=tuple(map(str.strip, output_reco_row["Categories"].split(", "))),
                unit = output_reco_row["Unit"],
            )
            # If this exchange exists already, add it
            # Check if exchange with same name and input already exists
            exchanges = lci_dict[(database.name, avoided_impacts_activity_id)]["exchanges"]
            for ex in exchanges:
                if ex["name"] == avoided_impact_exchange["name"] and ex["input"] == avoided_impact_exchange["input"]:
                    ex["amount"] += avoided_impact_exchange["amount"]
                    break
            else:
                exchanges.append(avoided_impact_exchange)

        # Build external activities from external sources
        external_activity_rows = lci_builder_df[(lci_builder_df['Linked process']!='')&(lci_builder_df['Flow Direction']!="recovered")]
        for _, output_reco_row in external_activity_rows.iterrows():
            # Scale the ecoinvent processes by the flow they are matched to in ecoinvent
            if output_reco_row['Stock/Flow IDs']:
                total_flow = self.get_flow_amount(
                    mfa_df=mfa_df,
                    product_list=product_list,
                    material_list=[m.strip() for m in output_reco_row["Materials"].split(',')],
                    flows_list=[m.strip() for m in output_reco_row["Stock/Flow IDs"].split(',')],
                    layer=str(output_reco_row['Layer']))
                amount = total_flow/input_amount
            elif output_reco_row["Scaled by flows"]:
                scaled_by_flows = [m.strip() for m in output_reco_row["Scaled by flows"].split(',')]
                scaling_ratio = self.get_flow_amount(
                    mfa_df=mfa_df,
                    flows_list=scaled_by_flows,
                    product_list=product_list,
                    # Todo bug?
                    )/input_amount
                if "Element to compound ratio" in output_reco_row:
                    element_to_compound_ratio = float(output_reco_row["Element to compound ratio"])
                else:
                    element_to_compound_ratio = 1
                amount = output_reco_row['Amount']*scaling_ratio / element_to_compound_ratio
            else:
                amount = output_reco_row['Amount']
            linked_process_database, linked_process_name = tuple(output_reco_row['Linked process'].split(':'))
            linked_process_database = ExternalDatabase(linked_process_database.upper())
            external_exchange = BrightwayHelpers.build_external_exchange(
                database=linked_process_database,
                ecoinvent=self.ecoinvent,
                biosphere=self.biosphere,
                process_name = linked_process_name,
                location=output_reco_row["Region"] if output_reco_row["Region"] else "RER",
                amount=amount,
                unit=output_reco_row["Unit"],
                flow_direction=output_reco_row["Flow Direction"],
                categories=tuple(map(str.strip, output_reco_row["Categories"].split(", ")))
            )
            # If this exchange exists already, add it
            # Check if exchange with same name and input already exists
            exchanges = lci_dict[(database.name, main_activity_id)]["exchanges"]
            for ex in exchanges:
                if ex["name"] == external_exchange["name"] and ex["input"] == external_exchange["input"]:
                    ex["amount"] += external_exchange["amount"]
                    break
            else:
                exchanges.append(external_exchange)

        return SingleLCI(
            main_activity_flow_name=main_activity_flow_name,
            avoided_impacts_flow_name=avoided_impacts_flow_name,
            chemistry=chemistry, 
            route=route, 
            scenario=scenario,
            year=year,
            location=location,
            lci_dict=lci_dict,
            total_inflow_amount=input_amount,
            output_amounts_alloy=output_amounts_alloy,
            output_amounts_element=output_amounts_element)

    def get_flow_amount(self, mfa_df: pd.DataFrame, flows_list: List[str], product_list: List[str], material_list: List[str] = [], layer: str = "4") -> int:
        if not layer:
            # If layer is not specified sum all products together for the total flow
            return mfa_df[
                        (mfa_df["Stock/Flow ID"].isin(flows_list)) 
                        & (mfa_df["Layer 4"] != "" )
                        & (mfa_df["Layer 1"].isin(product_list))
                    ]["Value"].sum()

        if "," not in layer:
            # If all material are in same layer
            return mfa_df[
                    (
                        True 
                        if not material_list 
                        else mfa_df['Layer ' + str(layer)].isin(material_list)
                    )
                    & (mfa_df["Stock/Flow ID"].isin(flows_list))
                    & (
                        True
                        if layer == "4"
                        else mfa_df["Layer 4"] == ""
                    )
                    & (
                        mfa_df["Layer 1"].isin(product_list)
                    )
                ]["Value"].sum()
        
        layers = layer.split(',') if ',' in layer else [layer for _ in range(0, len(material_list))]
        if len(layers)!=len(material_list):
            raise ValueError("number of layers and materials are mismatched")
        amount = 0
        for i in range(0, len(material_list)):
            amount += mfa_df[
                    (
                        True 
                        if not material_list 
                        else mfa_df['Layer ' + layers[i]]==material_list[i]
                    )
                    & (mfa_df["Stock/Flow ID"].isin(flows_list))
                    & (
                        True
                        if layers[i] == "4"
                        else mfa_df["Layer 4"] == ""
                    )
                    & (
                        mfa_df["Layer 1"].isin(product_list)
                    )
                ]["Value"].sum()
        return amount

    def run_lcia(self, database: bd.Database, lcia_method):
        for lci in self.lcis:
            lcia_result = self.run_lcia_for_route(database=database, lcia_method=lcia_method, lci=lci)
            self.lcia_results.append(lcia_result)

    def run_lcia_for_route(self, database: bd.Database, lcia_method: tuple, lci: SingleLCI):
        functional_unit = {next((act for act in database if lci.main_activity_flow_name == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit, lcia_method)
        lca.lci()
        lca.lcia()
        total_impact = lca.score

        functional_unit_avoided_impact = {next((act for act in database if lci.avoided_impacts_flow_name == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit_avoided_impact, lcia_method)
        lca.lci()
        lca.lcia()
        avoided_impact = lca.score

        return SingleLCIAResult(total_impact=total_impact, avoided_impact=avoided_impact, lci=lci)
    
    def save_lcis(self):
        StorageHelper.save_lcis(self.lcis)

    def load_latest_lcis(self, database: bd.Database):
        self.lcis = StorageHelper.load_latest_lcis()
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        database.write(big_dict)

    def save_database_to_excel(self, database: bd.Database):
        StorageHelper.save_database_to_excel(database)

    def save_lcia_results(self):
        StorageHelper.save_lcia_results(self.lcia_results)

    def load_latest_lcia_results(self):
        self.lcia_results = StorageHelper.load_latest_lcia_results()