from datetime import datetime
import pickle
import os
import shutil

import bw2data as bd
import pandas as pd
from bw2io.export.excel import write_lci_excel

from code_folder.helpers.constants import (
    BW_FORMAT_LCIS_DATA_FOLDER,
    LCIA_RESULTS_EXCEL_FOLDER,
    LOADABLE_LCI_DATA_FOLDER,
    LOADABLE_LCIA_RESULTS_DATA_FOLDER,
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
    def save_lcia_results_to_excel(lcia_results, lcia_methods):
        """Export LCIA results to Excel with one row per scenario/year/route/product and impact type."""
        if not lcia_results:
            print("⚠️ No LCIA results to export to Excel.")
            return

        os.makedirs(LCIA_RESULTS_EXCEL_FOLDER, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(LCIA_RESULTS_EXCEL_FOLDER, f"lcia_results_{timestamp}.xlsx")

        method_labels = [method[1] for method in lcia_methods]

        rows = []
        for result in lcia_results:
            metadata = {
                "Scenario": result.lci.scenario.value,
                "Year": result.lci.year,
                "Location": result.lci.location.value,
                "Product": result.lci.product.value,
                "RecyclingRoute": result.lci.route.value,
            }

            for impact_type, impacts in (
                ("normal", result.total_impacts),
                ("avoided", result.avoided_impacts),
            ):
                row = {**metadata, "Impact_type": impact_type}
                for label in method_labels:
                    row[label] = impacts.get(label)
                rows.append(row)

        columns = [
            "Scenario",
            "Year",
            "Location",
            "Product",
            "RecyclingRoute",
            "Impact_type",
            *method_labels,
        ]
        df = pd.DataFrame(rows, columns=columns)

        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="impact_per_kg", index=False)

        print(f"✅ Saved LCIA results to Excel at {file_path}")
