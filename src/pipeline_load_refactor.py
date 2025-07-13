from src.data_loader import load_current_data
from src.preprocessing import preprocess_data


def process_and_save_one_file(input_file, output_file):
    print(f"Processing file: {input_file}")
    try:
        df_raw = load_current_data(input_file)
        df_processed = preprocess_data(df_raw)
        df_processed.to_csv(output_file, index=False)
        print(f"Saved processed data to {output_file}")
    except Exception as e:
        print(f"❌ Ошибка при обработке файла {input_file}: {e}")
