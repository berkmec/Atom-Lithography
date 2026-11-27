#!/usr/bin/env python3
"""Exp134 (H152) — Fab-Scale Unit Economics, 5-Year TCO & v3.0 -> v7.0 Lifecycle Value Analysis.

Upgraded for OBS-060, OBS-062, OBS-068 & OBS-148:
- Live v7.0 BOM_DETAILED.csv ($5,692,800 Full / $5,392,800 Phase-1 Base+Safety / $5,247,800 v5 Base
  / $4,609,600 v4 Base / $4,189,600 v3 Base), reconciling the $76,200 safety starter-item overlap.
- Explicit unbudgeted lifecycle NRE/CAPEX adders ({Varsayım}): third-party SEMI S2 / IEC 61508
  assessment ($80k/$140k/$220k), TWPA foundry NRE ($150k/$300k/$550k), and multi-lot MEMS yield NRE
  ($200k/$450k/$900k).
- Explicit annual EHS/cryo/scrubber OPEX consumables (3He top-up, PH3/SiF4/HF scrubber media &
  radiation dosimetry, PT420 cold-head rebuild reserve) and updated 20-30 kW facility power
  reflecting 12.5 kW PT420 wall draw.
- Explicit 3-tier wafer diameter reconciliation (OBS-060): FOAK 50 mm (cad/params.py & S5.4-01
  $2,240/wafer) vs Pilot 100 mm vs Fab-scale 200 mm (+$1.85M bore/cryo/LL redesign CAPEX).
- Honest real 1% 29Si bath BOED (130.4 ms/cand) & 5%-dead blanker step-and-stitch (61.51%) throughput
  derating alongside write-ceiling bounds (OBS-068).
- Pure importable deterministic solver entrypoint run_tco_model() for live pytest execution (OBS-148).

100% portable: resolves repository root via Path(__file__).resolve().parents[2].
Strictly READ-ONLY with respect to canonical BOM.csv (SHA-256 verified), BOM_DETAILED.csv,
and results/exp128_bom_sensitivity/exp128.json.
Outputs: results/exp134_fab_economics_tco/exp134.json
Epistemic status: UNQUOTED_ROM_ESTIMATE, no_lab_measurement=true, no_supplier_quotes=true ({Model}/{Varsayım}/{Liste-Çapası}).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
BOM_CSV = ROOT / "research" / "atom_lithography_machine" / "BOM.csv"
BOM_DETAILED = ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"
EXP128_JSON = ROOT / "results" / "exp128_bom_sensitivity" / "exp128.json"
OUT_DIR = ROOT / "results" / "exp134_fab_economics_tco"
PRED_JSON = OUT_DIR / "predictions_exp134.json"
OUT_JSON = OUT_DIR / "exp134.json"

EXPECTED_BOM_SHA256 = "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"
Z90 = float(norm.ppf(0.90))  # 1.2815515655446004

# Machine physics constants (locked to DESIGN / Exp124 / Exp127 / config.py)
DAY_S = 86400.0
DAYS_YR = 365.0
DUTY = 0.50
FAB_UPTIME = 0.80  # 80% fab availability (20% scheduled cryo/UHV/source maintenance)
BEAMLETS_ARCHB = 1024  # 32x32 @ 0.50 mm pitch (Exp124 + Carbon F1 lock)
READOUT_CHANNELS = 56 * 160  # 8960 ch (56 chains x NL=160, Exp112/127)
BATH_YIELD_MODB = 0.51  # Mod B f=1% 29Si (Exp59/68)
DETECTOR_ETA = 0.9994  # Exp127 Cold-100K / 1.2 us / 1 GOhm @ 5 keV
SPEC_TIME_V3_S = 1.0  # Exp65/127 baseline spectroscopy integration per candidate
REAL_SI29_BOED_SPEC_TIME_S = 0.130374  # Real 1% 29Si lattice-bath BOED mean (boed_real_bath_benchmark.json)
BLANKER_5PCT_DEAD_STITCH_EFF = 0.6151  # auto_recal step-and-stitch honest throughput factor
K_REGISTER_QUBITS = 8  # K=8 nuclear-spin register (DESIGN §1)
K_SUB_UNIVERSAL = 4  # K_sub=4 universal Lie-rank 1023/1023 core

# Historical v3->v4 Hardware Upgrade Deltas (P10, P50_nom, P90) in USD — labeled {Varsayım}
V4_DELTAS = {
    "S5.5_flash_anneal_optics": (55_000.0, 95_000.0, 175_000.0),
    "PT420_decoupling_feedforward": (38_000.0, 68_000.0, 125_000.0),
    "M4_cavity_bus_and_gate_elec": (135_000.0, 245_000.0, 460_000.0),
    "S8_bayesian_rt_gpu_node": (7_000.0, 12_000.0, 22_000.0),
}

# OBS-062: Unbudgeted v7.0 Lifecycle NRE & Certification CAPEX Adders (P10, P50, P90 USD) — {Varsayım}
V7_LIFECYCLE_NRE_ADDERS = {
    "semi_s2_iec61508_third_party_cert_and_exhaust": (80_000.0, 140_000.0, 220_000.0),
    "twpa_nb_alox_nb_foundry_nre": (150_000.0, 300_000.0, 550_000.0),
    "mems_multilot_yield_integration_nre_adder": (200_000.0, 450_000.0, 900_000.0),
}

# OBS-062: Starter-item safety overlap part IDs in BOM_DETAILED.csv (reconciled against S7.SAFETY-01..06)
SAFETY_STARTER_OVERLAP_IDS = ("S1.6-01", "S1.6-02", "S5.5-04", "S7.1-03", "S7.4-04")

# OBS-060: 3-tier wafer diameter reconciliation specs ({Varsayım}, UNQUOTED_ROM_ESTIMATE)
WAFER_TIER_SPECS = {
    "FOAK_50mm": {
        "diameter_mm": 50.0,
        "area_ratio_vs_200mm": 1.0 / 16.0,
        "fits_current_cad_bore_150mm": True,
        "bore_redesign_capex_adder_usd": 0.0,
        "wafer_price_p10_p50_p90_usd": [1_200.0, 2_240.0, 4_200.0],
        "std_reg_per_wafer": 2.0e6 / 16.0,
        "dense_reg_per_wafer": 5.0e7 / 16.0,
        "source_anchor": "cad/params.py Ø50 mm + BOM_DETAILED.csv S5.4-01 ($56,000 / 25 wafers = $2,240/wafer)",
    },
    "PILOT_100mm": {
        "diameter_mm": 100.0,
        "area_ratio_vs_200mm": 1.0 / 4.0,
        "fits_current_cad_bore_150mm": False,
        "bore_redesign_capex_adder_usd": 650_000.0,
        "wafer_price_p10_p50_p90_usd": [2_500.0, 4_500.0, 8_500.0],
        "std_reg_per_wafer": 2.0e6 / 4.0,
        "dense_reg_per_wafer": 5.0e7 / 4.0,
        "source_anchor": "Requires >=Ø240 mm bore/LL upgrade (or 4x dicing into 50 mm coupons for FOAK)",
    },
    "FAB_200mm": {
        "diameter_mm": 200.0,
        "area_ratio_vs_200mm": 1.0,
        "fits_current_cad_bore_150mm": False,
        "bore_redesign_capex_adder_usd": 1_850_000.0,
        "wafer_price_p10_p50_p90_usd": [5_000.0, 12_000.0, 25_000.0],
        "std_reg_per_wafer": 2.0e6,
        "dense_reg_per_wafer": 5.0e7,
        "source_anchor": "Fab-scale 200 mm thick 28Si epi (16x FOAK area; requires >=Ø300 mm magnet/cryo/LL redesign +$1.85M)",
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_lognormal_p10_p50_p90(
    rng: np.random.Generator, p10: float, p50: float, p90: float, size: int
) -> np.ndarray:
    mu = math.log(p50)
    sigma = math.log(p90 / p10) / (2.0 * Z90)
    return np.exp(mu + sigma * rng.standard_normal(size))


def pct_summary(arr: np.ndarray) -> dict[str, float]:
    qs = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95, 99])
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)),
        "p05": float(qs[0]),
        "p10": float(qs[1]),
        "p25": float(qs[2]),
        "p50": float(qs[3]),
        "p75": float(qs[4]),
        "p90": float(qs[5]),
        "p95": float(qs[6]),
        "p99": float(qs[7]),
    }


def throughput_model(
    bayesian_speedup: float = 1.0,
    shot_cycle_s: float = 0.015,
    beamlets: int = BEAMLETS_ARCHB,
    readout_ch: int = READOUT_CHANNELS,
    stitch_eff: float = 1.0,
) -> dict[str, float]:
    """First-principles write vs. spectroscopy certified register throughput (registers/day)."""
    eff_yield = BATH_YIELD_MODB * DETECTOR_ETA
    attempts_per_reg = 1.0 / eff_yield  # ~1.9620
    write_shots_day = DUTY * DAY_S * beamlets / shot_cycle_s * stitch_eff
    write_reg_day = write_shots_day / attempts_per_reg
    spec_reg_day = (DUTY * DAY_S * readout_ch / (SPEC_TIME_V3_S / bayesian_speedup)) / attempts_per_reg
    net_reg_day = min(write_reg_day, spec_reg_day)
    bottleneck = "write" if write_reg_day < spec_reg_day else "spectroscopy"
    return {
        "bayesian_speedup_nom": bayesian_speedup,
        "shot_cycle_s": shot_cycle_s,
        "stitch_efficiency": stitch_eff,
        "write_shots_day": write_shots_day,
        "write_reg_day": write_reg_day,
        "spec_reg_day": spec_reg_day,
        "net_reg_day": net_reg_day,
        "net_reg_yr_80pct": net_reg_day * DAYS_YR * FAB_UPTIME,
        "bottleneck": bottleneck,
    }


def wafer_batch_throughput(
    net_reg_day: float,
    reg_per_wafer: float,
    t_swap_hr: float,
    uptime: float = FAB_UPTIME,
) -> dict[str, float]:
    """Amdahl's Law wafer-batch throughput with cryogenic/load-lock thermal swap overhead."""
    active_hr = (reg_per_wafer / net_reg_day) * 24.0
    cycle_hr = active_hr + t_swap_hr
    avail_hr_yr = 24.0 * DAYS_YR * uptime
    wafers_yr = avail_hr_yr / cycle_hr
    reg_yr = wafers_yr * reg_per_wafer
    return {
        "reg_per_wafer": reg_per_wafer,
        "t_swap_hr": t_swap_hr,
        "active_process_hr": active_hr,
        "total_cycle_hr": cycle_hr,
        "active_duty_fraction": active_hr / cycle_hr,
        "wafers_per_yr": wafers_yr,
        "reg_per_yr": reg_yr,
    }


