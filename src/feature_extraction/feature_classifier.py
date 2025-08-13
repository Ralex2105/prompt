import os, json, math
import numpy as np
from scipy.signal import butter, filtfilt, hilbert, find_peaks
from scipy.signal.windows import hann
from scipy.stats import skew, kurtosis, entropy

DEFAULT_FS = 25600.0      # fs = 25.6 кГц
DEFAULT_RPM = 1770.0      # ~29.5 Гц
EPS = 1e-12

DEFAULT_PARAMS = {
    "NUM_BALLS": 9,
    "BALL_DIAMETER": 0.0079,   # m
    "PITCH_DIAMETER": 0.0385,  # m
    "CONTACT_ANGLE": 0.0       # rad
}

def _robust_local_noise(freqs, spec, f0, window_hz=20.0, gap_hz=2.0):
    m = (freqs >= f0-window_hz) & (freqs <= f0+window_hz)
    if not np.any(m):
        return float(np.median(spec))
    g = (freqs > f0-gap_hz) & (freqs < f0+gap_hz)
    vals = spec[m & ~g]
    if vals.size == 0:
        return float(np.median(spec))
    q90 = np.quantile(vals, 0.90)
    vals = vals[vals <= q90]
    return float(np.median(vals)) if vals.size else float(np.median(spec))

def _peak_amp_near(freqs, spec, f0, tol=0.02):
    bw = max(f0*tol, 1.0)
    sel = (freqs >= f0-bw) & (freqs <= f0+bw)
    if not np.any(sel):
        return 0.0
    y = spec[sel]
    idx, _ = find_peaks(y)
    return float(y[idx].max()) if idx.size else float(y.max())

def _family_K(freqs, spec, f0, fr, w_main=1.0, w_h2=0.6, w_h3=0.3, w_sb=0.5, tol_main=0.015):
    a0  = _peak_amp_near(freqs, spec, f0,   tol=tol_main)
    a2  = _peak_amp_near(freqs, spec, 2*f0, tol=0.015)
    a3  = _peak_amp_near(freqs, spec, 3*f0, tol=0.02)
    as1 = _peak_amp_near(freqs, spec, abs(f0-fr), tol=0.02)
    as2 = _peak_amp_near(freqs, spec, f0+fr,      tol=0.02)
    noise = _robust_local_noise(freqs, spec, f0)
    num = w_main*a0 + w_h2*a2 + w_h3*a3 + w_sb*(as1+as2)
    Kf = float(num / (noise + EPS))
    primary_snr = float(a0 / (noise + EPS))
    return Kf, {"a0":a0, "a2":a2, "a3":a3, "as1":as1, "as2":as2, "noise":noise, "psnr":primary_snr}

def _family_K_ftf(freqs, spec, f0, fr):
    # FTF слабее
    return _family_K(freqs, spec, f0, fr, w_main=1.0, w_h2=0.4, w_h3=0.2, w_sb=0.8, tol_main=0.03)

def _best_rpm_by_family(EF, EY, defect_freqs_by_geometry, rpm_guess, span=0.2):
    rpms = np.linspace((1-span)*rpm_guess, (1+span)*rpm_guess, 13)
    best_rpm, best_score = rpm_guess, -np.inf
    for rpm in rpms:
        fr = rpm / 60.0
        fdef = defect_freqs_by_geometry(rpm)
        Ksum = 0.0
        for f0 in (fdef["BPFI"], fdef["BPFO"], fdef["BSF"], fdef["FTF"]):
            kf, _ = _family_K(EF, EY, f0, fr)
            Ksum += kf
        if Ksum > best_score:
            best_score = Ksum
            best_rpm = rpm
    return best_rpm

def load_bearing_params(path="bearing_config.json"):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return DEFAULT_PARAMS.copy()

bearing_params = load_bearing_params()

