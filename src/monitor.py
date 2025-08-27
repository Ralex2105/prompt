import os

from .file_monitor import FileMonitor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RAW_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_processed")
FEATURE_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_feature")
SUMMARY_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_summary")
DATA_ML_DIR = os.path.join(BASE_DIR, "..", "data", "data_ml")


from multiprocessing import Queue

def main():
    
    preprocess_queue = Queue()
    feature_queue = Queue()
    ml_queue = Queue()

    preprocess_monitor = FileMonitor(RAW_DATA_DIR, PROCESSED_DATA_DIR, 'preprocess', preprocess_queue)

    feature_monitor = FileMonitor(PROCESSED_DATA_DIR, FEATURE_DATA_DIR, 'extract_features', feature_queue)

    ml_monitor = FileMonitor(FEATURE_DATA_DIR, DATA_ML_DIR, 'ml_infer', ml_queue)

    defects_monitor = FileMonitor(DATA_ML_DIR, SUMMARY_DATA_DIR, 'process_defects', ml_queue)

    processes = []
    processes += preprocess_monitor.start()
    processes += feature_monitor.start()
    processes += ml_monitor.start()
    processes += defects_monitor.start()

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        preprocess_monitor.stop()
        feature_monitor.stop()
        ml_monitor.stop()
        defects_monitor.stop()
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    main()