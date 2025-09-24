import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

def load_model_and_forecast(n_days=30, model_path="./models/lgbm_forecasting_hph_model.pkl"):
    """
    Load model dan forecast untuk n_days ke depan.
    Setiap target diprediksi secara independent mulai dari day 1.
    
    Args:
        n_days: jumlah hari yang akan diprediksi
        model_path: path ke file model yang sudah disave
    
    Returns:
        dict: forecast_results dengan key = target_name, value = DataFrame
    """
    logger.info(f"Loading model from: {model_path}")
    
    with open(model_path, "rb") as f:
        model_data = pickle.load(f)

    forecast_results = {}
    target_columns = model_data["target_columns"]
    feature_cols = model_data["feature_cols"]
    lag_periods = model_data["lag_periods"]
    rolling_windows = model_data["rolling_windows"]
    original_last_data = model_data["last_data"].copy()  # Data asli, tidak diubah

    # Generate forecast dates
    forecast_dates = pd.date_range(
        start=original_last_data["Tanggal"].iloc[-1] + pd.Timedelta(days=1),
        periods=n_days,
        freq="D"
    )

    logger.info(f"Forecasting for {len(target_columns)} targets, {n_days} days")

    # Forecast setiap target secara independent
    for target_col in target_columns:
        logger.info(f"Forecasting {target_col}...")
        
        model = model_data["forecast_results"][target_col]["model"]
        forecasted_values = []
        
        # Reset last_values untuk setiap target (independent)
        last_values = original_last_data.copy()

        for day in range(n_days):
            # Create base forecast data structure
            forecast_data = {
                "Tanggal": forecast_dates[day],
                "year": forecast_dates[day].year,
                "month": forecast_dates[day].month,
                "day": forecast_dates[day].day,
                "dayofweek": forecast_dates[day].dayofweek,
                "quarter": forecast_dates[day].quarter,
                "weekofyear": forecast_dates[day].isocalendar().week
            }

            # Create lag features
            for lag in lag_periods:
                if day < lag:
                    # Gunakan data historis
                    lag_idx = len(last_values) - lag + day
                    if lag_idx >= 0:
                        forecast_data[f"{target_col}_lag_{lag}"] = last_values.iloc[lag_idx][target_col]
                    else:
                        forecast_data[f"{target_col}_lag_{lag}"] = last_values.iloc[0][target_col]
                else:
                    # Gunakan hasil prediksi sebelumnya untuk target yang sama
                    forecast_data[f"{target_col}_lag_{lag}"] = forecasted_values[day - lag]

            # Create rolling features (selalu dari data historis + prediksi sebelumnya)
            for window in rolling_windows:
                if day == 0:
                    # Hari pertama: pakai data historis
                    window_data = last_values[target_col].tail(window).values
                else:
                    # Kombinasi data historis + prediksi sebelumnya
                    if day >= window:
                        # Jika sudah cukup prediksi, pakai prediksi saja
                        window_data = forecasted_values[day-window:day]
                    else:
                        # Kombinasi historis + prediksi
                        hist_needed = window - day
                        hist_data = last_values[target_col].tail(hist_needed).tolist()
                        pred_data = forecasted_values[:day]
                        window_data = hist_data + pred_data
                
                forecast_data[f"{target_col}_rolling_mean_{window}"] = np.mean(window_data)
                forecast_data[f"{target_col}_rolling_std_{window}"] = np.std(window_data)
                forecast_data[f"{target_col}_rolling_min_{window}"] = np.min(window_data)
                forecast_data[f"{target_col}_rolling_max_{window}"] = np.max(window_data)

            # Fill missing features dengan rata-rata dari data historis
            for col in feature_cols:
                if col not in forecast_data:
                    if col in last_values.columns:
                        forecast_data[col] = last_values[col].mean()
                    else:
                        forecast_data[col] = 0  # fallback

            # Create DataFrame in one go to avoid fragmentation
            temp_df = pd.DataFrame([forecast_data])

            # Make prediction
            X_forecast = temp_df[feature_cols]
            pred_value_log = model.predict(X_forecast, num_iteration=model.best_iteration)[0]
            
            # Inverse transform (dari log scale ke harga asli)
            pred_value = np.exp(pred_value_log)
            forecasted_values.append(pred_value)

        # Save results untuk target ini
        forecast_results[target_col] = pd.DataFrame({
            "Tanggal": forecast_dates,
            f"Forecast_{target_col}": forecasted_values
        })

    logger.info(f"Forecasting completed for {len(target_columns)} targets")
    return forecast_results


