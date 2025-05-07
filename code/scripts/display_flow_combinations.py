import pandas as pd

# Script to read TC file and interpret all possible flow combinations

# Load your DataFrame
df = pd.read_csv("data/recovery_model_outputs/21_03_weee_cat1/TCs.csv")

inflow_cols = ["Input_FlowID"]
outflow_cols = ["Output_FlowID"]

combinations = df[inflow_cols + outflow_cols].drop_duplicates().reset_index(drop=True)
print(combinations)
