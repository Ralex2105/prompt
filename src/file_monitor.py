import os
import time
import multiprocessing
from queue import Empty

from .app import logger
from .load_preprocessing.pipeline_load_refactor import process_and_save_one_file
from .feature_extraction.feature_extraction import extract_features_from_file
from .model.process_defects import process_defects_file


def run_ml_inference_file(input_path: str, output_path: str):
    """
    Инференс CatBoost по фичам -> запись ml_data_*.csv.
    Перед сохранением индексы классов конвертируются в строки согласно исходной разметке.
    """
    import os
    import numpy as np
    import pandas as pd

    try:
        from catboost import CatBoostClassifier, Pool
    except ModuleNotFoundError:
        from .app import logger
        logger.error("CatBoost не установлен. Установите: pip install catboost (или poetry/conda)")
        raise

    df = pd.read_csv(input_path)

    # 1) фичи
    exclude = {"defect", "severity", "summary_defect", "summary_severity", "additional_note", "analysis_time"}
    feature_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
    if not feature_cols:
        tmp = df.drop(columns=[c for c in df.columns if c in exclude], errors="ignore").copy()
        for c in tmp.columns:
            tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
        feature_cols = [c for c in tmp.columns if pd.api.types.is_numeric_dtype(tmp[c]) and tmp[c].notna().any()]
        if not feature_cols:
            raise ValueError("Не найдено числовых фич для инференса.")
    X = df[feature_cols].copy()

    # 2) поиск моделей
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(here, ".."))
    model_dir_env = os.getenv("MODEL_DIR")
    defect_override = os.getenv("DEFECT_MODEL_PATH")
    severity_override = os.getenv("SEVERITY_MODEL_PATH")

    def find_model(name: str, override: str | None):
        candidates = []
        if override:
            candidates.append(override)
        if model_dir_env:
            candidates.append(os.path.join(model_dir_env, name))
        candidates += [
            os.path.join(project_root, "model", name),
            os.path.join(here, "model", name),
            os.path.join(project_root, "models", name),
            os.path.join(project_root, name),
            os.path.join(here, "..", "model", name),
            os.path.join(here, name),
            os.path.join("/", "mnt", "data", name),
        ]
        for p in candidates:
            if os.path.exists(p):
                return os.path.abspath(p)
        return None

    defect_path = find_model("model_defect.cbm", defect_override)
    severity_path = find_model("model_severity.cbm", severity_override)
    if not defect_path or not severity_path:
        from .app import logger
        logger.error("Не найдены model_defect.cbm и/или model_severity.cbm")
        raise FileNotFoundError("Не найдены model_defect.cbm и/или model_severity.cbm")

    # 3) инференс
    defect_clf = CatBoostClassifier();  defect_clf.load_model(defect_path)
    severity_clf = CatBoostClassifier(); severity_clf.load_model(severity_path)

    pool = Pool(X)

    def _to_1d(pred):
        pred = np.asarray(pred)
        if pred.ndim > 1:
            pred = np.squeeze(pred, axis=-1)
        return pred

    defect_raw = _to_1d(defect_clf.predict(pool, prediction_type="Class"))
    severity_raw = _to_1d(severity_clf.predict(pool, prediction_type="Class"))

    # 4) МАППИНГ ИНДЕКС -> СТРОКА
    DEFECT_NAMES = ["Normal", "Inner Race", "Outer Race", "Ball", "Cage", "Rotor", "Misalignment"]  # индексы 0..6
    SEVERITY_NAMES = ["None", "Low", "Medium", "High"]  # индексы 0..3

    def _map_to_names(arr, names):
        out = []
        K = len(names)
        for v in arr:
            if isinstance(v, str) and not v.isdigit():
                out.append(v)
                continue
            try:
                i = int(v)
                out.append(names[i] if 0 <= i < K else str(v))
            except Exception:
                out.append(str(v))
        return np.asarray(out, dtype=str)

    defect_labels = _map_to_names(defect_raw, DEFECT_NAMES)
    severity_labels = _map_to_names(severity_raw, SEVERITY_NAMES)

    # 5) сохранение
    out = df.copy()
    out["defect"] = defect_labels
    out["severity"] = severity_labels

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out.to_csv(output_path, index=False)
    return {
        "rows": len(out),
        "features_used": len(feature_cols),
        "output": output_path,
        "mode": "catboost+label_map",
        "defect_model": defect_path,
        "severity_model": severity_path,
    }
