import pickle
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_api_key
from datetime import datetime, timedelta
from loguru import logger
from helper.bahan_pokok import update_excel_with_forecast, load_model_and_forecast

router = APIRouter(tags=["Forecasting"])

@router.get("/wjes/forecasting_bahan_pokok_with_excel")
async def forecasting_bahan_pokok_with_excel(days: int = 1, x_api_key: str = Depends(get_api_key)):
    """
    Forecast H+1 dan langsung update ke Excel file
    
    Args:
        days: jumlah hari forecast (default: 1 untuk H+1)
    """
    try:
        today = datetime.today()
        logger.info(f"Starting {days}-day forecast with Excel update from: {today.strftime('%Y-%m-%d')}")

        # Path file Excel
        excel_path = "./temp_uploads/Harga_pangan_harian.xlsx"
        output_path = "./temp_uploads/Harga_pangan_harian.xlsx"

        # Load model dan forecast
        forecast_results = load_model_and_forecast(n_days=days, model_path="./models/lgbm_forecasting_hph_model.pkl")

        # Update Excel dengan hasil forecast
        update_status = update_excel_with_forecast(
            forecast_results=forecast_results,
            excel_path=excel_path,
            output_path=output_path
        )

        if update_status["status"] == "error":
            raise HTTPException(status_code=500, detail=update_status["message"])

        # Prepare response with forecast details
        response = {
            "status": "success",
            "forecast_date": today.strftime('%Y-%m-%d'),
            "forecast_period": f"{days} days",
            "excel_update": update_status,
            "forecast_summary": {}
        }

        # Add forecast summary
        for target, df_out in forecast_results.items():
            forecast_list = []
            for _, row in df_out.iterrows():
                forecast_dict = {
                    "tanggal": row['Tanggal'].strftime('%Y-%m-%d'),
                    "predicted_value": round(row[f"Forecast_{target}"], 0)  # Round to integer like in Excel
                }
                forecast_list.append(forecast_dict)
            
            response["forecast_summary"][target] = forecast_list

        response["summary"] = {
            "total_targets": len(forecast_results),
            "total_days": days,
            "targets_forecasted": list(forecast_results.keys()),
            "excel_updates": update_status["updates_count"],
            "new_rows_added": update_status["extended_rows"]
        }

        return response
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Required file not found (model or Excel)")
    except Exception as e:
        logger.error(f"Error in forecasting_bahan_pokok_with_excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")