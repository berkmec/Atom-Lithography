#!/usr/bin/env python3
"""Exp141 v5.0 Wafer Economics & Deployed Logical-Qubit Cost Module.

Pure, importable economics module for the Exp141 v5.0 Full-Machine Digital Twin:
1. Breaks the Exp134 CX4 silicon-wafer floor wall by comparing 3 wafer technologies
   (W1: $12k 200 mm thick 28Si epi; W2: $2.2k 200 mm thin 30 nm 28Si-on-SOI;
   W3: $3.6k 300 mm thin 30 nm 28Si-on-SOI, 2.25x area) under M3 v5.0 ($5,247,800).
2. Evaluates both wafer-fab manufacturing cost ($/logical_qubit_fab) and full
   100-logical-qubit deployed FT system CAPEX & 5-year TCO ($/logical_qubit_system,
   incorporating Exp138 surface-code distance d* & N_cand and Exp140 multi-cryostat
   2,887-cell thermal ceiling + $629.2k/1,024-cell Cryo-MUX stack).

100% portable (no hardcoded host paths). Read-only with respect to BOM.csv and
all prior experiment JSONs.
Epistemic status: no_lab_measurement=True, no_supplier_quotes=True ({Model}/{Varsayim}).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Epistemic & Physical Constants (locked to Exp128 v5.0, Exp134, Exp139, Exp140)
# ---------------------------------------------------------------------------
NO_LAB_MEASUREMENT = True
NO_SUPPLIER_QUOTES = True
EPISTEMIC_TAGS = ("{Model}", "{Varsayım}", "{Liste-Çapası}")

Z90 = 1.2815515655446004  # norm.ppf(0.90) — exact stdlib constant, zero SciPy import overhead

DAY_S = 86_400.0
DAYS_YR = 365.0
DUTY = 0.50
FAB_UPTIME = 0.80
HORIZON_YR = 5.0

BEAMLETS_ARCHB = 1024  # 32x32 @ 0.50 mm pitch (Exp124)
READOUT_CHANNELS = 56 * 160  # 8,960 ch (Exp112/127)
DETECTOR_ETA = 0.99936  # Exp127 Cold-100K / 1.2 us / 1 GOhm @ 5 keV
FLASH_SURVIVAL_V5 = 0.999207  # Exp139 v5_1x1530K_43p49J_cluster_clearing Route C f_act_bulk
DEFAULT_BATH_YIELD = 0.51  # Canonical KL Mod B f=1% (Exp134 anchor; Exp136 TB f*=1%: 0.5275)
SPEC_TIME_V3_S = 1.0  # Exp65/127 baseline spectroscopy
EXP140_BOED_MEAN_TIME_MS = 41.62  # Exp140 Q16.16 FPGA-BOED mean time/candidate (24.03x speedup)
EXP140_RO_MUX_RATIO = 32  # Exp140 S6.5 N_mux* = 32 cells per RF readout chain

# BOM Hardware Anchors (exact USD from Exp128 v3.0 / v4.0 / v5.0)
V3_M3_HW_NOM_USD = 4_189_600.0
V4_M3_HW_NOM_USD = 4_609_600.0
V5_M3_HW_NOM_USD = 5_247_800.0  # $4,609.6k + $724.2k (S5.6+S6.5) - $86k credit
V5_M3_PILOT_256_HW_NOM_USD = 4_790_400.0

# Correlated MC BOM P50 / nominal ratios (Exp128 v3/v4/v5: includes NL [110..163] & 20% C-class B/C wall)
HW_MC_P50_RATIO_V3 = 5_012_498.0 / V3_M3_HW_NOM_USD  # 1.19641
HW_MC_P50_RATIO_V5 = 6_152_668.48 / V5_M3_HW_NOM_USD  # 1.17243 (exact Exp128 v5.0 bom_with_bc_and_nl P50)
HW_MC_SIGMA_LOG = 0.385  # Matches Exp128/134 P10-P90 correlated BOM spread

# Exp140 Cryo-MUX & Runtime Cryostat Unit Costs ({Model}/{Liste-Çapası}/{Varsayım})
EXP140_CRYO_CELL_CAP_THERMAL = 2887  # Single LD400/PT420 hard 20 mK MXC limit (Exp140 tightest_stage=20mK_MXC)
EXP140_CRYO_CELL_NOMINAL_MODULE = 1024  # Single S6.5 32-chain Cryo-MUX module
EXP140_S65_MUX_1024_USD = (456_400.0, 629_200.0, 925_200.0)  # (low, nom, high)
# Per runtime modular cryostat bay (LD400 20mK DR $720k + PT420 $58.5k + S6.9 $68k
# + S6.3 B_M4 magnet $185k + S6.10 4K crossbar & DC DAC $83k + inter-fridge link $120k)
RUNTIME_CRYOSTAT_BAY_HW_USD = (790_000.0, 1_234_500.0, 2_050_000.0)
W3_300MM_STAGE_LOCK_ADDER_NOM_USD = 350_000.0  # Optional {Varsayım} 300mm S3/S5 chuck+load-lock adder sensitivity


@dataclass(frozen=True)
class WaferTechSpec:
    """Engineering cost & geometry specification for a 28Si wafer technology."""

    code: str
    label: str
    diameter_mm: int
    epi_thickness_nm: float
    area_factor_vs_200mm: float
    price_p10_usd: float
    price_p50_usd: float
    price_p90_usd: float
    dense_reg_per_wafer: float
    standard_reg_per_wafer: float
    epistemic_tag: str
    notes: str

    @property
    def dense_chips_10k(self) -> float:
        return self.dense_reg_per_wafer / 10_000.0

    @property
    def wafer_floor_per_chip_10k_usd(self) -> float:
        return self.price_p50_usd / self.dense_chips_10k


WAFER_SCENARIOS: dict[str, WaferTechSpec] = {
    "W1": WaferTechSpec(
        code="W1",
        label="v4.0 Ref: 200 mm Kalın 28Si Epi ($12k)",
        diameter_mm=200,
        epi_thickness_nm=500.0,
        area_factor_vs_200mm=1.00,
        price_p10_usd=5_000.0,
        price_p50_usd=12_000.0,
        price_p90_usd=25_000.0,
        dense_reg_per_wafer=5.0e7,
        standard_reg_per_wafer=2.0e6,
        epistemic_tag="{Varsayım}",
        notes="Exp134 CX4 çapası: kalın 500-1000 nm 28Si epi ($2,40/çip silikon zemini).",
    ),
    "W2": WaferTechSpec(
        code="W2",
        label="v5.0 İnce 30 nm 28Si-on-SOI 200 mm ($2,2k)",
        diameter_mm=200,
        epi_thickness_nm=30.0,
        area_factor_vs_200mm=1.00,
        price_p10_usd=1_500.0,
        price_p50_usd=2_200.0,
        price_p90_usd=3_200.0,
        dense_reg_per_wafer=5.0e7,
        standard_reg_per_wafer=2.0e6,
        epistemic_tag="{Varsayım}",
        notes="Exp139 aktif bölge <=23 nm -> >%95 daha az 28SiH4 gazı ($0,44/çip zemin, 5,45x düşüş).",
    ),
    "W3": WaferTechSpec(
        code="W3",
        label="v5.0 İnce 30 nm 28Si-on-SOI 300 mm ($3,6k)",
        diameter_mm=300,
        epi_thickness_nm=30.0,
        area_factor_vs_200mm=2.25,
        price_p10_usd=2_400.0,
        price_p50_usd=3_600.0,
        price_p90_usd=5_200.0,
        dense_reg_per_wafer=5.0e7 * 2.25,  # 1.125e8 reg/wafer (11,250 chips/wafer)
        standard_reg_per_wafer=2.0e6 * 2.25,  # 4.5e6 reg/wafer (450 chips/wafer)
        epistemic_tag="{Varsayım}",
        notes="300 mm 2,25x alan + 30 nm ince 28Si-on-SOI ($0,32/çip zemin, W1'e göre 7,50x düşüş).",
    ),
}


def wright_multiplier(n_units: float, learning_rate: float = 0.85) -> float:
    """Wright learning-curve unit cost multiplier C(N)/C(1) = N^(log2(b))."""
    n_eff = max(1.0, float(n_units))
    return float(n_eff ** math.log2(learning_rate))


def _sample_lognormal_p10_p50_p90(
    rng: np.random.Generator, p10: float, p50: float, p90: float, size: int
) -> np.ndarray:
    mu = math.log(p50)
    sigma = math.log(p90 / p10) / (2.0 * Z90)
    return np.exp(mu + sigma * rng.standard_normal(size))


def _pct_triplet(arr: np.ndarray) -> dict[str, float]:
    p10, p50, p90 = np.percentile(arr, [10.0, 50.0, 90.0])
    return {
        "mean": float(np.mean(arr)),
        "p10": float(p10),
        "p50": float(p50),
        "p90": float(p90),
    }


def compute_throughput_reg_day(
    bayesian_speedup: float = 1.0,
    shot_cycle_s: float = 0.015,
    bath_yield: float = DEFAULT_BATH_YIELD,
    detector_eta: float = DETECTOR_ETA,
    flash_survival: float = 1.0,
    beamlets: int = BEAMLETS_ARCHB,
    readout_ch: int = READOUT_CHANNELS,
) -> dict[str, Any]:
    """First-principles certified register throughput (write vs spectroscopy ceiling)."""
    eff_yield = bath_yield * detector_eta * flash_survival
    attempts_per_reg = 1.0 / eff_yield
    write_shots_day = DUTY * DAY_S * beamlets / shot_cycle_s
    write_reg_day = write_shots_day / attempts_per_reg
    spec_reg_day = (DUTY * DAY_S * readout_ch / (SPEC_TIME_V3_S / bayesian_speedup)) / attempts_per_reg
    net_reg_day = min(write_reg_day, spec_reg_day)
    return {
        "eff_yield": eff_yield,
        "write_reg_day": write_reg_day,
        "spec_reg_day": spec_reg_day,
        "net_reg_day": net_reg_day,
        "bottleneck": "write" if write_reg_day <= spec_reg_day else "spectroscopy",
    }


def simulate_fab_tco5_no_wafer(
    bom_hw_nom_usd: float,
    hw_mc_p50_ratio: float = HW_MC_P50_RATIO_V5,
    n_tools_wright: int = 1,
    wright_b: float = 0.85,
    n_mc: int = 20_000,
    seed: int = 2026141,
) -> dict[str, Any]:
    """Vectorised MC 5-year Commercial Fab-Tool TCO (ex-wafers), aligned to Exp134 & Exp128 v5.0."""
    rng = np.random.default_rng(seed)
    w_mult = wright_multiplier(n_tools_wright, wright_b)
    hw_p50 = bom_hw_nom_usd * hw_mc_p50_ratio * w_mult
    hw_mc = np.exp(math.log(hw_p50) + HW_MC_SIGMA_LOG * rng.standard_normal(n_mc))

    install_mult = _sample_lognormal_p10_p50_p90(rng, 1.20, 1.35, 1.55, n_mc)
    cleanroom_capex = _sample_lognormal_p10_p50_p90(rng, 1.5e6, 2.5e6, 4.5e6, n_mc) * (
        0.70 + 0.30 * w_mult
    )
    power_kw = rng.uniform(15.0, 25.0, size=n_mc)
    elec_rate = _sample_lognormal_p10_p50_p90(rng, 0.09, 0.14, 0.22, n_mc)
    opex_power = power_kw * 8760.0 * elec_rate
    opex_hvac = _sample_lognormal_p10_p50_p90(rng, 80_000.0, 120_000.0, 200_000.0, n_mc)
    opex_ph3 = _sample_lognormal_p10_p50_p90(rng, 28_000.0, 45_000.0, 75_000.0, n_mc)
    # Slight fleet FTE amortization at volume (N=1 -> 1.0x, N=100 -> 0.60x per tool)
    fte_scale = 0.60 + 0.40 * (max(1, n_tools_wright) ** -0.25)
    opex_fte = _sample_lognormal_p10_p50_p90(rng, 2.0, 3.0, 4.5, n_mc) * 160_000.0 * fte_scale
    maint_frac = _sample_lognormal_p10_p50_p90(rng, 0.06, 0.08, 0.11, n_mc)

    opex_yr = opex_power + opex_hvac + opex_ph3 + opex_fte + maint_frac * hw_mc
    tco5 = install_mult * hw_mc + cleanroom_capex + HORIZON_YR * opex_yr

    return {
        "bom_hw_nom_usd": bom_hw_nom_usd,
        "wright_multiplier": w_mult,
        "hw_mc_samples": hw_mc,
        "opex_yr_samples": opex_yr,
        "tco5_samples": tco5,
        "tco5_summary_usd": _pct_triplet(tco5),
        "opex_yr_summary_usd": _pct_triplet(opex_yr),
    }


def _wafer_batch_chip_economics(
    tco5_samples: np.ndarray,
    net_reg_day: float,
    spec: WaferTechSpec,
    t_swap_hr: float,
    rng: np.random.Generator,
    use_dense: bool = True,
    s56_serial_overhead_hr: float = 0.0,
) -> dict[str, Any]:
    """Compute Amdahl batch kinematics and full MC chip/register cost for one (machine, wafer) pair."""
    reg_per_wafer = spec.dense_reg_per_wafer if use_dense else spec.standard_reg_per_wafer
    chips_per_wafer = reg_per_wafer / 10_000.0
    t_active_hr = (reg_per_wafer / net_reg_day) * 24.0
    t_total_hr = t_active_hr + t_swap_hr + s56_serial_overhead_hr
    avail_hr_yr = 24.0 * DAYS_YR * FAB_UPTIME
    wafers_yr = avail_hr_yr / t_total_hr
    wafers_5yr = wafers_yr * HORIZON_YR
    chips_5yr = wafers_5yr * chips_per_wafer
    reg_5yr = wafers_5yr * reg_per_wafer

    # Deterministic nominal wafer price (for clean P50 machine vs wafer decomposition)
    mach_per_chip_samples = tco5_samples / chips_5yr
    wafer_floor_chip = spec.price_p50_usd / chips_per_wafer
    tot_chip_nom_wafer = mach_per_chip_samples + wafer_floor_chip

    # Full stochastic wafer price MC
    wafer_price_mc = _sample_lognormal_p10_p50_p90(
        rng, spec.price_p10_usd, spec.price_p50_usd, spec.price_p90_usd, len(tco5_samples)
    )
    tot_chip_stoch_wafer = mach_per_chip_samples + (wafer_price_mc / chips_per_wafer)
    tot_reg_stoch = tot_chip_stoch_wafer / 10_000.0

    mach_p50 = float(np.median(mach_per_chip_samples))
    tot_nom_p50 = float(np.median(tot_chip_nom_wafer))

    return {
        "wafer_code": spec.code,
        "wafer_label": spec.label,
        "diameter_mm": spec.diameter_mm,
        "epi_thickness_nm": spec.epi_thickness_nm,
        "reg_per_wafer": reg_per_wafer,
        "chips_10k_per_wafer": chips_per_wafer,
        "t_active_hr": t_active_hr,
        "t_swap_hr": t_swap_hr,
        "s56_serial_overhead_hr": s56_serial_overhead_hr,
        "t_total_hr": t_total_hr,
        "active_duty_fraction": t_active_hr / t_total_hr,
        "wafers_per_yr": wafers_yr,
        "chips_10k_per_yr": wafers_yr * chips_per_wafer,
        "reg_5yr": reg_5yr,
        "machine_usd_per_chip_10k_p50": mach_p50,
        "wafer_floor_usd_per_chip_10k": wafer_floor_chip,
        "total_usd_per_chip_10k_nom_wafer_p50": tot_nom_p50,
        "wafer_share_of_chip_cost": wafer_floor_chip / tot_nom_p50,
        "machine_share_of_chip_cost": mach_p50 / tot_nom_p50,
        "usd_per_chip_10k_stoch_wafer": _pct_triplet(tot_chip_stoch_wafer),
        "usd_per_register_stoch_wafer": _pct_triplet(tot_reg_stoch),
        "usd_per_register_nom_wafer_p50": tot_nom_p50 / 10_000.0,
    }


def evaluate_v5_wafer_economics(
    bom_v5_m3: float = V5_M3_HW_NOM_USD,
    bom_v3_m3: float = V3_M3_HW_NOM_USD,
    bath_yield: float = DEFAULT_BATH_YIELD,
    t_swap_dense_hr: float = 1.0,
    t_swap_standard_hr: float = 8.0,
    v5_shot_cycle_s: float = 0.015,
    v5_bayesian_speedup: float = 1000.0 / EXP140_BOED_MEAN_TIME_MS,  # Exp140 Q16.16 41.62 ms -> 24.03x (write-limited!)
    w3_300mm_tool_adder_usd: float = 0.0,
    n_tools_wright: int = 1,
    wright_b: float = 0.85,
    n_mc: int = 20_000,
    seed: int = 2026141,
    cx4_reduction_threshold: float = 0.40,
) -> dict[str, Any]:
    """Evaluate W1/W2/W3 wafer-fab economics under M3 v5.0 vs v3.0 and score Exp134 CX4 closure.

    Args:
        bom_v5_m3: Nominal M3 v5.0 hardware BOM in USD (default $5,247,800).
        bom_v3_m3: Nominal M3 v3.0 baseline hardware BOM in USD (default $4,189,600).
        bath_yield: Mod B nuclear-bath yield (default 0.51 canonical KL; Exp136 f*=1% 0.5275).
        t_swap_dense_hr: Cold-shuttle wafer swap time in hours (default 1.0 h, Exp134 anchor).
        t_swap_standard_hr: Standard DR wafer swap time in hours (default 8.0 h).
        v5_shot_cycle_s: Write shot cycle in seconds (0.015 s -> 7.61x; 0.010 s -> 11.42x).
        v5_bayesian_speedup: Effective BOED-FPGA speedup (24.03x -> write-limited ceiling).
        w3_300mm_tool_adder_usd: Optional 300 mm S3/S5 chuck+load-lock BOM adder applied to W3 only (default $0).
        n_tools_wright: Fleet size for Wright learning curve (1 for N=1 commercial fab tool).
        wright_b: Wright learning rate (default 0.85).
        n_mc: Monte Carlo sample count (default 20,000; <0.05 s runtime).
        seed: Deterministic RNG seed.
        cx4_reduction_threshold: Required total chip-cost reduction fraction (default >=40%).

    Returns:
        Structured dict with W1/W2/W3 breakdowns, CX4 closure verdicts (both vs v3.0-W1
        baseline and same-wafer apples-to-apples), pipelined vs serial S5.6 check,
        and W3 300 mm stage/load-lock capex sensitivity.
    """
    tp_v3 = compute_throughput_reg_day(
        bayesian_speedup=1.0,
        shot_cycle_s=0.015,
        bath_yield=bath_yield,
        detector_eta=DETECTOR_ETA,
        flash_survival=1.0,
    )
    tp_v5_15ms = compute_throughput_reg_day(
        bayesian_speedup=v5_bayesian_speedup,
        shot_cycle_s=v5_shot_cycle_s,
        bath_yield=bath_yield,
        detector_eta=DETECTOR_ETA,
        flash_survival=FLASH_SURVIVAL_V5,
    )
    tp_v5_10ms = compute_throughput_reg_day(
        bayesian_speedup=v5_bayesian_speedup,
        shot_cycle_s=0.010,
        bath_yield=bath_yield,
        detector_eta=DETECTOR_ETA,
        flash_survival=FLASH_SURVIVAL_V5,
    )

    tco_v3 = simulate_fab_tco5_no_wafer(
        bom_hw_nom_usd=bom_v3_m3,
        hw_mc_p50_ratio=HW_MC_P50_RATIO_V3,
        n_tools_wright=n_tools_wright,
        wright_b=wright_b,
        n_mc=n_mc,
        seed=seed,
    )
    tco_v5 = simulate_fab_tco5_no_wafer(
        bom_hw_nom_usd=bom_v5_m3,
        hw_mc_p50_ratio=HW_MC_P50_RATIO_V5,
        n_tools_wright=n_tools_wright,
        wright_b=wright_b,
        n_mc=n_mc,
        seed=seed + 1,
    )
    tco_v5_w3 = (
        tco_v5
        if w3_300mm_tool_adder_usd == 0.0
        else simulate_fab_tco5_no_wafer(
            bom_hw_nom_usd=bom_v5_m3 + w3_300mm_tool_adder_usd,
            hw_mc_p50_ratio=HW_MC_P50_RATIO_V5,
            n_tools_wright=n_tools_wright,
            wright_b=wright_b,
            n_mc=n_mc,
            seed=seed + 2,
        )
    )
    tco_v5_w3_sens350k = simulate_fab_tco5_no_wafer(
        bom_hw_nom_usd=bom_v5_m3 + W3_300MM_STAGE_LOCK_ADDER_NOM_USD,
        hw_mc_p50_ratio=HW_MC_P50_RATIO_V5,
        n_tools_wright=n_tools_wright,
        wright_b=wright_b,
        n_mc=n_mc,
        seed=seed + 3,
    )

    rng_w = np.random.default_rng(seed + 10)
    scenarios_out: dict[str, Any] = {}

    # Compute v3.0-W1 baseline first (canonical Exp134 reference)
    v3_w1_dense = _wafer_batch_chip_economics(
        tco_v3["tco5_samples"], tp_v3["net_reg_day"], WAFER_SCENARIOS["W1"], t_swap_dense_hr, rng_w, use_dense=True
    )
    ref_v3_w1_chip_p50 = v3_w1_dense["total_usd_per_chip_10k_nom_wafer_p50"]

    for code, spec in WAFER_SCENARIOS.items():
        tco_v5_active = tco_v5_w3 if code == "W3" else tco_v5
        v3_dense = (
            v3_w1_dense
            if code == "W1"
            else _wafer_batch_chip_economics(
                tco_v3["tco5_samples"], tp_v3["net_reg_day"], spec, t_swap_dense_hr, rng_w, use_dense=True
            )
        )
        v5_dense_15ms = _wafer_batch_chip_economics(
            tco_v5_active["tco5_samples"], tp_v5_15ms["net_reg_day"], spec, t_swap_dense_hr, rng_w, use_dense=True
        )
        v5_dense_10ms = _wafer_batch_chip_economics(
            tco_v5_active["tco5_samples"], tp_v5_10ms["net_reg_day"], spec, t_swap_dense_hr, rng_w, use_dense=True
        )
        # Non-pipelined S5.6 Route C serial overhead sensitivity (+28.33 min = 0.4722 hr/wafer, Exp139)
        v5_dense_15ms_serial_s56 = _wafer_batch_chip_economics(
            tco_v5_active["tco5_samples"],
            tp_v5_15ms["net_reg_day"],
            spec,
            t_swap_dense_hr,
            rng_w,
            use_dense=True,
            s56_serial_overhead_hr=28.33 / 60.0,
        )
        v5_std_8h = _wafer_batch_chip_economics(
            tco_v5_active["tco5_samples"], tp_v5_15ms["net_reg_day"], spec, t_swap_standard_hr, rng_w, use_dense=False
        )

        c_v3_same = v3_dense["total_usd_per_chip_10k_nom_wafer_p50"]
        c_v5_15 = v5_dense_15ms["total_usd_per_chip_10k_nom_wafer_p50"]
        c_v5_10 = v5_dense_10ms["total_usd_per_chip_10k_nom_wafer_p50"]
        m_v3_same = v3_dense["machine_usd_per_chip_10k_p50"]
        m_v5_15 = v5_dense_15ms["machine_usd_per_chip_10k_p50"]

        red_vs_v3_w1_15ms = 1.0 - (c_v5_15 / ref_v3_w1_chip_p50)
        red_vs_v3_w1_10ms = 1.0 - (c_v5_10 / ref_v3_w1_chip_p50)
        red_same_wafer_15ms = 1.0 - (c_v5_15 / c_v3_same)
        red_same_wafer_10ms = 1.0 - (c_v5_10 / c_v3_same)
        mach_red_15ms = 1.0 - (m_v5_15 / m_v3_same)

        scenarios_out[code] = {
            "wafer_spec": {
                "code": spec.code,
                "label": spec.label,
                "diameter_mm": spec.diameter_mm,
                "epi_thickness_nm": spec.epi_thickness_nm,
                "area_factor_vs_200mm": spec.area_factor_vs_200mm,
                "price_p10_p50_p90_usd": [spec.price_p10_usd, spec.price_p50_usd, spec.price_p90_usd],
                "dense_chips_10k_per_wafer": spec.dense_chips_10k,
                "wafer_floor_per_chip_10k_usd": spec.wafer_floor_per_chip_10k_usd,
                "epistemic_tag": spec.epistemic_tag,
            },
            "v3_0_dense_1h": v3_dense,
            "v5_0_dense_1h_15ms": v5_dense_15ms,
            "v5_0_dense_1h_10ms": v5_dense_10ms,
            "v5_0_dense_1h_15ms_serial_s56": v5_dense_15ms_serial_s56,
            "v5_0_standard_8h_15ms": v5_std_8h,
            "reductions": {
                "vs_v3_W1_baseline_15ms_frac": red_vs_v3_w1_15ms,
                "vs_v3_W1_baseline_10ms_frac": red_vs_v3_w1_10ms,
                "same_wafer_v3_to_v5_15ms_frac": red_same_wafer_15ms,
                "same_wafer_v3_to_v5_10ms_frac": red_same_wafer_10ms,
                "machine_component_reduction_15ms_frac": mach_red_15ms,
                "cx4_ge_40pct_vs_v3_W1_pass": bool(red_vs_v3_w1_15ms >= cx4_reduction_threshold),
                "cx4_ge_40pct_same_wafer_pass": bool(red_same_wafer_15ms >= cx4_reduction_threshold),
                "cx4_ge_50pct_vs_v3_W1_pass": bool(red_vs_v3_w1_15ms >= 0.50),
            },
        }

    w3_sens350k_eval = _wafer_batch_chip_economics(
        tco_v5_w3_sens350k["tco5_samples"],
        tp_v5_15ms["net_reg_day"],
        WAFER_SCENARIOS["W3"],
        t_swap_dense_hr,
        rng_w,
        use_dense=True,
    )
    w3_sens350k_chip = w3_sens350k_eval["total_usd_per_chip_10k_nom_wafer_p50"]

    cx4_summary = {
        "threshold_frac": cx4_reduction_threshold,
        "v3_W1_reference_chip_10k_usd": ref_v3_w1_chip_p50,
        "W1_v5_15ms_chip_10k_usd": scenarios_out["W1"]["v5_0_dense_1h_15ms"]["total_usd_per_chip_10k_nom_wafer_p50"],
        "W1_cx4_pass": scenarios_out["W1"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"],
        "W2_v5_15ms_chip_10k_usd": scenarios_out["W2"]["v5_0_dense_1h_15ms"]["total_usd_per_chip_10k_nom_wafer_p50"],
        "W2_reduction_vs_v3_W1_frac": scenarios_out["W2"]["reductions"]["vs_v3_W1_baseline_15ms_frac"],
        "W2_reduction_same_wafer_frac": scenarios_out["W2"]["reductions"]["same_wafer_v3_to_v5_15ms_frac"],
        "W2_cx4_pass_vs_v3_W1": scenarios_out["W2"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"],
        "W2_cx4_pass_same_wafer": scenarios_out["W2"]["reductions"]["cx4_ge_40pct_same_wafer_pass"],
        "W3_v5_15ms_chip_10k_usd": scenarios_out["W3"]["v5_0_dense_1h_15ms"]["total_usd_per_chip_10k_nom_wafer_p50"],
        "W3_reduction_vs_v3_W1_frac": scenarios_out["W3"]["reductions"]["vs_v3_W1_baseline_15ms_frac"],
        "W3_reduction_same_wafer_frac": scenarios_out["W3"]["reductions"]["same_wafer_v3_to_v5_15ms_frac"],
        "W3_cx4_pass_vs_v3_W1": scenarios_out["W3"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"],
        "W3_cx4_pass_same_wafer": scenarios_out["W3"]["reductions"]["cx4_ge_40pct_same_wafer_pass"],
        "W3_with_350k_300mm_stage_adder_chip_10k_usd": w3_sens350k_chip,
        "W3_with_350k_300mm_stage_adder_red_vs_v3_W1_frac": 1.0 - (w3_sens350k_chip / ref_v3_w1_chip_p50),
        "W2_zero_hardware_mod_note": "W2 (200 mm thin 30 nm 28Si-on-SOI) fits existing M3 v5.0 200 mm CAD/BOM with $0 tool modification.",
        "W3_300mm_cad_note": "W3 (300 mm) requires S3 stage & S5 load-lock scaling (~$350k {Varsayim}); impact is <+$0.005/chip.",
        "cx4_wall_broken_in_W2_and_W3": bool(
            (not scenarios_out["W1"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"])
            and scenarios_out["W2"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"]
            and scenarios_out["W3"]["reductions"]["cx4_ge_40pct_vs_v3_W1_pass"]
        ),
    }

    return {
        "no_lab_measurement": NO_LAB_MEASUREMENT,
        "no_supplier_quotes": NO_SUPPLIER_QUOTES,
        "epistemic_tags": list(EPISTEMIC_TAGS),
        "assumptions": {
            "bom_v3_m3_usd": bom_v3_m3,
            "bom_v5_m3_usd": bom_v5_m3,
            "bath_yield": bath_yield,
            "t_swap_dense_hr": t_swap_dense_hr,
            "t_swap_standard_hr": t_swap_standard_hr,
            "v5_shot_cycle_s": v5_shot_cycle_s,
            "n_tools_wright": n_tools_wright,
            "wright_b": wright_b,
            "n_mc": n_mc,
            "seed": seed,
        },
        "throughput": {
            "v3_0": tp_v3,
            "v5_0_15ms": tp_v5_15ms,
            "v5_0_10ms": tp_v5_10ms,
            "effective_speedup_15ms_vs_v3": tp_v5_15ms["net_reg_day"] / tp_v3["net_reg_day"],
            "effective_speedup_10ms_vs_v3": tp_v5_10ms["net_reg_day"] / tp_v3["net_reg_day"],
        },
        "fab_tco5_no_wafer": {
            "v3_0_usd": tco_v3["tco5_summary_usd"],
            "v5_0_usd": tco_v5["tco5_summary_usd"],
            "v5_vs_v3_tco_delta_frac": (
                tco_v5["tco5_summary_usd"]["p50"] / tco_v3["tco5_summary_usd"]["p50"] - 1.0
            ),
        },
        "scenarios": scenarios_out,
        "cx4_closure": cx4_summary,
    }


def _extract_exp138_targets(exp138_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Flexibly parse Exp138 surface-code scaling targets for eps_L in {1e-6, 1e-9, 1e-12}.

    Accepts either:
    - Nested dicts or lists under 'target_logical_error_rates', 'scaling_targets',
      'logical_targets', 'targets', or 'machine_scaling'
    - Direct keys '1e-6'/'1e-9'/'1e-12', float keys 1e-6/1e-9/1e-12, or 'eps_1e-6'/...
    - Or a single {'Lambda': ..., 'd0': ..., 'eps0': ..., 'N_cand': ...} scaling law.
    """
    container: Any = exp138_summary
    for k in (
        "target_logical_error_rates",
        "scaling_targets",
        "logical_targets",
        "targets",
        "machine_scaling",
    ):
        val = exp138_summary.get(k)
        if isinstance(val, (dict, list)):
            container = val
            break

    # Normalize list-of-dicts format into a keyed dict
    if isinstance(container, list):
        by_eps: dict[str, dict[str, Any]] = {}
        for item in container:
            if not isinstance(item, dict):
                continue
            eps_raw = item.get("target_eps_L", item.get("eps_L", item.get("target")))
            if eps_raw is not None:
                try:
                    ef = float(eps_raw)
                    for tk, tv in (("1e-6", 1e-6), ("1e-9", 1e-9), ("1e-12", 1e-12)):
                        if abs(math.log10(ef) - math.log10(tv)) < 0.05:
                            by_eps[tk] = item
                except (ValueError, TypeError):
                    by_eps[str(eps_raw)] = item
        container = by_eps

    default_n_cand = int(
        exp138_summary.get("N_cand", exp138_summary.get("n_cand", exp138_summary.get("n_candidates", 6)))
    )
    target_map = {"1e-6": 1e-6, "1e-9": 1e-9, "1e-12": 1e-12}
    parsed: dict[str, dict[str, Any]] = {}

    for tkey, eps_val in target_map.items():
        entry = None
        if isinstance(container, dict):
            for cand_k in (tkey, eps_val, f"eps_{tkey}", f"eps_L_{tkey}", f"target_{tkey}"):
                if isinstance(container.get(cand_k), dict):
                    entry = container[cand_k]
                    break

        if entry is not None:
            d_star = int(entry.get("d_star", entry.get("d", entry.get("distance", 11))))
            n_cand = int(entry.get("N_cand", entry.get("n_cand", entry.get("n_candidates", default_n_cand))))
            n_active = int(
                entry.get(
                    "N_active",
                    entry.get(
                        "n_active",
                        entry.get("N_data_plus_ancilla", 2 * d_star * d_star - 1),
                    ),
                )
            )
            n_phys = int(
                entry.get(
                    "N_phys_per_logical",
                    entry.get(
                        "n_phys_per_logical",
                        entry.get("N_phys", entry.get("n_phys_total", n_active * n_cand)),
                    ),
                )
            )
            parsed[tkey] = {
                "target_eps_L": eps_val,
                "d_star": d_star,
                "N_cand": n_cand,
                "N_active": n_active,
                "N_phys_per_logical": n_phys,
            }
        elif "Lambda" in exp138_summary and float(exp138_summary["Lambda"]) > 1.0:
            # Analytic exponential suppression law: eps_L(d) = eps0 * Lambda^(-(d - d0)/2)
            lam = float(exp138_summary["Lambda"])
            d0 = int(exp138_summary.get("d0", 5))
            eps0 = float(exp138_summary.get("eps0", 1e-3))
            d_star = d0
            while eps0 * (lam ** (-(d_star - d0) / 2.0)) > eps_val and d_star < 99:
                d_star += 2
            n_active = 2 * d_star * d_star - 1
            parsed[tkey] = {
                "target_eps_L": eps_val,
                "d_star": d_star,
                "N_cand": default_n_cand,
                "N_active": n_active,
                "N_phys_per_logical": n_active * default_n_cand,
            }

    if not parsed:
        raise ValueError(
            "exp138_summary must contain target distance entries for '1e-6'/'1e-9'/'1e-12' "
            "or a valid 'Lambda' > 1.0 error-suppression scaling dict."
        )
    return parsed


