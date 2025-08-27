import unittest
import pandas as pd
from src.data_loader import load_current_data
import os


class TestDataLoaderWithRealData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.getcwd(), 'test_data')
        cls.real_data_file = os.path.join(cls.test_data_dir, 'current_1.csv')

    def test_load_current_1_structure(self):
 
        df = load_current_data(self.real_data_file)

        expected_columns = ['current_R', 'current_S', 'current_T']
        self.assertListEqual(list(df.columns), expected_columns)

        self.assertFalse(df.isnull().values.any(), "Обнаружены пропуски в данных current_1.csv")

        self.assertGreater(len(df), 0, "Файл current_1.csv пустой!")

        for col in expected_columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df[col]),
                            f"Колонка {col} содержит не числовые данные")

    def test_load_current_1_data_values(self):

        df = load_current_data(self.real_data_file)

        first_row = df.iloc[0]
        self.assertAlmostEqual(first_row['current_R'], 1.894377, places=5)
        self.assertAlmostEqual(first_row['current_S'], 0.949463, places=5)
        self.assertAlmostEqual(first_row['current_T'], -2.165271, places=5)
