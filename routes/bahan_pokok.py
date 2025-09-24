import pickle
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_api_key
from datetime import datetime
from loguru import logger
from helper.bahan_pokok import load_model_and_forecast

router = APIRouter(tags=["Forecasting"])

@router.get("/wjes/forecasting_bahan_pokok")
async def forecasting_bahan_pokok(x_api_key: str = Depends(get_api_key)):
    try:
        # Get today's date
        today = datetime.today()

        # Forecast for the next 30 days using the same function
        forecast_results = load_model_and_forecast(n_days=30, model_path="./models/lgbm_forecasting_hph_model.pkl")

        # Prepare the response structure with only today's forecast
        response = {"status": "success", "forecast": {}}

        for target, df_out in forecast_results.items():
            # Get the forecast for today only
            today_forecast = df_out[df_out["Tanggal"] == today.strftime('%Y-%m-%d')]

            # Only include today's forecast in the response
            response["forecast"][target] = today_forecast.to_dict(orient="records")

        return response
    except Exception as e:
        logger.error(f"Error in forecasting_bahan_pokok: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")