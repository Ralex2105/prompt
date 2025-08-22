import os
from pathlib import Path

from src.load_preprocessing.data_visualiser import (
    data_visualize, data_visualize_combined, data_visualize_dq
)
from src.feature_extraction.feature_extraction import extract_features_from_file
# from src.load_preprocessing.preprocessing import process_and_save_one_file  # если нужно предобрабатывать

# Директории
RAW_DATA_DIR = Path("../data")
PROCESSED_DATA_DIR = Path("../processed_data")
FEATURE_DATA_DIR = Path("../feature_data")
FILE_AMOUNT = 36  # processed_1.csv ... processed_35.csv

# Создадим папки на всякий случай (на будущее — если раскомментируешь предобработку/визуализацию)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_DATA_DIR.mkdir(parents=True, exist_ok=True)

"""
# Предобработка (раскомментируй при необходимости)
for file_number in range(1, FILE_AMOUNT):
    input_file = RAW_DATA_DIR / f"current_{file_number}.csv"
    output_file = PROCESSED_DATA_DIR / f"processed_{file_number}.csv"
    process_and_save_one_file(str(input_file), str(output_file))
"""

# Выделение признаков
FS = 51200   # частота дискретизации
RPM = 1770   # оценка оборотов (а не Fs!)

for file_number in range(1, FILE_AMOUNT):
    input_file = PROCESSED_DATA_DIR / f"processed_{file_number}.csv"
    # Кладём результат как <processed_N>_features.csv внутри FEATURE_DATA_DIR
    output_file = FEATURE_DATA_DIR / f"processed_{file_number}_features.csv"

    if not input_file.exists():
        print(f"[skip] Нет файла: {input_file}")
        continue

    try:
        saved = extract_features_from_file(str(input_file), str(output_file), FS, RPM)
        print(f"[ok] {saved}")
    except Exception as e:
        print(f"[error] {input_file}: {e}")