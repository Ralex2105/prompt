import unittest
import pandas as pd
import numpy as np
from src.preprocessing import preprocess_data


class TestPreprocessing(unittest.TestCase):

    def setUp(self):

        np.random.seed(42)
        self.df_raw = pd.DataFrame({
            'current_R': np.random.normal(0, 1, 1000),
            'current_S': np.random.normal(0, 1, 1000),
            'current_T': np.random.normal(0, 1, 1000)
        })

        self.df_with_nans = self.df_raw.copy()
        self.df_with_nans.loc[10:20, 'current_R'] = np.nan
        self.df_with_nans.loc[50:55, 'current_S'] = np.nan
        self.df_with_nans.loc[70:75, 'current_T'] = np.nan

    def test_handle_missing_values_interpolate(self):
        df_processed = preprocess_data(self.df_with_nans, fill_method='interpolate',
                                       normalize=False, filter_signals=False)

        self.assertFalse(df_processed.isnull().values.any(), "После интерполяции остались пропуски")

    def test_handle_missing_values_drop(self):
        df_processed = preprocess_data(self.df_with_nans, fill_method='drop',
                                       normalize=False, filter_signals=False)

        self.assertLess(len(df_processed), len(self.df_with_nans),
                        "Строки с пропусками не были удалены!")

        self.assertFalse(df_processed.isnull().values.any(), "Остались пропуски после удаления строк!")

    def test_normalization(self):
        df_processed = preprocess_data(self.df_raw, fill_method='interpolate',
                                       normalize=True, filter_signals=False)

        mean = df_processed.mean().round(decimals=2)
        std = df_processed.std().round(decimals=2)

        for column in df_processed.columns:
            self.assertAlmostEqual(mean[column], 0, places=1,
                                   msg=f"Среднее по колонке {column} не близко к 0 после нормализации!")
            self.assertAlmostEqual(std[column], 1, places=1,
                                   msg=f"Стандартное отклонение по колонке {column} не близко к 1 после нормализации!")

    def test_filter_signals(self):
        """Проверка фильтрации сигналов полосовым фильтром."""
        df_processed = preprocess_data(self.df_raw, fill_method='interpolate',
                                       normalize=False, filter_signals=True,
                                       filter_band=(50, 1000), sampling_rate=25600.0)

        self.assertFalse(df_processed.isnull().values.any(), "После фильтрации возникли пропуски!")
        for column in df_processed.columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df_processed[column]),
                            f"Колонка {column} после фильтрации содержит нечисловые данные!")

    def test_combined_preprocessing(self):
        """Проверка выполнения всех шагов предобработки одновременно."""
        df_processed = preprocess_data(self.df_with_nans, fill_method='interpolate',
                                       normalize=True, filter_signals=True,
                                       filter_band=(50, 1000), sampling_rate=25600.0)

        self.assertFalse(df_processed.isnull().values.any(), "Пропуски после полного препроцессинга!")

        mean = df_processed.mean()
        for column in df_processed.columns:
            self.assertAlmostEqual(mean[column], 0, delta=0.1,
                                   msg=f"Среднее по колонке {column} не близко к 0 после полного препроцессинга!")

        std = df_processed.std()
        for column in df_processed.columns:
            self.assertGreater(std[column], 0.1,
                               msg=f"Стандартное отклонение по колонке {column} слишком мало после фильтрации!")
