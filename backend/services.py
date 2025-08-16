import pandas as pd
from pathlib import Path

# Point to the backend folder where this file lives
BASE_DIR = Path(__file__).resolve().parent

def get_dataframes():
    """
    Loads all required CSVs from the backend directory.
    """
    states_df = pd.read_csv(BASE_DIR / "states_and_union_territories.csv")
    cities_df = pd.read_csv(BASE_DIR / "cities.csv")
    budget_duration_df = pd.read_csv(BASE_DIR / "city_budget_duration.csv")
    cities_type_df = pd.read_csv(BASE_DIR / "cities_type_data.csv")
    return states_df, cities_df, budget_duration_df, cities_type_df

def build_type_name_map(cities_type_df: pd.DataFrame) -> dict[int, str]:
    if "Type_ID" not in cities_type_df.columns or "Type_Name" not in cities_type_df.columns:
        return {}
    dedup = cities_type_df[["Type_ID", "Type_Name"]].drop_duplicates()
    return dict(zip(dedup["Type_ID"].astype(int), dedup["Type_Name"].astype(str)))