def update_excel_with_forecast(forecast_results, excel_path="./temp_uploads/Harga_pangan_harian.xlsx", 
                              output_path="./temp_uploads/Harga_pangan_harian.xlsx"):
    """
    Update Excel file dengan hasil forecast, extend tanggal jika perlu
    
    Args:
        forecast_results: dict hasil dari load_model_and_forecast()
        excel_path: path ke file Excel yang akan di-update
        output_path: path untuk save hasil update
    
    Returns:
        dict: status dan informasi update
    """
    try:
        logger.info(f"Reading Excel file: {excel_path}")
        df_excel = pd.read_excel(excel_path)
        
        # Convert Tanggal column to datetime
        df_excel['Tanggal'] = pd.to_datetime(df_excel['Tanggal'], format='%d/%m/%y')
        
        logger.info(f"Excel data shape: {df_excel.shape}")
        logger.info(f"Excel date range: {df_excel['Tanggal'].min()} to {df_excel['Tanggal'].max()}")
        
        # Get the last date in Excel
        last_excel_date = df_excel['Tanggal'].max()
        
        # Process each forecast target
        updated_count = 0
        extended_count = 0
        
        # Target mapping yang diperluas untuk mapping nama target ke kolom Excel
        target_mapping = {
            "Beras_Premium": "Beras Premium",
            "Beras_Medium": "Beras Medium", 
            "Beras_SPHP": "Beras SPHP",
            "Jagung_Tk_Peternak": "Jagung Tk Peternak",
            "Kedelai_Biji_Kering_Impor": "Kedelai Biji Kering (Impor)",
            "Bawang_Merah": "Bawang Merah",
            "Bawang_Putih_Bonggol": "Bawang Putih Bonggol",
            "Cabai_Merah_Keriting": "Cabai Merah Keriting",
            "Cabai_Merah_Besar": "Cabai Merah Besar",
            "Daging_Sapi": "Daging Sapi Murni",
            "Cabai_Rawit_Merah": "Cabai Rawit Merah",
            "Daging_Ayam_Ras": "Daging Ayam Ras",
            "Telur_Ayam_Ras": "Telur Ayam Ras",
            "Gula_Konsumsi": "Gula Konsumsi",
            "Minyak_Goreng_Kemasan": "Minyak Goreng Kemasan",
            "Minyak_Goreng_Curah": "Minyak Goreng Curah",
            "Tepung_Terigu_Curah": "Tepung Terigu (Curah)",
            "Minyakita": "Minyakita",
            "Tepung_Terigu_Kemasan": "Tepung Terigu Kemasan",
            "Ikan_Kembung": "Ikan Kembung",
            "Ikan_Tongkol": "Ikan Tongkol",
            "Ikan_Bandeng": "Ikan Bandeng",
            "Garam_Konsumsi": "Garam Konsumsi",
            "Daging_Kerbau_Beku_Impor": "Daging Kerbau Beku (Impor Luar Negeri)",
            "Daging_Kerbau_Segar_Lokal": "Daging Kerbau Segar (Lokal)"
        }
        
        # Collect all dates that need to be added
        all_forecast_dates = set()
        for forecast_df in forecast_results.values():
            forecast_dates = pd.to_datetime(forecast_df['Tanggal'])
            all_forecast_dates.update(forecast_dates)
        
        # Check if we need to extend the Excel data
        max_forecast_date = max(all_forecast_dates) if all_forecast_dates else last_excel_date
        
        if max_forecast_date > last_excel_date:
            logger.info(f"Extending Excel from {last_excel_date} to {max_forecast_date}")
            
            # Generate new date range
            new_dates = pd.date_range(
                start=last_excel_date + timedelta(days=1),
                end=max_forecast_date,
                freq='D'
            )
            
            # Prepare new rows data efficiently
            new_rows_data = []
            for i, new_date in enumerate(new_dates):
                new_row_data = {'Tanggal': new_date, 'No': len(df_excel) + i + 1}
                # Initialize other columns with NaN
                for col in df_excel.columns:
                    if col not in ['Tanggal', 'No']:
                        new_row_data[col] = np.nan
                new_rows_data.append(new_row_data)
            
            # Create new DataFrame and concatenate efficiently
            if new_rows_data:
                new_df = pd.DataFrame(new_rows_data)
                df_excel = pd.concat([df_excel, new_df], ignore_index=True)
                extended_count = len(new_rows_data)
                logger.info(f"Extended Excel with {extended_count} new rows")
        
        # Update Excel with forecast values efficiently
        forecast_updates = {}  # Collect all updates first
        
        for target, forecast_df in forecast_results.items():
            logger.info(f"Processing target: {target}")
            
            excel_col = target_mapping.get(target, target)
            forecast_col = f"Forecast_{target}"
            
            if excel_col not in df_excel.columns:
                logger.warning(f"Column '{excel_col}' not found in Excel.")
                available_cols = [col for col in df_excel.columns if col not in ['No', 'Tanggal']]
                logger.info(f"Available columns: {available_cols[:10]}...")  # Show first 10
                continue
            
            # Collect updates for this target
            for _, forecast_row in forecast_df.iterrows():
                forecast_date = pd.to_datetime(forecast_row['Tanggal'])
                forecast_value = round(forecast_row[forecast_col], 0)
                
                # Find matching date index
                date_mask = df_excel['Tanggal'] == forecast_date
                if date_mask.any():
                    idx = df_excel.index[date_mask][0]
                    if excel_col not in forecast_updates:
                        forecast_updates[excel_col] = {}
                    forecast_updates[excel_col][idx] = forecast_value
                    updated_count += 1
        
        # Apply all updates at once to avoid fragmentation
        for col, updates in forecast_updates.items():
            for idx, value in updates.items():
                df_excel.loc[idx, col] = value
        
        # Sort by date and reset index
        df_excel = df_excel.sort_values('Tanggal').reset_index(drop=True)
        
        # Update No column to be sequential after sorting
        df_excel['No'] = range(1, len(df_excel) + 1)
        
        # Convert Tanggal back to the original format for Excel
        df_excel['Tanggal'] = df_excel['Tanggal'].dt.strftime('%d/%m/%y')
        
        # Save updated Excel file
        df_excel.to_excel(output_path, index=False)
        
        logger.info(f"Excel updated successfully! Updates: {updated_count}, New rows: {extended_count}")
        logger.info(f"Saved to: {output_path}")
        
        return {
            "status": "success",
            "updates_count": updated_count,
            "extended_rows": extended_count,
            "output_path": output_path,
            "excel_shape": df_excel.shape,
            "message": f"Updated {updated_count} values and added {extended_count} new rows"
        }
        
    except FileNotFoundError:
        logger.error(f"Excel file not found: {excel_path}")
        return {"status": "error", "message": f"File not found: {excel_path}"}
    except Exception as e:
        logger.error(f"Error updating Excel: {str(e)}")
        return {"status": "error", "message": str(e)}