from __future__ import annotations
import json, math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.signal import butter, filtfilt, hilbert, welch, coherence

try:
    from src.feature_extraction.fault_params import CONFIG
except Exception:
    from fault_params import CONFIG

DEFAULT_FS: int = 25600
DEFAULT_RPM: float = 1770.0

def _safe_norm(fc, fs):
    ny = max(1e-6, 0.5 * fs)

    def _n(c):
        try:
            w = float(c) / ny
        except Exception:
            w = 0.5
        return min(0.999, max(1e-6, w))

    if isinstance(fc, (tuple, list)):
        lo, hi = sorted((_n(fc[0]), _n(fc[1])))
        return (max(1e-5, lo), min(0.999, hi))
    return _n(fc)


def _butter(x: NDArray[np.float64], fs: float, fc: float | tuple, btype: str, order: int = 2) -> NDArray[np.float64]:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    w = _safe_norm(fc, fs)
    b, a = butter(order, w, btype=btype)
    return filtfilt(b, a, x)


def _mcsa_sidebands_score(f_psd: NDArray[np.float64], Pxx: NDArray[np.float64],
                          mains: float, side_freq: float,
                          multipliers=CONFIG["MCSA_M_MULTIPLIERS"], bw: float = None) -> float:
    if side_freq <= 0 or f_psd.size == 0:
        return 0.0
    bw = float(CONFIG["MCSA_SB_BW"] if bw is None else bw)

    def peak_at(freq):
        m = (f_psd >= freq - bw) & (f_psd <= freq + bw)
        return float(np.max(Pxx[m]) if np.any(m) else 0.0)

    mask_noise = (f_psd >= mains + 5.0) & (f_psd <= mains + 80.0)
    for k in (2, 3):
        mask_noise &= ~((f_psd >= k * mains - 2.0) & (f_psd <= k * mains + 2.0))
    noise = float(np.median(Pxx[mask_noise])) if np.any(mask_noise) else 1e-12
    total = 0.0
    for mlt in multipliers:
        df = mlt * side_freq
        total += peak_at(mains + df) + peak_at(mains - df)
    return 10.0 * math.log10((total + 1e-12) / (noise + 1e-12))


def _autoselect_shaft_hz(env_f: NDArray[np.float64], env_A: NDArray[np.float64], rpm_guess: float) -> float:
    base = max(0.1, rpm_guess / 60.0)
    cand = np.linspace(0.70 * base, 1.30 * base, 25)

    def fam_total(fr_):
        fam = _bearing_family(fr_)
        return (_family_score_env(env_f, env_A, fr_, fam.BPFI)
                + _family_score_env(env_f, env_A, fr_, fam.BPFO)
                + _family_score_env(env_f, env_A, fr_, fam.BSF)
                + _family_score_env(env_f, env_A, fr_, fam.FTF))

    scores = np.array([fam_total(fr_) for fr_ in cand])
    i = int(np.argmax(scores));
    fr_best = float(cand[i])
    if 0 < i < len(cand) - 1:
        x = cand[i - 1:i + 2];
        y = scores[i - 1:i + 2]
        denom = (x[0] - x[1]) * (x[0] - x[2]) * (x[1] - x[2])
        if abs(denom) > 1e-12:
            a = (x[2] * (y[1] - y[0]) + x[1] * (y[0] - y[2]) + x[0] * (y[2] - y[1])) / denom
            b = (x[2] ** 2 * (y[0] - y[1]) + x[1] ** 2 * (y[2] - y[0]) + x[0] ** 2 * (y[1] - y[2])) / denom
            xv = -b / (2 * a) if abs(a) > 1e-12 else fr_best
            if cand[0] <= xv <= cand[-1]: fr_best = float(xv)
    return fr_best


