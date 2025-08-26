import os
from src.file_monitor import FileMonitor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory paths (absolute, based on this file location)
RAW_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_processed")
FEATURE_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_feature")
SUMMARY_DATA_DIR = os.path.join(BASE_DIR, "..", "data", "data_summary")

from multiprocessing import Queue

def main():
    # Create queues to pass output filenames between stages
    preprocess_queue = Queue()
    feature_queue = Queue()

    # Stage 1: Preprocess raw 'current_*.csv' -> 'processed_*.csv'
    preprocess_monitor = FileMonitor(RAW_DATA_DIR, PROCESSED_DATA_DIR, 'preprocess', preprocess_queue)

    # Stage 2: Extract features 'processed_*.csv' -> 'feature_data_*.csv'
    feature_monitor = FileMonitor(PROCESSED_DATA_DIR, FEATURE_DATA_DIR, 'extract_features', feature_queue)

    # Stage 3: Process defects 'feature_data_*.csv' -> 'summary_data_*.csv'
    # Important: pass feature_queue so the last stage can also consume queued names immediately
    defects_monitor = FileMonitor(FEATURE_DATA_DIR, SUMMARY_DATA_DIR, 'process_defects', feature_queue)

    # Start monitors
    processes = []
    processes += preprocess_monitor.start()
    processes += feature_monitor.start()
    processes += defects_monitor.start()

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        preprocess_monitor.stop()
        feature_monitor.stop()
        defects_monitor.stop()
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    main()