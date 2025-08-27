import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
from scipy.fft import fft, fftfreq

def normalize(df: pd.DataFrame, dc: bool = True) -> pd.DataFrame:
    if dc:
        return df - df.mean()
    else:
        return (df - df.mean()) / df.std()
        
    
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
    hf = bandpass_filter(sig, band[0], band[1], fs)
    env = np.abs(hilbert(hf))
    return fft_transform(env, fs)

def dq_transform(df: pd.DataFrame) -> pd.DataFrame:

    i_a = df['current_R']
    i_b = df['current_S']
    i_c = df['current_T']

    i_d = (np.sqrt(2)/np.sqrt(3))*i_a - (np.sqrt(1)/np.sqrt(6))*i_b
    i_q = (1/np.sqrt(2))*i_b - (1/np.sqrt(2))*i_c

    df = pd.DataFrame({
        'i_d': i_d,
        'i_q': i_q
    }, index=df.index)
    
    return df

def preprocess_data(df: pd.DataFrame, dc: bool = True, combined: bool = False, dq: bool = False) -> pd.DataFrame:

    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(how='all')
    df = normalize(df, dc)

    if combined:
        df = df.mean(axis=1)
    if dq:
        df = dq_transform(df)

    return df
