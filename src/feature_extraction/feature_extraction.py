# -*- coding: utf-8 -*-
"""
Backwards-compatible feature extraction:
- Сохраняет имена функций/выходные столбцы прежними (f1..f26, defect, severity, K_value, fault_code).
- Внутри: допускает окна с 1–2 фазами (дорисовка недостающих каналов),
  устойчивое чтение CSV чанками, адаптивная калибровка severity только для подшипников.
"""

from __future__ import annotations
import os
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Fallback import path — чтобы файл работал и как модуль, и как скрипт
try:
    from src.feature_extraction.feature_classifier import (
        DEFAULT_FS, DEFAULT_RPM, get_feature_vector, classify_defect_scored, severity_from_K
    )
except ImportError:
    from feature_classifier import (
        DEFAULT_FS, DEFAULT_RPM, get_feature_vector, classify_defect_scored, severity_from_K
    )

# === Параметры обработки (поведение по умолчанию прежнее) ===
WINDOW_SEC = 1.0                 # окно ≈1 с
STEP_SEC = 0.5                   # шаг ≈0.5 с
MIN_VALID_RATIO = 0.80           # минимум валидных (не-NaN) точек в окне на фазу
CHUNK_SECONDS = 10.0             # читать CSV кусками по 10 секунд

BEARING_DEFECTS = {"Inner Race", "Outer Race", "Ball", "Cage"}

# === Утилиты ===
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    # допустимые варианты имён
    mapping = {}
    for c in df.columns:
        lc = c.lower().strip()
        if 'current_r' in lc or lc in ('r', 'phase_r', 'ia', 'phase_a'):
            mapping[c] = 'Current_R'
        elif 'current_s' in lc or lc in ('s', 'phase_s', 'ib', 'phase_b'):
            mapping[c] = 'Current_S'
        elif 'current_t' in lc or lc in ('t', 'phase_t', 'ic', 'phase_c'):
            mapping[c] = 'Current_T'
    out = df.copy()
    out.rename(columns=mapping, inplace=True)
    for need in ['Current_R', 'Current_S', 'Current_T']:
        if need not in out.columns:
            out[need] = np.nan
    return out[['Current_R', 'Current_S', 'Current_T']]

def _clean_window(arr: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Заменяет NaN на медиану окна, возвращает (массив, окно_валидно_по_доле)."""
    x = arr.astype(float, copy=False)
    valid_mask = np.isfinite(x)
    ratio = float(np.mean(valid_mask))
    if ratio == 0.0:
        return np.zeros_like(x), False
    med = float(np.nanmedian(x)) if np.any(valid_mask) else 0.0
    x = np.where(np.isfinite(x), x, med)
    return x, (ratio >= MIN_VALID_RATIO)

# === Публичная ф-ция (имя/выход прежние) ===

def extract_features_from_file(csv_path: str,
                               output_path: Optional[str] = None,
                               fs: float = DEFAULT_FS,
                               rpm_guess: float = DEFAULT_RPM) -> str:
    """
    Читает csv_path, проходит окнами и пишет *_features.csv (или output_path).
    Возвращает путь к сохранённому CSV. Формат столбцов как прежде.
    """
    if output_path is None:
        base, ext = os.path.splitext(csv_path)
        output_path = f"{base}_features.csv"

    # если передана папка — складываем в неё <input>_features.csv
    if os.path.isdir(output_path):
        base_in = os.path.splitext(os.path.basename(csv_path))[0]
        output_path = os.path.join(output_path, f"{base_in}_features.csv")

    # гарантируем существование директории назначения
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    window = int(WINDOW_SEC * fs)
    step = int(STEP_SEC * fs)
    chunk = int(CHUNK_SECONDS * fs)

    feats: List[List[float]] = []
    defects: List[str] = []
    severities: List[str] = []
    Kvals: List[float] = []
    codes: List[Optional[str]] = []

    tail = np.empty((0, 3), dtype=float)

    reader = pd.read_csv(csv_path, chunksize=chunk)
    for df in reader:
        sig = _normalize_columns(df).to_numpy(dtype=float)
        # склеиваем хвост для перекрытия
        if tail.size:
            sig = np.vstack([tail, sig])

        n = sig.shape[0]
        if n < window:
            tail = sig  # целиком в хвост, ждём следующий чанк
            continue

        # бегущие окна
        start = 0
        while start + window <= n:
            seg = sig[start:start+window, :]  # (N,3)
            # очистка/валидация по каналам
            ok_flags = []
            channels = []
            for ch in range(3):
                cleaned, ok = _clean_window(seg[:, ch])
                channels.append(cleaned)
                ok_flags.append(ok)

            n_valid = sum(ok_flags)
            if n_valid == 0:
                start += step
                continue

            # заполняем недостающие каналы: при 1 фазе дублируем её, при 2 — берём среднее двух
            if n_valid == 1:
                idx = ok_flags.index(True)
                base = channels[idx]
                R = base
                S = base
                T = base
            elif n_valid == 2:
                vals = [channels[i] for i, ok in enumerate(ok_flags) if ok]
                fill = (vals[0] + vals[1]) * 0.5
                filled = []
                for ok, ch in zip(ok_flags, channels):
                    filled.append(ch if ok else fill)
                R, S, T = filled
            else:
                R, S, T = channels

            fv = get_feature_vector(R, S, T, fs=fs, rpm_guess=rpm_guess)
            defect, severity, K, code = classify_defect_scored(R, S, T, fs=fs, rpm_guess=rpm_guess)

            feats.append(fv)
            defects.append(defect)
            severities.append(severity)
            Kvals.append(float(K))
            codes.append(code)

            # шаг окна
            start += step

        # оставляем перекрывающий хвост
        last_start = max(0, n - window + step)
        tail = sig[last_start:, :]

    # если ничего не набрали — создаём пустой CSV с заголовком прежнего формата
    cols = [f"f{i}" for i in range(1, 27)] + ["defect", "severity", "K_value", "fault_code"]
    if not feats:
        pd.DataFrame(columns=cols).to_csv(output_path, index=False)
        return output_path

    out = pd.DataFrame(feats, columns=[f"f{i}" for i in range(1, 27)])
    out["defect"] = defects
    out["severity"] = severities
    out["K_value"] = Kvals
    out["fault_code"] = codes

    # адаптивная перекалибровка severity только для подшипников — интерфейс/значения меток те же
    is_bearing = out["defect"].isin(BEARING_DEFECTS)
    if is_bearing.any():
        Kb = out.loc[is_bearing, "K_value"].to_numpy()
        if Kb.size >= 10:  # чтобы квантиль был осмысленным
            q70 = float(np.quantile(Kb, 0.70))
            q90 = float(np.quantile(Kb, 0.90))
            thr_med = max(3.0, q70)  # минимум «Medium» не ниже 3
            thr_high = max(4.0, q90) # минимум «High» не ниже 4
            def map_sev(k):
                if k >= thr_high:
                    return "High"
                if k >= thr_med:
                    return "Medium"
                return "Low"
            out.loc[is_bearing, "severity"] = [map_sev(k) for k in out.loc[is_bearing, "K_value"]]

    out.to_csv(output_path, index=False)
    return output_path
