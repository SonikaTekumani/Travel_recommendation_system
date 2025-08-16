from pydantic import BaseModel, Field
from typing import List

class CitiesRequest(BaseModel):
    budget: float = Field(..., ge=0)
    duration: float = Field(..., ge=0)
    experience_types: List[int] = Field(..., min_items=1)

class CityResult(BaseModel):
    name: str
    match_score: float
    matching_types: list[str]
