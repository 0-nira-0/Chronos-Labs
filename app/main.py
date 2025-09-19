import os
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

API_KEY = os.getenv("API_KEY")

app = FastAPI(title="Weather Calculations API")

#разрешаем все origin для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #на проде заменить на фронт
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#проверка ключа
def require_api_key(authorization: Optional[str] = Header(None)):
    if not API_KEY:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

#модель ответа
class CalcResponse(BaseModel):
    input: dict
    results: dict
    meta: dict

@app.get("/api/health")
async def health():
    return {"status": "proverka git action"}

@app.get("/api/weather/calc", response_model=CalcResponse, dependencies=[Depends(require_api_key)])
async def weather_calc(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    start: Optional[str] = Query(None, description="Start date"),
    end: Optional[str] = Query(None, description="End date")
):
    start_ts = time.time()


    results = {
        "daily": [
            {"date": start or "2023-09-01", "rain_mm": 0.0, "very_wet": False},
            {"date": end or "2023-09-02", "rain_mm": 5.0, "very_wet": False}
        ],
        "summary": {"mean_mm": 2.5, "max_mm": 5.0, "n_very_wet": 0}
    }

    return {
        "input": {"lat": lat, "lon": lon, "start": start, "end": end},
        "results": results,
        "meta": {"status": "mock", "duration_ms": int((time.time() - start_ts) * 1000)}
    }
#future features like changing background(eto ot siebia) i czto nibud jeszcze pridumaju