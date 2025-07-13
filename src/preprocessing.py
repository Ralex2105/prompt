import pandas as pd
import numpy as np
from scipy import signal


def preprocess_data(
        df: pd.DataFrame,
        fill_method: str = 'interpolate',
        normalize: bool = True,
        filter_signals: bool = True,
        filter_band: tuple = (50, 1000),
        sampling_rate: float = 25600.0,
        round_digits: int = None
) -> pd.DataFrame:
    """
    Универсальная предобработка:
    - удаляет нечисловые строки (только float/NaN допускаются)
    - заполняет пропуски (интерполяция/ffill/bfill/drop)
    - нормализует данные (Z-score)
    - опционально фильтрует (bandpass)
    - опционально округляет числа до нужного количества знаков
    """

    # 1. Преобразуем всё к числовому типу; ошибки — в NaN
    df = df.apply(pd.to_numeric, errors='coerce')

    # 2. Удаляем полностью пустые строки (если все три NaN)
    df = df.dropna(how='all')
    # (Если нужно оставить только полностью заполненные строки, раскомментируй строку ниже)
    # df = df.dropna()

    # 3. Обработка пропусков (интерполяция/заполнение)
    if df.isnull().values.any():
        if fill_method == 'interpolate':
            df = df.interpolate(method='linear').ffill().bfill()
        elif fill_method == 'ffill':
            df = df.ffill()
        elif fill_method == 'bfill':
            df = df.bfill()
        elif fill_method == 'drop':
            df = df.dropna()
        else:
            raise ValueError(f"Неизвестный метод заполнения: {fill_method}")

    # 4. Нормализация
    if normalize:
        df = (df - df.mean()) / df.std(ddof=0)

    # 5. Фильтрация сигналов (bandpass, если включено)
    if filter_signals:
        sos = signal.butter(4, filter_band, btype='bandpass', fs=sampling_rate, output='sos')
        df = pd.DataFrame(signal.sosfiltfilt(sos, df.values, axis=0), columns=df.columns, index=df.index)

    # 6. Округление (если задано)
    if round_digits is not None:
        df = df.round(round_digits)

    return df
