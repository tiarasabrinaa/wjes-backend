import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger

# Load model dan forecast
def load_model_and_forecast(tahun, bulan, model_path='./models/lgbm_forecasting_model.pkl'):
    """
    Load model dan forecast untuk periode tertentu
    """
    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    target_cols = model_data['target_cols']
    bulan_map = model_data['bulan_map']
    last_data = model_data['last_data']
    second_last_data = model_data['second_last_data']

    # Konversi bulan ke angka jika berupa string
    if isinstance(bulan, str):
        bulan_num = bulan_map.get(bulan)
        if bulan_num is None:
            raise ValueError(f"Bulan '{bulan}' tidak valid. Gunakan: {list(bulan_map.keys())} atau angka 1-12")
    else:
        bulan_num = bulan
        if not (1 <= bulan_num <= 12):
            raise ValueError("Bulan harus antara 1-12")

    # data input untuk forecasting
    forecast_period = pd.DataFrame({
        "Tahun": [tahun],
        "Bulan_num": [bulan_num]
    })

    # lag features
    for col in target_cols:
        forecast_period[f"{col}_lag1"] = [last_data[col]]
        forecast_period[f"{col}_lag2"] = [second_last_data[col]]

    # forecasting
    forecast_result = model.predict(forecast_period)

    result_df = pd.DataFrame(forecast_result, columns=target_cols)
    result_df['Tahun'] = tahun
    result_df['Bulan'] = get_month_name(bulan_num)
    
    # Reorder columns to match Excel format
    cols = ['Tahun', 'Bulan'] + target_cols
    result_df = result_df[cols]
    
    result_df.index = [f"{tahun}-{bulan_num:02d}"]

    return result_df


def get_month_name(bulan_num):
    """Convert month number to Indonesian month name"""
    bulan_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    return bulan_names.get(bulan_num, 'Unknown')


def forecast_multiple_periods(start_tahun, start_bulan, n_periods, model_path='./models/lgbm_forecasting_model.pkl'):
    """
    Forecast multiple periods sekaligus
    """
    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    target_cols = model_data['target_cols']
    bulan_map = model_data['bulan_map']

    # Konversi bulan ke angka jika berupa string
    if isinstance(start_bulan, str):
        start_bulan_num = bulan_map.get(start_bulan)
        if start_bulan_num is None:
            raise ValueError(f"Bulan '{start_bulan}' tidak valid")
    else:
        start_bulan_num = start_bulan

    results = []
    current_tahun = start_tahun
    current_bulan = start_bulan_num

    # lag features
    lag1_data = model_data['last_data'][target_cols].values
    lag2_data = model_data['second_last_data'][target_cols].values

    for i in range(n_periods):
        # input
        forecast_period = pd.DataFrame({
            "Tahun": [current_tahun],
            "Bulan_num": [current_bulan]
        })

        # lag features
        for j, col in enumerate(target_cols):
            forecast_period[f"{col}_lag1"] = [lag1_data[j]]
            forecast_period[f"{col}_lag2"] = [lag2_data[j]]

        # Forecast
        forecast_result = model.predict(forecast_period)

        # Simpan hasil
        period_name = f"{current_tahun}-{current_bulan:02d}"
        result_row = pd.DataFrame(forecast_result, columns=target_cols, index=[period_name])
        result_row['Tahun'] = current_tahun
        result_row['Bulan'] = get_month_name(current_bulan)
        
        # Reorder columns
        cols = ['Tahun', 'Bulan'] + target_cols
        result_row = result_row[cols]
        
        results.append(result_row)

        # Update lag data untuk periode selanjutnya
        lag2_data = lag1_data.copy()
        lag1_data = forecast_result.flatten()

        # Update bulan dan tahun
        current_bulan += 1
        if current_bulan > 12:
            current_bulan = 1
            current_tahun += 1

    return pd.concat(results)


