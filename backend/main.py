from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import CitiesRequest, CityResult
from services import get_dataframes, build_type_name_map
import pandas as pd

app = FastAPI(title="Travel Recommender API", version="0.1.0")

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set to your frontend origin(s) in prod
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
        # Normalize Duration_Range once
        if "Duration_Range" in budget_duration_df.columns:
            budget_duration_df["Duration_Range"] = budget_duration_df["Duration_Range"].astype(str).str.replace(r"[^\d\-]", "", regex=True)
    except FileNotFoundError as e:
        raise RuntimeError(f"Dataset not found: {e.filename}")
    except pd.errors.EmptyDataError:
        raise RuntimeError("One of the CSV files is empty.")
    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.post("/api/cities", response_model=list[CityResult])
def get_cities(payload: CitiesRequest):
    try:
        budget = payload.budget
        duration = payload.duration
        experience_types = payload.experience_types

        if budget is None or duration is None:
            raise HTTPException(status_code=400, detail="Budget and duration are required.")
        if not isinstance(budget, (int, float)) or not isinstance(duration, (int, float)):
            raise HTTPException(status_code=400, detail="Budget and duration must be numbers.")
        if not experience_types:
            raise HTTPException(status_code=400, detail="experience_types must be a non-empty list of IDs.")

        bdf = budget_duration_df.copy()

        # Parse numeric ranges for filtering
        budget_min = bdf["Budget_Range"].str.split("-").str[0].astype(int)
        budget_max = bdf["Budget_Range"].str.split("-").str[1].astype(int)
        duration_min = bdf["Duration_Range"].str.split("-").str.astype(int)
        duration_max = bdf["Duration_Range"].str.split("-").str[1].astype(int)

        filtered_cities = bdf[
            (budget_min <= budget) &
            (budget_max >= budget) &
            (duration_min <= duration) &
            (duration_max >= duration)
        ]

        # Group types by city
        ctype = cities_type_df[cities_type_df["Type_ID"].isin(experience_types)]
        city_matches = (
            ctype.groupby("City_ID")
            .agg(Type_ID=("Type_ID", list), City_Name=("City_Name", "first"))
            .reset_index()
        )

        final_cities = filtered_cities[filtered_cities["City_ID"].isin(city_matches["City_ID"])]
        final_cities = final_cities.merge(city_matches[["City_ID", "Type_ID", "City_Name"]], on="City_ID", how="left")

        req_types_set = set(experience_types)

        def _score(type_list):
            if not isinstance(type_list, list) or len(req_types_set) == 0:
                return 0.0
            overlap = len(req_types_set.intersection(type_list))
            return (overlap / len(req_types_set)) * 100.0

        final_cities["match_score"] = final_cities["Type_ID"].apply(_score)
        final_cities = final_cities.sort_values("match_score", ascending=False)

        type_map = type_names or {}

        results: list[CityResult] = []
        for _, row in final_cities.iterrows():
            matching = sorted({type_map.get(tid, str(tid)) for tid in (row["Type_ID"] or []) if tid in req_types_set})
            results.append(
                CityResult(
                    name=row["City_Name"],
                    match_score=round(float(row["match_score"]), 2),
                    matching_types=matching
                )
            )

        return results

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing key: {e.args[0]}")
    except Exception as e:
        # Avoid leaking internals; log in real app
        raise HTTPException(status_code=500, detail=str(e))
