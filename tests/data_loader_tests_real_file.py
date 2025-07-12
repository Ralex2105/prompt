import unittest
import pandas as pd
from src.data_loader import load_current_data
import os


class TestDataLoaderWithRealData(unittest.TestCase):
    """
    Тесты загрузки реальных данных из файла current_1.csv
    """

    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = os.path.join(os.getcwd(), 'test_data')
        cls.real_data_file = os.path.join(cls.test_data_dir, 'current_1.csv')

    def test_load_current_1_structure(self):
        """
        Проверка структуры данных в файле current_1.csv
        """
        df = load_current_data(self.real_data_file)

        # Проверка наличия всех фаз R, S, T
        expected_columns = ['current_R', 'current_S', 'current_T']
        self.assertListEqual(list(df.columns), expected_columns)

        # Проверка, что нет пропусков
        self.assertFalse(df.isnull().values.any(), "Обнаружены пропуски в данных current_1.csv")

        # Проверка, что загружено корректное число записей
        self.assertGreater(len(df), 0, "Файл current_1.csv пустой!")

        # Проверка типа данных
        for col in expected_columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df[col]),
                            f"Колонка {col} содержит не числовые данные")

    def test_load_current_1_data_values(self):
        """
        Проверка значений в первых строках файла current_1.csv
        """
        df = load_current_data(self.real_data_file)

        first_row = df.iloc[0]
        self.assertAlmostEqual(first_row['current_R'], 1.894377, places=5)
        self.assertAlmostEqual(first_row['current_S'], 0.949463, places=5)
        self.assertAlmostEqual(first_row['current_T'], -2.165271, places=5)
