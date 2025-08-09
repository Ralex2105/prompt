import pandas as pd
import numpy as np
from feature_classifier import get_feature_vector, classify_defect

def extract_features_from_file(filename, window_size=25600, step=12800):
    # Загружаем данные и приводим имена столбцов к единому виду
    data = pd.read_csv(filename)
    data.columns = [c.strip().replace(" ", "_").replace(",", "") for c in data.columns]
    required = ["Current_R", "Current_S", "Current_T"]
    # Если каких-то фаз нет, создаём полностью NaN-столбец
    for col in required:
        if col not in data:
            data[col] = np.nan

    features, defect_types, severities = [], [], []
    reader = (data.iloc[i:i+step*2] for i in range(0, len(data), step*2))
    for chunk in reader:
        if len(chunk) < window_size:
            continue
        for i in range(0, len(chunk) - window_size + 1, step):
            window = chunk.iloc[i:i+window_size].copy()
            # Для каждой фазы: если всё NaN, то заполняем нулями, иначе медианой
            for col in required:
                if window[col].isnull().all():
                    window[col] = 0.0
                else:
                    window[col] = window[col].fillna(window[col].median())
            feats = get_feature_vector(
                window['Current_R'].values,
                window['Current_S'].values,
                window['Current_T'].values
            )
            features.append(feats)
            d_type, d_sev = classify_defect(
                window['Current_R'].values,
                window['Current_S'].values,
                window['Current_T'].values
            )
            defect_types.append(d_type)
            severities.append(d_sev)
    return np.array(features), np.array(defect_types), np.array(severities)