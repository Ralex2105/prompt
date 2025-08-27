import pandas as pd
import numpy as np
import os
from src.load_preprocessing.pipeline_load_refactor import csv_sort


FEATURE_DATA_DIR = "feature_data"


def data_concat(data_dir=FEATURE_DATA_DIR):
    data_files = csv_sort(data_dir)
    df_list = []
    for f in data_files:
        path = os.path.join(data_dir, f)
        df_tmp = pd.read_csv(path)
        df_list.append(df_tmp)
    # Итоговый датафрейм
    df = pd.concat(df_list, ignore_index=True)
    return df


def get_X_y_defect_y_severity(df):
    # Список типов дефектов (включая "Normal")
    defect_types = ["Normal", "Inner Race", "Outer Race", "Ball", "Cage", "Rotor", "Misalignment"]
    
    # Словарь для кодировки степени дефекта
    severity_map = {"Low": 1, "Medium": 2, "High": 3}
    
    y_defect = df["defect"].apply(lambda x: defect_types.index(x))
    
    y_severity = df["severity"].map(severity_map).fillna(0).astype(int)
    
    drop_cols = ["defect", "severity"]
    X = df.drop(columns=drop_cols)
    
    print("X shape:", X.shape)
    print("y_defect shape:", y_defect.shape)
    print("y_severity shape:", y_severity.shape)

    print("\nРаспределение по классам типов дефектов:")
    for class_idx, class_name in enumerate(defect_types):
        count = (y_defect == class_idx).sum()
        print(f"Class {class_idx} ({class_name}): Количество элементов {count}")
    
    print("\nРаспределение по классам степеней дефектов:")
    for level_idx, level_name in enumerate(["None", "Low", "Medium", "High"]):
        count = (y_severity == level_idx).sum()
        print(f"Class {level_idx} ({level_name}): Количество элементов {count}")
    
    return X, y_defect, y_severity