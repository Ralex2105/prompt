import unittest
import pandas as pd
import numpy as np
import os
from src.data_loader import load_current_data, EXPECTED_PHASES


class TestDataLoaderSimple(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.file_with_header = "test_with_header.csv"
        pd.DataFrame({
            'current_R': [1.1, 2.2],
            'current_S': [3.3, 4.4],
            'current_T': [5.5, 6.6]
        }).to_csv(cls.file_with_header, index=False)

        cls.file_no_header = "test_no_header.csv"
        with open(cls.file_no_header, 'w') as f:
            f.write("7.7,8.8,9.9\n,11.1,12.2\n13.3,,15.5\n")

        cls.file_only_r = "test_only_r.csv"
        with open(cls.file_only_r, 'w') as f:
            f.write("100.0\n200.0\n")

        cls.file_r_and_t = "test_r_and_t.csv"
        with open(cls.file_r_and_t, 'w') as f:
            f.write("1.0,,2.0\n,,-3.0\n")

        cls.file_header_wrong_order = "test_header_wrong_order.csv"
        pd.DataFrame({
            'current_S': [1, 2],
            'current_T': [3, 4],
            'current_R': [5, 6]
        }).to_csv(cls.file_header_wrong_order, index=False)

    @classmethod
    def tearDownClass(cls):
        files = [
            cls.file_with_header, cls.file_no_header, cls.file_only_r,
            cls.file_r_and_t, cls.file_header_wrong_order
        ]
        for fname in files:
            try:
                os.remove(fname)
            except Exception:
                pass

    def test_with_header(self):
        df = load_current_data(self.file_with_header)
        self.assertListEqual(list(df.columns), EXPECTED_PHASES)
        self.assertAlmostEqual(df.iloc[0]['current_R'], 1.1, places=2)
        self.assertAlmostEqual(df.iloc[1]['current_T'], 6.6, places=2)

    def test_no_header(self):
        df = load_current_data(self.file_no_header)
        self.assertListEqual(list(df.columns), EXPECTED_PHASES)
        self.assertEqual(df.shape, (3, 3))
        self.assertAlmostEqual(df.iloc[0]['current_R'], 7.7, places=2)
        self.assertTrue(np.isnan(df.iloc[1]['current_R']))
        self.assertAlmostEqual(df.iloc[1]['current_S'], 11.1, places=2)
        self.assertAlmostEqual(df.iloc[2]['current_T'], 15.5, places=2)

    def test_only_r(self):
        df = load_current_data(self.file_only_r)
        self.assertListEqual(list(df.columns), EXPECTED_PHASES)
        self.assertEqual(df.shape[1], 3)
        self.assertAlmostEqual(df.iloc[0]['current_R'], 100.0, places=2)
        self.assertTrue(df['current_S'].isnull().all())
        self.assertTrue(df['current_T'].isnull().all())

    def test_r_and_t(self):
        df = load_current_data(self.file_r_and_t)
        self.assertListEqual(list(df.columns), EXPECTED_PHASES)
        self.assertEqual(df.shape, (2, 3))
        self.assertAlmostEqual(df.iloc[0]['current_R'], 1.0, places=2)
        self.assertTrue(np.isnan(df.iloc[0]['current_S']))
        self.assertAlmostEqual(df.iloc[0]['current_T'], 2.0, places=2)
        self.assertTrue(np.isnan(df.iloc[1]['current_R']))
        self.assertTrue(np.isnan(df.iloc[1]['current_S']))
        self.assertAlmostEqual(df.iloc[1]['current_T'], -3.0, places=2)
