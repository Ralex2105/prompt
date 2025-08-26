import os

from src.load_preprocessing.pipeline_load_refactor import process_and_save_all_files
from src.load_preprocessing.pipeline_load_refactor import features_for_all_files

# Get the project root directory (one level up from src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directory paths
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data')
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data_processed')
FEATURE_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data_feature')
SUMMARY_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data_summary')
ML_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'data_ml')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'model')


# Create directories if they don't exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, FEATURE_DATA_DIR, SUMMARY_DATA_DIR, MODEL_DIR]:
    os.makedirs(directory, exist_ok=True)
    gitkeep_path = os.path.join(directory, '.gitkeep')
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, 'w') as f:
            pass  # Create empty .gitkeep file

process_and_save_all_files(RAW_DATA_DIR)
print("Starting feature extraction...")
features_for_all_files(PROCESSED_DATA_DIR)
print("Feature extraction completed.")
