from data_visualiser import data_visualize, data_visualize_combined, data_visualize_dq
from pipeline_load_refactor import process_and_save_one_file
import matplotlib.pyplot as plt


# process_and_save_one_file("Data_Set_main/current_1.csv", "src/processed_current_1.csv")

# data_visualize("Data_Set_main/current_1.csv")
# data_visualize("src/processed_current_1.csv")
# data_visualize_combined("src/processed_current_1.csv")
data_visualize_dq("src/processed_current_1.csv")
plt.show()



