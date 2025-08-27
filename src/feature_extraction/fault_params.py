from __future__ import annotations
import json, os
from typing import Dict, Tuple


MAINS_HZ: float = 60.0
HPF_HZ: float   = 4.0

ENV_BAND_DEFAULT: Tuple[float, float] = (2000.0, 3000.0)
ENV_BAND_SCAN:    Tuple[float, float] = (800.0, 7000.0)
ENV_BAND_WIDTH:   float = 600.0
USE_ADAPTIVE_ENVELOPE: bool = True


FAMILY_T: float = 3.5
GAP_MIN:  float = 0.50
PSNR_T:   float = 5.0

WEIGHT_ENV:  float = 0.50
WEIGHT_MCSA: float = 0.50
MCSA_SB_BW:  float = 1.0
MCSA_M_MULTIPLIERS = (1, 2)

FAMILY_WEIGHTS = {
    "Inner Race": 3.0,
    "Outer Race": 3.0,
    "Ball": 3.0,
    "Cage": 0.5
}


ROTOR_SNR_T:   float = 12.0
COH_MSC_MIN:   float = 0.15
A100_A50_MIN:  float = 0.6

ROTOR_BB_MAX_OFFSET: float = 3.5
ROTOR_BB_MIN_PAIR_DB: float = 6.0

ECC_M = (1, 2)
ECC_BW: float = 1.0
ECC_MIN_REL: float = 0.001

ALLOW_SINGLE_PHASE_ROTOR: bool = True

SEVERITY = {"low": 5.0, "med": 7.0, "high": 9.0}

def _pair(v):
    try:
        return (float(v[0]), float(v[1]))
    except Exception:
        return None

def _to_bool(v):
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return v != 0
    if isinstance(v, str): return v.strip().lower() in {"1","true","yes","on","y","t","да","истина"}
    return bool(v)

def _apply_overrides(d: Dict):
    gl = globals()
    for k in ("ENV_BAND_DEFAULT", "ENV_BAND_SCAN"):
        if k in d:
            p = _pair(d[k])
            if p: gl[k] = p

    if "SEVERITY" in d and isinstance(d["SEVERITY"], dict):
        for kk in ("low", "med", "high"):
            if kk in d["SEVERITY"]:
                SEVERITY[kk] = float(d["SEVERITY"][kk])

    if "FAMILY_WEIGHTS" in d and isinstance(d["FAMILY_WEIGHTS"], dict):
        for name, val in d["FAMILY_WEIGHTS"].items():
            FAMILY_WEIGHTS[name] = float(val)

    scalar_keys = [
        "MAINS_HZ","HPF_HZ",
        "ENV_BAND_WIDTH",
        "FAMILY_T","GAP_MIN","PSNR_T",
        "WEIGHT_ENV","WEIGHT_MCSA","MCSA_SB_BW",
        "ROTOR_SNR_T","COH_MSC_MIN","A100_A50_MIN",
        "ROTOR_BB_MAX_OFFSET","ROTOR_BB_MIN_PAIR_DB",
        "ECC_BW","ECC_MIN_REL",
    ]
    for k in scalar_keys:
        if k in d:
            try: gl[k] = type(gl[k])(d[k])
            except Exception: pass

    for k in ("USE_ADAPTIVE_ENVELOPE","ALLOW_SINGLE_PHASE_ROTOR"):
        if k in d:
            gl[k] = _to_bool(d[k])

    if "MCSA_M_MULTIPLIERS" in d:
        try: gl["MCSA_M_MULTIPLIERS"] = tuple(int(x) for x in d["MCSA_M_MULTIPLIERS"])
        except Exception: pass
    if "ECC_M" in d:
        try: gl["ECC_M"] = tuple(int(x) for x in d["ECC_M"])
        except Exception: pass

def _load_from_json():
    path = os.getenv("FAULT_CONFIG", "fault_config.json")
    if not os.path.isfile(path): return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "profiles" in data:
            prof = os.getenv("FAULT_PROFILE", data.get("active_profile", "balanced"))
            prof = str(prof).lower()
            if prof in data["profiles"]:
                _apply_overrides(data["profiles"][prof])
        elif isinstance(data, dict):
            _apply_overrides(data)
    except Exception:
        pass

_load_from_json()

CONFIG: Dict = {
    "MAINS_HZ": MAINS_HZ, "HPF_HZ": HPF_HZ,
    "ENV_BAND_DEFAULT": ENV_BAND_DEFAULT, "ENV_BAND_SCAN": ENV_BAND_SCAN,
    "ENV_BAND_WIDTH": ENV_BAND_WIDTH, "USE_ADAPTIVE_ENVELOPE": USE_ADAPTIVE_ENVELOPE,
    "FAMILY_T": FAMILY_T, "GAP_MIN": GAP_MIN, "PSNR_T": PSNR_T,
    "WEIGHT_ENV": WEIGHT_ENV, "WEIGHT_MCSA": WEIGHT_MCSA,
    "MCSA_SB_BW": MCSA_SB_BW, "MCSA_M_MULTIPLIERS": MCSA_M_MULTIPLIERS,
    "FAMILY_WEIGHTS": FAMILY_WEIGHTS,
    "ROTOR_SNR_T": ROTOR_SNR_T, "COH_MSC_MIN": COH_MSC_MIN, "A100_A50_MIN": A100_A50_MIN,
    "ROTOR_BB_MAX_OFFSET": ROTOR_BB_MAX_OFFSET, "ROTOR_BB_MIN_PAIR_DB": ROTOR_BB_MIN_PAIR_DB,
    "ECC_M": ECC_M, "ECC_BW": ECC_BW, "ECC_MIN_REL": ECC_MIN_REL,
    "ALLOW_SINGLE_PHASE_ROTOR": ALLOW_SINGLE_PHASE_ROTOR,
    "SEVERITY": SEVERITY,
}