def _fft_amp(x: NDArray[np.float64], fs: float) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Амплитудный спектр (односторонний) с нормировкой на окно Ханна.
    Args:
        x: временной ряд (A).
        fs: частота дискретизации, Гц.

    Returns:
        f: массив частот (Гц),
        amp: амплитудный спектр (в тех же единицах, что x), нормированный на суммарную амплитуду окна.
    """
    n = int(2 ** math.ceil(math.log2(max(8, len(x)))))
    if n <= 8:
        return np.array([0.0]), np.array([0.0])
    X = np.fft.rfft(x * np.hanning(len(x)), n=n)
    f = np.fft.rfftfreq(n, d=1.0 / fs)
    amp = (2.0 / (np.sum(np.hanning(len(x))) + 1e-12)) * np.abs(X)
    return f, amp


def preprocess_per_phase(x: NDArray[np.float64], fs: float) -> NDArray[np.float64]:
    """Предобработка фазного тока: центрирование, подавление дрейфа, очистка NaN.

    Args:
        x: временной ряд фазы (A).
        fs: частота дискретизации, Гц.

    Returns:
        Предобработанный сигнал той же длины.
    """
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    x = x - np.nanmean(x)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    try:
        if CONFIG["HPF_HZ"] and CONFIG["HPF_HZ"] > 0:
            x = _butter(x, fs, CONFIG["HPF_HZ"], "highpass", order=2)
    except Exception:
        pass
    return x

def envelope_spectrum_2_3k(x: NDArray[np.float64], fs: float) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Спектр огибающей после ВЧ-полосовой фильтрации и преобразования Хилберта.

    Args:
        x: временной ряд (A), агрегированный ток (например, среднее по фазам).
        fs: частота дискретизации, Гц.

    Returns:
        fe: частоты спектра огибающей (Гц).
        Ae: амплитудный спектр огибающей (условные единицы).
    """
    lo, hi = CONFIG["ENV_BAND_DEFAULT"]
    if CONFIG.get("USE_ADAPTIVE_ENVELOPE", True):
        scan_lo, scan_hi = CONFIG["ENV_BAND_SCAN"]
        width = float(CONFIG["ENV_BAND_WIDTH"])
        best_kurt, best = -np.inf, (lo, hi)
        centers = np.linspace(scan_lo + width / 2, scan_hi - width / 2, 9)
        for c in centers:
            band = (max(50.0, c - width / 2), c + width / 2)
            try:
                xf = _butter(x, fs, band, "bandpass", order=2)
                env = np.abs(hilbert(xf))
                k = _safe_kurtosis(env)
                if k > best_kurt:
                    best_kurt, best = k, band
            except Exception:
                continue
        lo, hi = best
    try:
        xf = _butter(x, fs, (lo, hi), "bandpass", order=2)
        env = np.abs(hilbert(xf))
        fe, Ae = _fft_amp(env - np.mean(env), fs)
    except Exception:
        fe, Ae = np.array([0.0]), np.array([0.0])
    return fe, Ae


# === Статистики (робастные) ===

def _safe_stats(x: NDArray[np.float64]) -> Tuple[float, float, float, float, float]:
    """Робастные статистики: std, skewness, kurtosis (эксцесс), mean, entropy.

    Args:
        x: массив значений (вещественный).

    Returns:
        (std, skew, kurt, mean, entropy), где kurt — эксцесс (kurtosis-3).
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    m = np.mean(x);
    s = np.std(x)
    if s < 1e-12:
        return s, 0.0, 0.0, m, 0.0
    z = (x - m) / s
    skew = np.mean(z ** 3);
    kurt = np.mean(z ** 4) - 3.0
    hist, _ = np.histogram(x, bins=50, density=True)
    p = hist / (np.sum(hist) + 1e-12)
    ent = -np.sum(p * np.log2(p + 1e-12))
    return s, float(skew), float(kurt), float(m), float(ent)


def _safe_kurtosis(x: NDArray[np.float64]) -> float:
    """Удобная обёртка: возвращает эксцесс, либо 0 при вырожденности.

    Args:
        x: массив значений.

    Returns:
        kurtosis-3 (float).
    """
    s, _, ku, _, _ = _safe_stats(x)
    return ku if s > 0 else 0.0


@dataclass
class BearingSet:
    """Набор характерных частот подшипника (Гц)."""
    BPFI: float;
    BPFO: float;
    BSF: float;
    FTF: float


def _load_bearing_config(path: str = "bearing_config.json") -> Optional[Dict[str, float]]:
    """Загрузка конфигурации подшипника.

    Поддерживает ключи:
      * абсолютные частоты BPFI/BPFO/BSF/FTF (в Гц) или коэффициенты (<10),
      * геометрия: N (число тел качения), D (делительный диаметр), D_BALL (диаметр тела), THETA/THETA_DEG.

    Returns:
        Словарь параметров или None, если файл отсутствует/повреждён.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k.upper(): float(v) for k, v in data.items()}
    except Exception:
        return None


