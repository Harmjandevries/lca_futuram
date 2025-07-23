from datetime import datetime
import pickle
from helpers.constants import LOADABLE_LCI_DATA_FOLDER, BW_FORMAT_LCIS_DATA_FOLDER, LOADABLE_LCIA_RESULTS_DATA_FOLDER
from bw2io.export.excel import write_lci_excel
import os
import bw2data as bd

class StorageHelper:
    @staticmethod
    def save_lcis(lcis):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lci_run_{timestamp}.pkl"
        file_path = os.path.join(LOADABLE_LCI_DATA_FOLDER, filename)
        with open(file_path, "wb") as f:
            pickle.dump(lcis, f)

        print(f"✅ Saved {len(lcis)} LCIs to {file_path}")

    @staticmethod
    def load_latest_lcis():
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
        os.makedirs(BW_FORMAT_LCIS_DATA_FOLDER, exist_ok=True)

        # Use database name from database
        db_name = database.name

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{db_name}_export_{timestamp}.xlsx"
        file_path = os.path.join(BW_FORMAT_LCIS_DATA_FOLDER, filename)

        # Call Brightway's export function
        write_lci_excel(db_name, dirpath=BW_FORMAT_LCIS_DATA_FOLDER)
        print(f"✅ Saved database '{db_name}' to Excel at {file_path}")

    @staticmethod
    def save_lcia_results(lcia_results):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lcia_run_{timestamp}.pkl"
        file_path = os.path.join(LOADABLE_LCIA_RESULTS_DATA_FOLDER, filename)
        with open(file_path, "wb") as f:
            pickle.dump(lcia_results, f)

        print(f"✅ Saved {len(lcia_results)} LCIA results to {file_path}")

    @staticmethod
    def load_latest_lcia_results():
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