def defect_freqs_by_geometry(rpm: float) -> dict:
    fr = rpm / 60.0  # частота вращения вала
    z  = bearing_params["NUM_BALLS"]
    Bd = bearing_params["BALL_DIAMETER"]
    Pd = bearing_params["PITCH_DIAMETER"]
    ct = math.cos(bearing_params["CONTACT_ANGLE"])
    bpfi = (z/2.0) * (1 + (Bd/Pd)*ct) * fr
    bpfo = (z/2.0) * (1 - (Bd/Pd)*ct) * fr
    bsf  = (Pd/(2.0*Bd)) * (1 - ((Bd/Pd)*ct)**2) * fr
    ftf  = 0.5 * (1 - (Bd/Pd)*ct) * fr
    return {"BPFI": bpfi, "BPFO": bpfo, "BSF": bsf, "FTF": ftf}

def _butter(sig, fs, Wn, btype, order=4):
    b, a = butter(order, np.asarray(Wn)/(0.5*fs), btype=btype)
    return filtfilt(b, a, sig)

def preprocess_per_phase(x, fs=DEFAULT_FS):
    x = np.asarray(x, float)
    if np.all(np.isnan(x)):
        x = np.zeros_like(x)
    else:
        med = np.nanmedian(x)
        x = np.nan_to_num(x, nan=med)
    x -= np.mean(x)
    # НЧ-фильтр срез чуть ниже Fs/2 берём 0.45*Fs
    y = _butter(x, fs, 0.45*fs, 'low', order=4)
    return y - np.mean(y)

def envelope_spectrum_2_3k(sig, fs=DEFAULT_FS, band=(2000.0, 3000.0)):
    hf = _butter(sig, fs, band, 'bandpass', order=4)
    env = np.abs(hilbert(hf))
    N   = len(env)
    Y   = np.abs(np.fft.rfft(env*hann(N)))
    F   = np.fft.rfftfreq(N, 1.0/fs)
    if Y.size:
        Y[0] = 0.0
    return F, Y

def _safe_stats(region):
    r = np.asarray(region, float)
    if r.size == 0: r = np.array([0.0])
    st = float(np.std(r))
    sk = float(skew(r, bias=False)) if r.size > 1 else 0.0
    ku = float(kurtosis(r, bias=False)) if r.size > 1 else 0.0
    if not np.isfinite(sk): sk = 0.0
    if not np.isfinite(ku): ku = 0.0
    mu = float(np.mean(r))
    rr = np.clip(r, 0.0, None)
    if rr.sum() <= 0:
        probs = np.array([1.0])
    else:
        probs = rr / rr.sum();
        probs = np.clip(probs, 1e-12, 1.0)
        probs /= probs.sum()
    en = float(entropy(probs))
    return [st, sk, ku, mu, en]


def get_feature_vector(current_R, current_S, current_T, fs=DEFAULT_FS, rpm=DEFAULT_RPM):
    a = analyze_signal(current_R, current_S, current_T, fs, rpm)
    EF, EY = a["EF"], a["EY"]
    peak = a["peak_amps"]
    main_amp = max(a["main_amp"], EPS)

    # f1–f4: относительные амплитуды пиков дефектов к основной
    f1 = peak["BPFI"] / main_amp
    f2 = peak["BPFO"] / main_amp
    f3 = peak["BSF"] / main_amp
    f4 = peak["FTF"] / main_amp

    # f5 боковые полосы вокруг основной
    sideband_amp = 0.0
    RF, RY = a["RF"], a["RY"]
    m = (RF >= 50.0 - 5.0) & (RF <= 50.0 + 5.0)
    idx = np.where(m)[0]
    for i in idx:
        if abs(RF[i] - 50.0) < 0.5:
            continue
        if RY[i] > sideband_amp:
            sideband_amp = float(RY[i])
    f5 = sideband_amp / main_amp

    # f6-f25: 4 группы по 5 статистик
    stats = []
    for f0 in [a["fdef"]["BPFI"], a["fdef"]["BPFO"], a["fdef"]["BSF"], a["fdef"]["FTF"]]:
        w = (EF > f0 - 10.0) & (EF < f0 + 10.0)
        region = EY[w] if np.any(w) else np.array([0.0])
        stats.extend(_safe_stats(region))

    # f26 наклон тренда спектра огибающей
    if EF.size >= 2:
        slope = float(np.polyfit(EF, EY, 1)[0])
    else:
        slope = 0.0

    v = np.array([f1, f2, f3, f4, f5] + stats + [slope], float)
    return np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)