def evaluate_logical_qubit_economics(
    exp138_summary: dict[str, Any],
    exp140_cryo_cap: int = EXP140_CRYO_CELL_CAP_THERMAL,
    bom_v5_m3: float = V5_M3_HW_NOM_USD,
    n_logical_system: int = 100,
    wright_b: float = 0.85,
    wafer_econ: dict[str, Any] | None = None,
    n_mc: int = 20_000,
    seed: int = 2026142,
) -> dict[str, Any]:
    """Compute true $/logical_qubit across eps_L in {1e-6, 1e-9, 1e-12} for both:
      (A) Silicon wafer fabrication ($/logical_qubit_fab on W1/W2/W3), and
      (B) Full deployed N_L=100 fault-tolerant runtime system (multi-cryostat Exp140
          thermal ceiling + Cryo-MUX S6.5 TWPA/HEMT/RFSoC + 5-yr cryo/facility OPEX
          + wafer fabrication, with amortized vs dedicated M3 v5.0 fab tool).

    Args:
        exp138_summary: Parsed Exp138 surface-code scaling dict (d*, N_active, N_phys_per_logical).
        exp140_cryo_cap: Hard thermal cell ceiling per LD400/PT420 cryostat (default 2,887, Exp140).
        bom_v5_m3: Nominal M3 v5.0 hardware BOM in USD (default $5,247,800).
        n_logical_system: Target FT quantum computer size in logical qubits (default 100).
        wright_b: Wright learning-curve slope for multi-cryostat/multi-module deployment (default 0.85).
        wafer_econ: Optional precomputed output from evaluate_v5_wafer_economics().
        n_mc: MC sample count for runtime system uncertainty bands.
        seed: Deterministic RNG seed.
    """
    targets = _extract_exp138_targets(exp138_summary)
    if wafer_econ is None:
        wafer_econ = evaluate_v5_wafer_economics(bom_v5_m3=bom_v5_m3, n_mc=n_mc, seed=seed - 1)

    fab_tco5_v5_p50 = wafer_econ["fab_tco5_no_wafer"]["v5_0_usd"]["p50"]
    rng = np.random.default_rng(seed)

    # Pre-sample runtime hardware uncertainty factors (common random numbers across targets)
    cryo_hw_samples = _sample_lognormal_p10_p50_p90(rng, *RUNTIME_CRYOSTAT_BAY_HW_USD, n_mc)
    mux_1024_samples = _sample_lognormal_p10_p50_p90(rng, *EXP140_S65_MUX_1024_USD, n_mc)
    install_samples = _sample_lognormal_p10_p50_p90(rng, 1.20, 1.35, 1.55, n_mc)
    maint_samples = _sample_lognormal_p10_p50_p90(rng, 0.06, 0.08, 0.11, n_mc)
    # Per-cryostat annual facility OPEX (25 kW PT420/GHS/rack power + cryo-lab HVAC + 0.5 FTE/fridge)
    cryo_opex_base_yr = (
        rng.uniform(20.0, 30.0, size=n_mc) * 8760.0 * _sample_lognormal_p10_p50_p90(rng, 0.09, 0.14, 0.22, n_mc)
        + _sample_lognormal_p10_p50_p90(rng, 30_000.0, 45_000.0, 70_000.0, n_mc)
        + _sample_lognormal_p10_p50_p90(rng, 0.35, 0.50, 0.75, n_mc) * 160_000.0
    )

    by_target: dict[str, Any] = {}
    for tkey, tinfo in targets.items():
        d_star = tinfo["d_star"]
        n_active = tinfo["N_active"]
        n_cand = tinfo["N_cand"]
        n_phys_logical = tinfo["N_phys_per_logical"]

        # 1. Single-cryostat capacity & modular scaling for N_L=100 logical qubits
        logical_per_cryo_thermal = exp140_cryo_cap // n_active
        logical_per_cryo_nominal_1024 = EXP140_CRYO_CELL_NOMINAL_MODULE // n_active
        single_patch_fits_one_cryostat = bool(n_active <= exp140_cryo_cap)
        total_active_cells = n_logical_system * n_active
        total_placed_candidates = n_logical_system * n_phys_logical

        n_cryo_thermal_min = math.ceil(total_active_cells / exp140_cryo_cap)
        n_cryo_unsplit = (
            math.ceil(n_logical_system / logical_per_cryo_thermal)
            if logical_per_cryo_thermal >= 1
            else n_cryo_thermal_min
        )
        # Physically faithful deployment: keep whole surface-code patches inside one 20 mK cryostat whenever possible
        n_cryo_deploy = n_cryo_unsplit
        n_cryo_nominal_1024 = math.ceil(total_active_cells / EXP140_CRYO_CELL_NOMINAL_MODULE)
        # Discrete 32-cell Exp140 S6.5 readout chains (1024-cell module = 32 chains)
        n_ro_chains = math.ceil(total_active_cells / EXP140_RO_MUX_RATIO)
        n_mux_1024_modules = n_ro_chains / 32.0

        # 2. Silicon fab manufacturing cost per logical qubit across W1 / W2 / W3 (N=1 fab tool)
        # Uses Exp134 conservative convention (N_phys_per_logical * usd_per_certified_register);
        # raw candidate-site rate (scaled by eff_yield) is also reported for zero double-counting ambiguity.
        eff_yield_v5 = wafer_econ["throughput"]["v5_0_15ms"]["eff_yield"]
        fab_cost_by_wafer: dict[str, Any] = {}
        for wcode in ("W1", "W2", "W3"):
            sc_15 = wafer_econ["scenarios"][wcode]["v5_0_dense_1h_15ms"]
            usd_per_reg_p50 = sc_15["usd_per_register_nom_wafer_p50"]
            usd_per_cand_raw_p50 = usd_per_reg_p50 * eff_yield_v5
            fab_per_logical = n_phys_logical * usd_per_reg_p50
            fab_per_logical_raw_cand = n_phys_logical * usd_per_cand_raw_p50
            fab_per_active_bare = n_active * usd_per_reg_p50
            fab_cost_by_wafer[wcode] = {
                "usd_per_logical_fab_p50": fab_per_logical,
                "usd_per_logical_fab_raw_candidate_p50": fab_per_logical_raw_cand,
                "usd_per_logical_bare_active_p50": fab_per_active_bare,
                "system_100L_chip_fab_usd_p50": fab_per_logical * n_logical_system * 5.0,  # 5x spare/qualification dies
            }

        # 3. Deployed 100-Logical-Qubit Runtime System CAPEX & 5-Year TCO (unsplit-patch cryostat packing)
        w_cryo = wright_multiplier(n_cryo_deploy, wright_b)
        w_mux = wright_multiplier(max(1.0, n_mux_1024_modules), wright_b)

        # Unlearned (N=1 unit pricing) & Wright-learned (b=85% volume pricing)
        sys_cryo_hw_n1 = n_cryo_deploy * cryo_hw_samples
        sys_mux_hw_n1 = n_mux_1024_modules * mux_1024_samples
        sys_hw_n1 = sys_cryo_hw_n1 + sys_mux_hw_n1

        sys_cryo_hw_wr = n_cryo_deploy * cryo_hw_samples * w_cryo
        sys_mux_hw_wr = n_mux_1024_modules * mux_1024_samples * w_mux
        sys_hw_wr = sys_cryo_hw_wr + sys_mux_hw_wr

        # Wafer + fab chip allocation (using W3 300 mm thin SOI with 5x die qualification spare)
        chips_w3_usd = fab_cost_by_wafer["W3"]["system_100L_chip_fab_usd_p50"]

        # Runtime facility cleanroom bay ($1.2M base + $0.35M per cryostat bay)
        runtime_facility_capex = 1_200_000.0 + 350_000.0 * n_cryo_deploy
        sys_opex_5yr_wr = HORIZON_YR * (n_cryo_deploy * cryo_opex_base_yr + maint_samples * sys_hw_wr)
        sys_opex_5yr_n1 = HORIZON_YR * (n_cryo_deploy * cryo_opex_base_yr + maint_samples * sys_hw_n1)

        # Total 5-yr TCO (amortized fab tool vs dedicated full M3 v5.0 fab tool)
        sys_tco5_amort_wr = install_samples * sys_hw_wr + runtime_facility_capex + sys_opex_5yr_wr + chips_w3_usd
        sys_tco5_amort_n1 = install_samples * sys_hw_n1 + runtime_facility_capex + sys_opex_5yr_n1 + chips_w3_usd
        sys_tco5_ded_fab_wr = sys_tco5_amort_wr + fab_tco5_v5_p50

        by_target[tkey] = {
            "target_eps_L": tinfo["target_eps_L"],
            "d_star": d_star,
            "N_cand": n_cand,
            "N_active_per_logical": n_active,
            "N_phys_per_logical": n_phys_logical,
            "single_cryostat_capacity": {
                "exp140_thermal_cap_cells": exp140_cryo_cap,
                "single_patch_fits_one_cryostat": single_patch_fits_one_cryostat,
                "logical_qubits_per_cryostat_thermal": logical_per_cryo_thermal,
                "logical_qubits_per_1024_module": logical_per_cryo_nominal_1024,
            },
            "system_scale": {
                "n_logical_qubits": n_logical_system,
                "total_active_cells": total_active_cells,
                "total_placed_candidates": total_placed_candidates,
                "n_cryostats_deployed_unsplit": n_cryo_deploy,
                "n_cryostats_thermal_min": n_cryo_thermal_min,
                "n_cryostats_nominal_1024": n_cryo_nominal_1024,
                "n_ro_chains_32cell": n_ro_chains,
                "n_mux_1024_modules": round(n_mux_1024_modules, 4),
                "wright_mult_cryo": w_cryo,
                "wright_mult_mux": w_mux,
            },
            "fab_manufacturing_by_wafer": fab_cost_by_wafer,
            "deployed_100L_system_usd": {
                "runtime_hw_capex_n1": _pct_triplet(sys_hw_n1),
                "runtime_hw_capex_wright": _pct_triplet(sys_hw_wr),
                "system_5yr_tco_amortized_fab_n1": _pct_triplet(sys_tco5_amort_n1),
                "system_5yr_tco_amortized_fab_wright": _pct_triplet(sys_tco5_amort_wr),
                "system_5yr_tco_dedicated_fab_wright": _pct_triplet(sys_tco5_ded_fab_wr),
            },
            "usd_per_logical_qubit_deployed": {
                "amortized_fab_n1_p50": float(np.median(sys_tco5_amort_n1) / n_logical_system),
                "amortized_fab_wright": _pct_triplet(sys_tco5_amort_wr / n_logical_system),
                "dedicated_fab_wright": _pct_triplet(sys_tco5_ded_fab_wr / n_logical_system),
                "fab_chip_share_of_deployed_tco": chips_w3_usd / float(np.median(sys_tco5_amort_wr)),
            },
        }

    return {
        "no_lab_measurement": NO_LAB_MEASUREMENT,
        "no_supplier_quotes": NO_SUPPLIER_QUOTES,
        "epistemic_tags": list(EPISTEMIC_TAGS),
        "assumptions": {
            "exp140_cryo_cap_cells": exp140_cryo_cap,
            "bom_v5_m3_usd": bom_v5_m3,
            "fab_tco5_v5_p50_usd": fab_tco5_v5_p50,
            "n_logical_system": n_logical_system,
            "wright_b": wright_b,
            "runtime_cryostat_bay_hw_p10_p50_p90_usd": list(RUNTIME_CRYOSTAT_BAY_HW_USD),
            "s65_mux_1024_p10_p50_p90_usd": list(EXP140_S65_MUX_1024_USD),
        },
        "by_target_eps_L": by_target,
    }


