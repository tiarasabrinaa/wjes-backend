import pickle
from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_api_key
from utils import json_parse
from pathlib import Path
from helper.ihk import load_model_and_forecast
import base64
from loguru import logger
from datetime import datetime

router = APIRouter(tags=["Forecasting"])

@router.get("/wjes/forecasting_ihk")
async def forecasting_ihk(x_api_key: str = Depends(get_api_key)):
    try:
        now = datetime.now()
        year = now.year

        month = now.strftime("%B")

        result = load_model_and_forecast(year, month)

        return {
            "status": "success",
            "forecast": result.round(2).to_dict(orient="index")
        }
    except Exception as e:
        logger.error(f"Error in forecasting_ihk: {e}")
        raise HTTPException(500, f"Internal Server Error: {e}")