from .data_loader import load_current_data
from .preprocessing import preprocess_data
from src.feature_extraction.feature_extraction import extract_features_from_file, extract_features_from_file_for_learning
import os

def csv_sort(data_dir: str):
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    def sort_key(filename):
        try:
            if 'processed' in filename:
                return int(filename.split('_')[1])
            return int(filename.split('_')[1].split('.')[0])
        except (IndexError, ValueError):
            return filename
    
    csv_files.sort(key=sort_key)
    return csv_files

def process_and_save_one_file(input_file: str, output_file: str) -> bool:

    print(f"Обработка файла: {input_file}")
    try:
        df_raw = load_current_data(input_file)
        df_processed = preprocess_data(df_raw)
        df_processed.to_csv(output_file, index=False)
        print(f"[OK] Обработанный файл сохранен: {output_file}")
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] Файл {input_file} не найден")
        return False
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке файла {input_file}: {str(e)}")
        return False


def process_and_save_all_files(data_dir: str):
    
    print(f"Начало обработки файлов в директории: {data_dir}")
    try:
        processed_files = []
        failed_files = []
        
        csv_files = csv_sort(data_dir)
        
        processed_dir = os.path.join(os.path.dirname(data_dir), 'data_processed')
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
        print(f"[OK] Успешно обработано: {len(processed_files)} файлов")
        if failed_files:
            print(f"[ERROR] Не удалось обработать: {len(failed_files)} файлов")
            for f in failed_files:
                print(f"  - {f}")
        
    except FileNotFoundError:
        print(f"[ERROR] Директория {data_dir} не найдена")
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке файлов: {str(e)}")


def features_for_one_file(input_file: str, output_file: str) -> bool:
    print(f"Обработка файла: {input_file}")
    try:
        df_features = extract_features_from_file(input_file)
        df_features.to_csv(output_file, index=False)
        print(f"[OK] Обработанный файл сохранен: {output_file}")
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] Файл {input_file} не найден")
        return False
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке файла {input_file}: {str(e)}")
        return False


def features_for_one_file_for_all(input_file: str, output_file: str) -> bool:
    print(f"Обработка файла: {input_file}")
    try:
        df_features = extract_features_from_file_for_learning(input_file)
        df_features.to_csv(output_file, index=False)
        print(f"[OK] Обработанный файл сохранен: {output_file}")
        return True

    except FileNotFoundError:
        print(f"[ERROR] Файл {input_file} не найден")
        return False
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке файла {input_file}: {str(e)}")
        return False


def features_for_all_files(data_dir: str):
    
    print(f"Начало выделения признаков и таргета файлов в директории: {data_dir}")
    try:
        features_files = []
        failed_files = []
        
        csv_files = csv_sort(data_dir)
        
        features_dir = os.path.join(os.path.dirname(data_dir), 'data_feature')
        os.makedirs(features_dir, exist_ok=True)
        
        for csv_file in csv_files:
            input_path = os.path.join(data_dir, csv_file)

            if '_processed' in csv_file:
                output_filename = csv_file.replace('_processed', '_features')
            else:
                base_name = os.path.splitext(csv_file)[0]
                output_filename = f"{base_name}_features.csv"
            output_path = os.path.join(features_dir, output_filename)
            
            if features_for_one_file_for_all(input_path, output_path):
                features_files.append(csv_file)
            else:
                failed_files.append(csv_file)
        
        print(f"\nОбработка завершена:")
        print(f"[OK] Успешно обработано: {len(features_files)} файлов")
        if failed_files:
            print(f"[ERROR] Не удалось обработать: {len(failed_files)} файлов")
            for f in failed_files:
                print(f"  - {f}")
        
    except FileNotFoundError:
        print(f"[ERROR] Директория {data_dir} не найдена")
    except Exception as e:
        print(f"[ERROR] Ошибка при обработке файлов: {str(e)}")