def _bearing_family(shaft_hz: float) -> BearingSet:
    """Вычисляет BPFI/BPFO/BSF/FTF (Гц) из геометрии, коэффициентов или по умолчанию.

    Args:
        shaft_hz: частота вращения вала (Гц), т.е. RPM/60.

    Returns:
        BearingSet(BPFI, BPFO, BSF, FTF) в Гц.
    """
    cfg = _load_bearing_config()
    if cfg:
        N = cfg.get("N")
        D = cfg.get("D")
        d = cfg.get("D_BALL", cfg.get("D_B", cfg.get("D_BALLS", cfg.get("D_BALL_DIAM", cfg.get("D_BALL_DIAMETER",
                                                                                               cfg.get("D_BALL_D",
                                                                                                       cfg.get(
                                                                                                           "D_BALL_MM",
                                                                                                           cfg.get(
                                                                                                               "D_BALL_DIAM_MM",
                                                                                                               cfg.get(
                                                                                                                   "D_BALLS_DIAM",
                                                                                                                   cfg.get(
                                                                                                                       "D_BALLS_DIAMETER",
                                                                                                                       cfg.get(
                                                                                                                           "D_BALLS_MM",
                                                                                                                           cfg.get(
                                                                                                                               "D_BALLS_D"))))))))))))
        if d is None:
            d = cfg.get("D_SMALL", cfg.get("D_BALL_ALT", cfg.get("D_BALL_DIAMETER_ALT")))
        theta = cfg.get("THETA", cfg.get("THETA_DEG"))
        theta_rad = None
        if theta is not None:
            if "THETA_DEG" in cfg:
                theta_rad = math.radians(theta)
            else:
                theta_rad = float(theta)
        else:
            theta_rad = 0.0
        if all(v is not None for v in (N, D, d)):
            N = float(N);
            D = float(D);
            d = float(d)
            c = (d / D) * math.cos(theta_rad)
            bpfi_coef = (N / 2.0) * (1.0 + c)
            bpfo_coef = (N / 2.0) * (1.0 - c)
            bsf_coef = (D / (2.0 * d)) * (1.0 - c ** 2)
            ftf_coef = 0.5 * (1.0 - c)
            return BearingSet(bpfi_coef * shaft_hz,
                              bpfo_coef * shaft_hz,
                              bsf_coef * shaft_hz,
                              ftf_coef * shaft_hz)
        vals = {}
        have_any = False
        for name in ("BPFI", "BPFO", "BSF", "FTF"):
            if name in cfg:
                v = float(cfg[name])
                have_any = True
                vals[name] = (v * shaft_hz) if v < 10.0 else v
        if have_any:
            return BearingSet(vals.get("BPFI", 4.825 * shaft_hz),
                              vals.get("BPFO", 3.175 * shaft_hz),
                              vals.get("BSF", 2.322 * shaft_hz),
                              vals.get("FTF", 0.397 * shaft_hz))
    return BearingSet(4.825 * shaft_hz, 3.175 * shaft_hz, 2.322 * shaft_hz, 0.397 * shaft_hz)


def _family_score_env(f: NDArray[np.float64], A: NDArray[np.float64], fr: float, fam_hz: float) -> float:
    """Скоринг семейства подшипника в спектре огибающей.

    Args:
        f: частоты огибающей (Гц),
        A: амплитуды огибающей,
        fr: частота вала (Гц),
        fam_hz: центральная частота семейства (BPFI/BPFO/BSF/FTF) в Гц.

    Returns:
        Балл в дБ: 20·log10(энергия сигналов/локальный шум).
    """
    if fam_hz <= 0 or fr <= 0:
        return 0.0
    harmonics = [fam_hz * k for k in range(1, 4)]
    sidebands = [h + fr for h in harmonics] + [h - fr for h in harmonics]
    peaks = harmonics + sidebands
    total_signal = 0.0
    for p in peaks:
        if p > 0:
            w = max(1.0, 0.1 * fr)
            m = (f >= p - w) & (f <= p + w)
            total_signal += np.sum(A[m]) if np.any(m) else 0.0

    noise_band_low = max(10.0, fam_hz - 50.0)
    noise_band_high = fam_hz + 50.0
    m_noise = (f >= noise_band_low) & (f <= noise_band_high) & ~np.isin(f, peaks)
    noise = np.mean(A[m_noise]) if np.any(m_noise) else 1e-12
    return 20.0 * math.log10((total_signal + 1e-12) / (noise * len(peaks) + 1e-12))

