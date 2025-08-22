# -*- coding: utf-8 -*-
"""
fault_params.py — обновлено
Совместимость сохранена: экспортируется CONFIG с прежними ключами + несколько новых (опционально используемых).
Главные изменения по умолчанию:
- ROTOR_BB_MAX_OFFSET увеличен до 3.5 Гц (было 2.0) — лучше покрытие по скольжению
- MCSA_M_MULTIPLIERS = (1, 2) — разрешаем вторую кратность боковых для подшипника
- Добавлен флаг ALLOW_SINGLE_PHASE_ROTOR=True — включать роторную ветку и при 1 фазе
"""

from __future__ import annotations
import json, os
from typing import Dict, Tuple

# ===== БАЗА (спектр/предобработка) =====
MAINS_HZ: float = 50.0               # частота сети (Европа — 50 Гц)
HPF_HZ: float   = 1.0                # ВЧ-фильтр против дрейфа (Гц)

# Полоса демодуляции (огибающая) — помогает подшипнику
ENV_BAND_DEFAULT: Tuple[float, float] = (2000.0, 3000.0)
ENV_BAND_SCAN:    Tuple[float, float] = (800.0, 7000.0)   # скан резонанса
ENV_BAND_WIDTH:   float = 600.0
USE_ADAPTIVE_ENVELOPE: bool = True

# ===== ПОДШИПНИК (тип дефекта) =====
FAMILY_T: float = 2.4                # мин. семейный K (дБ) для подтверждения
GAP_MIN:  float = 0.20               # относительный разрыв top/second - 1.0
PSNR_T:   float = 4.5                # чистота спектра огибающей

# Комбинированный скоринг: огибающая + MCSA (f1 ± f_fault)
WEIGHT_ENV:  float = 0.50            # вклад огибающей
WEIGHT_MCSA: float = 0.50            # вклад MCSA — лучше разделяет Inner/Outer
MCSA_SB_BW:  float = 1.0             # полуширина окна для боковых (Гц)
MCSA_M_MULTIPLIERS = (1, 2)          # кратности f_fault (добавили 2-ю)

# Поджимаем перекос в Ball при равной борьбе
FAMILY_WEIGHTS = {"Inner Race": 1.0, "Outer Race": 1.0, "Ball": 0.60, "Cage": 1.0}

# ===== РОТОР / НЕСОСНОСТЬ =====
ROTOR_SNR_T:   float = 4.5           # SNR у f1 для входа в роторную ветку (дБ)
COH_MSC_MIN:   float = 0.28          # минимум межфазной когерентности @ f1
A100_A50_MIN:  float = 0.18          # «запасной» критерий для Misalignment (исторический)

# Broken bars: пара на (1 ± δ)·f1 (δ ~ 2s·f1). Берём относительную «силу пары».
ROTOR_BB_MAX_OFFSET: float = 3.5     # макс. отстрой от f1, Гц (было 2.0)
ROTOR_BB_MIN_PAIR_DB: float = 8.0    # порог по «паре» в дБ относительно фундамента

# Несоосность/эксцентриситет: f1 ± m·f_r
ECC_M = (1, 2)
ECC_BW: float = 1.0                  # окно вокруг каждой линии (Гц)
ECC_MIN_REL: float = 0.015           # относит. энергия боковых к фундаменту

# Разрешить роторную ветку и при одном канале
ALLOW_SINGLE_PHASE_ROTOR: bool = True

# ===== ТЯЖЕСТЬ (severity) =====
SEVERITY = {"low": 2.0, "med": 4.0, "high": 7.0}

# ---------------------------------------------------------------------
# Переопределения из JSON (fault_config.json) и профилей (FAULT_PROFILE)
# ---------------------------------------------------------------------

def _pair(v):
    try:
        return (float(v[0]), float(v[1]))
    except Exception:
        return None