def _smoke_test() -> None:
    """Self-contained verification & console readout for standalone execution."""
    w_res = evaluate_v5_wafer_economics(bom_v5_m3=V5_M3_HW_NOM_USD)
    cx4 = w_res["cx4_closure"]

    # Validate W1/W2/W3 invariants
    assert w_res["no_lab_measurement"] is True
    assert w_res["no_supplier_quotes"] is True
    assert abs(w_res["throughput"]["effective_speedup_15ms_vs_v3"] - 7.6190476 * FLASH_SURVIVAL_V5) < 0.01
    assert not cx4["W1_cx4_pass"], "W1 thick epi must reproduce Exp134 CX4 silicon floor wall"
    assert cx4["W2_cx4_pass_vs_v3_W1"] and cx4["W2_cx4_pass_same_wafer"], "W2 thin SOI must break CX4"
    assert cx4["W3_cx4_pass_vs_v3_W1"] and cx4["W3_cx4_pass_same_wafer"], "W3 300mm thin SOI must break CX4"
    assert cx4["cx4_wall_broken_in_W2_and_W3"] is True
    assert (
        cx4["W3_v5_15ms_chip_10k_usd"]
        < cx4["W2_v5_15ms_chip_10k_usd"]
        < cx4["W1_v5_15ms_chip_10k_usd"]
        < cx4["v3_W1_reference_chip_10k_usd"]
    )

    # Representative Exp138 placeholder scaling test (d=7/11/15 for 1e-6/1e-9/1e-12, N_cand=6)
    mock_exp138 = {
        "target_logical_error_rates": {
            "1e-6": {"d_star": 7, "N_cand": 6, "N_active": 97, "N_phys_per_logical": 582},
            "1e-9": {"d_star": 11, "N_cand": 6, "N_active": 241, "N_phys_per_logical": 1446},
            "1e-12": {"d_star": 15, "N_cand": 6, "N_active": 449, "N_phys_per_logical": 2694},
        }
    }
    l_res = evaluate_logical_qubit_economics(mock_exp138, wafer_econ=w_res)
    bt = l_res["by_target_eps_L"]
    assert (
        bt["1e-6"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
        < bt["1e-9"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
        < bt["1e-12"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
    )
    # Also verify Lambda-scaling parser fallback & list-of-dicts parser
    l_res_lam = evaluate_logical_qubit_economics({"Lambda": 3.5, "d0": 5, "eps0": 1e-4, "N_cand": 6}, wafer_econ=w_res)
    assert set(l_res_lam["by_target_eps_L"].keys()) == {"1e-6", "1e-9", "1e-12"}
    l_res_list = evaluate_logical_qubit_economics(
        {
            "targets": [
                {"target_eps_L": 1e-6, "d_star": 7, "N_cand": 6},
                {"target_eps_L": 1e-9, "d_star": 11, "N_cand": 6},
                {"target_eps_L": 1e-12, "d_star": 15, "N_cand": 6},
            ]
        },
        wafer_econ=w_res,
    )
    assert l_res_list["by_target_eps_L"]["1e-9"]["N_active_per_logical"] == 241
    # Verify W3 300 mm +$350k stage/load-lock sensitivity still breaks CX4 cleanly
    assert cx4["W3_with_350k_300mm_stage_adder_red_vs_v3_W1_frac"] > 0.80

    print("=== wafer_econ141.py SMOKE TEST PASSED ===")
    print(f"Fab 5y TCO (ex-wafer, N=1): v3.0=${w_res['fab_tco5_no_wafer']['v3_0_usd']['p50']/1e6:.2f}M -> v5.0=${w_res['fab_tco5_no_wafer']['v5_0_usd']['p50']/1e6:.2f}M")
    print(f"Throughput speedup (v5 15ms/10ms vs v3): {w_res['throughput']['effective_speedup_15ms_vs_v3']:.2f}x / {w_res['throughput']['effective_speedup_10ms_vs_v3']:.2f}x")
    print(f"v3.0 W1 Ref (10k-chip): ${cx4['v3_W1_reference_chip_10k_usd']:.3f}")
    for code in ("W1", "W2", "W3"):
        sc = w_res["scenarios"][code]
        s15 = sc["v5_0_dense_1h_15ms"]
        red = sc["reductions"]
        print(
            f"  {code} ({sc['wafer_spec']['diameter_mm']}mm, ${sc['wafer_spec']['price_p10_p50_p90_usd'][1]:,.0f}): "
            f"chip=${s15['total_usd_per_chip_10k_nom_wafer_p50']:.3f} "
            f"(mach=${s15['machine_usd_per_chip_10k_p50']:.3f}, waf=${s15['wafer_floor_usd_per_chip_10k']:.3f} [{s15['wafer_share_of_chip_cost']*100:.1f}%]) | "
            f"vs v3-W1: -{red['vs_v3_W1_baseline_15ms_frac']*100:.1f}% | same-wafer: -{red['same_wafer_v3_to_v5_15ms_frac']*100:.1f}% | CX4={red['cx4_ge_40pct_vs_v3_W1_pass']}"
        )
    print(
        f"  W3 +$350k 300mm S3/S5 adder sensitivity: chip=${cx4['W3_with_350k_300mm_stage_adder_chip_10k_usd']:.3f} "
        f"(vs v3-W1: -{cx4['W3_with_350k_300mm_stage_adder_red_vs_v3_W1_frac']*100:.1f}%)"
    )
    print("Mock Exp138 (d=7/11/15, N_cand=6, 100 Logical Qubits):")
    for tk in ("1e-6", "1e-9", "1e-12"):
        r = bt[tk]
        print(
            f"  eps_L={tk:5s} (d*={r['d_star']:2d}, N_act={r['N_active_per_logical']:3d}, N_phys={r['N_phys_per_logical']:4d}): "
            f"cryos={r['system_scale']['n_cryostats_deployed_unsplit']:2d} (minCell={r['system_scale']['n_cryostats_thermal_min']:2d}, nom1024={r['system_scale']['n_cryostats_nominal_1024']:2d}) | "
            f"fab(W3)=${r['fab_manufacturing_by_wafer']['W3']['usd_per_logical_fab_p50']:.4f}/L | "
            f"100L TCO(amort,Wr)=${r['deployed_100L_system_usd']['system_5yr_tco_amortized_fab_wright']['p50']/1e6:.1f}M "
            f"(${r['usd_per_logical_qubit_deployed']['amortized_fab_wright']['p50']/1e3:.1f}k/L; dedFab=${r['usd_per_logical_qubit_deployed']['dedicated_fab_wright']['p50']/1e3:.1f}k/L)"
        )
    # Verify JSON-serializability
    json.dumps({"wafer_econ": w_res, "logical_econ": l_res})
    print("JSON serialization check: OK")


if __name__ == "__main__":
    _smoke_test()