def wright_multiplier(n_tools: int, b: float) -> float:
    return float(n_tools ** math.log2(b))


def logical_qubit_cells(d: int) -> dict[str, float]:
    """Rotated surface code physical cells per logical qubit."""
    n_bare = 2 * d * d - 1  # d^2 data + (d^2 - 1) ancilla
    return {
        "distance_d": d,
        "n_phys_bare": float(n_bare),
        "n_cells_modb_1over051": float(n_bare / BATH_YIELD_MODB),
        "n_cells_modb_ncand3": float(n_bare * 3.0),
    }


def build_unit_econ_summary(
    tco_5yr_arr: np.ndarray,
    reg_5yr: float,
    wafer_cost_5yr: float | np.ndarray = 0.0,
    reg_per_chip: float = 10_000.0,
) -> dict[str, Any]:
    tot_tco = tco_5yr_arr + wafer_cost_5yr
    usd_per_reg = tot_tco / reg_5yr
    usd_per_phys_k8 = usd_per_reg / K_REGISTER_QUBITS
    usd_per_phys_k4 = usd_per_reg / K_SUB_UNIVERSAL
    usd_per_chip_10k = usd_per_reg * reg_per_chip
    logical = {}
    for d in (7, 11, 17):
        lc = logical_qubit_cells(d)
        logical[f"d{d}"] = {
            "n_phys_bare": lc["n_phys_bare"],
            "n_cells_modb_1over051": lc["n_cells_modb_1over051"],
            "usd_bare_p50": float(np.median(usd_per_reg * lc["n_phys_bare"])),
            "usd_bare_p10": float(np.percentile(usd_per_reg * lc["n_phys_bare"], 10)),
            "usd_bare_p90": float(np.percentile(usd_per_reg * lc["n_phys_bare"], 90)),
            "usd_modb_p50": float(np.median(usd_per_reg * lc["n_cells_modb_1over051"])),
            "usd_modb_p10": float(np.percentile(usd_per_reg * lc["n_cells_modb_1over051"], 10)),
            "usd_modb_p90": float(np.percentile(usd_per_reg * lc["n_cells_modb_1over051"], 90)),
            "usd_ncand3_p50": float(np.median(usd_per_reg * lc["n_cells_modb_ncand3"])),
        }
    return {
        "tco_5yr_usd": pct_summary(tot_tco),
        "reg_5yr": reg_5yr,
        "usd_per_register": pct_summary(usd_per_reg),
        "usd_per_phys_qubit_k8": pct_summary(usd_per_phys_k8),
        "usd_per_phys_qubit_k4": pct_summary(usd_per_phys_k4),
        "usd_per_chip_10k": pct_summary(usd_per_chip_10k),
        "logical_qubit_m4": logical,
    }


def _sample_correlated_bom(
    priced_df: pd.DataFrame,
    rng: np.random.Generator,
    n_samples: int,
    bc_shock: np.ndarray,
    chain_scale: np.ndarray,
) -> np.ndarray:
    """Draw correlated log-normal BOM realizations for any subset of BOM_DETAILED rows."""
    k = len(priced_df)
    subs = priced_df["subsystem"].to_numpy(dtype=object)
    procs = priced_df["procurement_class"].to_numpy(dtype=object)
    is_rd = np.array(["R&D" in str(p) for p in procs], dtype=float)
    same_sub = (subs[:, None] == subs[None, :]).astype(float)
    both_rd = np.outer(is_rd, is_rd)

    corr = 0.25 + 0.30 * same_sub + 0.20 * both_rd
    np.fill_diagonal(corr, 1.0)
    eigvals, eigvecs = np.linalg.eigh(corr)
    if eigvals.min() < 1e-6:
        eigvals = np.maximum(eigvals, 1e-6)
        corr = (eigvecs * eigvals) @ eigvecs.T
        d_inv = 1.0 / np.sqrt(np.diag(corr))
        corr = corr * np.outer(d_inv, d_inv)
    L = np.linalg.cholesky(corr)

    mu_part = np.log(priced_df["usd_nom"].to_numpy(dtype=float))
    sigma_part = np.log(
        priced_df["usd_high"].to_numpy(dtype=float) / priced_df["usd_low"].to_numpy(dtype=float)
    ) / (2.0 * Z90)
    s66_chain_mask = priced_df["part_id"].isin([f"S6.6-0{i}" for i in range(1, 7)]).to_numpy(dtype=bool)

    out = np.empty(n_samples, dtype=np.float64)
    chunk = 10_000
    for start in range(0, n_samples, chunk):
        end = min(start + chunk, n_samples)
        m = end - start
        z_corr = rng.standard_normal((m, k)) @ L.T
        c_mat = np.exp(mu_part[None, :] + sigma_part[None, :] * z_corr)
        if np.any(s66_chain_mask):
            c_mat[:, s66_chain_mask] *= (chain_scale[start:end] * bc_shock[start:end])[:, None]
        out[start:end] = c_mat.sum(axis=1)
    return out


