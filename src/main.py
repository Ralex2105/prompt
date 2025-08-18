import os
import sys

# # Add the project root to the Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualise_reports.data_visualiser import data_visualize

from feature_extraction.feature_extraction import extract_features_from_file


PROCESSED_DATA_DIR = "processed_files"
FEATURE_DATA_DIR = "feature_data"


file_numbers = [file_number for file_number in range(1, 39)]
# Вызов выделения признаков

# for file_number in file_numbers:
#     input_file = os.path.join(PROCESSED_DATA_DIR, f"current_{file_number}_processed.csv")
#     os.makedirs(FEATURE_DATA_DIR, exist_ok=True)
#     extract_features_from_file(input_file, FEATURE_DATA_DIR, 51200, 25600)

