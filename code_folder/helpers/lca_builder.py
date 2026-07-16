import pandas as pd
from pathlib import Path
from typing import List, Optional
from code_folder.helpers.constants import SHARED_RM_OUTPUT_FILE, SCENARIO_DATABASE_YEARS, SCRAP_DATABASE_NAME, SCRAP_PROCESSES_FILE, SingleLCI, SingleLCIAResult, ExternalDatabase,  Location, Scenario, Route, Product, INPUT_DATA_FOLDER, ECOINVENT_NAME, BIOSPHERE_NAME, route_lci_names, SUPPORTED_YEARS_OBS, SUPPORTED_YEARS_SCENARIO, SUPERSTRUCTURE_NAME
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
    VALID_SCENARIO_BACKGROUND_MODES = {"bau2020", "bauyear", "scenario"}

    def __init__(
        self,
        database_name: str,
        use_shared_rm_output: bool = False,
        scenario_background_direct: str = "scenario",
        scenario_background_avoided: str = "bauyear",
    ):

        baseline_db_name = BrightwayHelpers.resolve_scenario_db_name(
            scenario=Scenario.BAU,
            year=2020,
        )
        self.baseline_2020_db = bd.Database(baseline_db_name)
        self.baseline_db = self.baseline_2020_db

        self.background_db = bd.Database(SUPERSTRUCTURE_NAME)
        self.database_name = database_name
        self.database = bd.Database(database_name)
        self.biosphere = bd.Database(BIOSPHERE_NAME)
        self.scrap = None
        self.built_scrap_dbs = set()

        self.scrap_processes: List[dict] = []
        self.lcis: List[SingleLCI] = []
        self.lcia_results: List[SingleLCIAResult] = []
        self.use_shared_rm_output = use_shared_rm_output
        self.scenario_background_direct = self._validate_background_mode(scenario_background_direct, "scenario_background_direct")
        self.scenario_background_avoided = self._validate_background_mode(scenario_background_avoided, "scenario_background_avoided")

    def build_all_lcis(self,
                       route_selection:List[Route],
                       product_selection: List[Product],
                       year_selection: List[int],
                       scenario_selection: List[Scenario],
                       location_selection: List[Location],
                       add_scrap: bool
                       ):
        """Build LCIs for all combinations of the provided selections and write to DB."""
        for year in year_selection:
            # Update baseline_db to use BAU for the current year (only year adapts, scenario stays BAU)
            baseline_db_name = BrightwayHelpers.resolve_scenario_db_name(
                scenario=Scenario.BAU,
                year=year,
            )
            self.baseline_db = bd.Database(baseline_db_name)
            
            for scenario in scenario_selection:
                # Filter scenarios for relevant years
                if (scenario == Scenario.OBS and year not in SUPPORTED_YEARS_OBS) or \
                (scenario in [Scenario.BAU, Scenario.CIR, Scenario.REC] and year not in SUPPORTED_YEARS_SCENARIO):
                    continue
                resolved_ecoinvent_db = BrightwayHelpers.resolve_scenario_db_name(
                            scenario=scenario,
                            year=year,
                        )
                self.background_db = bd.Database(resolved_ecoinvent_db)
                scrap_scenario, scrap_year = self._resolve_scrap_scenario_year(
                    mode=self.scenario_background_direct,
                    scenario=scenario,
                    year=year,
                )
                scrap_db_name = BrightwayHelpers.resolve_scrap_db_name(
                    scenario=scrap_scenario,
                    year=scrap_year,
                )
                if add_scrap and scrap_db_name not in self.built_scrap_dbs:
                    if scrap_db_name in bd.databases:
                        bd.Database(scrap_db_name).deregister()
                    self.scrap = bd.Database(scrap_db_name)
                    scrap_background_db = self._resolve_background_db(self.scenario_background_direct)
                    scrap_processes = self.build_scrap_processes(ecoinvent_db=scrap_background_db)
                    self.scrap.write({k: v for d in scrap_processes for k, v in d.items()})
                    self.built_scrap_dbs.add(scrap_db_name)
                else:
                    self.scrap = bd.Database(scrap_db_name)

                for route in route_selection:
                    for product in product_selection:
                        for location in location_selection:
                            lci = self.build_lci(route=route, product=product, year=year, scenario=scenario, location=location)
                            if lci:
                                self.lcis.append(lci)
                                print(f"Finished LCI for route: {route.value}, scenario: {scenario.value}, product: {product.value}, year: {year}, location: {location.value}")


        # Adds all the lci_dict together in a big dict
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        self.database.write(big_dict)

    def build_lci(self, route:Route, product:Product, year: int, scenario:Scenario, location:Location):
        """Build a sifngle LCI for a specific (route, product, year, scenario, location)."""
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
        rm_output_path = SHARED_RM_OUTPUT_FILE if self.use_shared_rm_output else (input_folder / "rm_output.csv")

        mfa_df = pd.read_csv(rm_output_path).fillna("")
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
        main_activity_flow_name = f"{route_lci_names[route]}{main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
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
        avoided_impacts_flow_name =  f"avoided impacts for {route_lci_names[route]}{main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        avoided_impacts_activity_id, avoided_impacts_dict = BrightwayHelpers.build_base_process(
            name=avoided_impacts_flow_name,
            database_name=self.database_name,
            is_waste=False
        )
        lci_dict.update(avoided_impacts_dict)
        return avoided_impacts_activity_id, avoided_impacts_flow_name

    def _add_recovered_materials(self, lci_dict: dict, lci_builder_df: pd.DataFrame, avoided_impacts_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float) -> None:
        """Add recovered material exchanges to the avoided impacts activity."""
        avoided_background_db = self._resolve_background_db(self.scenario_background_avoided)
        output_recovered_material_rows = lci_builder_df[
    (lci_builder_df["Flow Direction"] == "recovered") |
    (lci_builder_df["LCI Flow Type"] == "recovered")
    ]
        for _, output_reco_row in output_recovered_material_rows.iterrows():
            material_list = self._split_csv_values(output_reco_row.get("Materials", ""))
            flows_list = self._split_csv_values(output_reco_row.get("Stock/Flow IDs", ""))

            # Manual debug skip for a specific recovery flow.
            if "WEEE_mechRec1_Depollution" in flows_list:
                continue

            if flows_list:
                amount_factor = self._parse_optional_numeric(output_reco_row.get("Amount", ""), default=1.0)
                total_material = self.calculate_flow_amount(
                    mfa_df=mfa_df,
                    flows_list=flows_list,
                    product_list=product_list,
                    material_list=material_list,
                    layer=str(output_reco_row["Layer"])) * amount_factor
                amount_per_unit = total_material / input_amount
            elif output_reco_row.get("Amount") != "":
                amount_per_unit = self._parse_optional_numeric(output_reco_row["Amount"], default=0.0)
            else:
                continue

            linked_process_database, linked_process_name = tuple(output_reco_row['Linked process'].split(':'))
            linked_process_database = ExternalDatabase(linked_process_database.upper())

            reference_product = output_reco_row.get("LCI Flow Name", "") or None

            avoided_impact_exchange = BrightwayHelpers.build_external_exchange(
                database=linked_process_database,
                ecoinvent=avoided_background_db,
                biosphere=self.biosphere,
                scrap=self.scrap,
                process_name=linked_process_name,
                location=output_reco_row["Region"] if output_reco_row["Region"] else "RER",
                amount=amount_per_unit,
                flow_direction="output",
                categories=tuple(map(str.strip, output_reco_row["Categories"].split(", "))),
                unit=output_reco_row["Unit"],
                reference_product=reference_product if linked_process_database == ExternalDatabase.ECOINVENT else None,
            )
            self._merge_exchange(
                lci_dict[(self.database_name, avoided_impacts_activity_id)]["exchanges"],
                avoided_impact_exchange,
            )

    def _add_external_exchanges(self, lci_dict: dict, lci_builder_df: pd.DataFrame, main_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float) -> None:
        """Add external exchanges (ecoinvent/biosphere) to the main activity."""
        direct_background_db = self._resolve_background_db(self.scenario_background_direct)
        external_activity_rows = lci_builder_df[(lci_builder_df['Linked process']!='')&(lci_builder_df['Flow Direction']!="recovered")&(lci_builder_df['LCI Flow Type']!="recovered")]
        for _, external_row in external_activity_rows.iterrows():
            if external_row['Stock/Flow IDs']:
                amount_factor = self._parse_optional_numeric(external_row.get("Amount", ""), default=1.0)
                total_flow = self.calculate_flow_amount(
                    mfa_df=mfa_df,
                    product_list=product_list,
                    material_list=self._split_csv_values(external_row.get("Materials", "")),
                    flows_list=self._split_csv_values(external_row.get("Stock/Flow IDs", "")),
                    layer=str(external_row['Layer'])) * amount_factor
                amount = total_flow/input_amount
            else:
                if external_row.get("Amount") == "":
                    continue
                amount = self._parse_optional_numeric(external_row["Amount"], default=0.0)
            linked_process_database, linked_process_name = tuple(external_row['Linked process'].split(':'))
            linked_process_database = ExternalDatabase(linked_process_database.upper())

            reference_product = external_row.get("LCI Flow Name", "") or None
            external_exchange = BrightwayHelpers.build_external_exchange(
                database=linked_process_database,
                ecoinvent=direct_background_db,
                biosphere=self.biosphere,
                scrap=self.scrap,
                process_name = linked_process_name,
                location=external_row["Region"] if external_row["Region"] else "RER",
                amount=amount,
                unit=external_row["Unit"],
                flow_direction=external_row["Flow Direction"],
                categories=tuple(map(str.strip, external_row["Categories"].split(", "))),
                reference_product=reference_product if linked_process_database == ExternalDatabase.ECOINVENT else None,
            )
            self._merge_exchange(
                lci_dict[(self.database_name, main_activity_id)]["exchanges"],
                external_exchange,
            )

    def calculate_flow_amount(self, mfa_df: pd.DataFrame, flows_list: List[str], product_list: List[str], material_list: List[str] = [], layer: str = "4") -> int:
        """Calculate summed flow amount with optional material and layer filters."""
        def build_layer_empty_filter(target_layer: str):
            target_layer_int = int(str(target_layer).strip())
            layer_empty_filter = True
            for layer_idx in range(target_layer_int + 1, 5):
                layer_empty_filter = layer_empty_filter & (mfa_df[f"Layer {layer_idx}"] == "")
            return layer_empty_filter

        if "elvEmbeddedElectronics" in material_list:
            # this serves to produce a debug point and nothing else
            pass
        if not layer:
            # If layer is not specified sum all products together for the total flow
            return mfa_df[
                        (mfa_df["Stock/Flow ID"].isin(flows_list)) 
                        & (mfa_df["Layer 4"] != "" )
                        & (mfa_df["Layer 1"].isin(product_list))
                    ]["Value"].sum()

        if "," not in layer:
            # If all material are in same layer
            layer = layer.strip()
            layer_empty_filter = build_layer_empty_filter(layer)
            return mfa_df[
                    (
                        True 
                        if not material_list 
                        else mfa_df['Layer ' + str(layer)].isin(material_list)
                    )
                    & (mfa_df["Stock/Flow ID"].isin(flows_list))
                    & layer_empty_filter
                    & (
                        mfa_df["Layer 1"].isin(product_list)
                    )
                ]["Value"].sum()
        
        layers = [layer_value.strip() for layer_value in layer.split(',')] if ',' in layer else [layer for _ in range(0, len(material_list))]
        if len(layers)!=len(material_list):
            raise ValueError("number of layers and materials are mismatched")
        amount = 0
        for i in range(0, len(material_list)):
            layer_empty_filter = build_layer_empty_filter(layers[i])
            amount += mfa_df[
                    (
                        True 
                        if not material_list 
                        else mfa_df['Layer ' + layers[i]]==material_list[i]
                    )
                    & (mfa_df["Stock/Flow ID"].isin(flows_list))
                    & layer_empty_filter
                    & (
                        mfa_df["Layer 1"].isin(product_list)
                    )
                ]["Value"].sum()
        return amount

    def run_lcia(self, lcia_methods):
        """Compute LCIA for all built LCIs and store results in memory."""
        total_lcis = len(self.lcis)
        for index, lci in enumerate(self.lcis, start=1):
            print(
                f"Running LCIA {index}/{total_lcis} for {lci.main_activity_flow_name}",
                flush=True,
            )
            lcia_result = self.compute_lcia_for_lci(lcia_methods=lcia_methods, lci=lci)
            self.lcia_results.append(lcia_result)

    def compute_lcia_for_lci(self, lcia_methods, lci):
        main_act = next(act for act in self.database if lci.main_activity_flow_name == act["name"].lower())
        avoided_act = next(act for act in self.database if lci.avoided_impacts_flow_name == act["name"].lower())

        total_impacts, avoided_impacts = {}, {}

        lca = bc.LCA({main_act: -1}, lcia_methods[0])
        lca.lci()
        for method in lcia_methods:
            if method != lca.method:
                lca.switch_method(method)
            lca.lcia()
            total_impacts[method[1]] = lca.score

        lca_avoided = bc.LCA({avoided_act: -1}, lcia_methods[0])
        lca_avoided.lci()
        for method in lcia_methods:
            if method != lca_avoided.method:
                lca_avoided.switch_method(method)
            lca_avoided.lcia()
            avoided_impacts[method[1]] = lca_avoided.score

        return SingleLCIAResult(total_impacts=total_impacts, avoided_impacts=avoided_impacts, lci=lci)
    
    def save_lcis(self):
        """Persist built LCIs to a timestamped pickle file."""
        StorageHelper.save_lcis(self.lcis)

    def load_latest_lcis(self):
        """Load the latest saved LCIs and write their processes to the database."""
        self.lcis = StorageHelper.load_latest_lcis()
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        self.database.write(big_dict)

    def load_specific_lcis(self, file_name: str):
        self.lcis = StorageHelper.load_specific_lcis(file_name=file_name)
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

    def load_specific_lcia_results(self, file_name: str):
        self.lcia_results = StorageHelper.load_specific_lcia_results(file_name=file_name)

    def export_lcia_results_to_excel(self, lcia_methods):
        """Export the in-memory LCIA results to an Excel workbook."""
        StorageHelper.save_lcia_results_to_excel(self.lcia_results, lcia_methods)

    def export_lcia_contributions_to_excel(self, lcia_methods, top_n_flows: int = 50):
        """Export contribution analysis (recovered materials + technosphere inputs) to Excel."""
        StorageHelper.save_lcia_contributions_to_excel(
            self.lcia_results,
            lcia_methods,
            top_n_flows=top_n_flows,
        )

    def export_template(self, lcia_methods):
        """Export template format"""
        StorageHelper.export_template_excel(
            self.lcia_results,
            lcia_methods
        )

    @classmethod
    def _validate_background_mode(cls, mode: str, parameter_name: str) -> str:
        mode_normalized = str(mode).strip().lower()
        if mode_normalized not in cls.VALID_SCENARIO_BACKGROUND_MODES:
            valid_modes = ", ".join(sorted(cls.VALID_SCENARIO_BACKGROUND_MODES))
            raise ValueError(f"Invalid {parameter_name}='{mode}'. Expected one of: {valid_modes}.")
        return mode_normalized

    def _resolve_background_db(self, mode: str):
        if mode == "scenario":
            return self.background_db
        if mode == "bauyear":
            return self.baseline_db
        return self.baseline_2020_db

    @staticmethod
    def _resolve_scrap_scenario_year(mode: str, scenario: Scenario, year: int):
        if mode == "scenario":
            return scenario, year
        if mode == "bauyear":
            return Scenario.BAU, year
        return Scenario.BAU, 2020

    @staticmethod
    def _merge_exchange(exchanges: List[dict], new_exchange: dict) -> None:
        """Merge an exchange into a list, summing amounts for duplicate entries."""
        for exchange in exchanges:
            if exchange["name"] == new_exchange["name"] and exchange["input"] == new_exchange["input"]:
                exchange["amount"] += new_exchange["amount"]
                return
        exchanges.append(new_exchange)

    @staticmethod
    @staticmethod
    def _split_csv_values(value) -> List[str]:
        if pd.isna(value) or value == "":
            return []
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @staticmethod
    def _parse_optional_numeric(value, default: float = 1.0) -> float:
        if pd.isna(value) or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric value '{value}' in configuration") from exc

    def build_scrap_processes(self, ecoinvent_db: bd.Database):
        """
        Manually added piece of code to create (scrap) processes that can be universally used by the other processes
        """
        scrap_processes = []
        for sheet_name in pd.ExcelFile(SCRAP_PROCESSES_FILE).sheet_names:
            activity_id, activity_dict = BrightwayHelpers.build_base_process(
            name=sheet_name,
            database_name=self.scrap.name,
            is_waste=True
            )
            exchanges_list = pd.read_excel(
                SCRAP_PROCESSES_FILE,
                sheet_name=sheet_name,
            ).fillna("")
            for _, row in exchanges_list.iterrows():
                external_exchange = BrightwayHelpers.build_external_exchange(
                    database=ExternalDatabase(row['database'].upper()),
                    ecoinvent=ecoinvent_db,
                    biosphere=self.biosphere,
                    scrap=self.scrap,
                    process_name = row['activity name'],
                    location=row['location'],
                    amount=row['amount'],
                    unit='unknown',
                    flow_direction=row["flow direction"],
                    categories=tuple(map(str.strip, row["categories"].split(", "))),
                    reference_product=row['reference product'] if row['database'] == ExternalDatabase.ECOINVENT else None,
                )
                self._merge_exchange(
                activity_dict[(self.scrap.name, activity_id)]["exchanges"],
                external_exchange,
            )
            scrap_processes.append(activity_dict)
        return scrap_processes
