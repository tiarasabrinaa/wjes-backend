
import pickle
import pandas as pd

# Load model dan forecast
def load_model_and_forecast(tahun, bulan, model_path='./models/lgbm_forecasting_model.pkl'):
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
    result_df.index = [f"{tahun}-{bulan_num:02d}"]

    return result_df

# Forecast multi periode
def forecast_multiple_periods(start_tahun, start_bulan, n_periods, model_path='lgbm_forecasting_model.pkl'):
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