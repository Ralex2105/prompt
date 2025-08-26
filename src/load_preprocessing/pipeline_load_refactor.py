from src.load_preprocessing.preprocessing import preprocess_data
from src.load_preprocessing.data_loader import load_current_data
import os


def process_and_save_one_file(input_file: str, output_file: str) -> bool:

    print(f"Обработка файла: {input_file}")
    try:
        df_raw = load_current_data(input_file)
        df_processed = preprocess_data(df_raw)
        df_processed.to_csv(output_file, index=False)
        print(f"✓ Обработанный файл сохранен: {output_file}")
        return True
        
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл {input_file} не найден")
        return False
    except Exception as e:
        print(f"❌ Ошибка при обработке файла {input_file}: {str(e)}")
        return False

def csv_sort(data_dir: str):
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    csv_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    return csv_files


def process_and_save_all_files(data_dir: str):
    
    print(f"Начало обработки файлов в директории: {data_dir}")
    try:
        processed_files = []
        failed_files = []
        
        # Получаем список CSV файлов и сортируем их по числовому значению
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        csv_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
        
        # Создаем отдельную директорию для обработанных файлов
        processed_dir = os.path.join(os.path.dirname(data_dir), 'processed_files')
        os.makedirs(processed_dir, exist_ok=True)
        
        for csv_file in csv_files:
            input_path = os.path.join(data_dir, csv_file)
            output_filename = f"{os.path.splitext(csv_file)[0]}_processed.csv"
            output_path = os.path.join(processed_dir, output_filename)
            
            if process_and_save_one_file(input_path, output_path):
                processed_files.append(csv_file)
            else:
                failed_files.append(csv_file)
        
        print(f"\nОбработка завершена:")
        print(f"✓ Успешно обработано: {len(processed_files)} файлов")
        if failed_files:
            print(f"❌ Не удалось обработать: {len(failed_files)} файлов")
            for f in failed_files:
                print(f"  - {f}")
        
    except FileNotFoundError:
        print(f"❌ Ошибка: Директория {data_dir} не найдена")
    except Exception as e:
        print(f"❌ Ошибка при обработке файлов: {str(e)}")

