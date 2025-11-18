import pandas as pd
from typing import List
from code_folder.helpers.constants import SingleLCI, SingleLCIAResult, ExternalDatabase,  Location, Scenario, Route, Product, INPUT_DATA_FOLDER, ECOINVENT_NAME, BIOSPHERE_NAME, route_lci_names, SUPPORTED_YEARS_OBS, SUPPORTED_YEARS_SCENARIO, SUPERSTRUCTURE_NAME
import bw2data as bd
import bw2calc as bc
from code_folder.helpers.brightway_helpers import BrightwayHelpers
from code_folder.helpers.storage_helper import StorageHelper


class LCABuilder:
    """
    Build and evaluate LCIs/LCIAs from RM outputs and LCI builder sheets.

    This class orchestrates:
    - Reading per-route/product inputs
    - Building Brightway processes and exchanges
    - Running LCIA and persisting results
    """
    def __init__(self, database_name: str):
        # Setup BW databases
        user_input = input("Select database (1: Ecoinvent, 2: Superstructure): ")
        if user_input == '1':
            ecoinvent_database_name = ECOINVENT_NAME
        else:
            ecoinvent_database_name = SUPERSTRUCTURE_NAME


        self.ecoinvent = bd.Database(ecoinvent_database_name)
        self.database_name = database_name
        self.database = bd.Database(database_name)
        self.biosphere = bd.Database(BIOSPHERE_NAME)

        self.lcis: List[SingleLCI] = []
        self.lcia_results: List[SingleLCIAResult] = []

    def build_all_lcis(self,
                       route_selection:List[Route],
                       product_selection: List[Product],
                       year_selection=List[int],
                       scenario_selection=List[Scenario],
                       location_selection=List[Location],
                       ):
        """Build LCIs for all combinations of the provided selections and write to DB."""
        for route in route_selection:

            for product in product_selection:
                for year in year_selection:
                    for scenario in scenario_selection:
                        # Filter scenarios for relevant years
                        if (scenario == Scenario.OBS and year not in SUPPORTED_YEARS_OBS) or \
                        (scenario in [Scenario.BAU, Scenario.CIR, Scenario.REC] and year not in SUPPORTED_YEARS_SCENARIO):
                            continue
                        for location in location_selection:
                            lci = self.build_lci(route=route, product=product, year=year, scenario=scenario, location=location)
                            if lci:
                                self.lcis.append(lci)
                                print(f"Finished LCI for route: {route.value}, scenario: {scenario.value}, product: {product.value}, year: {year}, location: {location.value}")


        # Adds all the lci_dict together in a big dict
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        self.database.write(big_dict)

    def build_lci(self, route:Route, product:Product, year: int, scenario:Scenario, location:Location):
        """Build a single LCI for a specific (route, product, year, scenario, location)."""
        mfa_df, lci_builder_df = self._read_inputs(route=route, product=product, year=year, scenario=scenario)
        if lci_builder_df is None:
            return

        lci_dict = {}

        main_activity_id, main_activity_flow_name, input_amount, product_list = self._build_main_activity(
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            route=route,
            year=year,
            scenario=scenario,
            mfa_df=mfa_df,
        )

        if input_amount == 0:
            print(
                "No inflow amount found for the specified configuration. "
                f"route={route.value}, product={product.value}, year={year}, "
                f"scenario={scenario.value}, location={location.value}. "
                "Check rm_output.csv and lci_builder.xlsx inputs."
            )
            return

        avoided_impacts_activity_id, avoided_impacts_flow_name = self._build_avoided_activity(
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            route=route,
            year=year,
            scenario=scenario,
        )

        self._add_recovered_materials(
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            avoided_impacts_activity_id=avoided_impacts_activity_id,
            product_list=product_list,
            mfa_df=mfa_df,
            input_amount=input_amount,
        )

        self._add_external_exchanges(
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            main_activity_id=main_activity_id,
            product_list=product_list,
            mfa_df=mfa_df,
            input_amount=input_amount,
        )

        return SingleLCI(
            main_activity_flow_name=main_activity_flow_name,
            avoided_impacts_flow_name=avoided_impacts_flow_name,
            product=product, 
            route=route, 
            scenario=scenario,
            year=year,
            location=location,
            lci_dict=lci_dict,
            total_inflow_amount=input_amount)

    def _read_inputs(self, route: Route, product: Product, year: int, scenario: Scenario):
        """Load inputs for route/product and filter MFA by year/scenario.

        Returns (mfa_df_filtered, lci_builder_df) or (mfa_df_filtered, None) if sheet missing.
        """
        input_folder = INPUT_DATA_FOLDER / route.value

        mfa_df = pd.read_csv(input_folder / "rm_output.csv").fillna("")
        if product.value in pd.ExcelFile(input_folder / "lci_builder.xlsx").sheet_names:
            lci_builder_df = pd.read_excel(
                input_folder / "lci_builder.xlsx",
                sheet_name=product.value,
                dtype={"Layer": str}
            ).fillna("")
        else:
            return mfa_df[(mfa_df["Year"] == year) & (mfa_df["Scenario"] == scenario.value)], None

        mfa_df = mfa_df[
            (mfa_df["Year"] == year) &
            (mfa_df["Scenario"] == scenario.value)
        ]
        return mfa_df, lci_builder_df

    def _build_main_activity(self,  lci_dict: dict, lci_builder_df: pd.DataFrame, route: Route, year: int, scenario: Scenario, mfa_df: pd.DataFrame):
        """Create the main activity and compute total inflow amount.

        Returns (main_activity_id, main_activity_flow_name, input_amount, product_list).
        """
        main_activity_row = lci_builder_df[lci_builder_df["LCI Flow Type"]=="production"]
        main_activity_flow_name = f"{route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        main_activity_id, main_activity_dict = BrightwayHelpers.build_base_process(
            name=main_activity_flow_name,
            database_name=self.database_name,
            is_waste=True
        )
        lci_dict.update(main_activity_dict)
        input_flow_ids = [m.strip() for m in main_activity_row.iloc[0]['Stock/Flow IDs'].split(',')]
        product_list = [] if not main_activity_row["Materials"].iloc[0] else [m.strip() for m in main_activity_row["Materials"].iloc[0].split(',')]
        input_amount = self.calculate_flow_amount(mfa_df=mfa_df, flows_list=input_flow_ids, product_list=product_list, layer="")
        return main_activity_id, main_activity_flow_name, input_amount, product_list

    def _build_avoided_activity(self, lci_dict: dict, lci_builder_df: pd.DataFrame, route: Route, year: int, scenario: Scenario):
        """Create the avoided impacts activity.

        Returns (avoided_impacts_activity_id, avoided_impacts_flow_name).
        """
        main_activity_row = lci_builder_df[lci_builder_df["LCI Flow Type"]=="production"]
        avoided_impacts_flow_name =  f"avoided impacts for {route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        avoided_impacts_activity_id, avoided_impacts_dict = BrightwayHelpers.build_base_process(
            name=avoided_impacts_flow_name,
            database_name=self.database_name,
            is_waste=False
        )
        lci_dict.update(avoided_impacts_dict)
        return avoided_impacts_activity_id, avoided_impacts_flow_name

    def _add_recovered_materials(self, lci_dict: dict, lci_builder_df: pd.DataFrame, avoided_impacts_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float) -> None:
        """Add recovered material exchanges to the avoided impacts activity."""
        output_recovered_material_rows = lci_builder_df[
    (lci_builder_df["Flow Direction"] == "recovered") |
    (lci_builder_df["LCI Flow Type"] == "recovered")
]
        for _, output_reco_row in output_recovered_material_rows.iterrows():
            material_list = [m.strip() for m in output_reco_row["Materials"].split(',')]
            flows_list = [m.strip() for m in output_reco_row["Stock/Flow IDs"].split(',')]
            multiplier = self._get_recovery_multiplier(output_reco_row)

            total_material = self.calculate_flow_amount(
                mfa_df=mfa_df,
                flows_list=flows_list,
                product_list=product_list,
                material_list=material_list,
                layer=str(output_reco_row["Layer"]))  * multiplier

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
                unit=output_reco_row["Unit"],
            )
            self._merge_exchange(
                lci_dict[(self.database_name, avoided_impacts_activity_id)]["exchanges"],
                avoided_impact_exchange,
            )

    def _add_external_exchanges(self, lci_dict: dict, lci_builder_df: pd.DataFrame, main_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float) -> None:
        """Add external exchanges (ecoinvent/biosphere) to the main activity."""
        external_activity_rows = lci_builder_df[(lci_builder_df['Linked process']!='')&(lci_builder_df['Flow Direction']!="recovered")&(lci_builder_df['LCI Flow Type']!="recovered")]
        for _, external_row in external_activity_rows.iterrows():
            if external_row['Stock/Flow IDs']:
                total_flow = self.calculate_flow_amount(
                    mfa_df=mfa_df,
                    product_list=product_list,
                    material_list=[m.strip() for m in external_row["Materials"].split(',')],
                    flows_list=[m.strip() for m in external_row["Stock/Flow IDs"].split(',')],
                    layer=str(external_row['Layer']))
                amount = total_flow/input_amount
            elif external_row["Scaled by flows"]:
                scaled_by_flows = [m.strip() for m in external_row["Scaled by flows"].split(',')]
                scaling_ratio = self.calculate_flow_amount(
                    mfa_df=mfa_df,
                    flows_list=scaled_by_flows,
                    product_list=product_list,
                    )/input_amount
                if "Element to compound ratio" in external_row:
                    element_to_compound_ratio = float(external_row["Element to compound ratio"])
                else:
                    element_to_compound_ratio = 1
                amount = external_row['Amount']*scaling_ratio / element_to_compound_ratio
            else:
                amount = external_row['Amount']
            linked_process_database, linked_process_name = tuple(external_row['Linked process'].split(':'))
            linked_process_database = ExternalDatabase(linked_process_database.upper())
            external_exchange = BrightwayHelpers.build_external_exchange(
                database=linked_process_database,
                ecoinvent=self.ecoinvent,
                biosphere=self.biosphere,
                process_name = linked_process_name,
                location=external_row["Region"] if external_row["Region"] else "RER",
                amount=amount,
                unit=external_row["Unit"],
                flow_direction=external_row["Flow Direction"],
                categories=tuple(map(str.strip, external_row["Categories"].split(", ")))
            )
            self._merge_exchange(
                lci_dict[(self.database_name, main_activity_id)]["exchanges"],
                external_exchange,
            )

    def calculate_flow_amount(self, mfa_df: pd.DataFrame, flows_list: List[str], product_list: List[str], material_list: List[str] = [], layer: str = "4") -> int:
        """Calculate summed flow amount with optional material and layer filters."""
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

    def run_lcia(self, lcia_method):
        """Compute LCIA for all built LCIs and store results in memory."""
        for lci in self.lcis:
            lcia_result = self.compute_lcia_for_lci(lcia_method=lcia_method, lci=lci)
            self.lcia_results.append(lcia_result)

    def compute_lcia_for_lci(self, lcia_method: tuple, lci: SingleLCI):
        """Compute LCIA for a single LCI, returning a SingleLCIAResult."""
        functional_unit = {next((act for act in self.database if lci.main_activity_flow_name == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit, lcia_method)
        lca.lci()
        lca.lcia()
        total_impact = lca.score

        functional_unit_avoided_impact = {next((act for act in self.database if lci.avoided_impacts_flow_name == act["name"].lower())): -1}
        lca = bc.LCA(functional_unit_avoided_impact, lcia_method)
        lca.lci()
        lca.lcia()
        avoided_impact = lca.score

        return SingleLCIAResult(total_impact=total_impact, avoided_impact=avoided_impact, lci=lci)
    
    def save_lcis(self):
        """Persist built LCIs to a timestamped pickle file."""
        StorageHelper.save_lcis(self.lcis)

    def load_latest_lcis(self):
        """Load the latest saved LCIs and write their processes to the database."""
        self.lcis = StorageHelper.load_latest_lcis()
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        self.database.write(big_dict)

    def save_database_to_excel(self):
        """Export the current database to an Excel file in output_data."""
        StorageHelper.save_database_to_excel(self.database)

    def save_lcia_results(self):
        """Persist LCIA results to a timestamped pickle file."""
        StorageHelper.save_lcia_results(self.lcia_results)

    def load_latest_lcia_results(self):
        """Load the latest saved LCIA results from disk into memory."""
        self.lcia_results = StorageHelper.load_latest_lcia_results()

    @staticmethod
    def _merge_exchange(exchanges: List[dict], new_exchange: dict) -> None:
        """Merge an exchange into a list, summing amounts for duplicate entries."""
        for exchange in exchanges:
            if exchange["name"] == new_exchange["name"] and exchange["input"] == new_exchange["input"]:
                exchange["amount"] += new_exchange["amount"]
                return
        exchanges.append(new_exchange)

    @staticmethod
    def _get_recovery_multiplier(row: pd.Series) -> float:
        """Return the combined multiplier for recovery efficiency and unit conversion."""

        def _parse(value) -> float:
            if pd.isna(value) or value == "":
                return 1.0
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid numeric value '{value}' in recovery configuration") from exc

        unit_conversion = _parse(row.get("Weight per unit", 1.0))
        recovery_efficiency = _parse(row.get("Recovery efficiency", 1.0))
        return recovery_efficiency / unit_conversion