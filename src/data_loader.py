import pandas as pd
import numpy as np

EXPECTED_PHASES = ['current_R', 'current_S', 'current_T']


def load_current_data(file_path: str) -> pd.DataFrame:
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip().replace(' ', '')

    header_candidate = ','.join([x.lower() for x in EXPECTED_PHASES])
    if first_line.lower() == header_candidate:
        df = pd.read_csv(file_path)
    else:
        df = pd.read_csv(file_path, header=None)
        df.columns = EXPECTED_PHASES[:df.shape[1]]

    for phase in EXPECTED_PHASES:
        if phase not in df.columns:
            df[phase] = np.nan
    df = df[EXPECTED_PHASES]

    return df