def analyze_signal(current_R, current_S, current_T, fs=DEFAULT_FS, rpm=DEFAULT_RPM):
    r = preprocess_per_phase(current_R, fs)
    s = preprocess_per_phase(current_S, fs)
    t = preprocess_per_phase(current_T, fs)
    combo = (r + s + t) / 3.0

    # спектр по фазам
    def _raw_fft(x):
        N = len(x)
        F = np.fft.rfftfreq(N, 1.0/fs)
        Y = np.abs(np.fft.rfft(x * hann(N)))
        return F, Y

    RF_r, RY_r = _raw_fft(r)
    RF_s, RY_s = _raw_fft(s)
    RF_t, RY_t = _raw_fft(t)

    # общий набор для f1..f26
    RF, RY = RF_r, RY_r

    # огибающая 2–3 кГц
    EF, EY = envelope_spectrum_2_3k(combo, fs)

    # подбор rpm по семействам
    best_rpm = _best_rpm_by_family(EF, EY, defect_freqs_by_geometry, rpm)
    fdef = defect_freqs_by_geometry(best_rpm)
    fr = best_rpm / 60.0

    # пики и локальный шум
    peak_amps = {k: _peak_amp_near(EF, EY, f0, tol=0.02) for k, f0 in fdef.items()}
    noise_lvls = {k: _robust_local_noise(EF, EY, f0)     for k, f0 in fdef.items()}

    # роторные метрики по трём фазам
    def _band_max(F, Y, f0):
        bw = max(f0*0.02, 1.0)
        m = (F >= f0-bw) & (F <= f0+bw)
        return float(np.max(Y[m])) if np.any(m) else 0.0

    def _noise_50(F, Y):
        m = (F >= 40.0) & (F <= 60.0)
        gap = (F > 49.4) & (F < 50.6)
        vals = Y[m & ~gap]
        return float(np.median(vals)) if vals.size else float(np.median(Y))

    A50s  = [_band_max(*xy, 50.0)  for xy in [(RF_r,RY_r),(RF_s,RY_s),(RF_t,RY_t)]]
    A100s = [_band_max(*xy, 100.0) for xy in [(RF_r,RY_r),(RF_s,RY_s),(RF_t,RY_t)]]
    A150s = [_band_max(*xy, 150.0) for xy in [(RF_r,RY_r),(RF_s,RY_s),(RF_t,RY_t)]]
    noise50s = [_noise_50(*xy) for xy in [(RF_r,RY_r),(RF_s,RY_s),(RF_t,RY_t)]]

    A50_mean  = float(np.mean(A50s))
    A100_mean = float(np.mean(A100s))
    A150_mean = float(np.mean(A150s))
    noise50_mean = float(np.mean(noise50s))
    coh50 = float(min(A50s) / (max(A50s) + EPS))
    A50_SNR = A50_mean / (noise50_mean + EPS)
    main_amp = max(A50_mean, EPS)

    return {
        "EF": EF, "EY": EY,
        "RF": RF, "RY": RY,
        "fdef": fdef, "fr": fr,
        "peak_amps": peak_amps,
        "noise_levels": noise_lvls,
        # ротор
        "A50_mean": A50_mean, "A100_mean": A100_mean, "A150_mean": A150_mean,
        "A50_SNR": A50_SNR, "coh50": coh50, "main_amp": main_amp
    }