def _has_multiphase_info(r: np.ndarray, s: np.ndarray, t: np.ndarray) -> bool:
    """Проверяет, есть ли минимум две **разные** фазы (для когерентности/ротора).

    Args:
        r, s, t: фазные токи (A).

    Returns:
        True, если доступны ≥2 канала с заметными различиями (не дубли одного и того же).
    """
    chans = [np.asarray(c, float) for c in (r, s, t)]
    valid = [c for c in chans if np.std(c) > 1e-9]
    if len(valid) < 2: return False

    def almost_same(a, b):
        if np.std(a) < 1e-9 or np.std(b) < 1e-9: return True
        corr = float(np.corrcoef(a, b)[0, 1]);
        rmse = float(np.sqrt(np.mean((a - b) ** 2)))
        return (corr > 0.999) and (rmse < 1e-6)

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            if not almost_same(valid[i], valid[j]): return True
    return False



def _snr_mains(f_psd, Pxx, mains):
    """SNR фундаментальной частоты сети.

    Args:
        f_psd, Pxx: массивы частот и PSD
        mains: f1 (Гц)

    Returns:
        (SNR_dB, power_fund) — отношение энергии в узком окне вокруг f1 к медиане шума над f1
    """
    m = (f_psd >= mains - 1.5) & (f_psd <= mains + 1.5)
    p50 = float(np.sum(Pxx[m])) if np.any(m) else 0.0
    mask_noise = (f_psd >= mains + 5.0) & (f_psd <= mains + 50.0)
    p_noise = float(np.median(Pxx[mask_noise])) if np.any(mask_noise) else 1e-12
    return 10.0 * math.log10((p50 + 1e-12) / (p_noise + 1e-12)), p50


def _broken_bar_pair_db(f_psd, Pxx, mains, max_offset, dyn_limit):
    """Оценка симметричной пары пиков около f1 (сломанные стержни ротора).

    Args:
        f_psd, Pxx: частоты и PSD
        mains: f1 (Гц)
        max_offset: статический максимум δ (Гц) из конфига
        dyn_limit: динамический максимум δ (Гц), напр. 0.06·f1

    Returns:
        Псевдо-SNR пары в дБ относительно пика фундамента.
    """
    upper = max(float(max_offset), float(dyn_limit))
    deltas = np.linspace(0.1, upper, 50)

    def peak_at(freq, bw=0.5):
        m = (f_psd >= freq - bw) & (f_psd <= freq + bw)
        return float(np.max(Pxx[m]) if np.any(m) else 0.0)

    best = 0.0
    for d in deltas:
        p = peak_at(mains - d) + peak_at(mains + d)
        if p > best: best = p
    p_main = peak_at(mains, bw=0.5) + 1e-12
    return 10.0 * math.log10(best / p_main)


def _eccentricity_ratio(f_psd, Pxx, mains, fr, m_values, bw):
    """Относительная энергия боковых f1 ± m·f_r (несоосность/эксцентриситет).

    Args:
        f_psd, Pxx: частоты и PSD
        mains: f1 (Гц)
        fr: частота вала (Гц)
        m_values: набор m (например, (1,2))
        bw: ширина окна вокруг каждой боковой (Гц)

    Returns:
        Отношение суммарной энергии боковых к энергии фундамента (безразмерное)
    """

    def band_power(freq):
        m = (f_psd >= freq - bw) & (f_psd <= freq + bw)
        return float(np.sum(Pxx[m])) if np.any(m) else 0.0

    num, den = 0.0, band_power(mains) + 1e-12
    for m_ in m_values:
        num += band_power(mains - m_ * fr) + band_power(mains + m_ * fr)
    return num / den


