import os
import numpy as np
import pandas as pd
from src.feature_extraction.feature_classifier import (
    get_feature_vector,
    classify_defect_scored,
    severity_from_K,
    DEFAULT_FS,
)

CANON = {"current_r": "Current_R", "current_s": "Current_S", "current_t": "Current_T"}
REQUIRED = ["Current_R", "Current_S", "Current_T"]

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c: c.strip().lower().replace(" ", "_").replace(",", "") for c in df.columns}
    df = df.rename(columns=lower)
    for low, canon in CANON.items():
        if low in df.columns:
            df = df.rename(columns={low: canon})
    for col in REQUIRED:
        if col not in df.columns:
            df[col] = np.nan
    return df[REQUIRED].copy()

def _clean_window(win: pd.DataFrame) -> pd.DataFrame:
    for col in REQUIRED:
        s = pd.to_numeric(win[col], errors="coerce")
        win[col] = 0.0 if s.isnull().all() else s.fillna(s.median())
    return win

def extract_features_from_file(
    filename: str,
    out_dir: str,
    window_size: int = int(DEFAULT_FS),
    step: int = int(DEFAULT_FS // 2),
    rows_per_chunk: int | None = None
) -> str:
    if rows_per_chunk is None:
        rows_per_chunk = window_size * 4

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(filename))[0]
    out_path = os.path.join(out_dir, f"{base}_features.csv")

    prev_tail = pd.DataFrame(columns=REQUIRED)
    rows = []

    for chunk in pd.read_csv(filename, chunksize=rows_per_chunk):
        chunk = _normalize_columns(chunk)
        if not prev_tail.empty:
            chunk = pd.concat([prev_tail, chunk], ignore_index=True)

        n = len(chunk)
        if n < window_size:
            prev_tail = chunk
            continue

        for start in range(0, n - window_size + 1, step):
            end = start + window_size
            win = _clean_window(chunk.iloc[start:end].copy())
            r = win["Current_R"].to_numpy(float)
            s = win["Current_S"].to_numpy(float)
            t = win["Current_T"].to_numpy(float)

            v = get_feature_vector(r, s, t, fs=DEFAULT_FS)
            defect, _, kmax, fault_code = classify_defect_scored(r, s, t, fs=DEFAULT_FS)

            rows.append({
                **{f"f{i+1}": float(v[i]) for i in range(len(v))},
                "defect": defect,
                "severity": "None",  #Исправить потом
                "K_value": float(kmax),
                "fault_code": fault_code,
            })

        prev_tail = chunk.iloc[max(0, n - window_size + 1):].copy()

    # адаптивная шкала по подшипниковым окнам (q70/q90)
    df = pd.DataFrame(rows)
    mask_bearing = df["fault_code"].notna()
    if mask_bearing.any():
        q70 = float(df.loc[mask_bearing, "K_value"].quantile(0.70))
        q90 = float(df.loc[mask_bearing, "K_value"].quantile(0.90))
        thr = {"low": max(q70, 2.0), "med": max(q90, 3.0)}
        df.loc[mask_bearing, "severity"] = df.loc[mask_bearing, "K_value"].apply(lambda k: severity_from_K(k, thr))
    else:
        # если подшипников вообще нет — severity оставим
        pass

    df.drop(columns=["K_value", "fault_code"], inplace=True)
    df.to_csv(out_path, index=False)
    df.to_csv(out_path, index=False)
    return out_path