def update_excel_with_forecast(forecast_df, excel_path="./temp_uploads/IHK.xlsx", 
                              output_path="./temp_uploads/IHK_updated.xlsx"):
    """
    Update Excel file dengan hasil forecast IHK
    
    Args:
        forecast_df: DataFrame hasil forecast dengan kolom Tahun, Bulan, dan target columns
        excel_path: path ke file Excel yang akan di-update
        output_path: path untuk save hasil update
    
    Returns:
        dict: status dan informasi update
    """
    try:
        logger.info(f"Reading Excel file: {excel_path}")
        df_excel = pd.read_excel(excel_path)
        
        logger.info(f"Excel data shape: {df_excel.shape}")
        logger.info(f"Excel columns: {df_excel.columns.tolist()}")
        
        # Column mapping dari nama forecast ke nama Excel
        column_mapping = {
            "Umum": "Umum",
            "Makanan_Minuman_dan_Tembakau": "Makanan, Minuman dan Tembakau",
            "Pakaian_dan_Alas_Kaki": "Pakaian dan Alas Kaki",
            "Perumahan_Air_Listrik_dan_Bahan_Bakar_Rumah_Tangga": "Perumahan, Air, Listrik dan Bahan Bakar Rumah Tangga",
            "Perlengkapan_Peralatan_dan_Pemeliharaan_Rutin_Rumah_Tangga": "Perlengkapan, Peralatan dan Pemeliharaan Rutin Rumah Tangga",
            "Kesehatan": "Kesehatan",
            "Transportasi": "Transportasi",
            "Informasi_Komunikasi_dan_Jasa_Keuangan": "Informasi, Komunikasi dan Jasa Keuangan",
            "Rekreasi_Olahraga_dan_Budaya": "Rekreasi, Olahraga dan Budaya",
            "Pendidikan": "Pendidikan",
            "Penyediaan_Makanan_dan_Minuman__Restoran": "Penyediaan Makanan dan Minuman/ Restoran",
            "Perawatan_Pribadi_da_Jasa_Lainnya": "Perawatan Pribadi da Jasa Lainnya"
        }
        
        # Get current data info
        if 'Tahun' in df_excel.columns and 'Bulan' in df_excel.columns:
            last_year = df_excel['Tahun'].max()
            last_month_data = df_excel[df_excel['Tahun'] == last_year]['Bulan'].iloc[-1]
            logger.info(f"Last data in Excel: {last_year} {last_month_data}")
        
        updated_count = 0
        added_rows = 0
        processed_periods = 0
        
        # Process each forecast row
        for idx, forecast_row in forecast_df.iterrows():
            forecast_tahun = forecast_row['Tahun']
            forecast_bulan = forecast_row['Bulan']
            
            logger.info(f"Processing forecast for {forecast_tahun} {forecast_bulan}")
            
            # Check if this period already exists in Excel
            existing_mask = (df_excel['Tahun'] == forecast_tahun) & (df_excel['Bulan'] == forecast_bulan)
            
            if existing_mask.any():
                # Update existing row
                logger.info(f"Updating existing row for {forecast_tahun} {forecast_bulan}")
                row_idx = df_excel.index[existing_mask][0]
                
                # Update all target columns using mapping
                for forecast_col, excel_col in column_mapping.items():
                    if forecast_col in forecast_row and excel_col in df_excel.columns:
                        old_value = df_excel.loc[row_idx, excel_col]
                        new_value = round(forecast_row[forecast_col], 2)
                        df_excel.loc[row_idx, excel_col] = new_value
                        logger.info(f"Updated {excel_col}: {old_value} -> {new_value}")
                        updated_count += 1
            else:
                # Add new row
                logger.info(f"Adding new row for {forecast_tahun} {forecast_bulan}")
                
                # Create new row with proper column mapping
                new_row = {
                    'Tahun': forecast_tahun,
                    'Bulan': forecast_bulan
                }
                
                # Map forecast columns to Excel columns
                for forecast_col, excel_col in column_mapping.items():
                    if forecast_col in forecast_row and excel_col in df_excel.columns:
                        new_row[excel_col] = round(forecast_row[forecast_col], 2)
                
                # Fill any missing columns with NaN to maintain Excel structure
                for col in df_excel.columns:
                    if col not in new_row:
                        new_row[col] = np.nan
                
                # Add to DataFrame
                df_excel = pd.concat([df_excel, pd.DataFrame([new_row])], ignore_index=True)
                added_rows += 1
            
            processed_periods += 1
        
        # Sort by Tahun and Bulan
        # Create month order for sorting
        month_order = {
            'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
            'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
        }
        
        df_excel['Bulan_num'] = df_excel['Bulan'].map(month_order)
        df_excel = df_excel.sort_values(['Tahun', 'Bulan_num']).drop('Bulan_num', axis=1).reset_index(drop=True)
        
        # Save updated Excel file
        df_excel.to_excel(output_path, index=False)
        
        logger.info(f"Excel updated successfully!")
        logger.info(f"Updates: {updated_count}, Added rows: {added_rows}, Processed periods: {processed_periods}")
        logger.info(f"Saved to: {output_path}")
        
        return {
            "status": "success",
            "updates_count": updated_count,
            "added_rows": added_rows,
            "processed_periods": processed_periods,
            "output_path": output_path,
            "excel_shape": df_excel.shape,
            "message": f"Updated {updated_count} values and added {added_rows} new rows"
        }
        
    except FileNotFoundError:
        logger.error(f"Excel file not found: {excel_path}")
        return {"status": "error", "message": f"File not found: {excel_path}"}
    except Exception as e:
        logger.error(f"Error updating Excel: {str(e)}")
        return {"status": "error", "message": str(e)}


