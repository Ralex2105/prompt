import numpy as np
import math
import json
from scipy.signal import butter, filtfilt, hilbert
from scipy.signal.windows import hann
from scipy.stats import skew, kurtosis, entropy

DEFAULT_FS = 25600.0

def load_bearing_params(config_path="bearing_config.json"):
    with open(config_path, "r") as f:
        params = json.load(f)
    return params

bearing_params = load_bearing_params()

def calc_defect_frequencies(rot_speed_hz):
    N = bearing_params["NUM_BALLS"]
    Bd = bearing_params["BALL_DIAMETER"]
    Pd = bearing_params["PITCH_DIAMETER"]
    cos_theta = math.cos(bearing_params["CONTACT_ANGLE"])
    bpfi = (N / 2.0) * (1 + (Bd / Pd) * cos_theta) * rot_speed_hz
    bpfo = (N / 2.0) * (1 - (Bd / Pd) * cos_theta) * rot_speed_hz
    bsf  = (Pd / (2.0 * Bd)) * (1 - ((Bd / Pd) * cos_theta)**2) * rot_speed_hz
    ftf  = 0.5 * (1 - (Bd / Pd) * cos_theta) * rot_speed_hz
    return {"BPFI": bpfi, "BPFO": bpfo, "BSF": bsf, "FTF": ftf}

def preprocess_signal(signal, fs=DEFAULT_FS):
    signal = np.nan_to_num(signal, nan=np.nanmedian(signal))
    signal = signal - np.mean(signal)
    lowcut, highcut = 1.0, 1000.0
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(N=4, Wn=[low, high], btype='band')
    filtered = filtfilt(b, a, signal)
    return filtered

def envelope_signal(signal):
    analytic_signal = hilbert(signal)
    return np.abs(analytic_signal)

def analyze_signal(current_R, current_S, current_T, fs=DEFAULT_FS):
    sigR = preprocess_signal(current_R, fs)
    sigS = preprocess_signal(current_S, fs)
    sigT = preprocess_signal(current_T, fs)
    envR = envelope_signal(sigR)
    envS = envelope_signal(sigS)
    envT = envelope_signal(sigT)
    env_avg = (envR + envS + envT) / 3.0
    N = len(env_avg)
    window = hann(N)
    env_fft = np.fft.rfft(env_avg * window)
    env_freqs = np.fft.rfftfreq(N, d=1.0/fs)
    env_mag = np.abs(env_fft)
    env_mag[0] = 0.0

    N_raw = len(sigR)
    raw_fft = np.fft.rfft(sigR * hann(N_raw))
    raw_freqs = np.fft.rfftfreq(N_raw, d=1.0/fs)
    raw_mag = np.abs(raw_fft)
    f_line_idx = np.argmax(raw_mag)
    main_freq = raw_freqs[f_line_idx]
    main_amp = raw_mag[f_line_idx]
    pole_pairs, slip = 2, 0.01
    rot_speed_hz = main_freq / pole_pairs * (1 - slip)
    defect_freqs = calc_defect_frequencies(rot_speed_hz)
    peak_amps = {}
    search_margin = 0.02
    for name, freq in defect_freqs.items():
        margin_hz = max(freq * search_margin, 1.0)
        f_min = max(0, freq - margin_hz)
        f_max = freq + margin_hz
        indices = np.where((env_freqs >= f_min) & (env_freqs <= f_max))[0]
        peak_amp = np.max(env_mag[indices]) if len(indices) > 0 else 0.0
        peak_amps[name] = peak_amp
    sideband_amp = 0.0
    sideband_window = 5.0
    side_indices = np.where((raw_freqs >= main_freq - sideband_window) & (raw_freqs <= main_freq + sideband_window))[0]
    for idx in side_indices:
        f = raw_freqs[idx]
        if abs(f - main_freq) < 0.5: continue
        if raw_mag[idx] > sideband_amp: sideband_amp = raw_mag[idx]
    baseline = float(np.median(env_mag))
    return {
        "defect_freqs": defect_freqs,
        "main_freq": float(main_freq),
        "main_amp": float(main_amp),
        "peak_amps": peak_amps,
        "sideband_amp": float(sideband_amp),
        "envelope_spectrum": (env_freqs, env_mag),
        "raw_spectrum": (raw_freqs, raw_mag),
        "baseline": baseline
    }

def classify_defect(current_R, current_S, current_T, fs=DEFAULT_FS):
    analysis = analyze_signal(current_R, current_S, current_T, fs)
    peak_amps = analysis["peak_amps"]
    sideband_amp = analysis["sideband_amp"]
    main_amp = analysis["main_amp"]
    env_mag = analysis["envelope_spectrum"][1]
    dyn_baseline = np.quantile(env_mag, 0.75)
    max_type, max_amp = None, 0.0
    for name, amp in peak_amps.items():
        if amp > max_amp and amp > 2 * dyn_baseline:
            max_amp = amp
            max_type = name
        if max_type:
            mapping = {"BPFI": "Inner Race", "BPFO": "Outer Race", "BSF": "Ball", "FTF": "Cage"}
            defect_type = mapping[max_type]
        elif sideband_amp > 0 and sideband_amp > 0.1 * main_amp:
            defect_type = "Rotor"
        else:
            defect_type = "Normal"
        if defect_type == "Normal":
            severity_label = "None"
        else:
            if defect_type in ["Inner Race", "Outer Race", "Ball", "Cage"]:
                K = max_amp / (dyn_baseline + 1e-12)
            elif defect_type == "Rotor":
                raw_mag = analysis["raw_spectrum"][1]
                noise_floor = np.median(raw_mag)
                K = sideband_amp / (noise_floor + 1e-12)
            else:
                K = 0.0
            if K < 3:
                severity_label = "Low"
            elif K < 10:
                severity_label = "Medium"
            else:
                severity_label = "High"
        return defect_type, severity_label

def get_feature_vector(current_R, current_S, current_T, fs=DEFAULT_FS):
    analysis = analyze_signal(current_R, current_S, current_T, fs)
    main_amp = analysis["main_amp"]
    peak_amps = analysis["peak_amps"]
    sideband_amp = analysis["sideband_amp"]
    env_freqs, env_mag = analysis["envelope_spectrum"]
    amp_ratios = [
        peak_amps["BPFI"] / main_amp,
        peak_amps["BPFO"] / main_amp,
        peak_amps["BSF"] / main_amp,
        peak_amps["FTF"] / main_amp,
        sideband_amp / main_amp
    ]
    window = 10
    stats = []
    for freq in analysis["defect_freqs"].values():
        idx = np.where((env_freqs > freq - window) & (env_freqs < freq + window))
        region = env_mag[idx]
        if len(region) == 0:
            region = [0]
        stats.extend([
            np.std(region),
            skew(region),
            kurtosis(region),
            np.mean(region),
            entropy(region/np.sum(region)+1e-12)
        ])
    x, y = env_freqs, env_mag
    slope = np.polyfit(x, y, 1)[0]
    return np.concatenate([amp_ratios, stats, [slope]])