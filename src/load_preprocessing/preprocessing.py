import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
from scipy.fft import fft, fftfreq

    
def bandpass_filter(sig, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut/nyq, highcut/nyq], btype='band')
    return filtfilt(b, a, sig)


def fft_transform(sig, fs):
    N = len(sig)
    yf = np.abs(fft(sig))[:N//2]
    xf = fftfreq(N, 1/fs)[:N//2]
    return xf, yf


def envelope_spectrum(sig, fs, band=(2000,3000)):
    # band: high-frequency band for envelope
    hf = bandpass_filter(sig, band[0], band[1], fs)
    env = np.abs(hilbert(hf))
    return fft_transform(env, fs)


def preprocess_data(df: pd.DataFrame, dc = True) -> pd.DataFrame:

    # Преобразуем всё к числовому типу; ошибки — в NaN
    df = df.apply(pd.to_numeric, errors='coerce')
    # Удаляем полностью пустые строки
    df = df.dropna(how='all')
    if dc:
        df = df - df.mean()

    return df