def load_and_forecast_with_excel_update(tahun, bulan, excel_path="./temp_uploads/IHK.xlsx", 
                                       output_path="./temp_uploads/IHK_updated.xlsx",
                                       model_path='./models/lgbm_forecasting_model.pkl'):
    """
    Combined function: Load model, forecast, dan update Excel untuk satu periode
    """
    try:
        logger.info(f"Starting forecast for {tahun} {bulan}")
        
        # Generate forecast
        forecast_result = load_model_and_forecast(tahun, bulan, model_path)
        
        # Update Excel
        excel_update_result = update_excel_with_forecast(
            forecast_df=forecast_result,
            excel_path=excel_path,
            output_path=output_path
        )
        
        return {
            "forecast_result": forecast_result,
            "excel_update": excel_update_result
        }
        
    except Exception as e:
        logger.error(f"Error in load_and_forecast_with_excel_update: {str(e)}")
        raise e


def forecast_multiple_periods_with_excel_update(start_tahun, start_bulan, n_periods, 
                                              excel_path="./temp_uploads/IHK.xlsx",
                                              output_path="./temp_uploads/IHK_updated.xlsx",
                                              model_path='./models/lgbm_forecasting_model.pkl'):
    """
    Combined function: Forecast multiple periods dan update Excel
    """
    try:
        logger.info(f"Starting multi-period forecast: {n_periods} periods from {start_tahun} {start_bulan}")
        
        # Generate multi-period forecast
        forecast_result = forecast_multiple_periods(start_tahun, start_bulan, n_periods, model_path)
        
        # Update Excel
        excel_update_result = update_excel_with_forecast(
            forecast_df=forecast_result,
            excel_path=excel_path,
            output_path=output_path
        )
        
        return {
            "forecast_result": forecast_result,
            "excel_update": excel_update_result
        }
        
    except Exception as e:
        logger.error(f"Error in forecast_multiple_periods_with_excel_update: {str(e)}")
        raise e


def get_next_month_forecast(model_path='./models/lgbm_forecasting_model.pkl',
                           excel_path="./temp_uploads/IHK.xlsx", 
                           output_path="./temp_uploads/IHK_updated.xlsx"):
    """
    Helper function untuk forecast bulan depan dan update Excel
    Otomatis deteksi bulan depan dari tanggal sekarang
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

        logger.info(f"Auto-forecasting for next month: {next_year}-{next_month:02d}")
        
        # Use the combined function
        result = load_and_forecast_with_excel_update(
            tahun=next_year,
            bulan=next_month,
            excel_path=excel_path,
            output_path=output_path,
            model_path=model_path
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_next_month_forecast: {str(e)}")
        raise e