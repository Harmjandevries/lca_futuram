from datetime import datetime
import pickle
import os
import shutil

import bw2data as bd
import bw2calc as bc
import pandas as pd
from bw2io.export.excel import write_lci_excel

from lca_futuram.helpers.constants import (
    BW_FORMAT_LCIS_DATA_FOLDER,
    functional_unit_label,
    LCIA_RESULTS_EXCEL_FOLDER,
    LOADABLE_LCI_DATA_FOLDER,
    LOADABLE_LCIA_RESULTS_DATA_FOLDER,
    Scenario,
)

class StorageHelper:
    """Utility functions for persisting and loading LCIs, LCIA results, and DB exports."""
    @staticmethod
    def save_lcis(lcis):
        """Save LCIs to a timestamped pickle in output_data/loadable_lcis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lci_run_{timestamp}.pkl"
        file_path = os.path.join(LOADABLE_LCI_DATA_FOLDER, filename)
        with open(file_path, "wb") as f:
            pickle.dump(lcis, f)

        print(f"✅ Saved {len(lcis)} LCIs to {file_path}")

    @staticmethod
    def load_latest_lcis():
        """Load the most recent saved LCIs from disk. Returns None if none exist."""
        files = [f for f in os.listdir(LOADABLE_LCI_DATA_FOLDER) if f.startswith("lci_run_") and f.endswith(".pkl")]
        if not files:
            print("⚠️ No LCI files found in folder.")
            return

        files.sort(reverse=True)
        latest_file = files[0]
        file_path = os.path.join(LOADABLE_LCI_DATA_FOLDER, latest_file)

        with open(file_path, "rb") as f:
            lcis = pickle.load(f)
        print(f"✅ Loaded {len(lcis)} LCIs from {file_path}")
        return lcis

    @staticmethod
    def load_specific_lcis(file_name: str):
        file_path = os.path.join(LOADABLE_LCI_DATA_FOLDER, file_name)
        with open(file_path, "rb") as f:
            lcis = pickle.load(f)
        print(f"✅ Loaded {len(lcis)} lcis results from {file_path}")
        return lcis

    @staticmethod
    def save_database_to_excel(database: bd.Database):
        """Export the given Brightway database to Excel into output_data/bw_format_lcis."""
        os.makedirs(BW_FORMAT_LCIS_DATA_FOLDER, exist_ok=True)

        # Use database name from database
        db_name = database.name

        # Export using Brightway's current API (returns the created file path)
        exported_path = write_lci_excel(db_name)

        # Move/copy export to our desired folder with a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_filename = f"{db_name}_export_{timestamp}.xlsx"
        dest_path = os.path.join(BW_FORMAT_LCIS_DATA_FOLDER, dest_filename)
        try:
            shutil.move(exported_path, dest_path)
        except Exception:
            # If move fails (e.g., across volumes), fall back to copy
            shutil.copy2(exported_path, dest_path)

        print(f"✅ Saved database '{db_name}' to Excel at {dest_path}")

    @staticmethod
    def save_lcia_results(lcia_results):
        """Save LCIA results to a timestamped pickle in output_data/loadable_lcia_results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lcia_run_{timestamp}.pkl"
        file_path = os.path.join(LOADABLE_LCIA_RESULTS_DATA_FOLDER, filename)
        with open(file_path, "wb") as f:
            pickle.dump(lcia_results, f)

        print(f"✅ Saved {len(lcia_results)} LCIA results to {file_path}")

    @staticmethod
    def load_latest_lcia_results():
        """Load the most recent saved LCIA results from disk. Returns None if none exist."""
        files = [f for f in os.listdir(LOADABLE_LCIA_RESULTS_DATA_FOLDER) if f.startswith("lcia_run_") and f.endswith(".pkl")]
        if not files:
            print("⚠️ No LCIA result files found in folder.")
            return

        files.sort(reverse=True)
        latest_file = files[0]
        file_path = os.path.join(LOADABLE_LCIA_RESULTS_DATA_FOLDER, latest_file)

        with open(file_path, "rb") as f:
            lcia_results = pickle.load(f)
        print(f"✅ Loaded {len(lcia_results)} LCIA results from {file_path}")
        return lcia_results

    @staticmethod
    def load_specific_lcia_results(file_name: str):
        """Load specific lcia jresults"""
        file_path = os.path.join(LOADABLE_LCIA_RESULTS_DATA_FOLDER, file_name)
        with open(file_path, "rb") as f:
            lcia_results = pickle.load(f)
        print(f"✅ Loaded {len(lcia_results)} LCIA results from {file_path}")
        return lcia_results

    @staticmethod
    def save_lcia_results_to_excel(lcia_results, lcia_methods):
        """Export LCIA results to Excel with one row per scenario/year/route/product and impact type."""
        if not lcia_results:
            print("⚠️ No LCIA results to export to Excel.")
            return

        os.makedirs(LCIA_RESULTS_EXCEL_FOLDER, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(LCIA_RESULTS_EXCEL_FOLDER, f"lcia_results_{timestamp}.xlsx")

        method_labels = [method[1] for method in lcia_methods]

        def _build_rows(scale_impacts: bool = False, impact_kind: str = "net"):
            rows = []
            for result in lcia_results:
                metadata = {
                    "Scenario": result.lci.scenario.value,
                    "Year": result.lci.year,
                    "Location": result.lci.location.value,
                    "Product": result.lci.product.value,
                    "RecyclingRoute": result.lci.route.value,
                }

                scale_factor = (
                    result.lci.total_inflow_amount if scale_impacts else 1
                )

                row = {**metadata, "Functional_unit": functional_unit_label(result.lci.route)}
                for label in method_labels:
                    total = result.total_impacts.get(label) or 0.0
                    avoided = result.avoided_impacts.get(label) or 0.0
                    if impact_kind == "direct":
                        value = total
                    elif impact_kind == "avoided":
                        value = avoided
                    else:
                        value = total - avoided
                    row[label] = value * scale_factor
                rows.append(row)
            return rows

        columns = [
            "Scenario",
            "Year",
            "Location",
            "Product",
            "RecyclingRoute",
            "Functional_unit",
            *method_labels,
        ]
        df = pd.DataFrame(_build_rows(scale_impacts=False, impact_kind="net"), columns=columns)
        df_direct = pd.DataFrame(_build_rows(scale_impacts=False, impact_kind="direct"), columns=columns)
        df_avoided = pd.DataFrame(_build_rows(scale_impacts=False, impact_kind="avoided"), columns=columns)
        df_total = pd.DataFrame(_build_rows(scale_impacts=True, impact_kind="net"), columns=columns)

        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="impact_per_kg", index=False)
            df_direct.to_excel(writer, sheet_name="direct_per_kg", index=False)
            df_avoided.to_excel(writer, sheet_name="avoided_per_kg", index=False)
            df_total.to_excel(writer, sheet_name="total_impacts", index=False)

        print(f"✅ Saved LCIA results to Excel at {file_path}")

    @staticmethod
    def save_lcia_contributions_to_excel(lcia_results, lcia_methods, top_n_flows: int = 50):
        """Export contribution analysis to Excel for recovered materials and technosphere inputs."""
        if not lcia_results:
            print("⚠️ No LCIA results to export contribution analysis.")
            return

        os.makedirs(LCIA_RESULTS_EXCEL_FOLDER, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(LCIA_RESULTS_EXCEL_FOLDER, f"lcia_contributions_{timestamp}.xlsx")

        recovered_rows = []
        process_rows = []
        total_results = len(lcia_results)

        def _activity_from_name(db, name_lower):
            return next(act for act in db if name_lower == act["name"].lower())

        for index, result in enumerate(lcia_results, start=1):
            if index == 1 or index % 10 == 0 or index == total_results:
                print(f"Contribution analysis progress: {index}/{total_results}", flush=True)
            if not result.lci.lci_dict:
                continue

            db_name = next(iter(result.lci.lci_dict.keys()))[0]
            db = bd.Database(db_name)

            try:
                main_act = _activity_from_name(db, result.lci.main_activity_flow_name)
                avoided_act = _activity_from_name(db, result.lci.avoided_impacts_flow_name)
            except StopIteration:
                print(f"⚠️ Could not find activities for {result.lci.main_activity_flow_name}")
                continue

            metadata = {
                "Scenario": result.lci.scenario.value,
                "Year": result.lci.year,
                "Location": result.lci.location.value,
                "Product": result.lci.product.value,
                "RecyclingRoute": result.lci.route.value,
            }

            lca_main = bc.LCA({main_act: -1}, lcia_methods[0])
            lca_main.lci()
            lca_avoided = bc.LCA({avoided_act: -1}, lcia_methods[0])
            lca_avoided.lci()

            avoided_exchanges = [
                exc for exc in avoided_act.exchanges()
                if exc.get("type") == "technosphere"
            ]
            main_exchanges = [
                exc for exc in main_act.exchanges()
                if exc.get("type") == "technosphere"
            ]

            for method in lcia_methods:
                if method != lca_main.method:
                    lca_main.switch_method(method)
                lca_main.lcia()

                if method != lca_avoided.method:
                    lca_avoided.switch_method(method)
                lca_avoided.lcia()

                main_scores = []
                for exc in main_exchanges:
                    demand = {exc.input: exc["amount"]}
                    try:
                        lca_main.redo_lcia(demand)
                        score = lca_main.score
                    except Exception:
                        lca_tmp = bc.LCA(demand, method)
                        lca_tmp.lci()
                        lca_tmp.lcia()
                        score = lca_tmp.score
                    main_scores.append((exc, score))

                if top_n_flows:
                    main_scores.sort(key=lambda item: abs(item[1]), reverse=True)
                    main_scores = main_scores[:top_n_flows]

                for exc, score in main_scores:
                    direction = "input" if exc.get("amount", 0) > 0 else "output"
                    process_rows.append({
                        **metadata,
                        "ImpactCategory": method[1],
                        "ExchangeName": exc.get("name", ""),
                        "ExchangeUnit": exc.get("unit", ""),
                        "ExchangeAmount": exc.get("amount", 0),
                        "ExchangeLocation": exc.get("location", ""),
                        "ExchangeDirection": direction,
                        "Contribution": float(score),
                    })

                for exc in avoided_exchanges:
                    demand = {exc.input: exc["amount"]}
                    try:
                        lca_avoided.redo_lcia(demand)
                        score = lca_avoided.score
                    except Exception:
                        lca_tmp = bc.LCA(demand, method)
                        lca_tmp.lci()
                        lca_tmp.lcia()
                        score = lca_tmp.score

                    recovered_rows.append({
                        **metadata,
                        "ImpactCategory": method[1],
                        "ExchangeName": exc.get("name", ""),
                        "ExchangeUnit": exc.get("unit", ""),
                        "ExchangeAmount": exc.get("amount", 0),
                        "ExchangeLocation": exc.get("location", ""),
                        "Contribution": float(score),
                    })

        recovered_df = pd.DataFrame(recovered_rows)
        process_df = pd.DataFrame(process_rows)

        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            recovered_df.to_excel(writer, sheet_name="recovered_materials", index=False)
            process_df.to_excel(writer, sheet_name="process_contributions", index=False)

        print(f"✅ Saved contribution analysis to Excel at {file_path}")

    @staticmethod
    def export_template_excel(
            lcia_results,
            lcia_methods
        ):
        """Export a compact template Excel with total GWP and per-category totals."""
        if not lcia_results:
            print("ƒsÿ‹÷? No LCIA results to export template.")
            return

        os.makedirs(LCIA_RESULTS_EXCEL_FOLDER, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(LCIA_RESULTS_EXCEL_FOLDER, f"lcia_template_{timestamp}.xlsx")

        target_year = 2050
        scenarios = [Scenario.BAU, Scenario.REC, Scenario.CIR]
        method_labels = [method[1] for method in lcia_methods]
        gwp_label = next(
            (label for label in method_labels if label.lower() == "climate change"),
            method_labels[0],
        )
        present_scenarios = {
            result.lci.scenario
            for result in lcia_results
            if result.lci.year == target_year and result.lci.scenario in scenarios
        }
        missing_scenarios = [scenario for scenario in scenarios if scenario not in present_scenarios]
        if missing_scenarios:
            missing_labels = ", ".join(scenario.value for scenario in missing_scenarios)
            message = (
                f"Missing LCIA results for year {target_year} and scenarios: {missing_labels}. "
                "Template export may be incomplete."
            )
            print(f"ƒsÿ‹÷? {message}")
            try:
                raise ValueError(message)
            except ValueError:
                pass

        def _scaled_scores(result, label):
            total = result.total_impacts.get(label, 0.0) or 0.0
            avoided = result.avoided_impacts.get(label, 0.0) or 0.0
            scale = result.lci.total_inflow_amount or 0.0
            direct = total * scale
            net = (total - avoided) * scale
            return direct, net

        column_order = [
            f"{Scenario.BAU.value} {target_year} net",
            f"{Scenario.REC.value} {target_year} net",
            f"{Scenario.CIR.value} {target_year} net",
            f"{Scenario.BAU.value} {target_year} direct",
            f"{Scenario.REC.value} {target_year} direct",
            f"{Scenario.CIR.value} {target_year} direct",
        ]

        product_rows = {}
        for result in lcia_results:
            if result.lci.year != target_year:
                continue
            if result.lci.scenario not in scenarios:
                continue

            product = result.lci.product.value
            if product not in product_rows:
                product_rows[product] = {"Product": product, **{col: 0.0 for col in column_order}}

            direct, net = _scaled_scores(result, gwp_label)
            scenario_value = result.lci.scenario.value
            product_rows[product][f"{scenario_value} {target_year} net"] += net
            product_rows[product][f"{scenario_value} {target_year} direct"] += direct

        product_df = pd.DataFrame(product_rows.values(), columns=["Product", *column_order])

        category_rows = []
        for label in method_labels:
            row = {"ImpactCategory": label, **{col: 0.0 for col in column_order}}
            for result in lcia_results:
                if result.lci.year != target_year:
                    continue
                if result.lci.scenario not in scenarios:
                    continue
                direct, net = _scaled_scores(result, label)
                scenario_value = result.lci.scenario.value
                row[f"{scenario_value} {target_year} net"] += net
                row[f"{scenario_value} {target_year} direct"] += direct
            category_rows.append(row)

        category_df = pd.DataFrame(category_rows, columns=["ImpactCategory", *column_order])

        
        obs_year = 2020
        obs_direct = 0.0
        obs_net = 0.0
        for result in lcia_results:
            if result.lci.year != obs_year:
                continue
            if result.lci.scenario != Scenario.OBS:
                continue
            direct, net = _scaled_scores(result, gwp_label)
            obs_direct += direct
            obs_net += net

        obs_total_df = pd.DataFrame(
            [{
                "Scenario": Scenario.OBS.value,
                "Year": obs_year,
                "ImpactCategory": gwp_label,
                "Direct": obs_direct,
                "Net": obs_net,
            }]
        )

        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            product_df.to_excel(writer, sheet_name="gwp_total", index=False)
            category_df.to_excel(writer, sheet_name="impact_categories_total", index=False)
            obs_total_df.to_excel(writer, sheet_name="obs_2020_total", index=False)

        print(f"ƒo. Saved template Excel at {file_path}")
