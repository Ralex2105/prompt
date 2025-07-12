import unittest
import pandas as pd
import numpy as np
from src.data_loader import load_current_data
import os


class TestDataLoader(unittest.TestCase):
    """
    Unit-тесты для проверки функции load_current_data с фазами R, S, T
    """

    @classmethod
    def setUpClass(cls):
        """
        Создание временных CSV-файлов
        """
        cls.temp_files = []

        # Данные с полным набором фаз без пропусков
        full_data = pd.DataFrame({
            'current_R': [1, 2, 3],
            'current_S': [4, 5, 6],
            'current_T': [7, 8, 9]
        })
        full_filename = 'test_full.csv'
        full_data.to_csv(full_filename, index=False)
        cls.temp_files.append(full_filename)

        # Данные без фазы S
        missing_s = pd.DataFrame({
            'current_R': [1, 2, 3],
            'current_T': [7, 8, 9]
        })
        missing_s_filename = 'test_missing_s.csv'
        missing_s.to_csv(missing_s_filename, index=False)
        cls.temp_files.append(missing_s_filename)

        # Данные с пропусками значений
        data_with_nans = pd.DataFrame({
            'current_R': [np.nan, 2, 3],
            'current_S': [4, np.nan, 6],
            'current_T': [7, 8, np.nan]
        })
        with_nans_filename = 'test_with_nans.csv'
        data_with_nans.to_csv(with_nans_filename, index=False)
        cls.temp_files.append(with_nans_filename)

    @classmethod
    def tearDownClass(cls):
        for filename in cls.temp_files:
            if os.path.exists(filename):
                os.remove(filename)

    def test_load_full_data(self):
        df = load_current_data('test_full.csv')
        self.assertListEqual(list(df.columns), ['current_R', 'current_S', 'current_T'])
        self.assertFalse(df.isnull().values.any())

    def test_load_missing_s(self):
        df = load_current_data('test_missing_s.csv')
        self.assertListEqual(list(df.columns), ['current_R', 'current_T'])
        self.assertFalse(df.isnull().values.any())

    def test_load_with_nans(self):
        df = load_current_data('test_with_nans.csv')
        self.assertListEqual(list(df.columns), ['current_R', 'current_S', 'current_T'])
        self.assertTrue(df.isnull().values.any())

    def test_load_no_phases(self):
        empty_file = 'test_no_phases.csv'
        pd.DataFrame({'some_column': [1, 2, 3]}).to_csv(empty_file, index=False)
        self.temp_files.append(empty_file)
        with self.assertRaises(ValueError):
            load_current_data(empty_file)


if __name__ == '__main__':
    unittest.main()
