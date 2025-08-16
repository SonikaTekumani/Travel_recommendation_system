from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import CitiesRequest, CityResult
from services import get_dataframes, build_type_name_map
import pandas as pd

app = FastAPI(title="Travel Recommender API", version="0.2.0")

# CORS: replace with your exact frontend origins in production
ALLOWED_ORIGINS = [
    "*",  # tighten to e.g. "https://<username>.github.io", "https://<username>.github.io/<repo-name>"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global, lazily initialized resources
states_df: pd.DataFrame | None = None
cities_df: pd.DataFrame | None = None
budget_duration_df: pd.DataFrame | None = None
cities_type_df: pd.DataFrame | None = None
type_names: dict[int, str] | None = None


@app.on_event("startup")
def startup_load_data():
    global states_df, cities_df, budget_duration_df, cities_type_df, type_names
    try:
        states_df, cities_df, budget_duration_df, cities_type_df = get_dataframes()
        type_names = build_type_name_map(cities_type_df)

        # Validate required columns in each dataframe
        required_columns = {
            "cities_df": ["City_ID", "City_Name", "State_ID", "State_Name"],
            "cities_type_df": ["City_Name", "City_ID", "Type_ID", "Type_Name"],
            "budget_duration_df": ["City_ID", "City_Name", "Budget_Range", "Duration_Range"],
            "states_df": ["State_ID", "State_Name"]
        }
        
        dataframes = {
            "cities_df": cities_df,
            "cities_type_df": cities_type_df, 
            "budget_duration_df": budget_duration_df,
            "states_df": states_df
        }
        
        for df_name, required_cols in required_columns.items():
            df = dataframes[df_name]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise RuntimeError(f"Missing columns in {df_name}: {missing}")

        # Normalize text columns to string in budget_duration_df
        for col in ("Budget_Range", "Duration_Range"):
            if col in budget_duration_df.columns:
                budget_duration_df[col] = budget_duration_df[col].astype(str)

        # Pre-split Budget_Range like "1000-5000" into numeric min/max
        if "Budget_Range" in budget_duration_df.columns:
            br = budget_duration_df["Budget_Range"].str.replace(r"[^\d\-]", "", regex=True)
            bparts = br.str.split("-", expand=True)
            budget_duration_df["budget_min"] = pd.to_numeric(bparts[0], errors="coerce")
            budget_duration_df["budget_max"] = pd.to_numeric(bparts[1], errors="coerce")

        # Pre-split Duration_Range like "2-5" days into numeric min/max
        if "Duration_Range" in budget_duration_df.columns:
            dr = budget_duration_df["Duration_Range"].str.replace(r"[^\d\-]", "", regex=True)
            dparts = dr.str.split("-", expand=True)
            budget_duration_df["duration_min"] = pd.to_numeric(dparts[0], errors="coerce")
            budget_duration_df["duration_max"] = pd.to_numeric(dparts[1], errors="coerce")

        # Ensure City_ID is consistent numeric type across all dataframes
        for df in [cities_df, budget_duration_df, cities_type_df]:
            if "City_ID" in df.columns:
                df["City_ID"] = pd.to_numeric(df["City_ID"], errors="coerce")
                df = df.dropna(subset=["City_ID"])
                df["City_ID"] = df["City_ID"].astype(int)

        # Ensure State_ID is consistent numeric type
        for df in [states_df, cities_df]:
            if "State_ID" in df.columns:
                df["State_ID"] = pd.to_numeric(df["State_ID"], errors="coerce")
                df = df.dropna(subset=["State_ID"])
                df["State_ID"] = df["State_ID"].astype(int)

        # Normalize Type_ID in cities_type_df
        if "Type_ID" in cities_type_df.columns:
            cities_type_df["Type_ID"] = pd.to_numeric(cities_type_df["Type_ID"], errors="coerce")
            cities_type_df = cities_type_df.dropna(subset=["Type_ID"])
            cities_type_df["Type_ID"] = cities_type_df["Type_ID"].astype(int)

        # Validate final required columns after processing
        final_required_cols = ["City_ID", "City_Name", "budget_min", "budget_max", "duration_min", "duration_max"]
        missing = [c for c in final_required_cols if c not in budget_duration_df.columns]
        if missing:
            raise RuntimeError(f"Missing processed columns in budget_duration_df: {missing}")

    except FileNotFoundError as e:
        raise RuntimeError(f"Dataset not found: {getattr(e, 'filename', str(e))}")
    except pd.errors.EmptyDataError:
        raise RuntimeError("One of the CSV files is empty.")
    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    ok = all(
        x is not None
        for x in (states_df, cities_df, budget_duration_df, cities_type_df, type_names)
    )
    return {"ready": ok}


@app.post("/api/cities", response_model=list[CityResult])
def get_cities(payload: CitiesRequest):
    try:
        budget = payload.budget
        duration = payload.duration
        experience_types = payload.experience_types

        # Basic validation
        if budget is None or duration is None:
            raise HTTPException(status_code=400, detail="Budget and duration are required.")
        if not isinstance(budget, (int, float)) or not isinstance(duration, (int, float)):
            raise HTTPException(status_code=400, detail="Budget and duration must be numbers.")
        if not experience_types or not all(isinstance(x, int) for x in experience_types):
            raise HTTPException(status_code=400, detail="experience_types must be a non-empty list of integer IDs.")

        # Work on a copy to avoid mutating globals
        bdf = budget_duration_df.copy()

        # Drop rows with missing bounds
        bdf = bdf.dropna(subset=["budget_min", "budget_max", "duration_min", "duration_max"])

        # Filter by budget and duration ranges
        matched_cities = bdf[
            (bdf["budget_min"] <= budget) &
            (bdf["budget_max"] >= budget) &
            (bdf["duration_min"] <= duration) &
            (bdf["duration_max"] >= duration)
        ][["City_ID", "City_Name"]].drop_duplicates()

        if matched_cities.empty:
            return []

        # Filter cities_type_df to only requested experience types
        requested_city_types = cities_type_df[
            cities_type_df["Type_ID"].isin(experience_types)
        ][["City_ID", "Type_ID", "Type_Name"]].copy()
        
        if requested_city_types.empty:
            return []

        # Get cities that match both budget/duration AND have requested experience types
        valid_city_ids = set(matched_cities["City_ID"]) & set(requested_city_types["City_ID"])
        
        if not valid_city_ids:
            return []

        # Filter to only valid cities
        final_matched_cities = matched_cities[matched_cities["City_ID"].isin(valid_city_ids)]
        final_city_types = requested_city_types[requested_city_types["City_ID"].isin(valid_city_ids)]

        # Group experience types by city
        city_type_groups = (
            final_city_types.groupby("City_ID")
            .agg(
                Type_IDs=("Type_ID", list),
                Type_Names=("Type_Name", list)
            )
            .reset_index()
        )

        # Join cities with their experience types
        final_cities = final_matched_cities.merge(city_type_groups, on="City_ID", how="left")
        
        # Handle cities with no matching types (shouldn't happen due to filtering above)
        final_cities["Type_IDs"] = final_cities["Type_IDs"].apply(lambda v: v if isinstance(v, list) else [])
        final_cities["Type_Names"] = final_cities["Type_Names"].apply(lambda v: v if isinstance(v, list) else [])

        # Calculate match score based on how many requested types the city has
        req_types_set = set(experience_types)

        def calculate_match_score(type_ids: list[int]) -> float:
            if not type_ids or not req_types_set:
                return 0.0
            city_types_set = set(type_ids)
            overlap = len(req_types_set.intersection(city_types_set))
            return (overlap / len(req_types_set)) * 100.0

        final_cities["match_score"] = final_cities["Type_IDs"].apply(calculate_match_score)
        
        # Sort by match score (highest first)
        final_cities = final_cities.sort_values("match_score", ascending=False)

        # Build results
        results: list[CityResult] = []
        for _, row in final_cities.iterrows():
            # Get the names of matching experience types
            city_type_ids = set(row["Type_IDs"]) if row["Type_IDs"] else set()
            matching_type_indices = [i for i, tid in enumerate(row["Type_IDs"]) if tid in req_types_set]
            matching_types = sorted([row["Type_Names"][i] for i in matching_type_indices])
            
            results.append(
                CityResult(
                    name=str(row["City_Name"]),
                    match_score=round(float(row["match_score"]), 2),
                    matching_types=matching_types
                )
            )
        
        return results

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing key: {e.args[0]}")
    except Exception as e:
        # Return concise error to client; log details server-side in a real app
        raise HTTPException(status_code=500, detail=str(e))
