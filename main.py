from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="UnitPriceCompare Teaching Mock")


class CompareRequest(BaseModel):
    product_a: str
    price_a: float
    quantity_a: float
    product_b: str
    price_b: float
    quantity_b: float
    unit: str


mock_results = {
    ("WATER_A", "WATER_B"): "WATER_B"
}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "UnitPriceCompare Teaching Mock"
    }


@app.post("/compare")
def compare_products(request: CompareRequest):
    key = (
        request.product_a.upper(),
        request.product_b.upper()
    )

    best_choice = mock_results.get(
        key,
        "NO_PRESET_RESULT"
    )

    return {
        "message":
            "This is a teaching mock response. "
            "No calculation is performed.",
        "received": request.model_dump(),
        "best_choice": best_choice
    }
