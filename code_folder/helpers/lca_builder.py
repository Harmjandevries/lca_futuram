import pandas as pd
from typing import Dict, Iterable, List, Tuple
from .constants import SingleLCI, SingleLCIAResult, ExternalDatabase,  Location, Scenario, Route, Product, INPUT_DATA_FOLDER, ECOINVENT_NAME, BIOSPHERE_NAME, route_lci_names, SUPPORTED_YEARS_OBS, SUPPORTED_YEARS_SCENARIO
from premise_superstructure import SCENARIO_MAP
import bw2data as bd
import bw2calc as bc
from .brightway_helpers import BrightwayHelpers
from .storage_helper import StorageHelper


class LCABuilder:
    """
    Build and evaluate LCIs/LCIAs from RM outputs and LCI builder sheets.

    This class orchestrates:
    - Reading per-route/product inputs
    - Building Brightway processes and exchanges
    - Running LCIA and persisting results
    """
    def __init__(self):
        # Setup BW databases
        self.ecoinvent = bd.Database(ECOINVENT_NAME)
        self.biosphere = bd.Database(BIOSPHERE_NAME)

        self.lcis: List[SingleLCI] = []
        self.lcia_results: List[SingleLCIAResult] = []
        self._scenario_parameter_cache: Dict[Tuple[str, int], str] = {}

    def build_all_lcis(self,
                       database: bd.Database,
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
                            lci = self.build_lci(database=database, route=route, product=product, year=year, scenario=scenario, location=location)
                            if lci:
                                self.lcis.append(lci)
                                print(f"Finished LCI for route: {route.value}, scenario: {scenario.value}, product: {product.value}, year: {year}, location: {location.value}")


        # Adds all the lci_dict together in a big dict
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        database.write(big_dict)

    def build_lci(self, database: bd.Database, route:Route, product:Product, year: int, scenario:Scenario, location:Location):
        """Build a single LCI for a specific (route, product, year, scenario, location)."""
        self._activate_background_scenario(scenario=scenario, year=year)
        mfa_df, lci_builder_df = self._read_inputs(route=route, product=product, year=year, scenario=scenario)
        if lci_builder_df is None:
            return

        lci_dict = {}
        output_amounts_alloy = {}
        output_amounts_element = {}

        main_activity_id, main_activity_flow_name, input_amount, product_list = self._build_main_activity(
            database=database,
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            route=route,
            year=year,
            scenario=scenario,
            mfa_df=mfa_df,
        )

        if input_amount == 0:
            raise ValueError(
                "No inflow amount found for the specified configuration. "
                f"route={route.value}, product={product.value}, year={year}, "
                f"scenario={scenario.value}, location={location.value}. "
                "Check rm_output.csv and lci_builder.xlsx inputs."
            )

        avoided_impacts_activity_id, avoided_impacts_flow_name = self._build_avoided_activity(
            database=database,
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            route=route,
            year=year,
            scenario=scenario,
        )

        self._add_recovered_materials(
            database=database,
            lci_dict=lci_dict,
            lci_builder_df=lci_builder_df,
            main_activity_id=main_activity_id,
            avoided_impacts_activity_id=avoided_impacts_activity_id,
            product_list=product_list,
            mfa_df=mfa_df,
            input_amount=input_amount,
            output_amounts_alloy=output_amounts_alloy,
            output_amounts_element=output_amounts_element,
        )

        self._add_external_exchanges(
            database=database,
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
            total_inflow_amount=input_amount,
            output_amounts_alloy=output_amounts_alloy,
            output_amounts_element=output_amounts_element)

    def _activate_background_scenario(self, scenario: Scenario, year: int) -> None:
        """Activate the Premise parameter set matching the requested scenario/year."""
        if scenario.value not in SCENARIO_MAP:
            return

        spec = SCENARIO_MAP[scenario.value]
        cache_key = (scenario.value, year)

        if cache_key not in self._scenario_parameter_cache:
            parameter_key = self._find_parameter_key(
                model=spec["model"],
                pathway=spec["pathway"],
                year=year,
            )
            self._scenario_parameter_cache[cache_key] = parameter_key

        parameter_key = self._scenario_parameter_cache[cache_key]

        if parameter_key is None:
            return

        from bw2data.parameters import scenarios as bw_scenarios  # Lazy import to avoid BW dependency at module load time

        try:
            bw_scenarios[parameter_key].apply()
        except KeyError as exc:  # pragma: no cover - defensive guard if BW state changes between runs
            raise KeyError(
                f"Premise scenario '{parameter_key}' not available in Brightway. "
                "Rebuild the superstructure database before running LCA."
            ) from exc

    def _find_parameter_key(self, model: str, pathway: str, year: int) -> str:
        """Return the Brightway parameter-set name for a Premise (model, pathway, year)."""
        from bw2data.parameters import scenarios as bw_scenarios

        model_lower = model.lower()
        pathway_lower = pathway.lower()
        year_str = str(year)

        def _iter_items() -> Iterable[Tuple[str, object]]:
            if hasattr(bw_scenarios, "items"):
                try:
                    return bw_scenarios.items()
                except TypeError:
                    pass
            if hasattr(bw_scenarios, "data"):
                return bw_scenarios.data.items()  # type: ignore[attr-defined]
            if hasattr(bw_scenarios, "_data"):
                return bw_scenarios._data.items()  # type: ignore[attr-defined]
            if hasattr(bw_scenarios, "keys"):
                return ((key, bw_scenarios[key]) for key in bw_scenarios.keys())
            return []

        for key, parameter in _iter_items():
            haystack_parts = [str(key).lower()]
            metadata = getattr(parameter, "metadata", None) or getattr(parameter, "meta", None)
            if metadata:
                if isinstance(metadata, dict):
                    haystack_parts.append(" ".join(str(v).lower() for v in metadata.values()))
                else:
                    haystack_parts.append(str(metadata).lower())

            haystack = " ".join(haystack_parts)

            if all(needle in haystack for needle in (model_lower, pathway_lower, year_str)):
                return str(key)

        raise KeyError(
            "Could not find a Premise scenario parameter set in Brightway "
            f"for model='{model}', pathway='{pathway}', year={year}. "
            "Ensure the superstructure database has been generated with matching configurations."
        )

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

    def _build_main_activity(self, database: bd.Database, lci_dict: dict, lci_builder_df: pd.DataFrame, route: Route, year: int, scenario: Scenario, mfa_df: pd.DataFrame):
        """Create the main activity and compute total inflow amount.

        Returns (main_activity_id, main_activity_flow_name, input_amount, product_list).
        """
        main_activity_row = lci_builder_df[lci_builder_df["LCI Flow Type"]=="production"]
        main_activity_flow_name = f"{route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        main_activity_id, main_activity_dict = BrightwayHelpers.build_base_process(
            name=main_activity_flow_name,
            is_waste=True
        )
        lci_dict.update(main_activity_dict)
        input_flow_ids = [m.strip() for m in main_activity_row.iloc[0]['Stock/Flow IDs'].split(',')]
        product_list = [] if not main_activity_row["Materials"].iloc[0] else [m.strip() for m in main_activity_row["Materials"].iloc[0].split(',')]
        input_amount = self.calculate_flow_amount(mfa_df=mfa_df, flows_list=input_flow_ids, product_list=product_list, layer="")
        return main_activity_id, main_activity_flow_name, input_amount, product_list

    def _build_avoided_activity(self, database: bd.Database, lci_dict: dict, lci_builder_df: pd.DataFrame, route: Route, year: int, scenario: Scenario):
        """Create the avoided impacts activity.

        Returns (avoided_impacts_activity_id, avoided_impacts_flow_name).
        """
        main_activity_row = lci_builder_df[lci_builder_df["LCI Flow Type"]=="production"]
        avoided_impacts_flow_name =  f"avoided impacts for {route_lci_names[route]} {main_activity_row['LCI Flow Name'].iloc[0]} - {year} - {scenario.value}".lower()
        avoided_impacts_activity_id, avoided_impacts_dict = BrightwayHelpers.build_base_process(
            name=avoided_impacts_flow_name,
            is_waste=False
        )
        lci_dict.update(avoided_impacts_dict)
        return avoided_impacts_activity_id, avoided_impacts_flow_name

    def _add_recovered_materials(self, database: bd.Database, lci_dict: dict, lci_builder_df: pd.DataFrame, main_activity_id: str, avoided_impacts_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float, output_amounts_alloy: dict, output_amounts_element: dict) -> None:
        """Add recovered material processes and their exchanges to main and avoided activities."""
        output_recovered_material_rows = lci_builder_df[
            (lci_builder_df["Flow Direction"]=="recovered")
        ]
        for _, output_reco_row in output_recovered_material_rows.iterrows():
            material_list = [m.strip() for m in output_reco_row["Materials"].split(',')]
            flows_list = [m.strip() for m in output_reco_row["Stock/Flow IDs"].split(',')]

            process_name = output_reco_row['LCI Flow Name']
            existing_id = BrightwayHelpers.get_existing_process_id_by_name(lcis=self.lcis, name=process_name)
            multiplier = self._get_recovery_multiplier(output_reco_row)

            if existing_id:
                process_id = existing_id
            else:
                process_id, process_dict = BrightwayHelpers.build_base_process(process_name)
                lci_dict.update(process_dict)

            total_material = self.calculate_flow_amount(
                mfa_df=mfa_df,
                flows_list=flows_list,
                product_list=product_list,
                material_list=material_list,
                layer=str(output_reco_row["Layer"]))  * multiplier
            technosphere_exchange = BrightwayHelpers.build_technosphere_exchange(
                name=output_reco_row["LCI Flow Name"],
                process_id=process_id,
                amount=-total_material / input_amount,
            )
            self._merge_exchange(
                lci_dict[(database.name, main_activity_id)]["exchanges"],
                technosphere_exchange,
            )
            output_amounts_alloy[output_reco_row['LCI Flow Name']] = total_material / input_amount
            for i in range(0, len(material_list)):
                material = material_list[i]
                layer = output_reco_row["Layer"].split(",")[i] if "," in output_reco_row["Layer"] else output_reco_row["Layer"]
                amount = self.calculate_flow_amount(mfa_df=mfa_df, flows_list=flows_list, product_list=product_list, material_list=[material],layer=layer) * multiplier
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
            self._merge_exchange(
                lci_dict[(database.name, avoided_impacts_activity_id)]["exchanges"],
                avoided_impact_exchange,
            )

    def _add_external_exchanges(self, database: bd.Database, lci_dict: dict, lci_builder_df: pd.DataFrame, main_activity_id: str, product_list: list, mfa_df: pd.DataFrame, input_amount: float) -> None:
        """Add external exchanges (ecoinvent/biosphere) to the main activity."""
        external_activity_rows = lci_builder_df[(lci_builder_df['Linked process']!='')&(lci_builder_df['Flow Direction']!="recovered")]
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
                lci_dict[(database.name, main_activity_id)]["exchanges"],
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

    def run_lcia(self, database: bd.Database, lcia_method):
        """Compute LCIA for all built LCIs and store results in memory."""
        for lci in self.lcis:
            lcia_result = self.compute_lcia_for_lci(database=database, lcia_method=lcia_method, lci=lci)
            self.lcia_results.append(lcia_result)

    def compute_lcia_for_lci(self, database: bd.Database, lcia_method: tuple, lci: SingleLCI):
        """Compute LCIA for a single LCI, returning a SingleLCIAResult."""
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
        """Persist built LCIs to a timestamped pickle file."""
        StorageHelper.save_lcis(self.lcis)

    def load_latest_lcis(self, database: bd.Database):
        """Load the latest saved LCIs and write their processes to the database."""
        self.lcis = StorageHelper.load_latest_lcis()
        big_dict = {k: v for lci in self.lcis for k, v in lci.lci_dict.items()}
        database.write(big_dict)

    def save_database_to_excel(self, database: bd.Database):
        """Export the current database to an Excel file in output_data."""
        StorageHelper.save_database_to_excel(database)

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

        unit_conversion = _parse(row.get("Unit conversion", 1.0))
        recovery_efficiency = _parse(row.get("Recovery efficiency", 1.0))
        return unit_conversion * recovery_efficiency