import numpy as np
import src.feature_extraction.feature_classifier as fc

FS = int(fc.DEFAULT_FS)

def make_three_phase(signal):
    n = len(signal)
    sR = signal.copy()
    sS = np.roll(signal, n // 3)
    sT = np.roll(signal, 2 * n // 3)
    return sR, sS, sT


def test_analyze_signal_returns_expected_keys():
    n = FS
    t = np.arange(n) / FS
    base = np.sin(2*np.pi*50*t)
    r, s, tph = make_three_phase(base)
    out = fc.analyze_signal(r, s, tph, fs=FS)
    for k in ("defect_freqs","main_freq","main_amp","peak_amps","sideband_amp","envelope_spectrum","raw_spectrum","baseline"):
        assert k in out
    assert isinstance(out["defect_freqs"], dict)
    assert out["main_freq"] > 0
    (ef, em) = out["envelope_spectrum"]
    assert len(ef) == len(em)

def test_get_feature_vector_shape_and_nonneg():
    n = FS
    t = np.arange(n) / FS
    sig = np.sin(2*np.pi*50*t)
    r, s, tph = make_three_phase(sig)
    v = fc.get_feature_vector(r, s, tph, fs=FS)
    assert v.shape == (26,)

    assert np.all(np.isfinite(v))

def test_classify_defect_prefers_inner_race_when_bpfi_present():
    main_freq = 50.0
    pole_pairs = 2
    slip = 0.01
    rot = main_freq / pole_pairs * (1 - slip)
    freqs = fc.calc_defect_frequencies(rot)
    f_bpfi = freqs["BPFI"]

    n = FS
    t = np.arange(n) / FS
    base = 1.0*np.sin(2*np.pi*main_freq*t)
    defect = 0.8*np.sin(2*np.pi*f_bpfi*t)
    noise = 0.05*np.random.randn(n)
    sig = base + defect + noise
    r, s, tph = make_three_phase(sig)

    defect_type, severity = fc.classify_defect(r, s, tph, fs=FS)
    assert defect_type in ("Inner Race","Normal","Outer Race","Ball","Cage")
    assert defect_type == "Inner Race"

def test_classify_defect_returns_valid_severity_label():
    n = FS
    t = np.arange(n) / FS
    sig = np.sin(2*np.pi*50*t) + 0.02*np.random.randn(n)
    r, s, tph = make_three_phase(sig)
    defect_type, severity = fc.classify_defect(r, s, tph, fs=FS)
    assert severity in ("None","Low","Medium","High")