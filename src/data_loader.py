import pandas as pd


EXPECTED_PHASES = ['current_R', 'current_S', 'current_T']


def load_current_data(file_path: str) -> pd.DataFrame:
    """
    Загружает данные токов фаз из CSV-файла.
    Обрабатывает случаи, когда некоторые фазы отсутствуют или содержат пропуски.

    param: file_path (str): Путь к файлу CSV с фазными токами.
    returns: pd.DataFrame: DataFrame с колонками доступных фаз.
    """

    df = pd.read_csv(file_path)

    available_phases = [phase for phase in EXPECTED_PHASES if phase in df.columns]

    if not available_phases:
        raise ValueError("В файле нет данных ни по одной из фаз (R, S, T)!")

    df = df[available_phases]

    if df.isnull().values.any():
        print(f"Обнаружены пропущенные значения в фазах {available_phases}")

    return df