def classify_defect(current_R, current_S, current_T, fs=DEFAULT_FS, rpm=DEFAULT_RPM):
    a = analyze_signal(current_R, current_S, current_T, fs, rpm)

    K = {k: a["peak_amps"][k] / (a["noise_levels"][k] + 1e-12) for k in a["peak_amps"]}
    fault, kval = None, 0.0
    # более мягкий порог на детект + шире границы severity
    DETECT_T = 2.0
    LOW_T    = 4.0
    MED_T    = 8.0
    HIGH_T   = 16.0

    for name in ["BPFI", "BPFO", "BSF", "FTF"]:
        if K[name] > kval and K[name] >= DETECT_T:
            fault, kval = name, K[name]

    if fault is not None:
        mapping = {"BPFI": "Inner Race", "BPFO": "Outer Race", "BSF": "Ball", "FTF": "Cage"}
        if   kval < LOW_T:  sev = "Low"
        elif kval < MED_T:  sev = "Medium"
        elif kval < HIGH_T: sev = "High"
        else:               sev = "High"
        return mapping[fault], sev

    # Расцентровка и дефект ротора
    A50  = a.get("A50_mean", 0.0)
    A100 = a.get("A100_mean", 0.0)
    A150 = a.get("A150_mean", 0.0)
    SNR  = a.get("A50_SNR", 0.0)      # A50 / noise вокруг 50 Гц
    coh  = a.get("coh50", 0.0)        # согласованность по фазам [0..1]

    pattern = (A100 >= 0.25*A50) or (A150 >= 0.15*A50)
    rotor_strong = (SNR >= 10.0) and (coh >= 0.6) and pattern

    if rotor_strong:
        #северити для ротора (возможно надо пофиксить)
        if SNR < 14:
            sev = "Low"
        elif SNR < 22:
            sev = "Medium"
        else:
            sev = "High"

        if A100 >= 0.45 * A50:
            return "Misalignment", sev
        else:
            return "Rotor", sev

    return "Normal", "None"


def classify_defect_scored(current_R, current_S, current_T, fs=DEFAULT_FS, rpm=DEFAULT_RPM):
    a = analyze_signal(current_R, current_S, current_T, fs, rpm)
    EF, EY = a["EF"], a["EY"]
    fr     = a["fr"];  fdef = a["fdef"]

    # BPFI/BPFO/BSF обычные, FTF другой
    Kmap, Pmap = {}, {}
    for key in ["BPFI","BPFO","BSF"]:
        Kmap[key], Pmap[key] = _family_K(EF, EY, fdef[key], fr)
    Kmap["FTF"], Pmap["FTF"] = _family_K_ftf(EF, EY, fdef["FTF"], fr)

    # сортируем по K
    order = sorted(Kmap, key=lambda k: Kmap[k], reverse=True)
    top_key = order[0]; top_val = Kmap[top_key]
    second_val = Kmap[order[1]]

    # пороги
    GAP_MIN = 0.20
    # общий порог
    FAMILY_T   = 3.2
    PSNR_T     = 1.8

    #Для FTF
    FTF_FAMILY_T = 2.6
    FTF_PSNR_T   = 1.4

    # проверка подшипника
    gap_ok = (top_val - second_val) / (top_val + EPS) >= GAP_MIN
    psnr   = Pmap[top_key]["psnr"]

    accept_bearing = False
    if top_key == "FTF":
        accept_bearing = (top_val >= FTF_FAMILY_T) and (psnr >= FTF_PSNR_T)
    else:
        accept_bearing = (top_val >= FAMILY_T) and (psnr >= PSNR_T)

    if accept_bearing and gap_ok:
        mapping = {"BPFI":"Inner Race","BPFO":"Outer Race","BSF":"Ball","FTF":"Cage"}
        # severity
        if   top_val < 5:   sev = "Low"
        elif top_val < 10:  sev = "Medium"
        else:               sev = "High"
        return mapping[top_key], sev, float(top_val), top_key

    # ротор/расцентровка
    A50, A100, SNR, coh = a["A50_mean"], a["A100_mean"], a["A50_SNR"], a["coh50"]
    rotor_K = A50 / (np.median(a["RY"]) + EPS)

    rotor_strong = (SNR >= 12.0) and (coh >= 0.65) and (A100 >= 0.25*A50)
    if rotor_strong:
        sev = "High" if SNR >= 20 else ("Medium" if SNR >= 14 else "Low")
        kind = "Misalignment" if A100 >= 0.45*A50 else "Rotor"
        return kind, sev, float(rotor_K), None

    # ничего яркого
    return "Normal", "None", 0.0, None

def severity_from_K(kval: float, thresholds: dict | None = None) -> str:
    if thresholds is None or kval <= 0:
        return "None"
    if kval < thresholds['low']:
        return "Low"
    if kval < thresholds['med']:
        return "Medium"
    return "High"