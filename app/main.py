import os
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import xarray as xr
import numpy as np
from pathlib import Path

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

# #проверка ключа
# def require_api_key(authorization: Optional[str] = Header(None)):
#     if not API_KEY:
#         return
#     if not authorization:
#         raise HTTPException(status_code=401, detail="Missing Authorization header")
#     parts = authorization.split()
#     if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != API_KEY:
#         raise HTTPException(status_code=401, detail="Invalid API key")

# #модель ответа
# class CalcResponse(BaseModel):
#     input: dict
#     results: dict
#     meta: dict

# @app.get("/api/health")
# async def health():
#     return {"status": "proverka git action"}

# @app.get("/api/weather/calc", response_model=CalcResponse, dependencies=[Depends(require_api_key)])
# async def weather_calc(
#     lat: float = Query(..., description="Latitude"),
#     lon: float = Query(..., description="Longitude"),
#     start: Optional[str] = Query(None, description="Start date"),
#     end: Optional[str] = Query(None, description="End date")
# ):
#     start_ts = time.time()


#     results = {
#         "daily": [
#             {"date": start or "2023-09-01", "rain_mm": 0.0, "very_wet": False},
#             {"date": end or "2023-09-02", "rain_mm": 5.0, "very_wet": False}
#         ],
#         "summary": {"mean_mm": 2.5, "max_mm": 5.0, "n_very_wet": 0}
#     }

#     return {
#         "input": {"lat": lat, "lon": lon, "start": start, "end": end},
#         "results": results,
#         "meta": {"status": "mock", "duration_ms": int((time.time() - start_ts) * 1000)}
#     }


# 1) Кладемо файли
DATA_DIR = Path("./data")  # сам обереш яка папка зручніше, поки ./data

# 2) 9 файлів, що я надіслала (точні назви)
FILES = {
    "2023-08-27": "3B-DAY.MS.MRG.3IMERG.20230827-S000000-E235959.V07B.nc4",
    "2023-08-28": "3B-DAY.MS.MRG.3IMERG.20230828-S000000-E235959.V07B.nc4",
    "2023-08-29": "3B-DAY.MS.MRG.3IMERG.20230829-S000000-E235959.V07B.nc4",
    "2023-08-30": "3B-DAY.MS.MRG.3IMERG.20230830-S000000-E235959.V07B.nc4",
    "2023-08-31": "3B-DAY.MS.MRG.3IMERG.20230831-S000000-E235959.V07B.nc4",
    "2023-09-01": "3B-DAY.MS.MRG.3IMERG.20230901-S000000-E235959.V07B.nc4",
    "2023-09-02": "3B-DAY.MS.MRG.3IMERG.20230902-S000000-E235959.V07B.nc4",
    "2023-09-03": "3B-DAY.MS.MRG.3IMERG.20230903-S000000-E235959.V07B.nc4",
    "2023-09-04": "3B-DAY.MS.MRG.3IMERG.20230904-S000000-E235959.V07B.nc4",
}

# Допоміжне: перевести км у градуси (приблизно; для демо ок)
def km_to_deg(km: float) -> float:
    return km / 111.0

# Вибір bbox з урахуванням напрямку осей.
def bbox_sel(da, lat, lon, radius_km=10.0):
    d = km_to_deg(radius_km)
    lat_min, lat_max = lat - d, lat + d
    lon_min, lon_max = lon - d, lon + d
    lat_axis = da["lat"]
    lon_axis = da["lon"]
    lat_slice = slice(lat_min, lat_max) if lat_axis[0] < lat_axis[-1] else slice(lat_max, lat_min)
    lon_slice = slice(lon_min, lon_max) if lon_axis[0] < lon_axis[-1] else slice(lon_max, lon_min)
    return da.sel(lat=lat_slice, lon=lon_slice)

# Якщо дата є у словнику — беремо точну назву; інакше будуємо шаблон на майбутнє
def resolve_file(date_str: str) -> Path:
    if date_str in FILES:
        return DATA_DIR / FILES[date_str]
    # За потреби можна підлаштувати шаблон під інші файли
    fname = f"3B-DAY.MS.MRG.3IMERG.{date_str.replace('-','')}-S000000-E235959.V07B.nc4"
    return DATA_DIR / fname

# Головна логіка
def get_precip_risk(lat: float, lon: float, date_str: str, radius_km: float = 10.0, threshold_mm: float = 10.0):
    fpath = resolve_file(date_str)
    if not fpath.exists():
        raise FileNotFoundError(f"Data file not found: {fpath}")

    ds = xr.open_dataset(fpath)

    # Назва змінної може відрізнятись між продуктами/версіями
    var_name = "precipitation"
    if var_name not in ds:
        var_name = "precipitationCal" if "precipitationCal" in ds else list(ds.data_vars)[0]

    pr = ds[var_name]
    pr_box = bbox_sel(pr, lat, lon, radius_km)

    arr = pr_box.values
    valid = int(np.isfinite(arr).sum())
    avg = float(np.nanmean(arr)) if valid > 0 else float("nan")

    return {
        "rain_mm_day": None if not np.isfinite(avg) else avg,
        "very_wet": bool(avg > threshold_mm) if np.isfinite(avg) else False,
        "threshold_mm": float(threshold_mm),
        "valid_pixels": valid,
        "meta": {
            "data_source": "GPM_3IMERGDF V07 Final",
            "file_used": fpath.name,
            "var": var_name
        }
    }

# Схема відповіді для /docs
class RiskResponse(BaseModel):
    rain_mm_day: float 
    very_wet: bool
    threshold_mm: float
    valid_pixels: int
    meta: dict

# Ендпоінт
@app.get("/weather_risk", response_model=RiskResponse)
def weather_risk(
    lat: float = Query(..., ge=-90, le=90, description="широта"),
    lon: float = Query(..., ge=-180, le=180, description="довгота"),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"),
    radius_km: float = Query(10.0, gt=0, le=100, description="радіус для усереднення (км)"),
    threshold_mm: float = Query(10.0, ge=0, description="поріг 'дуже вологе' (мм/день)")
):
    try:
        return get_precip_risk(lat, lon, date, radius_km, threshold_mm)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"processing_error: {e}")

#future features like changing background(eto ot siebia) i czto nibud jeszcze pridumaju