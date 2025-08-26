import os
from .load_preprocessing.pipeline_load_refactor import process_and_save_one_file
from .load_preprocessing.preprocessing import preprocess_data
from .feature_extraction.feature_extraction import extract_features_from_file
from .model.process_defects import process_defects_file
from .load_preprocessing.data_visualiser import data_visualize, data_visualize_combined, data_visualize_dq

# Commented out visualization code as in the original
# process_and_save_one_file("Data_Set_main/current_1.csv", "src/processed_current_1.csv")
# data_visualize("Data_Set_main/current_1.csv")
# data_visualize("src/processed_current_1.csv")
# data_visualize_combined("src/processed_current_1.csv")
# data_visualize_dq("src/processed_current_1.csv")
# plt.show()

# Directory paths
RAW_DATA_DIR = "../data/data"
PROCESSED_DATA_DIR = "../data/da    ta_processed"
FEATURE_DATA_DIR = "../data/data_feature"
SUMMARY_DATA_DIR = "../data/data_summary"
FILE_AMOUNT = 39  # Adjusted to include current_38.csv

# Create directories if they don't exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, FEATURE_DATA_DIR, SUMMARY_DATA_DIR]:
    os.makedirs(directory, exist_ok=True)
    gitkeep_path = os.path.join(directory, '.gitkeep')
    if not os.path.exists(gitkeep_path):
        with open(gitkeep_path, 'w') as f:
            pass  # Create empty .gitkeep file

"""
#Раскомментить, если нужно выполнить предобработку
for file_number in range(1, FILE_AMOUNT):
    input_file = os.path.join(RAW_DATA_DIR, f"current_{file_number}.csv")
    output_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
    process_and_save_one_file(input_file, output_file)
"""

"""
#Вызов выделения признаков
"""
print("Starting feature extraction...")
for file_number in range(1, FILE_AMOUNT):
    input_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
    feature_output_file = os.path.join(FEATURE_DATA_DIR, f"feature_data_{file_number}.csv")

    # Check if input file exists
    if os.path.exists(input_file):
        print(f"[extract_features] Processing file: {input_file}")
        extract_features_from_file(input_file, feature_output_file)
        print(f"[extract_features] Features extracted to: {feature_output_file}")
    else:
        print(f"[extract_features] Input file not found: {input_file}")
print("Feature extraction completed.")

"""
#Вызов постобработки дефектов
"""
print("\nStarting defect post-processing...")
for file_number in range(1, FILE_AMOUNT):
    input_file = os.path.join(FEATURE_DATA_DIR, f"feature_data_{file_number}.csv")
    summary_output_file = os.path.join(SUMMARY_DATA_DIR, f"summary_data_{file_number}.csv")

    # Check if input file exists
    if os.path.exists(input_file):
        print(f"[process_defects] Processing file: {input_file}")
        result = process_defects_file(input_file, summary_output_file)
        print(f"[process_defects] Processed file saved as: {summary_output_file}")
        print(f"[process_defects] Summary Defect: {result['summary_defect']}")
        print(f"[process_defects] Summary Severity: {result['summary_severity']}")
        print(f"[process_defects] Additional Note: {result['additional_note']}")
        print(f"[process_defects] Analysis Time: {result['analysis_time']}")
        print("-" * 50)
    else:
        print(f"[process_defects] Input file not found: {input_file}")
print("Defect post-processing completed.")