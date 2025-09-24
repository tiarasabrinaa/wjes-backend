from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from helper.ihk import (
    get_next_month_forecast, 
    load_and_forecast_with_excel_update, 
    forecast_multiple_periods_with_excel_update,
    load_model_and_forecast
)
from dependencies import get_api_key
from loguru import logger
import os

router = APIRouter(tags=["IHK Forecasting"])


@router.get("/wjes/forecasting_ihk_update_excel")
async def forecasting_ihk_update_excel(x_api_key: str = Depends(get_api_key)):
    """
    Forecasting IHK untuk bulan depan dan update Excel secara otomatis
    """
    try:
        # Get current date info
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Calculate next month
        next_month = current_month + 1
        next_year = current_year
        if next_month > 12:
            next_month = 1
            next_year += 1

        logger.info(f"Memulai forecast IHK untuk bulan depan: {next_year}-{next_month:02d}")

        # Check file paths
        excel_path = "./temp_uploads/IHK.xlsx"
        output_path = "./temp_uploads/IHK_updated.xlsx"
        
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail=f"File Excel tidak ditemukan: {excel_path}")

        # Use the helper function for next month forecast
        result = get_next_month_forecast(
            model_path='./models/lgbm_forecasting_model.pkl',
            excel_path=excel_path,
            output_path=output_path
        )

        forecast_df = result["forecast_result"]
        excel_update = result["excel_update"]

        # Check if Excel update failed
        if excel_update["status"] == "error":
            raise HTTPException(status_code=500, detail=excel_update["message"])

        logger.info(f"IHK forecast dan Excel update berhasil: {output_path}")

        return {
            "status": "success",
            "forecast_type": "Next Month IHK Forecast with Excel Update",
            "forecast_date": now.strftime('%Y-%m-%d'),
            "forecast_period": f"{next_year}-{next_month:02d}",
            "excel_update": excel_update,
            "forecast_values": forecast_df.round(4).to_dict(orient="index"),
            "summary": {
                "total_targets": len([col for col in forecast_df.columns if col not in ['Tahun', 'Bulan']]),
                "excel_updates": excel_update["updates_count"],
                "new_excel_rows": excel_update["added_rows"],
                "processed_periods": excel_update["processed_periods"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in forecasting_ihk_update_excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/wjes/forecasting_ihk_custom")
async def forecasting_ihk_custom(tahun: int, bulan: int, x_api_key: str = Depends(get_api_key)):
    """
    Forecasting IHK untuk periode tertentu dan update Excel
    
    Args:
        tahun: Tahun yang akan diprediksi (contoh: 2025)
        bulan: Bulan yang akan diprediksi (1-12)
    """
    try:
        if not (1 <= bulan <= 12):
            raise HTTPException(status_code=400, detail="Bulan harus antara 1-12")
        
        if tahun < 2020 or tahun > 2030:
            raise HTTPException(status_code=400, detail="Tahun harus antara 2020-2030")

        logger.info(f"Custom IHK forecast untuk: {tahun}-{bulan:02d}")

        # Check file paths
        excel_path = "./temp_uploads/IHK.xlsx"
        output_path = "./temp_uploads/IHK_updated.xlsx"
        
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail=f"File Excel tidak ditemukan: {excel_path}")

        # Use the combined helper function
        result = load_and_forecast_with_excel_update(
            tahun=tahun,
            bulan=bulan,
            excel_path=excel_path,
            output_path=output_path,
            model_path='./models/lgbm_forecasting_model.pkl'
        )

        forecast_df = result["forecast_result"]
        excel_update = result["excel_update"]

        if excel_update["status"] == "error":
            raise HTTPException(status_code=500, detail=excel_update["message"])

        return {
            "status": "success",
            "forecast_type": "Custom Period IHK Forecast",
            "forecast_date": datetime.now().strftime('%Y-%m-%d'),
            "forecast_period": f"{tahun}-{bulan:02d}",
            "excel_update": excel_update,
            "forecast_values": forecast_df.round(4).to_dict(orient="index"),
            "summary": {
                "total_targets": len([col for col in forecast_df.columns if col not in ['Tahun', 'Bulan']]),
                "excel_updates": excel_update["updates_count"],
                "new_excel_rows": excel_update["added_rows"],
                "processed_periods": excel_update["processed_periods"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in forecasting_ihk_custom: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/wjes/forecasting_ihk_multiple")
async def forecasting_ihk_multiple(start_tahun: int, start_bulan: int, n_periods: int = 6,
                                  x_api_key: str = Depends(get_api_key)):
    """
    Forecasting IHK untuk beberapa periode sekaligus dan update Excel
    
    Args:
        start_tahun: Tahun mulai forecast
        start_bulan: Bulan mulai forecast (1-12)
        n_periods: Jumlah periode yang akan diprediksi (default: 6)
    """
    try:
        if not (1 <= start_bulan <= 12):
            raise HTTPException(status_code=400, detail="Bulan harus antara 1-12")
        
        if start_tahun < 2020 or start_tahun > 2030:
            raise HTTPException(status_code=400, detail="Tahun harus antara 2020-2030")
            
        if n_periods < 1 or n_periods > 24:
            raise HTTPException(status_code=400, detail="n_periods harus antara 1-24")

        logger.info(f"Multiple IHK forecast: {n_periods} periods from {start_tahun}-{start_bulan:02d}")

        # Check file paths
        excel_path = "./temp_uploads/IHK.xlsx"
        output_path = "./temp_uploads/IHK_updated.xlsx"
        
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail=f"File Excel tidak ditemukan: {excel_path}")

        # Use the combined helper function for multiple periods
        result = forecast_multiple_periods_with_excel_update(
            start_tahun=start_tahun,
            start_bulan=start_bulan,
            n_periods=n_periods,
            excel_path=excel_path,
            output_path=output_path,
            model_path='./models/lgbm_forecasting_model.pkl'
        )

        forecast_df = result["forecast_result"]
        excel_update = result["excel_update"]

        if excel_update["status"] == "error":
            raise HTTPException(status_code=500, detail=excel_update["message"])

        return {
            "status": "success",
            "forecast_type": "Multiple Periods IHK Forecast",
            "forecast_date": datetime.now().strftime('%Y-%m-%d'),
            "forecast_periods": n_periods,
            "start_period": f"{start_tahun}-{start_bulan:02d}",
            "excel_update": excel_update,
            "forecast_values": forecast_df.round(4).to_dict(orient="index"),
            "summary": {
                "total_targets": len([col for col in forecast_df.columns if col not in ['Tahun', 'Bulan']]),
                "total_periods": n_periods,
                "excel_updates": excel_update["updates_count"],
                "new_excel_rows": excel_update["added_rows"],
                "processed_periods": excel_update["processed_periods"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in forecasting_ihk_multiple: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/wjes/forecasting_ihk_only")
async def forecasting_ihk_only(x_api_key: str = Depends(get_api_key)):
    """
    Forecasting IHK untuk bulan depan tanpa update Excel (hanya return hasil)
    """
    try:
        # Get next month
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        next_month = current_month + 1
        next_year = current_year
        if next_month > 12:
            next_month = 1
            next_year += 1

        logger.info(f"IHK forecast only untuk: {next_year}-{next_month:02d}")

        # Generate forecast only (no Excel update)
        forecast_df = load_model_and_forecast(
            tahun=next_year,
            bulan=next_month,
            model_path='./models/lgbm_forecasting_model.pkl'
        )

        return {
            "status": "success",
            "forecast_type": "Next Month IHK Forecast Only",
            "forecast_date": now.strftime('%Y-%m-%d'),
            "forecast_period": f"{next_year}-{next_month:02d}",
            "forecast_values": forecast_df.round(4).to_dict(orient="index"),
            "summary": {
                "total_targets": len([col for col in forecast_df.columns if col not in ['Tahun', 'Bulan']]),
                "forecast_period": f"{next_year}-{next_month:02d}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in forecasting_ihk_only: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")