def _apply_overrides(d: Dict):
    """Аккуратно применить значения из словаря к глобальным параметрам."""
    gl = globals()

    # кортежи-полосы
    for k in ("ENV_BAND_DEFAULT", "ENV_BAND_SCAN"):
        if k in d:
            p = _pair(d[k])
            if p: gl[k] = p

    # словари
    if "SEVERITY" in d and isinstance(d["SEVERITY"], dict):
        for kk in ("low", "med", "high"):
            if kk in d["SEVERITY"]:
                SEVERITY[kk] = float(d["SEVERITY"][kk])

    if "FAMILY_WEIGHTS" in d and isinstance(d["FAMILY_WEIGHTS"], dict):
        for name, val in d["FAMILY_WEIGHTS"].items():
            FAMILY_WEIGHTS[name] = float(val)

    # прочие скаляры/булевы
    scalar_keys = [
        "MAINS_HZ","HPF_HZ",
        "ENV_BAND_WIDTH","USE_ADAPTIVE_ENVELOPE",
        "FAMILY_T","GAP_MIN","PSNR_T",
        "WEIGHT_ENV","WEIGHT_MCSA","MCSA_SB_BW",
        "ROTOR_SNR_T","COH_MSC_MIN","A100_A50_MIN",
        "ROTOR_BB_MAX_OFFSET","ROTOR_BB_MIN_PAIR_DB",
        "ECC_BW","ECC_MIN_REL","ALLOW_SINGLE_PHASE_ROTOR",
    ]
    for k in scalar_keys:
        if k in d:
            try:
                gl[k] = type(gl[k])(d[k])
            except Exception:
                pass

    # списки/кортежи индексов
    if "MCSA_M_MULTIPLIERS" in d:
        try: gl["MCSA_M_MULTIPLIERS"] = tuple(int(x) for x in d["MCSA_M_MULTIPLIERS"])
        except Exception: pass
    if "ECC_M" in d:
        try: gl["ECC_M"] = tuple(int(x) for x in d["ECC_M"])
        except Exception: pass

def _load_from_json():
    """fault_config.json с поддержкой профилей."""
    path = os.getenv("FAULT_CONFIG", "fault_config.json")
    if not os.path.isfile(path):
        return
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
        # мягко игнорируем ошибки чтения/парсинга
        pass

# применять переопределения на импорт
_load_from_json()

# ===== Экспорт единого словаря CONFIG =====
CONFIG: Dict = {
    # база
    "MAINS_HZ": MAINS_HZ, "HPF_HZ": HPF_HZ,
    "ENV_BAND_DEFAULT": ENV_BAND_DEFAULT, "ENV_BAND_SCAN": ENV_BAND_SCAN,
    "ENV_BAND_WIDTH": ENV_BAND_WIDTH, "USE_ADAPTIVE_ENVELOPE": USE_ADAPTIVE_ENVELOPE,

    # подшипник
    "FAMILY_T": FAMILY_T, "GAP_MIN": GAP_MIN, "PSNR_T": PSNR_T,

    # комбинированный скоринг
    "WEIGHT_ENV": WEIGHT_ENV, "WEIGHT_MCSA": WEIGHT_MCSA,
    "MCSA_SB_BW": MCSA_SB_BW, "MCSA_M_MULTIPLIERS": MCSA_M_MULTIPLIERS,
    "FAMILY_WEIGHTS": FAMILY_WEIGHTS,

    # ротор / несоосность
    "ROTOR_SNR_T": ROTOR_SNR_T, "COH_MSC_MIN": COH_MSC_MIN, "A100_A50_MIN": A100_A50_MIN,
    "ROTOR_BB_MAX_OFFSET": ROTOR_BB_MAX_OFFSET, "ROTOR_BB_MIN_PAIR_DB": ROTOR_BB_MIN_PAIR_DB,
    "ECC_M": ECC_M, "ECC_BW": ECC_BW, "ECC_MIN_REL": ECC_MIN_REL,

    # прочее
    "ALLOW_SINGLE_PHASE_ROTOR": ALLOW_SINGLE_PHASE_ROTOR,

    # severity
    "SEVERITY": SEVERITY,
}