# -----------------------------------------------------------------------------


class FileMonitor:
    """
    Следит за входной директорией и запускает обработку новых .csv по этапам:
      1) preprocess:      current_*.csv      -> processed_*.csv
      2) extract_features: processed_*.csv   -> feature_data_*.csv
      3) ml_infer:        feature_data_*.csv -> ml_data_*.csv
      4) process_defects: ml_data_*.csv      -> summary_data_*.csv
    """

    def __init__(self, input_dir: str, output_dir: str, action: str, queue=None, poll_interval: float = 1.0):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.action = action  # 'preprocess' | 'extract_features' | 'ml_infer' | 'process_defects'
        self.queue = queue
        self.poll_interval = poll_interval
        self._stop_event = multiprocessing.Event()
        self._proc = None
        self.seen_files = set()

        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def start(self):
        self._proc = multiprocessing.Process(target=self._monitor_loop, daemon=True)
        self._proc.start()
        logger.info(f"[{self.action}] monitor started: {self.input_dir} -> {self.output_dir}")
        return [self._proc]

    def stop(self):
        self._stop_event.set()
        if self._proc and self._proc.is_alive():
            self._proc.terminate()
        logger.info(f"[{self.action}] monitor stopped")


    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                files = [f for f in os.listdir(self.input_dir) if f.endswith(".csv")]
                files.sort()
                for file in files:
                    if file in self.seen_files:
                        continue

                    ok = (
                        (self.action == "preprocess" and file.startswith("current_")) or
                        (self.action == "extract_features" and file.startswith("processed_")) or
                        (self.action == "ml_infer" and file.startswith("feature_data_")) or
                        (self.action == "process_defects" and file.startswith("ml_data_"))
                    )
                    if not ok:
                        continue
                    try:
                        self._process_file(file)
                    except Exception as e:
                        logger.exception(f"[{self.action}] monitor error on '{file}': {e}")
                    finally:
                        self.seen_files.add(file)

            except Exception as e:
                logger.exception(f"[{self.action}] monitor loop error: {e}")

            time.sleep(self.poll_interval)

    def _process_file(self, file: str):
        input_path = os.path.join(self.input_dir, file)

        if self.action == "preprocess":
            identifier = file.replace("current_", "").replace(".csv", "")
            output_filename = f"processed_{identifier}.csv"
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Preprocess: {input_path} -> {output_path}")
            process_and_save_one_file(input_path, output_path)

        elif self.action == "extract_features":
            identifier = file.replace("processed_", "").replace(".csv", "")
            output_filename = f"feature_data_{identifier}.csv"
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Extract features: {input_path} -> {output_path}")
            extract_features_from_file(input_path, output_path)

        elif self.action == "ml_infer":
            identifier = file.replace("feature_data_", "").replace(".csv", "")
            output_filename = f"ml_data_{identifier}.csv"
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] ML inference: {input_path} -> {output_path}")
            run_ml_inference_file(input_path, output_path)

        elif self.action == "process_defects":
            identifier = file.replace("ml_data_", "").replace(".csv", "")
            output_filename = f"summary_data_{identifier}.csv"
            output_path = os.path.join(self.output_dir, output_filename)
            logger.info(f"[{self.action}] Processing defects: {input_path} -> {output_path}")
            result = process_defects_file(input_path, output_path)
            if isinstance(result, dict):
                logger.info(f"[{self.action}] Saved summary -> {output_path}")
                logger.info(f"[{self.action}] Summary Defect: {result.get('summary_defect')}")
                logger.info(f"[{self.action}] Summary Severity: {result.get('summary_severity')}")
                logger.info(f"[{self.action}] Additional Note: {result.get('additional_note')}")
                logger.info(f"[{self.action}] Analysis Time: {result.get('analysis_time')}")

        if self.queue:
            identifier = (
                file.replace("current_", "")
                    .replace("processed_", "")
                    .replace("feature_data_", "")
                    .replace("ml_data_", "")
                    .replace(".csv", "")
            )
            prefix_map = {
                "preprocess": "processed_",
                "extract_features": "feature_data_",
                "ml_infer": "ml_data_",
                "process_defects": "summary_data_",
            }
            output_file = f"{prefix_map.get(self.action, '')}{identifier}.csv"
            self.queue.put(output_file)
