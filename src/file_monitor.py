import os
import time
import multiprocessing
import logging
from queue import Empty

from .app import logger
from src.load_preprocessing.pipeline_load_refactor import process_and_save_one_file
from src.feature_extraction.feature_extraction import extract_features_from_file
from src.model.process_defects import process_defects_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FileMonitor:
    def __init__(self, input_dir, output_dir, action, queue=None):
        """
        Initialize the FileMonitor with input and output directories, action type, and a queue for passing files between processes.

        :param input_dir: Directory to monitor for new files.
        :param output_dir: Directory where processed files will be saved.
        :param action: The action to perform: 'preprocess', 'extract_features', or 'process_defects'.
        :param queue: Multiprocessing Queue to pass files from one stage to the next (optional).
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.action = action
        self.queue = queue
        self.running = multiprocessing.Event()
        self.running.set()
        self.seen_files = set()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def update_seen_files(self):
        """Keep only those seen files that still exist (do not overwrite, to preserve 'new file' detection)."""
        existing = set([f for f in os.listdir(self.input_dir) if f.endswith('.csv') and os.path.exists(os.path.join(self.input_dir, f))])
        # Drop files that were deleted; do NOT reset to 'existing' (that breaks new-file detection)
        self.seen_files &= existing
        logger.info(f"[{self.action}] Seen files (post-cleanup): {self.seen_files}")

    def monitor(self):
        """Monitor the input directory and process files (from directory or queue)."""
        while self.running.is_set():
            # List current CSVs
            current_files = set([f for f in os.listdir(self.input_dir) if f.endswith('.csv') and os.path.exists(os.path.join(self.input_dir, f))])
            logger.info(f"[{self.action}] Checking directory {self.input_dir}, current files: {current_files}")

            # New files are those not seen yet
            new_files = current_files - self.seen_files
            logger.info(f"[{self.action}] New files: {new_files}")

            for file in sorted(new_files):
                # Only process files with correct prefix
                if (self.action == 'preprocess' and file.startswith('current_')) or \
                   (self.action == 'extract_features' and file.startswith('processed_')) or \
                   (self.action == 'process_defects' and file.startswith('feature_data_')):
                    logger.info(f"[{self.action}] Detected new file in directory: {file}")
                    try:
                        self.process_file(file)
                        self.seen_files.add(file)
                        if self.queue:
                            identifier = file.replace('current_', '').replace('processed_', '').replace('feature_data_', '').replace('.csv', '')
                            output_file = f"{'processed_' if self.action == 'preprocess' else 'feature_data_' if self.action == 'extract_features' else 'summary_data_'}{identifier}.csv"
                            self.queue.put(output_file)
                            logger.info(f"[{self.action}] Queued file for next process: {output_file}")
                    except Exception as e:
                        logger.error(f"[{self.action}] Error processing file from directory: {file}: {e}")

            # If we have a queue and are the last stage, also consume queued items
            if self.queue and self.action == 'process_defects':
                try:
                    while True:
                        file = self.queue.get_nowait()
                        logger.info(f"[{self.action}] Processing file from queue: {file}")
                        try:
                            input_path = os.path.join(self.input_dir, file)
                            if os.path.exists(input_path) and file not in self.seen_files:
                                self.process_file(file, input_path)
                                self.seen_files.add(file)
                            else:
                                logger.warning(f"[{self.action}] File from queue does not exist or already processed: {input_path}")
                        except Exception as e:
                            logger.error(f"[{self.action}] Error processing file from queue: {file}: {e}")
                except Empty:
                    pass  # No file in queue

            # Cleanup seen files for any that disappeared
            self.update_seen_files()
            time.sleep(5)  # Poll every 5 seconds

    def process_file(self, file, input_path=None):
        """
        Process a file based on the action.

        :param file: File name to process.
        :param input_path: Optional explicit input path.
        """
        if input_path is None:
            input_path = os.path.join(self.input_dir, file)

        if self.action == 'preprocess':
            identifier = file.replace('current_', '').replace('.csv', '')
            output_filename = f'processed_{identifier}.csv'
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Preprocessing file: {input_path} -> {output_path}")
            process_and_save_one_file(input_path, output_path)

        elif self.action == 'extract_features':
            identifier = file.replace('processed_', '').replace('.csv', '')
            output_filename = f'feature_data_{identifier}.csv'
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Extracting features: {input_path} -> {output_path}")
            extract_features_from_file(input_path, output_path)

        elif self.action == 'process_defects':
            identifier = file.replace('feature_data_', '').replace('.csv', '')
            output_filename = f'summary_data_{identifier}.csv'
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Processing defects: {input_path} -> {output_path}")

            result = process_defects_file(input_path, output_path)

            # Log a quick readable summary
            if isinstance(result, dict):
                logger.info("-" * 50)
                logger.info(f"[{self.action}] File: {file}")
                logger.info(f"[{self.action}] Summary Defect: {result.get('summary_defect')}")
                logger.info(f"[{self.action}] Summary Severity: {result.get('summary_severity')}")
                logger.info(f"[{self.action}] Additional Note: {result.get('additional_note')}")
                logger.info(f"[{self.action}] Analysis Time: {result.get('analysis_time')}")
                logger.info("-" * 50)

    def start(self):
        """Start the monitor in a single process."""
        process = multiprocessing.Process(target=self.monitor)
        process.start()
        return [process]

    def stop(self):
        """Stop the monitor."""
        self.running.clear()
