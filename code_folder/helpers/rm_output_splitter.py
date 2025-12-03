"""Utility for splitting recovery model outputs into targeted CSV files.

The script reads a single recovery model output CSV and writes filtered
subsets based on pre-defined groups of Stock/Flow IDs and Layer 1 values.

Usage
-----
python -m code_folder.helpers.rm_output_splitter \
    --input data/input_data/<route>/rm_output.csv \
    --output-dir data/input_data/<route>/splits

Edit ``OUTPUT_DEFINITIONS`` below to define the desired subsets.
Each definition needs a unique ``name`` plus lists of ``layer1_values`` and
``stockflow_ids``. The script keeps all years, scenarios and locations while
filtering on those two columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import pandas as pd


@dataclass(frozen=True)
class OutputDefinition:
    """Describes one filtered output file."""

    name: str
    layer1_values: List[str]
    stockflow_ids: List[str]

    def select(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return rows matching the configured Layer 1 and Stock/Flow IDs."""

        return frame[
            frame["Layer 1"].isin(self.layer1_values)
            & frame["Stock/Flow ID"].isin(self.stockflow_ids)
        ]


# Edit this list to describe the splits you want to generate.
# Example:
# OutputDefinition(
#     name="anode_graphite",
#     layer1_values=["battLiCO_subsub"],
#     stockflow_ids=["BATT_2RM_AAMRegeneration"],
# ),
OUTPUT_DEFINITIONS: List[OutputDefinition] = []


REQUIRED_COLUMNS = {"Year", "Scenario", "Location", "Stock/Flow ID", "Layer 1", "Layer 2", "Layer 3", "Layer 4", "Value"}


def validate_columns(frame: pd.DataFrame) -> None:
    """Ensure the recovery model output has the expected columns."""

    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input file is missing required columns: {missing_list}")


def ensure_output_dir(path: Path) -> None:
    """Create the output directory if it does not exist."""

    path.mkdir(parents=True, exist_ok=True)


def load_input(path: Path) -> pd.DataFrame:
    """Load the recovery model output CSV."""

    data = pd.read_csv(path)
    validate_columns(data)
    return data


def generate_outputs(definitions: Iterable[OutputDefinition], frame: pd.DataFrame, output_dir: Path) -> None:
    """Write one CSV per definition to the output directory."""

    for definition in definitions:
        selection = definition.select(frame)
        output_path = output_dir / f"rm_output_{definition.name}.csv"
        selection.to_csv(output_path, index=False)
        print(
            f"Wrote {len(selection)} rows to {output_path} "
            f"(Layer 1 in {definition.layer1_values}, Stock/Flow IDs in {definition.stockflow_ids})"
        )


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the full recovery model output CSV (rm_output.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the split CSV files (defaults to the input file's directory)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not OUTPUT_DEFINITIONS:
        raise ValueError("No output definitions provided. Populate OUTPUT_DEFINITIONS before running the script.")

    input_path: Path = args.input
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_dir = args.output_dir or input_path.parent
    ensure_output_dir(output_dir)

    frame = load_input(input_path)
    generate_outputs(OUTPUT_DEFINITIONS, frame, output_dir)


if __name__ == "__main__":
    main()
