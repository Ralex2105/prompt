import os
import unittest
import pandas as pd
from src.load_preprocessing.pipeline_load_refactor import process_and_save_one_file

RAW_DATA_DIR = "../prompt/data"
PROCESSED_DATA_DIR = "../prompt/data_processed"
FILE_AMOUNT = 36 

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

class TestDataProcessingPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for file_number in range(1, FILE_AMOUNT):
            input_file = os.path.join(RAW_DATA_DIR, f"current_{file_number}.csv")
            output_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
            process_and_save_one_file(input_file, output_file)

    def test_processed_files_exist(self):
        for file_number in range(1, FILE_AMOUNT):
            processed_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
            self.assertTrue(os.path.isfile(processed_file),
                            f"Файл не найден: {processed_file}")

    def test_processed_files_no_all_nans(self):
        for file_number in range(1, FILE_AMOUNT):
            processed_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
            df = pd.read_csv(processed_file)
            self.assertFalse(df.isnull().all(axis=1).any(),
                             f"Есть полностью пустые строки в файле: {processed_file}")

    def test_processed_files_numeric(self):
        for file_number in range(1, FILE_AMOUNT):
            processed_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
            df = pd.read_csv(processed_file)
            for col in df.columns:
                self.assertTrue(pd.api.types.is_numeric_dtype(df[col]),
                                f"Нечисловые данные в колонке {col} файла {processed_file}")
