import numpy as np

FS = 25600
N_BALLS = 9
D = 0.052
d = 0.025
phi = 0.0
RPM = 1770

SEVERITY_THRESHOLDS = {
    'low': 0.1,
    'medium': 0.3
}

def compute_bearing_fault_freqs(rpm, d, D, z, phi):
    fr = rpm / 60.0
    Dp = (D + d) / 2.0
    bpfi = (z/2) * (1 + (d/Dp) * np.cos(phi)) * fr
    bpfo = (z/2) * (1 - (d/Dp) * np.cos(phi)) * fr
    bsf  = (Dp/(2*d)) * (1 - ((d/Dp)*np.cos(phi))**2) * fr
    ftf  = 0.5 * (1 - (d/Dp) * np.cos(phi)) * fr
    return {'BPFI': bpfi, 'BPFO': bpfo, 'BSF': bsf, 'FTF': ftf}



def detect_peaks_at(freqs, spectrum, target_freqs, tol=0.05):
    peaks = {}
    for name, f in target_freqs.items():
        mask = (freqs > f*(1-tol)) & (freqs < f*(1+tol))
        if np.any(mask):
            peak_amp = np.max(spectrum[mask])
        else:
            peak_amp = 0.0
        peaks[name] = peak_amp
    return peaks

def classify_defect(peaks):
    fault, amp = max(peaks.items(), key=lambda x: x[1])
    if amp <= 0:
        return None, 0.0
    return fault, amp


def severity_level(amp, ref_amp):
    K = amp / ref_amp if ref_amp>0 else 0
    if K < SEVERITY_THRESHOLDS['low']:
        return 'low', K
    elif K < SEVERITY_THRESHOLDS['medium']:
        return 'medium', K
    else:
        return 'high', K