def run_tco_model(
    n_samples: int = 50_000,
    seed: int = 2026134,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Execute full Exp134 v7.0-synced Fab Economics & 5-Year TCO Monte Carlo solver."""
    pred = json.loads(PRED_JSON.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # 1. Baseline & Immutability Gate (v7.0 BOM_DETAILED.csv + v3.0 historical bridge)
    # -------------------------------------------------------------------------
    bom_sha = sha256_file(BOM_CSV)
    sha_ok = bom_sha == EXPECTED_BOM_SHA256
    assert sha_ok, f"Canonical BOM.csv SHA mismatch: {bom_sha}"

    df = pd.read_csv(BOM_DETAILED)
    exp128 = json.loads(EXP128_JSON.read_text(encoding="utf-8"))
    bds = exp128["bom_detailed_summary"]

    m3_v7_full_nom = float(df["usd_nom"].sum())
    m3_v7_full_low = float(df["usd_low"].sum())
    m3_v7_full_high = float(df["usd_high"].sum())
    m1_hw_nom = float(bds["m1_nom_usd"])

    # Partition BOM_DETAILED.csv cleanly across versions (v3 -> v4 -> v5 -> Phase-1 Base+Safety -> v7 Full)
    notes_s = df["notes"].astype(str)
    mask_v3 = ~notes_s.str.contains("DELTA-V4.0|DELTA-V5.0|DELTA-V6.0|DELTA-V7.0", na=False)
    mask_v5_base = ~notes_s.str.contains("DELTA-V6.0|DELTA-V7.0", na=False)
    mask_safety = notes_s.str.contains("DELTA-V7.0-SAFETY", na=False)
    mask_phase1_base_safety = mask_v5_base | mask_safety

    df_v3 = df[mask_v3].reset_index(drop=True)
    df_phase1 = df[mask_phase1_base_safety].reset_index(drop=True)

    m3_v3_nom = float(df_v3["usd_nom"].sum())
    m3_v5_base_nom = float(df[mask_v5_base]["usd_nom"].sum())
    m3_phase1_nom = float(df_phase1["usd_nom"].sum())
    v7_safety_hw_nom = float(df[mask_safety]["usd_nom"].sum())

    # Exact starter-item safety overlap reconciliation (OBS-062)
    overlap_df = df[df["part_id"].isin(SAFETY_STARTER_OVERLAP_IDS)]
    safety_starter_overlap_usd = float(overlap_df["usd_nom"].sum())
    safety_starter_overlap_breakdown = {
        str(r["part_id"]): float(r["usd_nom"]) for _, r in overlap_df.iterrows()
    }

    assert abs(m3_v3_nom - 4_189_600.0) < 1.0, f"Unexpected v3 slice nom: {m3_v3_nom}"
    assert abs(m3_v7_full_nom - 5_692_800.0) < 1.0, f"Unexpected v7 Full nom: {m3_v7_full_nom}"
    assert abs(m3_v7_full_nom - float(bds["m3_nom_usd"])) < 1e-6

    # Throughput checks (both nominal ceiling and real 1% 29Si bath / stitch derated)
    tp_v3 = throughput_model(bayesian_speedup=1.0, shot_cycle_s=0.015)
    tp_v4_5x = throughput_model(bayesian_speedup=5.0, shot_cycle_s=0.015)
    tp_v4_10x_15ms = throughput_model(bayesian_speedup=10.0, shot_cycle_s=0.015)
    tp_v4_10x_10ms = throughput_model(bayesian_speedup=10.0, shot_cycle_s=0.010)
    tp_v4_15x_10ms = throughput_model(bayesian_speedup=15.0, shot_cycle_s=0.010)

    # OBS-068: Honest real 1% 29Si bath BOED (130.374 ms -> 7.67x vs 1.0 s) + 5%-dead blanker stitch (61.51%)
    real_bath_speedup = SPEC_TIME_V3_S / REAL_SI29_BOED_SPEC_TIME_S  # 7.6702x
    tp_v7_real_bath_nom_blanker = throughput_model(bayesian_speedup=real_bath_speedup, shot_cycle_s=0.015, stitch_eff=1.0)
    tp_v7_real_bath_5pct_stitch = throughput_model(
        bayesian_speedup=real_bath_speedup, shot_cycle_s=0.015, stitch_eff=BLANKER_5PCT_DEAD_STITCH_EFF
    )

    v3_tp_rel_err = abs(tp_v3["net_reg_day"] - 1.973e8) / 1.973e8
    cx1_ok = sha_ok and abs(m3_v7_full_nom - 5_692_800.0) < 1.0 and abs(m3_v3_nom - 4_189_600.0) < 1.0 and v3_tp_rel_err < 0.01
    assert cx1_ok, f"CX1 baseline gate failed! tp_v3={tp_v3['net_reg_day']}"

    # -------------------------------------------------------------------------
    # 2. Correlated Monte Carlo (v3.0, v4.0, v7.0 Phase-1, v7.0 Full + Lifecycle NRE/OPEX)
    # -------------------------------------------------------------------------
    N = int(n_samples)
    rng = np.random.default_rng(seed)

    # Exp114 B/C chain-class wall (20% C-class stress) + Exp112 NL band [110..163] (shared CRN)
    bc_regime_c = rng.random(N) < 0.20
    bc_shock = np.ones(N, dtype=np.float64)
    n_c = int(bc_regime_c.sum())
    bc_shock[bc_regime_c] = np.exp(np.log(5.5) + 0.35 * rng.standard_normal(n_c))
    nl_samples = rng.integers(110, 164, size=N)
    chain_scale = np.ceil(9000.0 / nl_samples) / 56.0

    # Sample full v7.0 BOM (all priced rows in BOM_DETAILED.csv v7.0), plus v3.0 & Phase-1 slices
    priced_v7 = df[df["usd_nom"] > 0].reset_index(drop=True)
    priced_v3 = df_v3[df_v3["usd_nom"] > 0].reset_index(drop=True)
    priced_p1 = df_phase1[df_phase1["usd_nom"] > 0].reset_index(drop=True)

    hw_v3 = _sample_correlated_bom(priced_v3, rng, N, bc_shock, chain_scale)
    hw_v7_phase1 = _sample_correlated_bom(priced_p1, rng, N, bc_shock, chain_scale)
    hw_v7_full = _sample_correlated_bom(priced_v7, rng, N, bc_shock, chain_scale)

    # Historical v4.0 Hardware Upgrade Deltas (preserved for v3->v4 bridge)
    v4_keys = list(V4_DELTAS.keys())
    v4_corr = np.full((len(v4_keys), len(v4_keys)), 0.45)
    np.fill_diagonal(v4_corr, 1.0)
    L_v4 = np.linalg.cholesky(v4_corr)
    z_v4 = rng.standard_normal((N, len(v4_keys))) @ L_v4.T
    v4_delta_mat = np.empty((N, len(v4_keys)), dtype=np.float64)
    v4_delta_nom_total = 0.0
    v4_delta_low_total = 0.0
    v4_delta_high_total = 0.0
    for j, key in enumerate(v4_keys):
        lo, nom, hi = V4_DELTAS[key]
        v4_delta_low_total += lo
        v4_delta_nom_total += nom
        v4_delta_high_total += hi
        sig = math.log(hi / lo) / (2.0 * Z90)
        v4_delta_mat[:, j] = np.exp(math.log(nom) + sig * z_v4[:, j])

    hw_v4_delta = v4_delta_mat.sum(axis=1)
    hw_v4 = hw_v3 + hw_v4_delta

    # OBS-062: Unbudgeted v7.0 Lifecycle NRE / Certification CAPEX (SEMI S2/IEC61508 + TWPA NRE + MEMS multi-lot NRE)
    nre_samples_by_key: dict[str, np.ndarray] = {}
    v7_nre_nom_total = 0.0
    for nkey, (lo, nom, hi) in V7_LIFECYCLE_NRE_ADDERS.items():
        nre_samples_by_key[nkey] = sample_lognormal_p10_p50_p90(rng, lo, nom, hi, N)
        v7_nre_nom_total += nom
    v7_nre_total = sum(nre_samples_by_key.values())
    # Net v7.0 lifecycle-loaded hardware + NRE (crediting starter-item safety overlap to avoid double counting)
    hw_v7_full_net_overlap = np.maximum(hw_v7_full - safety_starter_overlap_usd, 1.0)
    hw_v7_phase1_net_overlap = np.maximum(hw_v7_phase1 - safety_starter_overlap_usd, 1.0)
    hw_v7_full_lifecycle = hw_v7_full_net_overlap + v7_nre_total
    hw_v7_phase1_lifecycle = hw_v7_phase1_net_overlap + v7_nre_total

    # Program multiplier M_prog (Exp128 exact: P10=3.0x, P50=5.477x, P90=10.0x)
    mu_mprog = math.log(math.sqrt(3.0 * 10.0))
    sigma_mprog = math.log(10.0 / 3.0) / (2.0 * Z90)
    m_prog = np.exp(mu_mprog + sigma_mprog * rng.standard_normal(N))

    prog_v3_stoch = hw_v3 * m_prog
    prog_v4_stoch = hw_v4 * m_prog
    prog_v4_x3 = hw_v4 * 3.0
    prog_v4_x10 = hw_v4 * 10.0
    prog_v7_phase1_stoch = hw_v7_phase1 * m_prog
    prog_v7_full_stoch = hw_v7_full * m_prog
    prog_v7_full_lifecycle_stoch = hw_v7_full_net_overlap * m_prog + v7_nre_total

    # Cleanroom ISO-5/6 bay CAPEX ($1.5M / $2.5M / $4.5M) — 5-yr amortization
    cleanroom_capex = sample_lognormal_p10_p50_p90(rng, 1.5e6, 2.5e6, 4.5e6, N)
    # Commercial fab-tool installation factor (N-th tool, excludes FOAK R&D NRE): [1.20, 1.35, 1.55]
    install_mult = sample_lognormal_p10_p50_p90(rng, 1.20, 1.35, 1.55, N)

    # Annual Fixed OPEX components (OBS-062/126: 20-30 kW incl. 12.5 kW PT420 + 3He + scrubber + PT420 rebuild)
    power_kw = rng.uniform(20.0, 30.0, size=N)  # 12.5 kW PT420 + LD400 GHS + RF/GPU/HPC racks
    elec_rate = sample_lognormal_p10_p50_p90(rng, 0.09, 0.14, 0.22, N)  # $/kWh
    opex_power_yr = power_kw * 8760.0 * elec_rate
    opex_hvac_yr = sample_lognormal_p10_p50_p90(rng, 80_000.0, 120_000.0, 200_000.0, N)
    opex_ph3_yr = sample_lognormal_p10_p50_p90(rng, 28_000.0, 45_000.0, 75_000.0, N)
    opex_3he_topup_yr = sample_lognormal_p10_p50_p90(rng, 10_000.0, 18_000.0, 35_000.0, N)
    opex_scrubber_ehs_yr = sample_lognormal_p10_p50_p90(rng, 18_000.0, 32_000.0, 55_000.0, N)
    opex_pt420_rebuild_yr = sample_lognormal_p10_p50_p90(rng, 12_000.0, 20_000.0, 35_000.0, N)
    opex_fte_yr = sample_lognormal_p10_p50_p90(rng, 2.0, 3.0, 4.5, N) * 160_000.0
    maint_frac = sample_lognormal_p10_p50_p90(rng, 0.06, 0.08, 0.11, N)

    opex_ehs_cryo_extras_yr = opex_3he_topup_yr + opex_scrubber_ehs_yr + opex_pt420_rebuild_yr
    opex_common_base_yr = opex_power_yr + opex_hvac_yr + opex_ph3_yr + opex_fte_yr
    opex_fixed_v3_yr = opex_common_base_yr + maint_frac * hw_v3
    opex_fixed_v4_yr = opex_common_base_yr + maint_frac * hw_v4
    opex_fixed_v7_phase1_yr = opex_common_base_yr + opex_ehs_cryo_extras_yr + maint_frac * hw_v7_phase1
    opex_fixed_v7_full_yr = opex_common_base_yr + opex_ehs_cryo_extras_yr + maint_frac * hw_v7_full

    # 5-Year TCO (excluding variable wafers)
    foak_tco5_v3 = prog_v3_stoch + cleanroom_capex + 5.0 * opex_fixed_v3_yr
    foak_tco5_v4 = prog_v4_stoch + cleanroom_capex + 5.0 * opex_fixed_v4_yr
    foak_tco5_v7_phase1 = prog_v7_phase1_stoch + cleanroom_capex + 5.0 * opex_fixed_v7_phase1_yr
    foak_tco5_v7_full = prog_v7_full_stoch + cleanroom_capex + 5.0 * opex_fixed_v7_full_yr
    foak_tco5_v7_full_lifecycle = prog_v7_full_lifecycle_stoch + cleanroom_capex + 5.0 * opex_fixed_v7_full_yr

    fab_tco5_v3_n1 = hw_v3 * install_mult + cleanroom_capex + 5.0 * opex_fixed_v3_yr
    fab_tco5_v4_n1 = hw_v4 * install_mult + cleanroom_capex + 5.0 * opex_fixed_v4_yr
    fab_tco5_v7_phase1_n1 = hw_v7_phase1 * install_mult + cleanroom_capex + 5.0 * opex_fixed_v7_phase1_yr
    fab_tco5_v7_full_n1 = hw_v7_full * install_mult + cleanroom_capex + 5.0 * opex_fixed_v7_full_yr
    fab_tco5_v7_full_lifecycle_n1 = hw_v7_full_lifecycle * install_mult + cleanroom_capex + 5.0 * opex_fixed_v7_full_yr

    hw_m1 = hw_v3 * (m1_hw_nom / m3_v3_nom)
    m1_tco5_lab = hw_m1 * install_mult + 0.5 * cleanroom_capex + 5.0 * (0.65 * opex_fixed_v3_yr)

    # -------------------------------------------------------------------------
    # 3. Budget-Cap Headroom Analysis: v3.0 / v4.0 / v7.0 Phase-1 / v7.0 Full
    # -------------------------------------------------------------------------
    p_v4_bom_gt_50m = float(np.mean(hw_v4 > 50e6))
    p_v4_prog_gt_50m = float(np.mean(prog_v4_stoch > 50e6))
    p_v4_prog_gt_100m = float(np.mean(prog_v4_stoch > 100e6))
    p_v3_prog_gt_50m = float(np.mean(prog_v3_stoch > 50e6))
    p_v3_prog_gt_100m = float(np.mean(prog_v3_stoch > 100e6))
    se_v4_p100 = math.sqrt(p_v4_prog_gt_100m * (1.0 - p_v4_prog_gt_100m) / N)

    p_v7_p1_prog_gt_100m = float(np.mean(prog_v7_phase1_stoch > 100e6))
    p_v7_full_prog_gt_100m = float(np.mean(prog_v7_full_stoch > 100e6))
    p_v7_full_foak_tco5_gt_100m = float(np.mean(foak_tco5_v7_full > 100e6))
    p_v7_full_lifecycle_tco5_gt_100m = float(np.mean(foak_tco5_v7_full_lifecycle > 100e6))

    # Convergence check: first N/2 vs full N on v7.0 Full FOAK 5-yr TCO (and v4.0 legacy)
    half_p50 = float(np.median(foak_tco5_v7_full[: N // 2]))
    full_p50 = float(np.median(foak_tco5_v7_full))
    half_p95 = float(np.percentile(foak_tco5_v7_full[: N // 2], 95))
    full_p95 = float(np.percentile(foak_tco5_v7_full, 95))
    conv_p50_rel = abs(full_p50 - half_p50) / full_p50
    conv_p95_rel = abs(full_p95 - half_p95) / full_p95

    # -------------------------------------------------------------------------
    # 4. Regime I — Steady-State Capacity Limit Unit Economics (5-yr, 80% uptime)
    # -------------------------------------------------------------------------
    cap_scenarios = {
        "v3_0_baseline": (tp_v3, foak_tco5_v3, fab_tco5_v3_n1),
        "v4_0_bayes5x_15ms": (tp_v4_5x, foak_tco5_v4, fab_tco5_v4_n1),
        "v4_0_bayes10x_15ms_write_clamped": (tp_v4_10x_15ms, foak_tco5_v4, fab_tco5_v4_n1),
        "v4_0_bayes10x_10ms": (tp_v4_10x_10ms, foak_tco5_v4, fab_tco5_v4_n1),
        "v4_0_bayes15x_10ms_write_clamped": (tp_v4_15x_10ms, foak_tco5_v4, fab_tco5_v4_n1),
        "v7_0_real_si29_boed_nom_blanker": (tp_v7_real_bath_nom_blanker, foak_tco5_v7_full_lifecycle, fab_tco5_v7_full_lifecycle_n1),
        "v7_0_real_si29_boed_5pct_stitch": (tp_v7_real_bath_5pct_stitch, foak_tco5_v7_full_lifecycle, fab_tco5_v7_full_lifecycle_n1),
    }
    regime1_capacity = {}
    for name, (tp, foak_arr, fab_arr) in cap_scenarios.items():
        reg_5yr = tp["net_reg_yr_80pct"] * 5.0
        regime1_capacity[name] = {
            "throughput": tp,
            "foak_program_5yr": build_unit_econ_summary(foak_arr, reg_5yr),
            "fab_tool_n1_5yr": build_unit_econ_summary(fab_arr, reg_5yr),
        }

    v3_reg_p50 = regime1_capacity["v3_0_baseline"]["fab_tool_n1_5yr"]["usd_per_register"]["p50"]
    v4_5x_reg_p50 = regime1_capacity["v4_0_bayes5x_15ms"]["fab_tool_n1_5yr"]["usd_per_register"]["p50"]
    v4_10x10_reg_p50 = regime1_capacity["v4_0_bayes10x_10ms"]["fab_tool_n1_5yr"]["usd_per_register"]["p50"]
    red_5x_pct = 1.0 - v4_5x_reg_p50 / v3_reg_p50
    red_10x10_pct = 1.0 - v4_10x10_reg_p50 / v3_reg_p50
    eff_speedup_10x_15ms = tp_v4_10x_15ms["net_reg_day"] / tp_v3["net_reg_day"]

    # -------------------------------------------------------------------------
    # 5. Regime II — Wafer-Batch Fab Operation + OBS-060 3-Tier Wafer Reconciliation
    # -------------------------------------------------------------------------
    wafer_price_stoch = sample_lognormal_p10_p50_p90(rng, 5_000.0, 12_000.0, 25_000.0, N)

    wafer_configs = {
        "standard_2e6_8h": (2.0e6, 8.0),
        "standard_2e6_4h": (2.0e6, 4.0),
        "standard_2e6_1h": (2.0e6, 1.0),
        "dense_5e7_8h": (5.0e7, 8.0),
        "dense_5e7_4h": (5.0e7, 4.0),
        "dense_5e7_1h": (5.0e7, 1.0),
    }
    # Add scaled 200 mm bore/cryo/LL redesign CAPEX (+$1.85M) for v7 Fab-scale 200 mm tier
    fab_tco5_v7_200mm_n1 = fab_tco5_v7_full_lifecycle_n1 + 1_850_000.0 * (install_mult + 5.0 * maint_frac)

    regime2_wafer_batch = {}
    for wname, (rpw, tswap) in wafer_configs.items():
        per_ver = {}
        for vkey, (tp, fab_arr) in [
            ("v3_0", (tp_v3, fab_tco5_v3_n1)),
            ("v4_0_5x", (tp_v4_5x, fab_tco5_v4_n1)),
            ("v4_0_10x_10ms", (tp_v4_10x_10ms, fab_tco5_v4_n1)),
            ("v7_0_real_bath_stitch_200mm_scaled", (tp_v7_real_bath_5pct_stitch, fab_tco5_v7_200mm_n1)),
        ]:
            wb = wafer_batch_throughput(tp["net_reg_day"], rpw, tswap)
            wafers_5yr = wb["wafers_per_yr"] * 5.0
            reg_5yr = wb["reg_per_yr"] * 5.0
            econ_stoch = build_unit_econ_summary(
                fab_arr, reg_5yr, wafer_cost_5yr=wafers_5yr * wafer_price_stoch
            )
            by_wp = {}
            for wp in (5_000.0, 12_000.0, 25_000.0):
                tot_w = fab_arr + wafers_5yr * wp
                chip_p50 = float(np.median(tot_w / reg_5yr * 10_000.0))
                wafer_floor_chip = wp / (rpw / 10_000.0)
                by_wp[f"usd_{int(wp)}"] = {
                    "wafer_price_usd": wp,
                    "tco_5yr_p50_usd": float(np.median(tot_w)),
                    "usd_per_chip_10k_p50": chip_p50,
                    "wafer_cost_floor_per_chip_usd": wafer_floor_chip,
                    "wafer_share_of_chip_cost": wafer_floor_chip / chip_p50,
                    "usd_per_wafer_processed_p50": float(np.median(tot_w / wafers_5yr)),
                }
            per_ver[vkey] = {
                "batch_kinematics": wb,
                "fab_tool_n1_stoch_wafer": econ_stoch,
                "wafer_price_sweep": by_wp,
            }
        regime2_wafer_batch[wname] = per_ver

    # OBS-060: Explicit 3-tier wafer diameter comparison under v7.0 lifecycle TCO + real-bath stitch throughput
    wafer_tier_reconciliation: dict[str, Any] = {}
    for tname, tspec in WAFER_TIER_SPECS.items():
        adder = float(tspec["bore_redesign_capex_adder_usd"])
        tco_tier = fab_tco5_v7_full_lifecycle_n1 + adder * (install_mult + 5.0 * maint_frac)
        wb_dense = wafer_batch_throughput(tp_v7_real_bath_5pct_stitch["net_reg_day"], float(tspec["dense_reg_per_wafer"]), 1.0)
        wafers_5yr = wb_dense["wafers_per_yr"] * 5.0
        reg_5yr = wb_dense["reg_per_yr"] * 5.0
        wp_nom = float(tspec["wafer_price_p10_p50_p90_usd"][1])
        tot_tco_tier = tco_tier + wafers_5yr * wp_nom
        chip_p50 = float(np.median(tot_tco_tier / reg_5yr * 10_000.0))
        wafer_floor = wp_nom / (float(tspec["dense_reg_per_wafer"]) / 10_000.0)
        wafer_tier_reconciliation[tname] = {
            **tspec,
            "v7_lifecycle_tco5_no_wafer_p50_usd": float(np.median(tco_tier)),
            "dense_1h_swap_wafers_per_yr": round(wb_dense["wafers_per_yr"], 2),
            "dense_1h_swap_reg_per_yr": wb_dense["reg_per_yr"],
            "dense_1h_swap_usd_per_chip_10k_p50": round(chip_p50, 4),
            "wafer_cost_floor_per_chip_10k_usd": round(wafer_floor, 4),
        }

    std8_v3_chip = regime2_wafer_batch["standard_2e6_8h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"]
    std8_v4_chip = regime2_wafer_batch["standard_2e6_8h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"]
    std8_red_5x = 1.0 - std8_v4_chip / std8_v3_chip

    dense1_v3_chip = regime2_wafer_batch["dense_5e7_1h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"]
    dense1_v4_chip = regime2_wafer_batch["dense_5e7_1h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"]
    dense1_red_5x = 1.0 - dense1_v4_chip / dense1_v3_chip

    # -------------------------------------------------------------------------
    # 6. Wright Learning Curve (b in {0.82, 0.85, 0.88}, N = 1 -> 10 -> 100) — v7.0 Full Base
    # -------------------------------------------------------------------------
    n_grid = [1, 5, 10, 25, 50, 100]
    b_grid = [0.82, 0.85, 0.88]
    wb_dense1_v4 = wafer_batch_throughput(tp_v4_5x["net_reg_day"], 5.0e7, 1.0)
    wb_dense1_v7 = wafer_batch_throughput(tp_v7_real_bath_5pct_stitch["net_reg_day"], 5.0e7, 1.0)

    wright_curves = {}
    for b in b_grid:
        rows_b = {}
        for nt in n_grid:
            wm = wright_multiplier(nt, b)
            fac_scale = float(nt ** -0.08)
            hw_v4_n = hw_v4 * wm
            hw_v7_n = hw_v7_full * wm
            opex_n_yr = (
                opex_power_yr
                + opex_hvac_yr * fac_scale
                + opex_ph3_yr * fac_scale
                + opex_fte_yr * float(nt ** -0.15)
                + maint_frac * hw_v4_n
            )
            opex_v7_n_yr = (
                opex_power_yr
                + opex_hvac_yr * fac_scale
                + opex_ph3_yr * fac_scale
                + opex_ehs_cryo_extras_yr * fac_scale
                + opex_fte_yr * float(nt ** -0.15)
                + maint_frac * hw_v7_n
            )
            tco5_no_wafer_n = hw_v4_n * install_mult + cleanroom_capex * fac_scale + 5.0 * opex_n_yr
            tco5_v7_no_wafer_n = hw_v7_n * install_mult + cleanroom_capex * fac_scale + 5.0 * opex_v7_n_yr
            wafer_n_price = 12_000.0 * float(nt ** math.log2(0.92))

            tot_dense_n = tco5_no_wafer_n + (wb_dense1_v4["wafers_per_yr"] * 5.0) * wafer_n_price
            reg5_dense = wb_dense1_v4["reg_per_yr"] * 5.0
            usd_reg_dense_p50 = float(np.median(tot_dense_n / reg5_dense))

            tot_dense_v7_n = tco5_v7_no_wafer_n + (wb_dense1_v7["wafers_per_yr"] * 5.0) * wafer_n_price
            reg5_dense_v7 = wb_dense1_v7["reg_per_yr"] * 5.0
            usd_reg_dense_v7_p50 = float(np.median(tot_dense_v7_n / reg5_dense_v7))

            reg5_cap = tp_v4_5x["net_reg_yr_80pct"] * 5.0
            usd_reg_cap_p50 = float(np.median(tco5_no_wafer_n / reg5_cap))

            lc17 = logical_qubit_cells(17)
            lc11 = logical_qubit_cells(11)
            lc7 = logical_qubit_cells(7)

            rows_b[str(nt)] = {
                "n_tools": nt,
                "wright_hw_multiplier": wm,
                "hw_v4_nom_usd": (m3_v3_nom + v4_delta_nom_total) * wm,
                "hw_v7_full_nom_usd": m3_v7_full_nom * wm,
                "hw_v4_mc_p50_usd": float(np.median(hw_v4_n)),
                "hw_v7_full_mc_p50_usd": float(np.median(hw_v7_n)),
                "tco5_no_wafer_p50_usd": float(np.median(tco5_no_wafer_n)),
                "tco5_v7_no_wafer_p50_usd": float(np.median(tco5_v7_no_wafer_n)),
                "wafer_price_200mm_usd": wafer_n_price,
                "capacity_usd_per_reg_p50": usd_reg_cap_p50,
                "capacity_d17_modb_logical_p50": usd_reg_cap_p50 * lc17["n_cells_modb_1over051"],
                "dense_fab_usd_per_reg_p50": usd_reg_dense_p50,
                "dense_fab_usd_per_chip_10k_p50": usd_reg_dense_p50 * 10_000.0,
                "dense_fab_v7_real_bath_d17_logical_p50": usd_reg_dense_v7_p50 * lc17["n_cells_modb_1over051"],
                "dense_fab_d7_modb_logical_p50": usd_reg_dense_p50 * lc7["n_cells_modb_1over051"],
                "dense_fab_d11_modb_logical_p50": usd_reg_dense_p50 * lc11["n_cells_modb_1over051"],
                "dense_fab_d17_modb_logical_p50": usd_reg_dense_p50 * lc17["n_cells_modb_1over051"],
            }
        wright_curves[f"b_{int(round(b*100))}"] = rows_b

    w85_n100 = wright_curves["b_85"]["100"]

    # -------------------------------------------------------------------------
    # 7. v3.0 -> v4.0 Upgrade Value & Avoided-CAPEX Leverage
    # -------------------------------------------------------------------------
    avoided_v3_hw_5x = 4.0 * float(np.median(hw_v3))
    v4_upgrade_hw_p50 = float(np.median(hw_v4_delta))
    v4_hw_leverage_5x = avoided_v3_hw_5x / v4_upgrade_hw_p50
    avoided_v3_tco5_5x = 4.0 * float(np.median(fab_tco5_v3_n1))
    v4_extra_tco5 = float(np.median(fab_tco5_v4_n1 - fab_tco5_v3_n1))
    v4_tco_leverage_5x = avoided_v3_tco5_5x / max(v4_extra_tco5, 1.0)

    # -------------------------------------------------------------------------
    # 8. CDF Quantile Curves for PyCairo Figures
    # -------------------------------------------------------------------------
    cdf_probs = sorted(set([round(p, 4) for p in np.linspace(0.005, 0.995, 199).tolist()] + [0.001, 0.999]))
    cdf_curves = {
        "probs": cdf_probs,
        "v3_prog_stoch_usd": [float(v) for v in np.percentile(prog_v3_stoch, [p * 100 for p in cdf_probs])],
        "v4_prog_stoch_usd": [float(v) for v in np.percentile(prog_v4_stoch, [p * 100 for p in cdf_probs])],
        "v7_phase1_prog_stoch_usd": [float(v) for v in np.percentile(prog_v7_phase1_stoch, [p * 100 for p in cdf_probs])],
        "v7_full_prog_stoch_usd": [float(v) for v in np.percentile(prog_v7_full_stoch, [p * 100 for p in cdf_probs])],
        "v4_foak_tco5_usd": [float(v) for v in np.percentile(foak_tco5_v4, [p * 100 for p in cdf_probs])],
        "v7_full_foak_tco5_lifecycle_usd": [float(v) for v in np.percentile(foak_tco5_v7_full_lifecycle, [p * 100 for p in cdf_probs])],
        "v4_fab_tco5_usd": [float(v) for v in np.percentile(fab_tco5_v4_n1, [p * 100 for p in cdf_probs])],
        "v7_full_fab_tco5_lifecycle_usd": [float(v) for v in np.percentile(fab_tco5_v7_full_lifecycle_n1, [p * 100 for p in cdf_probs])],
    }

    # -------------------------------------------------------------------------
    # 9. Score Pre-Registered Verdicts (CX1-CX6 + honest v7.0 tail check)
    # -------------------------------------------------------------------------
    verdicts = {
        "CX1_baseline_gate": bool(cx1_ok),
        "CX2_v4_budget_cap_survival": bool(p_v4_bom_gt_50m < 0.001 and p_v4_prog_gt_100m < 0.05),
        "CX2_v7_phase1_budget_cap_survival": bool(p_v7_p1_prog_gt_100m < 0.05),
        "CX2_v7_full_honest_exceeds_5pct_cap": bool(p_v7_full_prog_gt_100m >= 0.05),
        "CX3_bayesian_unit_cost_collapse": bool(
            red_5x_pct >= 0.75 and red_10x10_pct >= 0.85 and eff_speedup_10x_15ms < 8.0
        ),
        "CX4_amdahl_wafer_floor": bool(std8_red_5x < 0.15 and dense1_red_5x > 0.50),
        "CX5_wright_learning_100x": bool(
            w85_n100["wright_hw_multiplier"] <= 0.40
            and w85_n100["dense_fab_d17_modb_logical_p50"] < 50.0
        ),
        "CX6_mc_convergence_50k": bool(conv_p50_rel <= 0.015 and se_v4_p100 < 0.002),
    }
    verdicts["success"] = bool(
        verdicts["CX1_baseline_gate"]
        and verdicts["CX2_v4_budget_cap_survival"]
        and verdicts["CX3_bayesian_unit_cost_collapse"]
        and verdicts["CX6_mc_convergence_50k"]
    )

    out = {
        "experiment": "exp134_fab_economics_tco",
        "hypothesis_id": "H152",
        "bom_version_synced": "v7.0",
        "procurement_status": "UNQUOTED_ROM_ESTIMATE",
        "predictions": pred,
        "baseline_gate": {
            "bom_csv_sha256": bom_sha,
            "sha256_ok": sha_ok,
            "bom_detailed_v3_nom_usd": m3_v3_nom,
            "bom_detailed_v5_base_nom_usd": m3_v5_base_nom,
            "bom_detailed_v7_phase1_nom_usd": m3_phase1_nom,
            "bom_detailed_m3_nom_usd": m3_v7_full_nom,
            "bom_detailed_m3_low_usd": m3_v7_full_low,
            "bom_detailed_m3_high_usd": m3_v7_full_high,
            "bom_detailed_m1_nom_usd": m1_hw_nom,
            "v7_vs_v3_hw_delta_usd": m3_v7_full_nom - m3_v3_nom,
            "v7_vs_v3_hw_pct_increase": (m3_v7_full_nom - m3_v3_nom) / m3_v3_nom,
            "v3_throughput_reg_day": tp_v3["net_reg_day"],
            "v3_throughput_rel_err_vs_exp127": v3_tp_rel_err,
            "gate_ok": cx1_ok,
        },
        "v7_lifecycle_tco_obs062": {
            "bom_v7_full_nom_usd": m3_v7_full_nom,
            "bom_v7_phase1_base_safety_nom_usd": m3_phase1_nom,
            "v7_safety_kit_hw_nom_usd": v7_safety_hw_nom,
            "safety_starter_overlap_reconciled_usd": safety_starter_overlap_usd,
            "safety_starter_overlap_breakdown_usd": safety_starter_overlap_breakdown,
            "unbudgeted_nre_adders_p10_p50_p90_usd": {k: list(v) for k, v in V7_LIFECYCLE_NRE_ADDERS.items()},
            "unbudgeted_nre_total_nom_usd": v7_nre_nom_total,
            "v7_full_lifecycle_hw_plus_nre_net_overlap_nom_usd": m3_v7_full_nom - safety_starter_overlap_usd + v7_nre_nom_total,
            "v7_phase1_prog_stoch_usd": pct_summary(prog_v7_phase1_stoch),
            "v7_full_prog_stoch_usd": pct_summary(prog_v7_full_stoch),
            "v7_full_lifecycle_prog_stoch_usd": pct_summary(prog_v7_full_lifecycle_stoch),
            "P_v7_phase1_prog_gt_100M": p_v7_p1_prog_gt_100m,
            "P_v7_full_prog_gt_100M": p_v7_full_prog_gt_100m,
            "P_v7_full_foak_5yr_tco_gt_100M": p_v7_full_foak_tco5_gt_100m,
            "P_v7_full_lifecycle_foak_5yr_tco_gt_100M": p_v7_full_lifecycle_tco5_gt_100m,
        },
        "wafer_tier_reconciliation_obs060": wafer_tier_reconciliation,
        "real_bath_throughput_obs068": {
            "real_si29_boed_mean_time_s": REAL_SI29_BOED_SPEC_TIME_S,
            "real_si29_boed_speedup_vs_1s": round(real_bath_speedup, 4),
            "blanker_5pct_dead_stitch_eff": BLANKER_5PCT_DEAD_STITCH_EFF,
            "tp_real_bath_nom_blanker": tp_v7_real_bath_nom_blanker,
            "tp_real_bath_5pct_stitch": tp_v7_real_bath_5pct_stitch,
        },
        "v4_hardware_deltas": {
            "components_p10_p50_p90_usd": {k: list(v) for k, v in V4_DELTAS.items()},
            "total_low_usd": v4_delta_low_total,
            "total_nom_usd": v4_delta_nom_total,
            "total_high_usd": v4_delta_high_total,
            "v4_m3_hw_nom_usd": m3_v3_nom + v4_delta_nom_total,
            "v4_hw_pct_increase_over_v3": v4_delta_nom_total / m3_v3_nom,
        },
        "opex_annual_breakdown_usd": {
            "power_20_30kw_incl_12p5kw_pt420": pct_summary(opex_power_yr),
            "cleanroom_hvac": pct_summary(opex_hvac_yr),
            "ph3_gas_ehs": pct_summary(opex_ph3_yr),
            "he3_topup_and_ghs_consumables": pct_summary(opex_3he_topup_yr),
            "scrubber_media_and_radiation_ehs": pct_summary(opex_scrubber_ehs_yr),
            "pt420_coldhead_rebuild_reserve": pct_summary(opex_pt420_rebuild_yr),
            "fte_operators_engineers": pct_summary(opex_fte_yr),
            "maintenance_spares_8pct_v3": pct_summary(maint_frac * hw_v3),
            "maintenance_spares_8pct_v4": pct_summary(maint_frac * hw_v4),
            "maintenance_spares_8pct_v7_full": pct_summary(maint_frac * hw_v7_full),
            "total_fixed_opex_yr_v3": pct_summary(opex_fixed_v3_yr),
            "total_fixed_opex_yr_v4": pct_summary(opex_fixed_v4_yr),
            "total_fixed_opex_yr_v7_phase1": pct_summary(opex_fixed_v7_phase1_yr),
            "total_fixed_opex_yr_v7_full": pct_summary(opex_fixed_v7_full_yr),
            "cleanroom_setup_capex": pct_summary(cleanroom_capex),
        },
        "tco_5yr_summary_no_wafers": {
            "m1_lab_5yr_tco_usd": pct_summary(m1_tco5_lab),
            "v3_fab_tool_n1_5yr_tco_usd": pct_summary(fab_tco5_v3_n1),
            "v4_fab_tool_n1_5yr_tco_usd": pct_summary(fab_tco5_v4_n1),
            "v7_phase1_fab_tool_n1_5yr_tco_usd": pct_summary(fab_tco5_v7_phase1_n1),
            "v7_full_fab_tool_n1_5yr_tco_usd": pct_summary(fab_tco5_v7_full_n1),
            "v7_full_lifecycle_fab_tool_n1_5yr_tco_usd": pct_summary(fab_tco5_v7_full_lifecycle_n1),
            "v3_foak_program_5yr_tco_usd": pct_summary(foak_tco5_v3),
            "v4_foak_program_5yr_tco_usd": pct_summary(foak_tco5_v4),
            "v7_phase1_foak_program_5yr_tco_usd": pct_summary(foak_tco5_v7_phase1),
            "v7_full_foak_program_5yr_tco_usd": pct_summary(foak_tco5_v7_full),
            "v7_full_lifecycle_foak_program_5yr_tco_usd": pct_summary(foak_tco5_v7_full_lifecycle),
        },
        "budget_cap_v3_vs_v4": {
            "n_samples": N,
            "seed": seed,
            "v3_hw_mc_usd": pct_summary(hw_v3),
            "v4_hw_mc_usd": pct_summary(hw_v4),
            "v7_phase1_hw_mc_usd": pct_summary(hw_v7_phase1),
            "v7_full_hw_mc_usd": pct_summary(hw_v7_full),
            "v3_prog_stoch_usd": pct_summary(prog_v3_stoch),
            "v4_prog_stoch_usd": pct_summary(prog_v4_stoch),
            "v7_phase1_prog_stoch_usd": pct_summary(prog_v7_phase1_stoch),
            "v7_full_prog_stoch_usd": pct_summary(prog_v7_full_stoch),
            "v4_prog_x3_usd": pct_summary(prog_v4_x3),
            "v4_prog_x10_usd": pct_summary(prog_v4_x10),
            "exceedance_probabilities": {
                "P_v3_BOM_gt_50M": float(np.mean(hw_v3 > 50e6)),
                "P_v4_BOM_gt_50M": p_v4_bom_gt_50m,
                "P_v7_full_BOM_gt_50M": float(np.mean(hw_v7_full > 50e6)),
                "P_v3_Prog_stoch_gt_50M": p_v3_prog_gt_50m,
                "P_v3_Prog_stoch_gt_100M": p_v3_prog_gt_100m,
                "P_v4_Prog_stoch_gt_50M": p_v4_prog_gt_50m,
                "P_v4_Prog_stoch_gt_100M": p_v4_prog_gt_100m,
                "P_v7_phase1_Prog_stoch_gt_100M": p_v7_p1_prog_gt_100m,
                "P_v7_full_Prog_stoch_gt_100M": p_v7_full_prog_gt_100m,
                "P_v7_full_foak_tco5_gt_100M": p_v7_full_foak_tco5_gt_100m,
                "P_v4_Prog_x10_gt_50M": float(np.mean(prog_v4_x10 > 50e6)),
                "P_v4_Prog_x10_gt_100M": float(np.mean(prog_v4_x10 > 100e6)),
                "SE_P_v4_Prog_gt_100M": se_v4_p100,
            },
            "convergence_25k_vs_50k": {
                "half_p50_usd": half_p50,
                "full_p50_usd": full_p50,
                "rel_diff_p50": conv_p50_rel,
                "half_p95_usd": half_p95,
                "full_p95_usd": full_p95,
                "rel_diff_p95": conv_p95_rel,
            },
        },
        "regime1_steady_state_capacity": regime1_capacity,
        "regime2_wafer_batch_amdahl": regime2_wafer_batch,
        "wright_learning_curves": wright_curves,
        "v3_to_v4_value_leverage": {
            "capacity_5x_unit_cost_reduction_frac": red_5x_pct,
            "capacity_10x_10ms_unit_cost_reduction_frac": red_10x10_pct,
            "effective_speedup_10x_at_15ms_write_clamped": eff_speedup_10x_15ms,
            "standard_2e6_8h_5x_chip_reduction_frac": std8_red_5x,
            "dense_5e7_1h_5x_chip_reduction_frac": dense1_red_5x,
            "avoided_4x_v3_hw_capex_usd": avoided_v3_hw_5x,
            "v4_upgrade_hw_p50_usd": v4_upgrade_hw_p50,
            "hw_capex_leverage_ratio_5x": v4_hw_leverage_5x,
            "avoided_4x_v3_tco5_usd": avoided_v3_tco5_5x,
            "v4_extra_tco5_usd": v4_extra_tco5,
            "tco5_leverage_ratio_5x": v4_tco_leverage_5x,
        },
        "cdf_curves": cdf_curves,
        "verdicts": verdicts,
        "epistemic_caveat": (
            "UNQUOTED_ROM_ESTIMATE: No real supplier quotes or fab measurements exist (TRL 1-2 / M0). "
            "Hardware CAPEX inherits BOM_DETAILED.csv v7.0 ($5.693M Full / $5.393M Phase-1 Base+Safety) "
            "plus explicit lifecycle NRE (SEMI S2/IEC 61508 assessment, TWPA foundry NRE, multi-lot MEMS NRE) "
            "and EHS/cryo/scrubber OPEX. FOAK CAD/BOM is Ø50 mm ($2,240/wafer); Fab-scale 200 mm includes "
            "+$1.85M bore/cryo/LL redesign CAPEX ({Varsayım})."
        ),
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
    }

    if write_outputs:
        OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    out = run_tco_model(n_samples=50_000, seed=2026134, write_outputs=True)
    bg = out["baseline_gate"]
    v7 = out["v7_lifecycle_tco_obs062"]
    tco = out["tco_5yr_summary_no_wafers"]
    print("=== EXP134 v7.0 FAB ECONOMICS & 5-YR TCO COMPLETE ===")
    print(f"Gate OK: {bg['gate_ok']} | v3=${bg['bom_detailed_v3_nom_usd']/1e6:.3f}M -> v7 Full=${bg['bom_detailed_m3_nom_usd']/1e6:.3f}M (+{bg['v7_vs_v3_hw_pct_increase']:.1%})")
    print(f"Safety overlap reconciled: -${v7['safety_starter_overlap_reconciled_usd']:,.0f} | Unbudgeted NRE: +${v7['unbudgeted_nre_total_nom_usd']:,.0f}")
    print(f"5-yr Fab-Tool TCO (N=1): v7 Phase-1 P50=${tco['v7_phase1_fab_tool_n1_5yr_tco_usd']['p50']/1e6:.2f}M | v7 Full Lifecycle P50=${tco['v7_full_lifecycle_fab_tool_n1_5yr_tco_usd']['p50']/1e6:.2f}M")
    print(f"5-yr FOAK Prog TCO (N=1): v7 Phase-1 P50=${tco['v7_phase1_foak_program_5yr_tco_usd']['p50']/1e6:.2f}M | v7 Full Lifecycle P50=${tco['v7_full_lifecycle_foak_program_5yr_tco_usd']['p50']/1e6:.2f}M")
    print(f"Budget Cap: P(v7 Phase-1 Prog >$100M)={v7['P_v7_phase1_prog_gt_100M']:.2%} | P(v7 Full Prog >$100M)={v7['P_v7_full_prog_gt_100M']:.2%} | P(v7 Full Lifecycle FOAK TCO >$100M)={v7['P_v7_full_lifecycle_foak_5yr_tco_gt_100M']:.2%}")
    print("VERDICTS:", out["verdicts"])


if __name__ == "__main__":
    main()
