import os

from src.load_preprocessing.data_visualiser import data_visualize, data_visualize_combined, data_visualize_dq

from src.feature_extraction.feature_extraction import extract_features_from_file

#Построение графиков
# process_and_save_one_file("Data_Set_main/current_1.csv", "src/processed_current_1.csv")
# data_visualize("Data_Set_main/current_1.csv")
# data_visualize("src/processed_current_1.csv")
# data_visualize_combined("src/processed_current_1.csv")
#data_visualize_dq("src/processed_current_1.csv")
#plt.show()





#Создать директорию prompt/data и наполнить её csv
#Создать директорию prompt/feature_data
#Создать директорию prompt/processed_data

RAW_DATA_DIR = "../data"
PROCESSED_DATA_DIR = "../processed_data"
FEATURE_DATA_DIR = "../feature_data"
FILE_AMOUNT = 36  # 35 + 1


"""
#Раскомментить, если нужно выполнить предобработку

for file_number in range(1, FILE_AMOUNT):
    input_file = os.path.join(RAW_DATA_DIR, f"current_{file_number}.csv")
    output_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
    process_and_save_one_file(input_file, output_file)
"""

#Вызов выделения признаков

for file_number in range(1, FILE_AMOUNT):
    output_file = os.path.join(FEATURE_DATA_DIR)
    input_file = os.path.join(PROCESSED_DATA_DIR, f"processed_{file_number}.csv")
    extract_features_from_file(input_file, output_file, 51200, 25600)






