import pickle
import pandas as pd
import numpy as np

def load_model_and_forecast(n_days=30, model_path="lgbm_forecasting_hph_model.pkl"):
    """
    Forecast setiap target secara independent mulai dari day 1.
    Setiap target diprediksi dari hari ke-1 sampai hari ke-n_days.
    """
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

    # Forecast setiap target secara independent
    for target_col in target_columns:
        print(f"📊 Forecasting {target_col}...")
        
        model = model_data["forecast_results"][target_col]["model"]
        forecasted_values = []
        
        # Reset last_values untuk setiap target (independent)
        last_values = original_last_data.copy()

        for day in range(n_days):
            # Create forecast dataframe for this specific day
            forecast_df = pd.DataFrame({
                "Tanggal": [forecast_dates[day]]
            })
            
            # Add time features
            forecast_df["year"] = forecast_df["Tanggal"].dt.year
            forecast_df["month"] = forecast_df["Tanggal"].dt.month
            forecast_df["day"] = forecast_df["Tanggal"].dt.day
            forecast_df["dayofweek"] = forecast_df["Tanggal"].dt.dayofweek
            forecast_df["quarter"] = forecast_df["Tanggal"].dt.quarter
            forecast_df["weekofyear"] = forecast_df["Tanggal"].dt.isocalendar().week

            temp_df = forecast_df.copy()

            # Create lag features
            for lag in lag_periods:
                if day < lag:
                    # Gunakan data historis
                    lag_idx = len(last_values) - lag + day
                    if lag_idx >= 0:
                        temp_df[f"{target_col}_lag_{lag}"] = last_values.iloc[lag_idx][target_col]
                    else:
                        temp_df[f"{target_col}_lag_{lag}"] = last_values.iloc[0][target_col]
                else:
                    # Gunakan hasil prediksi sebelumnya untuk target yang sama
                    temp_df[f"{target_col}_lag_{lag}"] = forecasted_values[day - lag]

            # Create rolling features (selalu dari data historis + prediksi sebelumnya)
            for window in rolling_windows:
                if day == 0:
                    # Hari pertama: pakai data historis
                    temp_df[f"{target_col}_rolling_mean_{window}"] = last_values[target_col].tail(window).mean()
                    temp_df[f"{target_col}_rolling_std_{window}"] = last_values[target_col].tail(window).std()
                    temp_df[f"{target_col}_rolling_min_{window}"] = last_values[target_col].tail(window).min()
                    temp_df[f"{target_col}_rolling_max_{window}"] = last_values[target_col].tail(window).max()
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
                    
                    temp_df[f"{target_col}_rolling_mean_{window}"] = np.mean(window_data)
                    temp_df[f"{target_col}_rolling_std_{window}"] = np.std(window_data)
                    temp_df[f"{target_col}_rolling_min_{window}"] = np.min(window_data)
                    temp_df[f"{target_col}_rolling_max_{window}"] = np.max(window_data)

            # Fill missing features dengan rata-rata dari data historis
            for col in feature_cols:
                if col not in temp_df.columns:
                    if col in last_values.columns:
                        temp_df[col] = last_values[col].mean()
                    else:
                        temp_df[col] = 0  # fallback

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
        
        print(f"✅ {target_col} forecasted for {n_days} days")

    return forecast_results