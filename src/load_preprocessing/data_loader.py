import pandas as pd
import numpy as np

EXPECTED_PHASES = ['current_R', 'current_S', 'current_T']


def load_current_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    if not all(col in df.columns for col in EXPECTED_PHASES):
        raise ValueError(f"Файл должен содержать колонки: {EXPECTED_PHASES}")

    for phase in EXPECTED_PHASES:
        if phase not in df.columns:
            df[phase] = np.nan
    df = df[EXPECTED_PHASES]

    return df