def get_feature_vector(curR: NDArray[np.float64], curS: NDArray[np.float64], curT: NDArray[np.float64],
                       fs: float = DEFAULT_FS, rpm_guess: float = DEFAULT_RPM) -> List[float]:
    """Формирует вектор признаков f1..f26 (совместим со старой моделью)

    Args:
        curR, curS, curT: фазные токи (A). Допускается одна/две фазы (пустые массивы для отсутствующих)
        fs: частота дискретизации (Гц), по умолчанию 25600
        rpm_guess: ожидаемая скорость (RPM) для начальной оценки f_r

    Returns:
        Список из 26 признаков [f1..f26] (float)
    """
    mains = CONFIG["MAINS_HZ"]
    r = preprocess_per_phase(curR, fs);
    s = preprocess_per_phase(curS, fs);
    t = preprocess_per_phase(curT, fs)
    x = (r + s + t) / 3.0

    fe, Ae = envelope_spectrum_2_3k(x, fs)
    f_psd, Pxx = welch(x, fs=fs, nperseg=min(8192, len(x)))


    pole_pairs = 2
    sync_hz = mains / pole_pairs
    slip_guess = 1 - (rpm_guess / 60.0) / sync_hz if sync_hz > 0 else 0.05
    fr = _autoselect_shaft_hz(fe, Ae, rpm_guess * (1 - slip_guess))

    fam = _bearing_family(fr)

    norm = float(np.max(Ae) + 1e-12)

    def peak_at_env(f0):
        w = max(1.5, 0.2 * fr)
        m = (fe >= f0 - w) & (fe <= f0 + w)
        return float(np.max(Ae[m]) / norm) if np.any(m) else 0.0

    f1 = peak_at_env(fam.BPFI);
    f2 = peak_at_env(fam.BPFO);
    f3 = peak_at_env(fam.BSF);
    f4 = peak_at_env(fam.FTF)

    def psd_band_mean(center, bw):
        m = (f_psd >= center - bw) & (f_psd <= center + bw)
        return float(np.mean(Pxx[m])) if np.any(m) else 0.0

    sb_bw = max(0.5, 0.05 * fr)
    f5 = 0.5 * (psd_band_mean(mains - fr, sb_bw) + psd_band_mean(mains + fr, sb_bw))

    def stats_around_env(f0):
        w = max(10.0, 0.5 * fr)
        m = (fe >= f0 - w) & (fe <= f0 + w)
        return _safe_stats(Ae[m]) if np.any(m) else (0, 0, 0, 0, 0)

    st_i = stats_around_env(fam.BPFI);
    st_o = stats_around_env(fam.BPFO);
    st_b = stats_around_env(fam.BSF);
    st_c = stats_around_env(fam.FTF)
    f6, f7, f8, f9, f10 = st_i
    f11, f12, f13, f14, f15 = st_o
    f16, f17, f18, f19, f20 = st_b
    f21, f22, f23, f24, f25 = st_c

    valid = (fe > 1.0) & np.isfinite(Ae) & (Ae > 0)
    if np.count_nonzero(valid) > 10:
        X = np.log10(fe[valid]);
        y = np.log10(Ae[valid])
        slope = float(np.polyfit(X, y, 1)[0])
    else:
        slope = 0.0
    f26 = slope

    return [f1, f2, f3, f4, f5,
            f6, f7, f8, f9, f10,
            f11, f12, f13, f14, f15,
            f16, f17, f18, f19, f20,
            f21, f22, f23, f24, f25,
            f26]

def severity_from_K(K: float) -> str:
    """Маппинг непрерывного скоринга K в категорию тяжести.

    Args:
        K: непрерывный скоринг (дБ).

    Returns:
        'Low'|'Medium'|'High'.
    """
    if K >= CONFIG["SEVERITY"]["high"]: return "High"
    if K >= CONFIG["SEVERITY"]["med"]:  return "Medium"
    if K >= CONFIG["SEVERITY"]["low"]:  return "Low"
    return "Low"


