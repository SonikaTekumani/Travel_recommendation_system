import pandas as pd
from pathlib import Path

# Adjust to your repo layout; place CSVs under app/data or set env var DATA_DIR
DATA_DIR = Path(
    # Prefer env var if provided
    (Path.cwd() / "app" / "data")
).resolve()

def _csv(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (DATA_DIR / path)

def get_dataframes():
    """
    Loads all required CSVs.
    Change filenames if your dataset names differ.
    """
    # If you want to keep absolute Windows paths, replace below with them.
    states_df = pd.read_csv(_csv("states_and_union_territories.csv"))
    cities_df = pd.read_csv(_csv("cities.csv"))
    budget_duration_df = pd.read_csv(_csv("city_budget_duration.csv"))
    cities_type_df = pd.read_csv(_csv("cities_type_data.csv"))
    return states_df, cities_df, budget_duration_df, cities_type_df

def build_type_name_map(cities_type_df: pd.DataFrame) -> dict[int, str]:
    if "Type_ID" not in cities_type_df.columns or "Type_Name" not in cities_type_df.columns:
        return {}
    dedup = cities_type_df[["Type_ID", "Type_Name"]].drop_duplicates()
    return dict(zip(dedup["Type_ID"].astype(int), dedup["Type_Name"].astype(str)))