def classify_defect_scored(curR: NDArray[np.float64], curS: NDArray[np.float64], curT: NDArray[np.float64],
                           fs: float = DEFAULT_FS, rpm_guess: float = DEFAULT_RPM) -> Tuple[
    str, str, float, Optional[str]]:
    """Классификатор с баллами: подшипник/ротор/дисбаланс/расцентровка/норма

    Args:
        curR, curS, curT: фазные токи (A) — допускаются пустые фазы
        fs: частота дискретизации (Гц)
        rpm_guess: ожидание по оборотам (RPM)

    Returns:
        (label, severity, score, extra), где:
          - label: 'Inner Race'|'Outer Race'|'Ball'|'Cage'|'Rotor'|'Misalignment'|'Normal'
          - severity: 'Low'|'Medium'|'High'
          - score: численный K (дБ)
          - extra: строка кода частоты семейства (например, '263.5Hz') или None
    """
    mains = CONFIG["MAINS_HZ"]
    r = preprocess_per_phase(curR, fs);
    s = preprocess_per_phase(curS, fs);
    t = preprocess_per_phase(curT, fs)
    x = (r + s + t) / 3.0

    fe, Ae = envelope_spectrum_2_3k(x, fs)
    f_psd, Pxx = welch(x, fs=fs, nperseg=min(8192, len(x)))

    pole_pairs = 2
    sync_hz = mains / pole_pairs
    slip_guess = 1 - (rpm_guess / 60.0) / sync_hz if sync_hz > 0 else 0.05
    fr = _autoselect_shaft_hz(fe, Ae, rpm_guess * (1 - slip_guess))

    fam = _bearing_family(fr)

    fam_scores = {}
    fam_codes = {}
    for name, hz in (("Inner Race", fam.BPFI), ("Outer Race", fam.BPFO), ("Ball", fam.BSF), ("Cage", fam.FTF)):
        k_env = _family_score_env(fe, Ae, fr, hz)
        k_mcsa = _mcsa_sidebands_score(f_psd, Pxx, mains, hz)
        k = CONFIG["WEIGHT_ENV"] * k_env + CONFIG["WEIGHT_MCSA"] * k_mcsa
        k *= CONFIG["FAMILY_WEIGHTS"].get(name, 1.0)
        fam_scores[name] = float(k)
        fam_codes[name] = f"{hz:.1f}Hz"

    names = list(fam_scores.keys())
    vals = np.array([fam_scores[n] for n in names])
    order = np.argsort(-vals)
    top, second = names[order[0]], names[order[1]]
    K_top, K_second = float(vals[order[0]]), float(vals[order[1]])
    gap_rel = (K_top / (K_second + 1e-6)) - 1.0

    psnr = 20.0 * math.log10((np.max(Ae) + 1e-9) / (np.median(Ae) + 1e-9)) if Ae.size else 0.0

    if (K_top >= CONFIG["FAMILY_T"]) and (gap_rel >= CONFIG["GAP_MIN"]) and (psnr >= CONFIG["PSNR_T"]):
        return top, severity_from_K(K_top), K_top, fam_codes[top]

    multiphase = _has_multiphase_info(r, s, t)
    allow_single = bool(CONFIG.get("ALLOW_SINGLE_PHASE_ROTOR", True))
    if multiphase or allow_single:
        snr_m, p50 = _snr_mains(f_psd, Pxx, mains)
        dyn_limit = 0.06 * mains
        bb_db = _broken_bar_pair_db(f_psd, Pxx, mains, CONFIG["ROTOR_BB_MAX_OFFSET"], dyn_limit)

        def max_coh(a, b):
            fcoh, Cxy = coherence(a, b, fs=fs, nperseg=min(8192, len(a)))
            mask = (fcoh >= mains - 1.0) & (fcoh <= mains + 1.0)
            return float(np.max(Cxy[mask]) if np.any(mask) else 0.0)

        if multiphase:
            coh = min(max_coh(r, s), max_coh(s, t), max_coh(r, t))
            coh_ok = (coh >= CONFIG["COH_MSC_MIN"])
        else:
            coh = 1.0
            coh_ok = True

        ecc_rel = _eccentricity_ratio(f_psd, Pxx, mains, fr, CONFIG["ECC_M"], CONFIG["ECC_BW"])

        if (snr_m >= CONFIG["ROTOR_SNR_T"]) and coh_ok:
            def band_power(freq, bw=1.5):
                m = (f_psd >= freq - bw) & (f_psd <= freq + bw)
                return float(np.sum(Pxx[m])) if np.any(m) else 0.0

            a100_a50 = (band_power(2 * mains) + 1e-12) / (band_power(mains) + 1e-12)

            if bb_db >= CONFIG["ROTOR_BB_MIN_PAIR_DB"]:
                return "Rotor", severity_from_K(max(snr_m / 2.0, bb_db / 2.0)), max(snr_m, bb_db), None
            elif ecc_rel >= CONFIG["ECC_MIN_REL"] and a100_a50 >= CONFIG["A100_A50_MIN"]:
                return "Misalignment", severity_from_K(snr_m / 2.0), snr_m, None
            else:
                return "Rotor", severity_from_K(snr_m / 2.0), snr_m, None

    return "Normal", "None", max(0.0, K_top), None


def classify_defect(curR: NDArray[np.float64], curS: NDArray[np.float64], curT: NDArray[np.float64],
                    fs: float = DEFAULT_FS, rpm_guess: float = DEFAULT_RPM) -> str:
    """Обёртка над classify_defect_scored с тем же API, возвращает только метку.

    Args:
        curR, curS, curT: фазные токи (A)
        fs: частота дискретизации (Гц)
        rpm_guess: обороты (RPM)
    """
    defect, _, _, _ = classify_defect_scored(curR, curS, curT, fs, rpm_guess)
    return defect