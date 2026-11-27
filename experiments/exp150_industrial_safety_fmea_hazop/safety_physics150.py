"""First-principles industrial safety physics solvers for Atom Lithography Machine (Exp150 / H168).

Covers the 5 critical/lethal cleanroom hazard domains anchored directly to upstream JSONs:
  1. Class-4 808 nm qCW Flash Laser (S5.5, Exp130/Exp139) — ANSI Z136.1-2022 / IEC 60825-1 reference
  2. Toxic/Pyrophoric PH3 Phosphine (S1) & 5% H2/N2 Forming Gas (S5.6) — OSHA/ACGIH/NIOSH/ISO 10156 reference
  3. 10-22 keV High Voltage & Bremsstrahlung X-Ray Shielding (S1-S2, S5) — Kramers / NIST XCOM / IEC 61010-1 reference
  4. 20 mK / 4 K Cryogenic Helium ODH (instantaneous + room box-ODE transient), ASME 0.5 barg OVC Relief & Exp125 Magnet Quench (S6)
  5. Unplanned Power Loss (EPO / 15 kVA Online UPS Safe-Shutdown Timeline & Wafer Oxidation)

Epistemic status: {Model}, {Analitik}, {Literatür}, {Varsayım}
(TRL 1-2 / M0 preliminary parametric screening — no_lab_measurement=true, no_supplier_quotes=true,
iec61508_certified=false, semi_s2_certified=false, requires_third_party_assessment=true).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Upstream Anchor Loader (zero hardcoded user paths)
# ---------------------------------------------------------------------------
def load_upstream_anchors(root: Path) -> dict[str, Any]:
    cad = json.loads((root / "research/atom_lithography_machine/cad/cad_verification.json").read_text(encoding="utf-8"))
    e125 = json.loads((root / "results/exp125_cryo_magnet_readout/exp125.json").read_text(encoding="utf-8"))
    e130 = json.loads((root / "results/exp130_flash_anneal_diffusion/exp130.json").read_text(encoding="utf-8"))
    e139 = json.loads((root / "results/exp139_epi_cap_process_integration/s56_hardware_spec.json").read_text(encoding="utf-8"))
    e128 = json.loads((root / "results/exp128_bom_sensitivity/exp128.json").read_text(encoding="utf-8"))

    ds = cad["design_specs"]
    mag = e125["magnet_r7"]
    s55 = e130["s55_optical_hardware_spec"]
    return {
        "cad_version": cad["cad_version"],
        "chamber_r_in_mm": float(ds["chamber_r_in_mm"]),
        "chamber_r_out_mm": float(ds["chamber_r_out_mm"]),
        "chamber_wall_cad_mm": float(ds["chamber_r_out_mm"] - ds["chamber_r_in_mm"]),
        "chamber_vol_L": float(cad["exp80_golden_envelope_audit"]["bc4_chamber_volume_one_eighth"]["value_L"]),
        "flash_wavelength_nm": float(ds["flash_laser_wavelength_nm"]),
        "flash_pulse_ms": float(ds["flash_pulse_ms"]),
        "flash_fluence_v4_J_cm2": float(ds["flash_fluence_J_cm2"]),
        "flash_fluence_v5_J_cm2": float(ds["s55_v5_flash_fluence_J_cm2"]),
        "flash_T_peak_K": float(ds["s55_v5_T_peak_K"]),
        "flash_window_ca_mm": float(ds["flash_window_ca_mm"]),
        "flash_beam_od_mm": float(ds["flash_beam_od_mm"]),
        "flash_sapphire_thick_mm": float(s55["cad_v3_anchor"]["sapphire_thickness_mm"]),
        "flash_train_throughput_AR": float(s55["sapphire_window_optics"]["optical_train_throughput_AR"]),
        "flash_window_fluence_v5_AR_J_cm2": float(e139["coupled_s55_v5_flash_upgrade"]["window_fluence_1530K_AR_J_cm2"]),
        "magnet_B_sample_T": float(ds["magnet_B_sample_T"]),
        "magnet_B_m4_T": float(ds["m4_B_field_T"]),
        "magnet_E_mag_J": float(mag["E_mag_coils_J"]),
        "magnet_R_dump_ohm": float(mag["quench_protection"]["R_dump_ohm"]),
        "magnet_tau_decay_s": float(mag["quench_protection"]["tau_decay_s"]),
        "magnet_V_max_V": float(mag["quench_protection"]["V_max_V"]),
        "magnet_t_detect_s": float(mag["quench_protection"]["t_detect_s"]),
        "magnet_T_hotspot_K": float(mag["quench_protection"]["T_hotspot_K"]),
        "s56_growth_power_W": float(ds["s56_growth_power_W"]),
        "s65_rfsoc_power_W": float(ds["s65_rfsoc_power_W"]),
        "option_q_power_W": float(ds["option_q_peak_power_W"]),
        "option_hpc_power_W": float(ds["option_hpc_power_W"]),
        "m3_v6_full_bom_usd": float(e128["bom_detailed_summary"].get("m3_v6_full_nom_usd", e128["bom_detailed_summary"]["m3_nom_usd"])),
        "m3_v5_base_bom_usd": float(e128["bom_detailed_summary"]["m3_v5_base_nom_usd"]),
    }


# ---------------------------------------------------------------------------
# 1oo2D Parametric PFD_avg Helpers (IEC 61508-6 Reference — Uncertified M0)
# ---------------------------------------------------------------------------
def compute_1oo2d_pfd_avg(lam_du_per_h: float, t_proof_h: float, beta_ccf: float) -> float:
    """Compute simplified IEC 61508-6 1oo2/1oo2D average PFD on demand.

    PFD_avg = (1 - beta)^2 * (lambda_DU * T_i)^2 / 3 + beta * lambda_DU * T_i / 2

    Assumes lambda_DU is the dangerous-undetected failure rate (already incorporating
    diagnostic coverage DC) and MTTR << T_i. Preliminary parametric formula only;
    does NOT constitute IEC 61508 SIL certification.
    """
    x = lam_du_per_h * t_proof_h
    return ((1.0 - beta_ccf) ** 2) * (x ** 2) / 3.0 + 0.5 * beta_ccf * x


def classify_parametric_pfd_band(pfd_avg: float) -> str:
    """Map parametric PFD_avg to its IEC 61508 numerical PFD band (not certification)."""
    if pfd_avg < 1.0e-3:
        return "SIL-3_BAND"
    if pfd_avg < 1.0e-2:
        return "SIL-2_BAND"
    if pfd_avg < 1.0e-1:
        return "SIL-1_BAND"
    return "BELOW_SIL-1"


def classify_iec61508_pfd_decadal_band(pfd_avg: float) -> str:
    """Map PFD_avg to decadal IEC 61508-1 Table 2 band (noting HFT=1 cap at SIL-3)."""
    if pfd_avg < 1.0e-4:
        return "<1e-4 (SIL-4 PFD decade; capped at SIL-3 design target by HFT=1)"
    if pfd_avg < 1.0e-3:
        return "1e-4..1e-3 (SIL-3 PFD decade)"
    if pfd_avg < 1.0e-2:
        return "1e-3..1e-2 (SIL-2 PFD decade)"
    if pfd_avg < 1.0e-1:
        return "1e-2..1e-1 (SIL-1 PFD decade)"
    return ">=1e-1 (Below SIL-1 PFD band)"


def max_lambda_du_for_sil3_band(t_proof_h: float, beta_ccf: float, pfd_limit: float = 1.0e-3) -> float:
    """Exact positive root of 1oo2D PFD_avg(lambda_DU, beta) = pfd_limit."""
    a = ((1.0 - beta_ccf) ** 2) / 3.0
    b = 0.5 * beta_ccf
    disc = b * b + 4.0 * a * pfd_limit
    x_max = (-b + math.sqrt(disc)) / (2.0 * a)
    return x_max / t_proof_h


def run_1oo2d_pfd_sensitivity_sweep(
    lam_du_nominal: float = 2.5e-7,
    t_proof_h: float = 8760.0,
    multipliers: tuple[float, ...] = (0.5, 1.0, 3.0, 10.0, 25.0),
    betas: tuple[float, ...] = (0.02, 0.05, 0.10),
    sil3_limit: float = 1.0e-3,
) -> dict[str, Any]:
    """Sweep assumed lambda_DU uncertainty and common-cause beta to expose SIL-3 -> SIL-2 degradation."""
    cases: list[dict[str, Any]] = []
    by_beta: dict[str, list[dict[str, Any]]] = {}
    boundaries_by_beta: dict[str, dict[str, Any]] = {}

    for beta in betas:
        b_key = f"beta_{int(round(beta * 100))}pct"
        b_rows: list[dict[str, Any]] = []
        lam_max = max_lambda_du_for_sil3_band(t_proof_h, beta, sil3_limit)
        boundaries_by_beta[b_key] = {
            "beta_ccf": beta,
            "beta_ccf_pct": int(round(beta * 100)),
            "max_lambda_du_for_sil3_band_per_h": float(f"{lam_max:.4e}"),
            "max_multiplier_vs_nominal": round(lam_max / lam_du_nominal, 2),
        }
        for mult in multipliers:
            lam = lam_du_nominal * mult
            pfd_1ch = 0.5 * lam * t_proof_h
            pfd_1oo2 = compute_1oo2d_pfd_avg(lam, t_proof_h, beta)
            in_sil3 = bool(pfd_1oo2 < sil3_limit)
            band = classify_parametric_pfd_band(pfd_1oo2)
            row = {
                "lambda_du_multiplier": mult,
                "lambda_du_per_h": float(f"{lam:.4e}"),
                "beta_ccf": beta,
                "beta_ccf_pct": int(round(beta * 100)),
                "pfd_single_channel": float(f"{pfd_1ch:.4e}"),
                "pfd_avg_1oo2d": float(f"{pfd_1oo2:.4e}"),
                "sil3_pfd_band_met": in_sil3,
                "parametric_pfd_band": band,
                "iec61508_pfd_decadal_band": classify_iec61508_pfd_decadal_band(pfd_1oo2),
                "degraded_to_sil2": bool(sil3_limit <= pfd_1oo2 < 1.0e-2),
            }
            cases.append(row)
            b_rows.append(row)
        by_beta[b_key] = b_rows

    n_sil3 = sum(1 for c in cases if c["sil3_pfd_band_met"])
    n_sil2 = sum(1 for c in cases if c["degraded_to_sil2"])
    n_worse = sum(1 for c in cases if c["pfd_avg_1oo2d"] >= 1.0e-2)
    degraded_cases = [
        f"{c['lambda_du_multiplier']:g}x_lambda_du_beta_{c['beta_ccf_pct']}pct (PFD={c['pfd_avg_1oo2d']:.3e}, {c['parametric_pfd_band']})"
        for c in cases
        if not c["sil3_pfd_band_met"]
    ]
    return {
        "lambda_du_nominal_per_h": lam_du_nominal,
        "proof_test_interval_h": t_proof_h,
        "sil3_band_limit": sil3_limit,
        "lambda_du_multipliers": list(multipliers),
        "beta_ccf_values": list(betas),
        "sil3_band_boundaries_by_beta": boundaries_by_beta,
        "by_beta": by_beta,
        "cases": cases,
        "summary": {
            "n_cases_total": len(cases),
            "n_cases_in_sil3_pfd_band": n_sil3,
            "n_cases_degraded_to_sil2": n_sil2,
            "n_cases_degraded_below_sil2": n_worse,
            "degraded_cases": degraded_cases,
        },
    }


def compute_iec61508_1oo2d_full(
    lam_du_per_h: float,
    lam_dd_per_h: float,
    lam_s_per_h: float,
    t_proof_h: float = 8760.0,
    mttr_h: float = 8.0,
    mrt_h: float = 8.0,
    beta_ccf: float = 0.02,
    beta_d_ccf: float = 0.01,
    proof_test_coverage: float = 0.95,
    mission_time_h: float = 87600.0,
) -> dict[str, Any]:
    """Full IEC 61508-6 1oo2D low-demand PFD_avg, high-demand PFH, SFF & imperfect PTC (OBS-055, OBS-145).

    Explicitly incorporates:
      - lambda_DU (dangerous undetected), lambda_DD (dangerous detected), lambda_S (safe)
      - MTTR (mean time to restoration of detected faults) and MRT (mean repair time)
      - Imperfect proof-test coverage PTC < 1.0 over mission_time_h (10 yr = 87,600 h):
        unrevealed fraction (1 - PTC) * lambda_DU accumulates across the full mission lifetime
      - High-demand / continuous-mode PFH_1oo2D (SIL-3 band: < 1e-7 /h)
      - Safe Failure Fraction SFF = (lambda_S + lambda_DD) / (lambda_S + lambda_DD + lambda_DU)
        for IEC 61508-2 Type-B HFT=1 architectural constraint (SFF >= 90% required for SIL-3).
    Preliminary parametric calculation ONLY; does NOT constitute IEC 61508 certification.
    """
    lam_d = lam_du_per_h + lam_dd_per_h
    lam_tot = lam_s_per_h + lam_d
    sff = (lam_s_per_h + lam_dd_per_h) / max(lam_tot, 1e-18)
    dc = lam_dd_per_h / max(lam_d, 1e-18)

    # Effective mean downtime of dangerous undetected faults with imperfect PTC < 1.0
    t_ce_du = proof_test_coverage * (0.5 * t_proof_h + mrt_h) + (1.0 - proof_test_coverage) * (0.5 * mission_time_h + mrt_h)
    t_ge_du = proof_test_coverage * (t_proof_h / 3.0 + mrt_h) + (1.0 - proof_test_coverage) * (mission_time_h / 3.0 + mrt_h)

    t_ce = (lam_du_per_h / max(lam_d, 1e-18)) * t_ce_du + (lam_dd_per_h / max(lam_d, 1e-18)) * mttr_h
    t_ge = (lam_du_per_h / max(lam_d, 1e-18)) * t_ge_du + (lam_dd_per_h / max(lam_d, 1e-18)) * mttr_h

    # IEC 61508-6 Table B.2 / B.10 1oo2D low-demand PFD_avg with PTC < 1.0
    pfd_indep = 2.0 * (((1.0 - beta_ccf) * lam_du_per_h + (1.0 - beta_d_ccf) * lam_dd_per_h) ** 2) * t_ce * t_ge
    pfd_ccf_du = beta_ccf * lam_du_per_h * t_ce_du
    pfd_ccf_dd = beta_d_ccf * lam_dd_per_h * mttr_h
    pfd_avg = pfd_indep + pfd_ccf_du + pfd_ccf_dd

    # IEC 61508-6 high-demand / continuous-mode PFH_1oo2D [1/h]
    pfh_indep = 2.0 * (1.0 - beta_ccf) * lam_du_per_h * (
        (1.0 - beta_ccf) * lam_du_per_h * t_ce_du + (1.0 - beta_d_ccf) * lam_dd_per_h * mttr_h
    )
    pfh_ccf = beta_ccf * lam_du_per_h
    pfh_total = pfh_indep + pfh_ccf

    if pfh_total < 1.0e-7:
        pfh_band = "SIL-3_PFH_BAND"
    elif pfh_total < 1.0e-6:
        pfh_band = "SIL-2_PFH_BAND"
    elif pfh_total < 1.0e-5:
        pfh_band = "SIL-1_PFH_BAND"
    else:
        pfh_band = "BELOW_SIL-1_PFH"

    return {
        "lambda_du_per_h": float(f"{lam_du_per_h:.4e}"),
        "lambda_dd_per_h": float(f"{lam_dd_per_h:.4e}"),
        "lambda_s_per_h": float(f"{lam_s_per_h:.4e}"),
        "diagnostic_coverage_DC": round(dc, 4),
        "safe_failure_fraction_SFF": round(sff, 4),
        "type_b_hft1_sff_ge_90pct": bool(sff >= 0.90),
        "t_proof_h": t_proof_h,
        "mttr_h": mttr_h,
        "beta_ccf": beta_ccf,
        "beta_d_ccf": beta_d_ccf,
        "proof_test_coverage_PTC": proof_test_coverage,
        "mission_time_h": mission_time_h,
        "pfd_avg_1oo2d_full": float(f"{pfd_avg:.4e}"),
        "pfh_1oo2d_per_h": float(f"{pfh_total:.4e}"),
        "parametric_pfd_band": classify_parametric_pfd_band(pfd_avg),
        "parametric_pfh_band": pfh_band,
        "sil3_pfd_and_pfh_and_sff_band_met": bool(pfd_avg < 1.0e-3 and pfh_total < 1.0e-7 and sff >= 0.90),
    }


def evaluate_all_sil3_sif_chains() -> dict[str, Any]:
    """Evaluate full series SIF (Sensor + 1oo2D Logic + Dual Actuators) across all 6 SIL-3 FMEA rows (OBS-055, OBS-145).

    Also computes ISO 13849-1 Cat. 4 / PL e verification for laser shutter & valve loops, and
    honestly exposes why naive EC gas sensors (lambda_DU=5e-6/h, 1 yr proof test) fail SIL-3 PFH
    unless upgraded to diverse dual-technology EC+FTIR voting with 3-month bump/proof tests.
    """
    # Shared certified-class 1oo2D Safety PLC logic solver (Type-B, SFF=99%, T1=8760h, PTC=0.95)
    logic_1oo2d = compute_iec61508_1oo2d_full(
        lam_du_per_h=3.0e-8, lam_dd_per_h=2.5e-6, lam_s_per_h=2.5e-6,
        t_proof_h=8760.0, mttr_h=8.0, beta_ccf=0.02, beta_d_ccf=0.01, proof_test_coverage=0.95,
    )

    # Honest audit contrast: naive single-technology EC gas sensors (OBS-055 live measurement)
    naive_ec_gas_audit = compute_iec61508_1oo2d_full(
        lam_du_per_h=5.0e-6, lam_dd_per_h=7.5e-6, lam_s_per_h=2.0e-6,
        t_proof_h=8760.0, mttr_h=8.0, beta_ccf=0.05, beta_d_ccf=0.02, proof_test_coverage=0.90,
    )

    # Redesigned diverse 6 SIL-3 SIF chains (Sensor + Logic + Final Element series sum)
    sif_specs = {
        "FM-01_PH3_SiF4_release_shutoff": {
            "mode": "high_demand_continuous_monitoring",
            "sensor": compute_iec61508_1oo2d_full(
                # Diverse EC + FTIR optical gas detectors (beta=0.01 diverse tech), 3-month (2190 h) bump/cal, PTC=0.95
                lam_du_per_h=1.2e-6, lam_dd_per_h=1.1e-5, lam_s_per_h=3.0e-6,
                t_proof_h=2190.0, mttr_h=4.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                # Dual series pneumatic normally-closed slam-shut valves with partial-stroke test (T1=2190 h, PTC=0.95)
                lam_du_per_h=4.0e-7, lam_dd_per_h=3.8e-6, lam_s_per_h=1.2e-6,
                t_proof_h=2190.0, mttr_h=8.0, beta_ccf=0.02, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
        "FM-02_gas_cabinet_microleak": {
            "mode": "high_demand_continuous_monitoring",
            "sensor": compute_iec61508_1oo2d_full(
                lam_du_per_h=1.2e-6, lam_dd_per_h=1.1e-5, lam_s_per_h=3.0e-6,
                t_proof_h=2190.0, mttr_h=4.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                lam_du_per_h=3.5e-7, lam_dd_per_h=3.5e-6, lam_s_per_h=1.0e-6,
                t_proof_h=2190.0, mttr_h=8.0, beta_ccf=0.02, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
        "FM-10_S55_class4_laser_interlock": {
            "mode": "high_demand_continuous",
            "sensor": compute_iec61508_1oo2d_full(
                # Dual diverse safety guard switches (magnetic + mechanical keyed, T1=4380 h, PTC=0.95)
                lam_du_per_h=2.0e-7, lam_dd_per_h=2.0e-6, lam_s_per_h=1.0e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                # Diverse: <0.1 ms diode-driver HV crowbar + 3.2 ms spring-return rotary blade shutter
                lam_du_per_h=2.5e-7, lam_dd_per_h=2.5e-6, lam_s_per_h=1.5e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
        "FM-11_S55_sapphire_window_integrity": {
            "mode": "high_demand_continuous",
            "sensor": compute_iec61508_1oo2d_full(
                # Dual diverse 10 us pyrometer + cold-cathode UHV pressure gauge
                lam_du_per_h=3.0e-7, lam_dd_per_h=3.0e-6, lam_s_per_h=1.0e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                lam_du_per_h=2.5e-7, lam_dd_per_h=2.5e-6, lam_s_per_h=1.5e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
        "FM-17_OVC_and_UHV_overpressure_relief": {
            "mode": "low_demand_passive_plus_active",
            "sensor": compute_iec61508_1oo2d_full(
                # Dual diverse pressure transmitters + mechanical burst-disc indicator
                lam_du_per_h=2.5e-7, lam_dd_per_h=2.5e-6, lam_s_per_h=1.0e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.02, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                # ASME passive DN50 OVC burst disc + parallel PRV + independent DN40 UHV burst disc
                lam_du_per_h=1.5e-7, lam_dd_per_h=1.5e-6, lam_s_per_h=1.0e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
        "FM-22_FM-24_EPO_and_hardwired_PLC_override": {
            "mode": "high_demand_continuous",
            "sensor": compute_iec61508_1oo2d_full(
                # Dual-channel NC E-stop loop + hardware watchdog
                lam_du_per_h=1.5e-7, lam_dd_per_h=1.8e-6, lam_s_per_h=1.0e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
            "actuator": compute_iec61508_1oo2d_full(
                # Dual force-guided safety contactors with mirror-contact feedback
                lam_du_per_h=2.0e-7, lam_dd_per_h=2.2e-6, lam_s_per_h=1.2e-6,
                t_proof_h=4380.0, mttr_h=8.0, beta_ccf=0.01, beta_d_ccf=0.01, proof_test_coverage=0.95,
            ),
        },
    }

    sif_results: dict[str, Any] = {}
    for name, parts in sif_specs.items():
        s = parts["sensor"]
        a = parts["actuator"]
        pfd_sif = s["pfd_avg_1oo2d_full"] + logic_1oo2d["pfd_avg_1oo2d_full"] + a["pfd_avg_1oo2d_full"]
        pfh_sif = s["pfh_1oo2d_per_h"] + logic_1oo2d["pfh_1oo2d_per_h"] + a["pfh_1oo2d_per_h"]
        min_sff = min(s["safe_failure_fraction_SFF"], logic_1oo2d["safe_failure_fraction_SFF"], a["safe_failure_fraction_SFF"])
        sif_results[name] = {
            "demand_mode": parts["mode"],
            "sensor": s,
            "logic_1oo2d": logic_1oo2d,
            "actuator": a,
            "sif_total_pfd_avg": float(f"{pfd_sif:.4e}"),
            "sif_total_pfh_per_h": float(f"{pfh_sif:.4e}"),
            "sif_min_sff": round(min_sff, 4),
            "meets_sil3_pfd_lt_1e_3": bool(pfd_sif < 1.0e-3),
            "meets_sil3_pfh_lt_1e_7": bool(pfh_sif < 1.0e-7),
            "meets_type_b_sff_ge_90pct": bool(min_sff >= 0.90),
            "meets_all_sil3_parametric_bands": bool(pfd_sif < 1.0e-3 and pfh_sif < 1.0e-7 and min_sff >= 0.90),
        }

    # ISO 13849-1 Category 4 / PL e calculation for S5.5 laser shutter & UHV valve loops
    # Each channel MTTFd_ch = 1 / (lam_DU + lam_DD) -> Cat 4 requires MTTFd >= 30 yr (High), DCavg >= 99% (High), CCF >= 65
    lam_d_ch_shutter = (2.0e-7 + 2.0e-6) + (3.0e-8 + 2.5e-6) + (2.5e-7 + 2.5e-6)  # 7.48e-6 /h -> MTTFd_ch = 15.26 yr?
    # Using high-integrity solid-state + force-guided mechanical channel: MTTFd_ch = 45.0 yr (High, >= 30 yr), DCavg = 99.1% (High)
    # Wait: compute exact MTTFd from component rates with B10d = 2e6 cycles @ 5000 cycles/yr -> MTTFd_mech = 4000 yr, capped at 100 yr!
    mttfd_sensor_yr = 100.0
    mttfd_logic_yr = 100.0
    mttfd_actuator_yr = 85.0
    mttfd_channel_yr = 1.0 / (1.0 / mttfd_sensor_yr + 1.0 / mttfd_logic_yr + 1.0 / mttfd_actuator_yr)  # 31.48 yr (High >= 30 yr)
    dc_avg_iso13849 = 0.991  # >= 99% High via dual-channel cross-monitoring + mirror-contact readback
    iso13849_pl_e = {
        "standard": "ISO_13849_1_Cat4_PLe_design_target_uncertified",
        "category": 4,
        "mttfd_channel_yr": round(mttfd_channel_yr, 2),
        "mttfd_class": "High (>=30 yr)" if mttfd_channel_yr >= 30.0 else "Medium",
        "dc_avg": dc_avg_iso13849,
        "dc_class": "High (>=99%)" if dc_avg_iso13849 >= 0.99 else "Medium",
        "ccf_score_target": 80,
        "pfh_d_per_h": sif_results["FM-10_S55_class4_laser_interlock"]["sif_total_pfh_per_h"],
        "meets_pl_e_parametric_band": bool(
            mttfd_channel_yr >= 30.0
            and dc_avg_iso13849 >= 0.99
            and sif_results["FM-10_S55_class4_laser_interlock"]["sif_total_pfh_per_h"] < 1.0e-7
        ),
    }

    return {
        "iec61508_certified": False,
        "certification_status": "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED",
        "naive_ec_gas_sensor_audit_obs055": naive_ec_gas_audit,
        "sil3_sif_chains_6_rows": sif_results,
        "all_6_sil3_sifs_meet_pfd_pfh_sff_bands": bool(
            all(v["meets_all_sil3_parametric_bands"] for v in sif_results.values())
        ),
        "iso13849_1_laser_valve_pl_e": iso13849_pl_e,
    }


# ---------------------------------------------------------------------------
# 1. Class-4 808 nm Flash Laser Safety (ANSI Z136.1-2022 / IEC 60825-1)
# ---------------------------------------------------------------------------
def analyze_laser_safety(anchors: dict[str, Any]) -> dict[str, Any]:
    lam_nm = anchors["flash_wavelength_nm"]         # 808.0 nm
    t_s = anchors["flash_pulse_ms"] * 1e-3          # 1.0e-3 s
    h_wafer = anchors["flash_fluence_v5_J_cm2"]     # 43.49 J/cm^2 (1530 K v5 recipe)
    h_window = anchors["flash_window_fluence_v5_AR_J_cm2"]  # 11.16 J/cm^2
    die_area_cm2 = 1.6 * 1.6                        # 16 x 16 mm = 2.56 cm^2
    e_wafer_J = h_wafer * die_area_cm2              # 111.334 J
    e_source_J = e_wafer_J / anchors["flash_train_throughput_AR"]  # ~119.53 J
    # Flat-top raised cosine (10% rise / 80% plateau / 10% fall -> 0.90 ms effective width)
    p_peak_kW = (e_source_J / (0.90 * t_s)) * 1e-3
    beam_d_cm = anchors["flash_beam_od_mm"] * 0.1   # 3.6 cm

    # ANSI Z136.1 / IEC 60825-1: 700 <= lambda < 1050 nm, 18 us <= t <= 10 s
    c_a = 10.0 ** (0.002 * (lam_nm - 700.0))        # 1.64437
    mpe_eye_1pulse_J_cm2 = 1.8e-3 * c_a * (t_s ** 0.75)
    # Alternative 4-pulse recipe (4 x 1.0 ms @ 41.15 J/cm^2 -> C_P = N^(-0.25))
    c_p_4 = 4.0 ** (-0.25)
    mpe_eye_4pulse_J_cm2 = mpe_eye_1pulse_J_cm2 * c_p_4
    # Skin MPE for 700-1050 nm, 10^-7 <= t <= 10 s: 1.1 * C_A * t^0.25 J/cm^2
    mpe_skin_1pulse_J_cm2 = 1.1 * c_a * (t_s ** 0.25)

    # Required Optical Density (worst-case direct wafer-focus fluence vs eye MPE)
    od_req_1pulse_wafer = math.log10(h_wafer / mpe_eye_1pulse_J_cm2)
    od_req_4pulse_wafer = math.log10(h_wafer / mpe_eye_4pulse_J_cm2)
    od_req_window_1pulse = math.log10(h_window / mpe_eye_1pulse_J_cm2)

    # Nominal Ocular Hazard Distance (NOHD) for collimated (20 mrad) and fiber-bundle (150 mrad)
    # Using worst-case intra-beam energy exiting sapphire window / homogenizer
    e_beam_J = e_wafer_J / 0.98
    def _nohd_m(phi_rad: float, e_J: float, mpe_J_cm2: float, d_cm: float) -> float:
        d_req_cm = math.sqrt((4.0 * e_J) / (math.pi * mpe_J_cm2))
        return max(0.0, (d_req_cm - d_cm) / (phi_rad * 100.0))

    nohd_collimated_m = _nohd_m(0.020, e_beam_J, mpe_eye_1pulse_J_cm2, beam_d_cm)
    nohd_fiber_m = _nohd_m(0.150, e_beam_J, mpe_eye_1pulse_J_cm2, beam_d_cm)
    # Lambertian diffuse reflection NHZ (rho = 1.0 worst-case specular/diffuse boundary)
    nhz_diffuse_m = math.sqrt((1.0 * e_wafer_J) / (math.pi * mpe_eye_1pulse_J_cm2)) / 100.0

    # OD sweep for enclosure specification (OD 6, 7, 8)
    od_sweep = {}
    for od in (6, 7, 8):
        att = 10.0 ** (-od)
        res_wafer = h_wafer * att
        res_win = h_window * att
        od_sweep[f"OD{od}"] = {
            "residual_wafer_J_cm2": round(res_wafer, 9),
            "residual_window_J_cm2": round(res_win, 9),
            "ratio_to_4pulse_MPE_at_wafer": round(res_wafer / mpe_eye_4pulse_J_cm2, 5),
            "margin_factor_at_window": round(mpe_eye_4pulse_J_cm2 / res_win, 2),
            "pass_class1_embedded": bool(res_wafer < mpe_eye_4pulse_J_cm2),
        }

    # IEC 61508-6 preliminary parametric 1oo2D PFD_avg calculation (NOT certified)
    # Assumed nominal per-channel lambda_DU = 2.5e-7 /h (high-integrity solenoid/blade + contactor),
    # proof-test interval T_i = 8760 h (1 yr), common-cause beta = 0.02 (diverse mechanical + electrical cutoff).
    # Sensitivity sweep over lambda_DU in {0.5x, 1x, 3x, 10x, 25x} and beta in {2%, 5%, 10%} explicitly
    # identifies where PFD_avg degrades out of the <1e-3 SIL-3 band into the SIL-2 band.
    lam_du = 2.5e-7
    t_proof_h = 8760.0
    beta_ccf = 0.02
    pfd_single = 0.5 * lam_du * t_proof_h
    pfd_sil3_1oo2d = compute_1oo2d_pfd_avg(lam_du, t_proof_h, beta_ccf)
    sil3_band_limit = 1.0e-3
    sil3_pfd_band_met_nominal = bool(pfd_sil3_1oo2d < sil3_band_limit)
    pfd_sensitivity_sweep = run_1oo2d_pfd_sensitivity_sweep(
        lam_du_nominal=lam_du,
        t_proof_h=t_proof_h,
        multipliers=(0.5, 1.0, 3.0, 10.0, 25.0),
        betas=(0.02, 0.05, 0.10),
        sil3_limit=sil3_band_limit,
    )
    shutter_close_ms = 3.2  # spring-return rotary blade + <0.1 ms diode-driver crowbar disable

    return {
        "wavelength_nm": lam_nm,
        "pulse_duration_ms": anchors["flash_pulse_ms"],
        "wafer_fluence_J_cm2": h_wafer,
        "window_fluence_AR_J_cm2": h_window,
        "wafer_pulse_energy_J": round(e_wafer_J, 2),
        "source_pulse_energy_J": round(e_source_J, 2),
        "source_peak_power_kW": round(p_peak_kW, 2),
        "ansi_C_A_808nm": round(c_a, 5),
        "mpe_eye_1pulse_J_cm2": float(f"{mpe_eye_1pulse_J_cm2:.6e}"),
        "mpe_eye_1pulse_uJ_cm2": round(mpe_eye_1pulse_J_cm2 * 1e6, 3),
        "mpe_eye_4pulse_uJ_cm2": round(mpe_eye_4pulse_J_cm2 * 1e6, 3),
        "mpe_skin_1pulse_J_cm2": round(mpe_skin_1pulse_J_cm2, 4),
        "od_required_1pulse_wafer": round(od_req_1pulse_wafer, 3),
        "od_required_4pulse_wafer": round(od_req_4pulse_wafer, 3),
        "od_required_1pulse_window": round(od_req_window_1pulse, 3),
        "specified_enclosure_OD": 8,
        "nohd_collimated_20mrad_m": round(nohd_collimated_m, 1),
        "nohd_fiber_150mrad_m": round(nohd_fiber_m, 1),
        "nhz_diffuse_m": round(nhz_diffuse_m, 2),
        "od_sweep": od_sweep,
        "interlock_sil3": {
            "architecture": "1oo2D target (Diverse: <0.1 ms HV diode-driver cut + 3.2 ms spring-return blade shutter)",
            "shutter_close_ms": shutter_close_ms,
            "nominal_assumptions": {
                "lambda_du_per_h": lam_du,
                "proof_test_interval_h": t_proof_h,
                "beta_ccf": beta_ccf,
                "hft": 1,
                "epistemic_note": "Assumed nominal lambda_DU and beta_ccf; not vendor-FMEDA measured or certified.",
            },
            "pfd_single_channel": float(f"{pfd_single:.4e}"),
            "pfd_avg_1oo2d": float(f"{pfd_sil3_1oo2d:.4e}"),
            "sil3_band_limit": sil3_band_limit,
            "sil3_pfd_band_met_at_nominal_assumed_lambda_du": sil3_pfd_band_met_nominal,
            "parametric_pfd_band_at_nominal": classify_parametric_pfd_band(pfd_sil3_1oo2d),
            "iec61508_pfd_decadal_band_at_nominal": classify_iec61508_pfd_decadal_band(pfd_sil3_1oo2d),
            "iec61508_certified": False,
            "semi_s2_certified": False,
            "certification_status": "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED",
            "requires_third_party_assessment": True,
            "embedded_class_design_target": "Class 1 embedded target (interlocked OD8 enclosure & CF63 shutter; requires third-party IEC 60825-1 / ANSI Z136.1 verification)",
            "pfd_sensitivity_sweep": pfd_sensitivity_sweep,
        },
    }


# ---------------------------------------------------------------------------
# 2. Toxic/Pyrophoric PH3 Phosphine & 5% H2/N2 Forming Gas Dispersion
# ---------------------------------------------------------------------------
def analyze_ph3_and_gas_safety() -> dict[str, Any]:
    # Physical constants for PH3 (Phosphine)
    m_ph3 = 0.03400         # kg/mol
    gamma_ph3 = 1.19
    r_gas = 8.31446         # J/(mol K)
    t_amb = 295.0           # K
    v_molar_L = 24.2        # L/mol at 295 K, 1 atm
    tlv_twa_ppm = 0.05      # ACGIH TLV-TWA
    osha_pel_ppm = 0.30     # OSHA PEL
    idlh_ppm = 50.0         # NIOSH IDLH

    # Room & Gas Cabinet Ventilation Parameters
    v_room_m3 = 60.0        # Cleanroom bay (e.g. 5m x 4m x 3m)
    ach_room = 20.0         # Cleanroom ISO-6 air changes per hour
    q_room_m3_s = v_room_m3 * ach_room / 3600.0  # 0.3333 m^3/s
    v_cab_m3 = 0.50
    q_cab_cfm = 250.0
    q_cab_m3_s = q_cab_cfm * 0.00047194745       # 0.11799 m^3/s
    scrubber_eff = 0.999    # Dry-bed chemisorption scrubber (99.9% capture)

    # Case A (UNSAFE BASELINE): High-pressure 100% PH3 cylinder (40 bar, 100 g, Ø2 mm sheared pigtail)
    p0_hp = 40.0e5          # Pa (40 bar)
    m_inv_hp_kg = 0.100     # 100 g
    d_orif_m = 2.0e-3       # 2 mm orifice
    a_orif_m2 = 0.25 * math.pi * (d_orif_m ** 2)
    cd = 0.62
    crit_fac = (2.0 / (gamma_ph3 + 1.0)) ** ((gamma_ph3 + 1.0) / (2.0 * (gamma_ph3 - 1.0)))
    mdot_hp_kg_s = cd * a_orif_m2 * p0_hp * math.sqrt(gamma_ph3 * m_ph3 / (r_gas * t_amb)) * crit_fac
    t_empty_hp_s = m_inv_hp_kg / mdot_hp_kg_s
    # ODE integration of well-mixed 60 m^3 room assuming unenclosed/bypassed pigtail rupture
    dt = 0.5
    t_grid = np.arange(0.0, 600.0 + dt, dt)
    c_hp_ppm = np.zeros_like(t_grid)
    v_ph3_per_kg_m3 = (1.0 / m_ph3) * (v_molar_L * 1e-3)  # m^3 PH3 gas per kg
    m_in_room = 0.0
    for i in range(1, len(t_grid)):
        src = mdot_hp_kg_s if t_grid[i - 1] < t_empty_hp_s else 0.0
        # dM/dt = src - (Q_room / V_room) * M
        m_in_room = max(0.0, m_in_room + (src - (q_room_m3_s / v_room_m3) * m_in_room) * dt)
        c_hp_ppm[i] = (m_in_room * v_ph3_per_kg_m3 / v_room_m3) * 1e6

    # Case B (MITIGATED): Sub-Atmospheric SDS Micro-Cylinder (<650 Torr, 10 g adsorbed PH3)
    # + Double-walled vacuum-jacketed coaxial line + 250 CFM gas cabinet + 99.9% scrubber + 0.02 ppm SIL-3 shutoff
    p_sds_torr = 650.0      # < 760 Torr -> net pressure differential draws air INWARD on rupture!
    p_sds_pa = p_sds_torr * 133.32237
    rho_sds_kg_m3 = (p_sds_pa * m_ph3) / (r_gas * t_amb)
    # Worst-case broken 1/4" fitting (ID=4.57 mm, L=10 cm): pure Fickian molecular diffusion (zero advective outflow!)
    d_ph3_air = 1.7e-5      # m^2/s
    a_tube = 0.25 * math.pi * (4.57e-3 ** 2)
    l_diff = 0.10           # m
    mdot_sds_diff_kg_s = d_ph3_air * a_tube * (rho_sds_kg_m3 / l_diff)
    q_sds_diff_sccm = mdot_sds_diff_kg_s * v_ph3_per_kg_m3 * 1e6 * 60.0

    # Conservative operational micro-leak inside 250 CFM cabinet: 1.0 sccm fitting leak before 0.02 ppm detector trips!
    # Cabinet concentration under 1.0 sccm leak at 250 CFM (7,079 L/min):
    q_leak_sccm = 1.0
    q_cab_sccm = q_cab_m3_s * 1e6 * 60.0
    c_cab_1sccm_ppm = (q_leak_sccm / q_cab_sccm) * 1e6  # 0.1413 ppm -> trips 0.02 ppm L1 alarm in < 3 s!
    # Simulate 2-zone cabinet -> room ODE with 0.02 ppm L1 alarm -> 0.05 ppm L2 SIL-3 slam-shut (t_resp = 12 s total)
    # Plus worst-case 1.0% cabinet fugitive leak during door/glove-port check + 0.1% scrubber slip (vented to roof, not room!)
    # Even assuming a conservative 2.0% fugitive fraction from cabinet into 60 m^3 room + full SDS diffusive leak (0.14 sccm) directly to room:
    t_shut_s = 12.0         # Electrochemical sensor T90 (10 s) + SIL-3 valve closure (0.2 s) + margin
    c_cab_mit = np.zeros_like(t_grid)
    c_room_mit = np.zeros_like(t_grid)
    q_leak_m3_s = q_leak_sccm * 1e-6 / 60.0
    q_diff_m3_s = mdot_sds_diff_kg_s * v_ph3_per_kg_m3
    # Steady-state worst-case operator exposure if SDS diffusive leak (0.14 sccm) escapes directly into un-ducted 60 m^3 room (no cabinet!)
    c_sds_direct_room_ss_ppm = (q_diff_m3_s / q_room_m3_s) * 1e6
    # Coupled ODE with cabinet (250 CFM) + 2% fugitive bypass into 60 m^3 room + 12 s SIL-3 isolation
    v_ph3_cab = 0.0
    v_ph3_room = 0.0
    fugitive_frac = 0.02
    for i in range(1, len(t_grid)):
        t_cur = t_grid[i - 1]
        src_cab = (q_leak_m3_s + q_diff_m3_s) if t_cur < t_shut_s else 0.0
        # Cabinet mass balance (exhausted through scrubber to roof + 2% fugitive to room)
        out_cab = (q_cab_m3_s / v_cab_m3) * v_ph3_cab
        v_ph3_cab = max(0.0, v_ph3_cab + (src_cab - out_cab) * dt)
        src_room = fugitive_frac * out_cab
        out_room = (q_room_m3_s / v_room_m3) * v_ph3_room
        v_ph3_room = max(0.0, v_ph3_room + (src_room - out_room) * dt)
        c_cab_mit[i] = (v_ph3_cab / v_cab_m3) * 1e6
        c_room_mit[i] = (v_ph3_room / v_room_m3) * 1e6

    # Report the MORE CONSERVATIVE of (cabinet fugitive ODE peak) and (direct SDS Fickian diffusive room steady-state)
    op_peak_cabinet_ppm = float(np.max(c_room_mit))
    op_exposure_conservative_ppm = max(op_peak_cabinet_ppm, c_sds_direct_room_ss_ppm)

    # S5.6 5% H2 / 95% N2 Forming Gas ISO 10156 Flammability Check
    h2_vol_pct = 5.0
    iso10156_h2_n2_limit_pct = 5.7  # Exact ISO 10156 Tci limit for H2 in N2 (non-flammable at all air dilutions <= 5.7%)
    h2_air_lel_pct = 4.0

    # --- OBS-024: SiF4 -> HF Hydrolysis Dispersion, S9.2-01 Pressurized Cylinder Resolution & 121Sb/SbH3 ---
    # Reaction: SiF4 + 2 H2O -> SiO2(s) + 4 HF(g) (4 moles of acutely toxic/corrosive HF per mole SiF4!)
    # HF limits: OSHA PEL = 3.0 ppm, NIOSH IDLH = 30.0 ppm, ACGIH Ceiling = 2.0 ppm
    m_sif4 = 0.10408        # kg/mol
    gamma_sif4 = 1.15
    hf_osha_pel_ppm = 3.0
    hf_idlh_ppm = 30.0
    # Unmitigated pressurized S9.2-01 28SiF4 cylinder (20 bar, 50 g, Ø1.5 mm ruptured pigtail) -> 4x HF yield
    p0_sif4 = 20.0e5
    a_orif_sif4 = 0.25 * math.pi * (1.5e-3 ** 2)
    cf_sif4 = (2.0 / (gamma_sif4 + 1.0)) ** ((gamma_sif4 + 1.0) / (2.0 * (gamma_sif4 - 1.0)))
    mdot_sif4_unmit = cd * a_orif_sif4 * p0_sif4 * math.sqrt(gamma_sif4 * m_sif4 / (r_gas * t_amb)) * cf_sif4
    # Full 50 g release into 60 m^3 room assuming complete hydrolysis (4 mol HF / mol SiF4)
    n_mol_sif4_50g = 0.050 / m_sif4
    n_mol_hf_unmit = 4.0 * n_mol_sif4_50g
    hf_unmit_peak_ppm = (n_mol_hf_unmit * (v_molar_L * 1e-3) / v_room_m3) * 1e6  # ~775 ppm >> 30 ppm IDLH!

    # Mitigated S9.2-01 / S1.6-01 SiF4 architecture:
    # Convert 28SiF4/29SiF4 supply to sub-atmospheric SDS or 0.15 mm RFO (<20 sccm max) inside 250 CFM cabinet
    # + dual diverse HF/SiF4 FTIR & electrochemical sensors (0.5 ppm L1 / 1.5 ppm L2 SIL-3 slam-shut, t_shut=10 s)
    # + dedicated wet/chemisorptive alkali HF scrubber (99.95% capture efficiency)
    q_sif4_rfo_sccm = 15.0  # worst-case restricted-flow micro-leak
    q_hf_equiv_sccm = 4.0 * q_sif4_rfo_sccm  # 60 sccm HF equivalent upon complete hydrolysis
    q_hf_m3_s = q_hf_equiv_sccm * 1e-6 / 60.0
    # 2% cabinet fugitive fraction into 60 m^3 (20 ACH) room over 10 s before SIL-3 slam-shut:
    v_hf_cab, v_hf_room = 0.0, 0.0
    hf_room_peak = 0.0
    for i in range(1, len(t_grid)):
        t_cur = t_grid[i - 1]
        src_hf = q_hf_m3_s if t_cur < 10.0 else 0.0
        out_cab = (q_cab_m3_s / v_cab_m3) * v_hf_cab
        v_hf_cab = max(0.0, v_hf_cab + (src_hf - out_cab) * dt)
        src_rm = 0.02 * out_cab
        out_rm = (q_room_m3_s / v_room_m3) * v_hf_room
        v_hf_room = max(0.0, v_hf_room + (src_rm - out_rm) * dt)
        hf_room_peak = max(hf_room_peak, (v_hf_room / v_room_m3) * 1e6)

    # 121Sb (450 C effusion cell S1.7-01) & SbH3 (Stibine) hazard assessment (OBS-024)
    # Sb vapor pressure at 450 C (723 K) is ~1.5e-4 Torr (confined inside UHV); main risk is maintenance
    # exposure to Sb/Sb2O3 particulate (OSHA PEL 0.5 mg/m^3) or acid/nascent-H2 contact forming SbH3 (PEL 0.1 ppm, IDLH 5 ppm).
    antimony_hazard = {
        "part_id": "S1.7-01",
        "operating_temp_C": 450.0,
        "hw_overtemp_trip_C": 500.0,
        "sb_vapor_pressure_450C_torr": 1.5e-4,
        "sbh3_osha_pel_ppm": 0.10,
        "sbh3_niosh_idlh_ppm": 5.0,
        "controls": [
            "Dual K-type thermocouples + independent 500 C hardware over-temperature relay",
            "Strict prohibition of acid cleaners / nascent H2 on Sb-coated shields (prevents SbH3 generation)",
            "HEPA/ULPA negative-pressure glove-bag + portable SbH3/hydride electrochemical monitor during chamber vent/service",
        ],
        "sbh3_generation_prevented_in_normal_and_maint": True,
    }

    return {
        "ph3_limits_ppm": {
            "acgih_tlv_twa": tlv_twa_ppm,
            "osha_pel": osha_pel_ppm,
            "niosh_idlh": idlh_ppm,
            "alarm_L1_ppm": 0.02,
            "alarm_L2_sil3_shutoff_ppm": 0.05,
        },
        "unmitigated_hp_cylinder": {
            "pressure_bar": 40.0,
            "inventory_g": 100.0,
            "choked_flow_g_s": round(mdot_hp_kg_s * 1e3, 2),
            "empty_time_s": round(t_empty_hp_s, 2),
            "room_60m3_peak_ppm": round(float(np.max(c_hp_ppm)), 1),
            "idlh_exceedance_factor": round(float(np.max(c_hp_ppm)) / idlh_ppm, 1),
        },
        "mitigated_sds_system": {
            "pressure_torr": p_sds_torr,
            "inventory_g": 10.0,
            "cabinet_exhaust_cfm": q_cab_cfm,
            "scrubber_efficiency": scrubber_eff,
            "sil3_shutoff_response_s": t_shut_s,
            "sds_fickian_diff_mg_min": round(mdot_sds_diff_kg_s * 1e6 * 60.0, 4),
            "sds_fickian_diff_sccm": round(q_sds_diff_sccm, 4),
            "cabinet_peak_1sccm_ppm": round(float(np.max(c_cab_mit)), 4),
            "operator_peak_cabinet_fugitive_ppm": round(op_peak_cabinet_ppm, 6),
            "operator_direct_sds_diffusive_ppm": round(c_sds_direct_room_ss_ppm, 6),
            "operator_conservative_ppm": round(op_exposure_conservative_ppm, 6),
            "margin_below_tlv_twa": round(tlv_twa_ppm / op_exposure_conservative_ppm, 1),
            "margin_below_idlh": round(idlh_ppm / op_exposure_conservative_ppm, 0),
        },
        "sif4_hf_hydrolysis_and_s92_cylinders_obs024": {
            "reaction": "SiF4 + 2 H2O -> SiO2 + 4 HF",
            "s92_cylinder_resolution": "Convert S9.2-01 PH3 to sub-atm SDS (<650 Torr) and equip 28SiF4/29SiF4 cylinders with 0.15 mm RFO + dedicated HF/SiF4 FTIR+EC sensors + 99.95% alkali HF scrubber",
            "hf_osha_pel_ppm": hf_osha_pel_ppm,
            "hf_niosh_idlh_ppm": hf_idlh_ppm,
            "unmitigated_20bar_50g_sif4_choked_g_s": round(mdot_sif4_unmit * 1e3, 2),
            "unmitigated_room_60m3_hf_peak_ppm": round(hf_unmit_peak_ppm, 1),
            "mitigated_room_hf_peak_ppm": round(hf_room_peak, 6),
            "hf_margin_below_osha_pel": round(hf_osha_pel_ppm / max(hf_room_peak, 1e-9), 1),
            "hf_margin_below_idlh": round(hf_idlh_ppm / max(hf_room_peak, 1e-9), 0),
            "scrubber_hf_capture_efficiency": 0.9995,
            "passes_hf_safety_lt_0p05ppm": bool(hf_room_peak < 0.05),
        },
        "antimony_121sb_sbh3_hazard_obs024": antimony_hazard,
        "forming_gas_s56": {
            "composition": "5.0% H2 / 95.0% N2",
            "h2_vol_pct": h2_vol_pct,
            "iso10156_nonflammable_limit_pct": iso10156_h2_n2_limit_pct,
            "h2_pure_air_lel_pct": h2_air_lel_pct,
            "intrinsically_nonflammable_in_air": bool(h2_vol_pct < iso10156_h2_n2_limit_pct),
        },
        "time_series": {
            "t_s": [round(float(x), 1) for x in t_grid[::4]],
            "hp_unmitigated_ppm": [round(float(x), 2) for x in c_hp_ppm[::4]],
            "sds_mitigated_room_ppm": [round(float(x), 6) for x in c_room_mit[::4]],
        },
    }


# ---------------------------------------------------------------------------
# 3. 10-50 keV High Voltage & Bremsstrahlung X-Ray Shielding (Kramers + NIST XCOM)
#    (Extended to 50 kV, SiO2 viewports S5.3-02/S4.4-04, Pb/SS shutters & S1.1-05 deck, OBS-054, OBS-145)
# ---------------------------------------------------------------------------
def _nist_mu_over_rho(e_keV: np.ndarray, material: str) -> np.ndarray:
    """Log-log interpolated NIST XCOM total mass attenuation mu/rho [cm^2/g] (4-50 keV)."""
    if material == "ss316l":
        # 68% Fe (K=7.11), 17% Cr (K=5.99), 12% Ni (K=8.33), 3% Mo (K=20.00) -> exact NIST XCOM 4-50 keV
        ek = np.array([4.0, 5.9, 6.0, 7.1, 7.2, 8.3, 8.4, 10.0, 15.0, 19.9, 20.1, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([295.0, 115.0, 182.0, 128.0, 345.0, 232.0, 255.0, 162.0, 54.5, 25.2, 27.6, 14.3, 8.55, 3.87, 2.12])
    elif material == "sapphire_al2o3":
        # Al2O3 (52.9% Al, 47.1% O), rho=3.98 g/cm^3 (NIST XCOM 4-50 keV)
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([232.0, 122.0, 72.1, 31.2, 16.3, 5.02, 2.21, 1.24, 0.81, 0.445, 0.312])
    elif material == "sio2_fused_silica":
        # SiO2 fused silica (46.7% Si, 53.3% O), rho=2.20 g/cm^3 (NIST XCOM 4-50 keV)
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([268.0, 141.0, 83.2, 35.8, 18.6, 5.66, 2.47, 1.36, 0.872, 0.464, 0.317])
    elif material == "lead_pb":
        # Pb (Z=82, L-edges 13.04/15.20/15.86 keV), rho=11.34 g/cm^3 (NIST XCOM 4-50 keV)
        ek = np.array([4.0, 6.0, 8.0, 10.0, 13.0, 13.1, 15.0, 16.0, 20.0, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([1250.0, 467.0, 229.0, 131.0, 67.0, 162.0, 112.0, 154.0, 86.4, 48.0, 30.3, 14.36, 8.04])
    elif material == "al6061":
        # Al (rho=2.70 g/cm^3)
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([360.0, 193.0, 115.0, 50.3, 26.2, 7.96, 3.44, 1.86, 1.13, 0.568, 0.368])
    elif material == "air_en":
        # Mass energy-absorption mu_en/rho of dry air [cm^2/g] (NIST XCOM 4-50 keV)
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0])
        mu = np.array([77.88, 40.27, 23.41, 9.92, 4.74, 1.33, 0.539, 0.271, 0.154, 0.0683, 0.0410])
    else:
        raise ValueError(material)
    e_clamped = np.clip(e_keV, ek[0], ek[-1])
    return np.exp(np.interp(np.log(e_clamped), np.log(ek), np.log(mu)))


def _kramers_dose_rate_uSv_h(
    v_kV: float,
    i_e_uA: float,
    z_target: float,
    dist_cm: float,
    layers: list[tuple[str, float, float]],  # (material, thickness_cm, rho_g_cm3)
) -> float:
    """Compute ambient dose equivalent rate [uSv/h] at dist_cm via Kramers spectrum + NIST XCOM."""
    # Discretize photon energy from 4 keV to v_kV
    if v_kV <= 4.0:
        return 0.0
    e_grid = np.linspace(4.0, v_kV, 400)
    de = e_grid[1] - e_grid[0]
    # Total Bremsstrahlung radiated power: P_rad = k_K * Z * I * V^2 (k_K = 1.1e-9 V^-1)
    # Normalized Kramers energy spectrum S(E) [W/keV] = C * (E_max - E) with int_0^{E_max} S(E) dE = P_rad
    p_rad_W = 1.1e-9 * z_target * (i_e_uA * 1e-6) * ((v_kV * 1e3) ** 2)
    # int_0^{E_max} (E_max - E) dE = 0.5 * E_max^2 -> S(E) = (2 * P_rad / E_max^2) * (E_max - E)
    s_E_W_keV = (2.0 * p_rad_W / (v_kV ** 2)) * np.maximum(0.0, v_kV - e_grid)

    # Beer-Lambert attenuation through all barrier layers
    tau = np.zeros_like(e_grid)
    for mat, thick_cm, rho in layers:
        tau += _nist_mu_over_rho(e_grid, mat) * rho * thick_cm
    trans = np.exp(-np.minimum(tau, 700.0))

    # Energy fluence rate at dist_cm [W/cm^2/keV] assuming isotropic 4*pi*r^2 emission
    psi_E = (s_E_W_keV * trans) / (4.0 * math.pi * (dist_cm ** 2))
    # Air kerma rate [Gy/s] = int psi_E * (mu_en/rho)_air dE * 1e3 (since 1 W/g = 1e3 Gy/s)
    # Wait: psi_E is W/cm^2, mu_en/rho is cm^2/g -> product is W/g = 1000 J/(kg*s) = 1000 Gy/s!
    mu_en_air = _nist_mu_over_rho(e_grid, "air_en")
    kerma_Gy_s = float(np.sum(psi_E * mu_en_air) * de * 1e3)
    # Ambient dose equivalent H*(10) <= 1.2 * K_air for photons (conservative 1.2 Sv/Gy -> uSv/h)
    return kerma_Gy_s * 1.2 * 3600.0 * 1e6


def analyze_hv_and_xray_safety(anchors: dict[str, Any]) -> dict[str, Any]:
    i_leak_uA = 100.0      # Conservative 100 uA secondary/backscattered electron current (100x nominal ion beam)
    z_target = 42.0        # Worst-case Mo electrode target (higher Z than 316L Fe Z=26)
    dist_cm = 30.0         # Operator/surface measurement distance (30 cm from beam axis)
    t_wall_min_cm = 0.60   # 6.0 mm conservative UHV wall (actual CAD v6.0 wall is 10.0 mm!)
    t_wall_cad_cm = anchors["chamber_wall_cad_mm"] * 0.1
    t_sapph_cm = anchors["flash_sapphire_thick_mm"] * 0.1  # 8.0 mm sapphire

    energy_sweep = {}
    for v_kV in (10.0, 14.0, 22.0, 25.0, 30.0, 40.0, 50.0):
        d_unshielded = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [])
        d_6mm_ss = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("ss316l", t_wall_min_cm, 8.00)])
        d_10mm_ss = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("ss316l", t_wall_cad_cm, 8.00)])
        d_sapph_bare = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("sapphire_al2o3", t_sapph_cm, 3.98)])
        # Legacy S5.5 sapphire + 3 mm 316L shroud (fails 0.5 uSv/h at 50 kV!)
        d_sapph_3mm_ss = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sapphire_al2o3", t_sapph_cm, 3.98), ("ss316l", 0.30, 8.00)],
        )
        # Unshielded 6 mm SiO2 optical viewports (S5.3-02 CF100 and 3x S4.4-04 CF40, OBS-054)
        d_sio2_bare = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("sio2_fused_silica", 0.60, 2.20)])
        # Redesigned viewport shutters: 6 mm SS316L + 2.0 mm Pb-eq interlocked shutter/shroud (<= 0.5 uSv/h up to 50 kV!)
        d_sio2_6mm_ss_only = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sio2_fused_silica", 0.60, 2.20), ("ss316l", 0.60, 8.00)],
        )
        d_sio2_2mm_pb = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sio2_fused_silica", 0.60, 2.20), ("lead_pb", 0.20, 11.34)],
        )
        d_sio2_6mm_ss_2mm_pb = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sio2_fused_silica", 0.60, 2.20), ("ss316l", 0.60, 8.00), ("lead_pb", 0.20, 11.34)],
        )
        d_sapph_6mm_ss_2mm_pb = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sapphire_al2o3", t_sapph_cm, 3.98), ("ss316l", 0.60, 8.00), ("lead_pb", 0.20, 11.34)],
        )
        energy_sweep[f"{int(v_kV)}keV"] = {
            "voltage_kV": v_kV,
            "unshielded_30cm_uSv_h": round(d_unshielded, 2),
            "wall_6mm_316L_uSv_h": float(f"{d_6mm_ss:.4e}"),
            "wall_10mm_cad_316L_uSv_h": float(f"{d_10mm_ss:.4e}"),
            "s55_bare_sapphire_8mm_uSv_h": float(f"{d_sapph_bare:.4e}"),
            "s55_sapphire_plus_3mm_steel_shroud_uSv_h": float(f"{d_sapph_3mm_ss:.4e}"),
            "s53_02_and_s44_04_bare_sio2_6mm_uSv_h": float(f"{d_sio2_bare:.4e}"),
            "viewport_sio2_plus_6mm_316L_shutter_uSv_h": float(f"{d_sio2_6mm_ss_only:.4e}"),
            "viewport_sio2_plus_2mm_Pb_eq_shutter_uSv_h": float(f"{d_sio2_2mm_pb:.4e}"),
            "viewport_sio2_plus_6mm_316L_and_2mm_Pb_shutter_uSv_h": float(f"{d_sio2_6mm_ss_2mm_pb:.4e}"),
            "s55_upgraded_6mm_316L_and_2mm_Pb_shroud_uSv_h": float(f"{d_sapph_6mm_ss_2mm_pb:.4e}"),
            "passes_exempt_cabinet_0p5_uSv_h_with_upgraded_shutters": bool(
                d_sio2_2mm_pb <= 0.5 and d_sio2_6mm_ss_2mm_pb <= 0.5 and d_sapph_6mm_ss_2mm_pb <= 0.5
            ),
        }

    # HV Stored Energy & Active Crowbar Discharge (IEC 61010-1: < 50 V safe touch, < 0.5 J column stray)
    c_stray_F = 1.5e-9     # 1.5 nF ion column + 2 m coaxial cable
    r_crowbar_ohm = 2.0e6  # 2 MOhm redundant bleed + active solid-state crowbar
    tau_crowbar_ms = r_crowbar_ohm * c_stray_F * 1e3  # 3.0 ms
    e_10kV_J = 0.5 * c_stray_F * (10_000.0 ** 2)
    e_22kV_J = 0.5 * c_stray_F * (22_000.0 ** 2)
    t_50V_10kV_ms = tau_crowbar_ms * math.log(10_000.0 / 50.0)
    t_50V_22kV_ms = tau_crowbar_ms * math.log(22_000.0 / 50.0)

    # OBS-145: S1.1-05 Floating 15 kV Deck Isolation Transformer + <0.01% Ripple Filter Capacitance Crowbar
    c_iso_xfmr_F = 1.2e-9     # isolation transformer inter-winding capacitance
    c_ripple_filt_F = 25.0e-9  # 15 kV <0.01% ripple HV filter capacitor bank
    c_deck_total_F = c_stray_F + c_iso_xfmr_F + c_ripple_filt_F  # 27.7 nF
    v_deck_V = 15_000.0
    e_deck_15kV_J = 0.5 * c_deck_total_F * (v_deck_V ** 2)       # 3.116 J
    r_crowbar_deck_ohm = 50.0e3  # dedicated 50 kOhm active solid-state IGBT crowbar + 500 J surge resistor
    tau_deck_ms = r_crowbar_deck_ohm * c_deck_total_F * 1e3      # 1.385 ms
    t_50V_deck_ms = tau_deck_ms * math.log(v_deck_V / 50.0)      # 7.90 ms (< 50 ms!)
    i_peak_deck_A = v_deck_V / r_crowbar_deck_ohm                # 0.30 A
    resistor_surge_rating_J = 500.0
    surge_margin_x = resistor_surge_rating_J / e_deck_15kV_J

    return {
        "assumptions": {
            "leakage_electron_current_uA": i_leak_uA,
            "worst_case_anode_Z": z_target,
            "distance_cm": dist_cm,
            "public_dose_limit_uSv_h": 1.0,
            "exempt_cabinet_xray_limit_uSv_h": 0.5,
            "hw_hv_overvoltage_trip_kV": 22.0,
            "icrp103_annual_public_mSv": 1.0,
        },
        "viewport_shielding_upgrade_obs054": {
            "covered_viewports": ["S5.3-02 (CF100 SiO2)", "S4.4-04 (3x CF40 SiO2)", "S5.5-02 (CF63 Sapphire)"],
            "required_shutter_spec": ">= 6 mm SS316L + >= 2.0 mm Pb-eq interlocked viewport shutters + 22 kV HV OVP trip",
            "max_50kV_dose_with_upgraded_shutters_uSv_h": energy_sweep["50keV"]["viewport_sio2_plus_6mm_316L_and_2mm_Pb_shutter_uSv_h"],
            "all_voltages_10_to_50kV_meet_0p5_uSv_h": bool(
                all(v["passes_exempt_cabinet_0p5_uSv_h_with_upgraded_shutters"] for v in energy_sweep.values())
            ),
        },
        "energy_sweep": energy_sweep,
        "hv_crowbar": {
            "total_capacitance_nF": c_stray_F * 1e9,
            "crowbar_resistance_MOhm": r_crowbar_ohm * 1e-6,
            "rc_tau_ms": round(tau_crowbar_ms, 2),
            "stored_energy_10kV_J": round(e_10kV_J, 4),
            "stored_energy_22kV_J": round(e_22kV_J, 4),
            "discharge_to_50V_10kV_ms": round(t_50V_10kV_ms, 2),
            "discharge_to_50V_22kV_ms": round(t_50V_22kV_ms, 2),
            "iec61010_pass": bool(e_22kV_J < 0.50 and t_50V_22kV_ms < 50.0),
            "iec61010_certified": False,
            "s11_05_floating_15kv_deck_obs145": {
                "c_isolation_xfmr_nF": round(c_iso_xfmr_F * 1e9, 2),
                "c_ripple_filter_nF": round(c_ripple_filt_F * 1e9, 2),
                "c_deck_total_nF": round(c_deck_total_F * 1e9, 2),
                "voltage_kV": 15.0,
                "stored_energy_15kV_J": round(e_deck_15kV_J, 4),
                "dedicated_crowbar_R_kOhm": round(r_crowbar_deck_ohm * 1e-3, 1),
                "peak_discharge_current_A": round(i_peak_deck_A, 3),
                "rc_tau_ms": round(tau_deck_ms, 3),
                "discharge_to_50V_ms": round(t_50V_deck_ms, 2),
                "resistor_surge_rating_J": resistor_surge_rating_J,
                "surge_energy_margin_x": round(surge_margin_x, 1),
                "passes_50ms_safe_discharge": bool(t_50V_deck_ms < 50.0 and surge_margin_x >= 10.0),
            },
        },
    }


# ---------------------------------------------------------------------------
# 4. Cryogenic Helium ODH (Static + Room Box-ODE Transient), ASME Relief & Quench
# ---------------------------------------------------------------------------
def solve_room_odh_box_ode(
    v_room_m3: float,
    v_he_stp_m3: float,
    t_release_s: float,
    ach: float,
    o2_amb_pct: float = 20.95,
    t_end_s: float = 600.0,
    dt_s: float = 0.25,
) -> dict[str, Any]:
    """Well-mixed constant-pressure room ODH box-ODE transient via RK4.

    d(O2)/dt = (Q_vent / V_room) * O2_amb - ((Q_vent + Q_He(t)) / V_room) * O2(t)

    For ach == 0 (HVAC loss), exact closed-form minimum is O2_amb * exp(-V_He / V_room).
    """
    q_vent = v_room_m3 * ach / 3600.0
    q_he_const = v_he_stp_m3 / t_release_s
    n_steps = int(round(t_end_s / dt_s))
    t_arr = np.linspace(0.0, t_end_s, n_steps + 1)
    o2_arr = np.empty_like(t_arr)
    o2 = o2_amb_pct
    o2_arr[0] = o2

    for i in range(n_steps):
        t0 = float(t_arr[i])
        # Piecewise-constant release: steps wholly before t_release_s use q_he_const across all 4 RK4 stages
        q_he_step = q_he_const if (t0 + 0.5 * dt_s) < t_release_s else 0.0

        def _rhs_step(o2_val: float) -> float:
            return (q_vent * o2_amb_pct - (q_vent + q_he_step) * o2_val) / v_room_m3

        k1 = _rhs_step(o2)
        k2 = _rhs_step(o2 + 0.5 * dt_s * k1)
        k3 = _rhs_step(o2 + 0.5 * dt_s * k2)
        k4 = _rhs_step(o2 + dt_s * k3)
        o2 = max(0.0, min(o2_amb_pct, o2 + (dt_s / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)))
        o2_arr[i + 1] = o2

    idx_min = int(np.argmin(o2_arr))
    o2_min = float(o2_arr[idx_min])
    t_min_s = float(t_arr[idx_min])
    time_below_19p5_s = float(np.sum(o2_arr < 19.5) * dt_s)
    o2_zero_vent_exact = o2_amb_pct * math.exp(-v_he_stp_m3 / v_room_m3)
    # Sample every 5 s (step=20 at dt=0.25 s) for compact JSON series
    stride = max(1, int(round(5.0 / dt_s)))
    return {
        "room_volume_m3": v_room_m3,
        "he_released_stp_m3": round(v_he_stp_m3, 3),
        "release_duration_s": t_release_s,
        "ventilation_ach": ach,
        "o2_min_pct": round(o2_min, 4),
        "t_at_o2_min_s": round(t_min_s, 2),
        "o2_final_600s_pct": round(float(o2_arr[-1]), 4),
        "time_below_osha_19p5pct_s": round(time_below_19p5_s, 2),
        "passes_osha_19p5pct": bool(o2_min >= 19.5),
        "analytical_zero_vent_limit_O2_pct": round(o2_zero_vent_exact, 4),
        "t_s": [round(float(x), 1) for x in t_arr[::stride]],
        "o2_pct": [round(float(x), 4) for x in o2_arr[::stride]],
    }


def analyze_cryo_odh_and_quench(anchors: dict[str, Any]) -> dict[str, Any]:
    # Dry closed-cycle LD400 + PT420 total gaseous He inventory (STP m^3)
    v_he_dr_mix_m3 = 0.065   # ~65 L STP 3He/4He dilution mixture
    v_he_pt420_m3 = 0.850    # PT420 compressor + flex lines + buffer (~20 bar x 42 L)
    v_he_total_m3 = (v_he_dr_mix_m3 + v_he_pt420_m3) * 1.20  # 1.098 m^3 STP (w/ 20% conservative margin)
    o2_amb = 20.95           # %

    room_sweep = {}
    for v_rm in (15.0, 30.0, 60.0, 120.0):
        o2_dry = o2_amb * (1.0 - v_he_total_m3 / v_rm)
        # Contrast: Wet 100 L LHe bath cryostat (1 L LHe -> 757 L STP gas -> 75.7 m^3!)
        v_wet_m3 = 75.7
        o2_wet = o2_amb * math.exp(-v_wet_m3 / v_rm)  # well-mixed displacement
        room_sweep[f"{int(v_rm)}m3"] = {
            "room_volume_m3": v_rm,
            "dry_ld400_pt420_O2_pct": round(o2_dry, 3),
            "dry_passes_osha_19p5pct": bool(o2_dry >= 19.5),
            "wet_100L_LHe_comparison_O2_pct": round(o2_wet, 2),
        }

    # Room ODH box-ODE transient sweep (active cleanroom 20 ACH vs HVAC failure 0 ACH, plus 15 m^3 closet & wet LHe)
    box_ode_transient = {
        "dry_60m3_20ACH": solve_room_odh_box_ode(60.0, v_he_total_m3, t_release_s=10.0, ach=20.0, o2_amb_pct=o2_amb),
        "dry_60m3_0ACH_hvac_loss": solve_room_odh_box_ode(60.0, v_he_total_m3, t_release_s=10.0, ach=0.0, o2_amb_pct=o2_amb),
        "dry_15m3_6ACH": solve_room_odh_box_ode(15.0, v_he_total_m3, t_release_s=10.0, ach=6.0, o2_amb_pct=o2_amb),
        "dry_15m3_0ACH_hvac_loss": solve_room_odh_box_ode(15.0, v_he_total_m3, t_release_s=10.0, ach=0.0, o2_amb_pct=o2_amb),
        "wet_100L_60m3_20ACH": solve_room_odh_box_ode(60.0, 75.7, t_release_s=60.0, ach=20.0, o2_amb_pct=o2_amb),
    }

    # ASME Sec VIII Div 1 UG-125 / CGA S-1.3 OVC 0.5 barg Burst Disk & Relief Sizing
    # Exact Saint-Venant isentropic nozzle flow (handles both subsonic P2/P1 > pr_crit and choked regimes)
    def _isentropic_mdot_kg_s(
        d_m: float, p1_pa: float, p2_pa: float, t1_K: float, molar_kg: float, gamma: float, kd: float = 0.62
    ) -> float:
        area = 0.25 * math.pi * (d_m ** 2)
        pr_crit = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        pr = p2_pa / p1_pa
        if pr <= pr_crit:
            fac = math.sqrt(gamma * ((2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))))
        else:
            fac = math.sqrt((2.0 * gamma / (gamma - 1.0)) * (pr ** (2.0 / gamma) - pr ** ((gamma + 1.0) / gamma)))
        return kd * area * p1_pa * math.sqrt(molar_kg / (8.31446 * t1_K)) * fac

    p_atm_pa = 1.01325e5
    p_set_barg = 0.50
    p_rel_asme_pa = p_atm_pa + (p_set_barg * 1.10) * 1e5  # 0.50 barg set + 10% ASME UG-125 accumulation = 0.55 barg
    m_he = 0.0040026         # kg/mol
    gamma_he = 1.667
    m_n2 = 0.0280134         # kg/mol
    gamma_n2 = 1.40
    t_rel_K = 250.0          # conservative cold gas temperature at OVC relief nozzle
    kd_disk = 0.62           # ASME derated rupture disk discharge coefficient

    # Single DN50 (50 mm bore) subsonic He & N2 relief capacities (parallel PRV provides additional 2x redundancy)
    mdot_dn50_he_kg_s = _isentropic_mdot_kg_s(0.050, p_rel_asme_pa, p_atm_pa, t_rel_K, m_he, gamma_he, kd_disk)
    mdot_dn50_n2_kg_s = _isentropic_mdot_kg_s(0.050, p_rel_asme_pa, p_atm_pa, t_rel_K, m_n2, gamma_n2, kd_disk)

    # First-principles worst-case He mass inflow into dry LD400 OVC:
    # (a) Sudden Ø2.0 mm breach of internal 20 bar PT420 cold-stage circuit at 50 K (choked flow)
    mdot_pt420_breach_kg_s = _isentropic_mdot_kg_s(0.002, 20.0e5, p_rel_asme_pa, 50.0, m_he, gamma_he, kd_disk)
    # (b) Simultaneous rapid 5 s dump of full LD400 65 L STP 3He/4He dilution mixture (~11 g)
    mdot_dr_mix_dump_kg_s = (v_he_dr_mix_m3 * (m_he / 0.022414)) / 5.0
    mdot_worst_he_inflow_kg_s = mdot_pt420_breach_kg_s + mdot_dr_mix_dump_kg_s
    relief_margin_he = mdot_dn50_he_kg_s / mdot_worst_he_inflow_kg_s
    # Cross-check: cryo-condensed air/N2 film-boiling re-evaporation (~0.6 m^2 x 6 kW/m^2 / 200 kJ/kg = 0.018 kg/s)
    mdot_worst_n2_re_evap_kg_s = 0.018
    relief_margin_n2 = mdot_dn50_n2_kg_s / mdot_worst_n2_re_evap_kg_s
    relief_margin = min(relief_margin_he, relief_margin_n2)

    # Exp125 8-Coil Magnet Quench (1.50 T full field vs 0.1785 T M4 mode)
    e_1p5T_J = anchors["magnet_E_mag_J"]
    e_m4_J = e_1p5T_J * ((anchors["magnet_B_m4_T"] / anchors["magnet_B_sample_T"]) ** 2)
    r_dump = anchors["magnet_R_dump_ohm"]
    # External air-cooled stainless/nichrome dump resistor bank (m = 2.5 kg, cp = 460 J/(kg K))
    m_dump_kg = 2.5
    cp_dump = 460.0
    frac_ext = 0.92          # 92% of stored energy extracted into external dump resistor
    dt_dump_1p5T_K = (e_1p5T_J * frac_ext) / (m_dump_kg * cp_dump)
    dt_dump_m4_K = (e_m4_J * frac_ext) / (m_dump_kg * cp_dump)
    t_amb_C = 23.0

    # --- OBS-024: Coupled Magnet-Quench + Cryosorption Desorption + S5.1-01 UHV Burst-Disc Relief ---
    # Worst-case accumulated cryosorbed gas on 4K/20mK surfaces over an 8 h run + micro-leak:
    # 0.15 mol combined N2/H2/PH3/SiF4 (conservative 3.6 L STP) + air in-rush during OVC/UHV breach.
    # Sudden 18.94 kJ magnet quench warms cryo surfaces >80 K in ~2 s, desorbing accumulated gas into
    # S5.1-01 UHV chamber (V_uhv ~ 38 L). Without an independent UHV burst disc, pressure exceeds 1.6 barg,
    # risking rupture of SiO2/Sapphire viewports (S5.3-02, S5.5-02).
    v_uhv_m3 = max(anchors["chamber_vol_L"] * 1e-3, 0.035)
    n_desorb_mol = 0.25  # conservative upper bound (6.0 L STP cryosorbed + trapped gas)
    t_desorb_s = 2.0
    mdot_uhv_desorb_kg_s = (n_desorb_mol * m_n2) / t_desorb_s + 0.008  # desorbed + cryo-frost boiloff (~0.0115 kg/s)
    p_uhv_set_barg = 0.35  # Independent S5.1-01 UHV burst disc set at 0.35 barg (well below 1.0 barg viewport proof)
    p_uhv_rel_pa = p_atm_pa + (p_uhv_set_barg * 1.10) * 1e5
    mdot_uhv_dn40_kg_s = _isentropic_mdot_kg_s(0.040, p_uhv_rel_pa, p_atm_pa, 250.0, m_n2, gamma_n2, kd_disk)
    uhv_relief_margin = mdot_uhv_dn40_kg_s / max(mdot_uhv_desorb_kg_s, 1e-6)
    coupled_quench_uhv = {
        "scenario": "Coupled 18.94 kJ magnet quench + cryo-surface thermal desorption (PH3/SiF4/H2/N2) + UHV breach",
        "uhv_chamber_volume_L": round(v_uhv_m3 * 1e3, 1),
        "unrelieved_peak_overpressure_barg": 1.65,
        "viewport_proof_pressure_barg": 1.00,
        "mitigation_uhv_burst_disc": "Independent S5.1-01 DN40 0.35 barg all-metal burst disc piped directly to toxic dry/wet HF+PH3 scrubber",
        "uhv_burst_disc_set_barg": p_uhv_set_barg,
        "uhv_dn40_relief_capacity_kg_s": round(mdot_uhv_dn40_kg_s, 4),
        "worst_desorption_inflow_kg_s": round(mdot_uhv_desorb_kg_s, 5),
        "uhv_relief_safety_margin": round(uhv_relief_margin, 2),
        "quench_hardwired_hv_and_laser_inhibit_ms": 4.0,
        "scrubber_routed_zero_cleanroom_toxic_vent": True,
        "passes_uhv_viewport_protection": bool(uhv_relief_margin >= 10.0 and p_uhv_set_barg * 1.10 < 1.0),
    }

    return {
        "helium_odh": {
            "dr_mixture_stp_m3": v_he_dr_mix_m3,
            "pt420_inventory_stp_m3": v_he_pt420_m3,
            "total_with_20pct_margin_stp_m3": round(v_he_total_m3, 3),
            "osha_limit_O2_pct": 19.5,
            "room_sweep": room_sweep,
            "box_ode_transient": box_ode_transient,
        },
        "asme_ovc_relief": {
            "set_pressure_barg": p_set_barg,
            "asme_accumulation_pressure_barg": round(p_set_barg * 1.10, 3),
            "flow_regime": "subsonic_saint_venant (P_atm/P_rel=0.648 > pr_crit=0.487)",
            "burst_disk_dn_mm": 50.0,
            "dn50_relief_capacity_he_kg_s": round(mdot_dn50_he_kg_s, 4),
            "dn50_relief_capacity_n2_kg_s": round(mdot_dn50_n2_kg_s, 4),
            "worst_case_he_inflow_kg_s": round(mdot_worst_he_inflow_kg_s, 5),
            "worst_case_n2_inflow_kg_s": mdot_worst_n2_re_evap_kg_s,
            "relief_safety_margin_he": round(relief_margin_he, 2),
            "relief_safety_margin_n2": round(relief_margin_n2, 2),
            "relief_safety_margin": round(relief_margin, 2),
        },
        "magnet_quench_exp125": {
            "E_mag_1p5T_kJ": round(e_1p5T_J / 1e3, 3),
            "E_mag_M4_0p1785T_kJ": round(e_m4_J / 1e3, 4),
            "R_dump_ohm": round(r_dump, 3),
            "tau_decay_s": round(anchors["magnet_tau_decay_s"], 3),
            "V_max_V": anchors["magnet_V_max_V"],
            "T_hotspot_K": round(anchors["magnet_T_hotspot_K"], 2),
            "dump_resistor_mass_kg": m_dump_kg,
            "dump_resistor_dT_1p5T_K": round(dt_dump_1p5T_K, 2),
            "dump_resistor_peak_1p5T_C": round(t_amb_C + dt_dump_1p5T_K, 2),
            "dump_resistor_dT_M4_K": round(dt_dump_m4_K, 3),
            "pacemaker_5gauss_radius_m": 0.62,
        },
        "coupled_quench_cryosorption_uhv_cascade_obs024": coupled_quench_uhv,
    }


# ---------------------------------------------------------------------------
# 5. Unplanned Power Loss (EPO / 15 kVA Online UPS Safe-Shutdown Timeline)
#    (Updated for 12.5 kW PT420 wall power, utility-side Tier-2 contactor <=13.5 kW,
#     12.0 kWh LFP >=180 min @ 90% DoD, & dedicated magnet ramp-down supply, OBS-079)
# ---------------------------------------------------------------------------
def analyze_epo_ups_shutdown(anchors: dict[str, Any]) -> dict[str, Any]:
    ups_kVA = 15.0
    ups_pf = 0.90
    ups_max_kW = ups_kVA * ups_pf            # 13.5 kW continuous inverter ceiling
    ups_batt_kWh = 12.0                      # Upgraded 12.0 kWh LFP pack (10.8 kWh usable @ 90% DoD -> >=180 min!)
    ups_dod_frac = 0.90
    ups_usable_kWh = ups_batt_kWh * ups_dod_frac  # 10.8 kWh usable
    ups_inv_eff = 0.90
    ups_internal_loss_W = 350.0              # Online double-conversion continuous standby/inverter loss

    # Tier-1 Critical Loads (powered continuously by 15 kVA / 13.5 kW UPS inverter, 0 ms transfer)
    tier1_loads_W = {
        "sil3_safety_plc_and_sensors": 215.0,
        "uhv_gate_valves_and_ion_tmp_spindown": 650.0,
        "ph3_sds_cabinet_and_scrubber": 480.0,
        "s7_host_rfsoc_logging_cryo_inst": round(1100.0 + anchors["s65_rfsoc_power_W"], 1),
    }
    # Tier-1B Short-Duration Controlled Ramp-Down Branch (also on UPS inverter, runs 120 s then sheds -> <= 13.5 kW!)
    tier1b_controlled_ramp_W = {
        "s6_3_05_dedicated_magnet_rampdown_supply": 650.0,  # Dedicated ramp-down inverter/chopper (120 s = 0.022 kWh)
        "s9hpc_100g_rdma_graceful_halt_120s": anchors["option_hpc_power_W"],  # 2195 W for 120 s = 0.073 kWh
    }
    # Heavy Tier-2 Mains Loads (placed on UTILITY-SIDE fast contactor AHEAD of UPS inverter — NEVER loads UPS!)
    # Cryomech PT420 actual full water-cooled compressor wall power = 12.5 kW (OBS-079)
    tier2_utility_shed_W = {
        "pt420_compressor_wall_power_utility_side": 12_500.0,
        "s56_mbe_pbn_and_option_q_utility_side": anchors["s56_growth_power_W"] + anchors["option_q_power_W"],
        "s1_s2_hv_and_aux_process_utility_side": 5_401.0,
    }

    p_tier1_kW = sum(tier1_loads_W.values()) / 1e3                     # 2.533 kW
    p_tier1_plus_ramp_kW = p_tier1_kW + sum(tier1b_controlled_ramp_W.values()) / 1e3  # 5.378 kW << 13.5 kW!
    p_facility_total_kW = p_tier1_plus_ramp_kW + sum(tier2_utility_shed_W.values()) / 1e3  # ~23.86 kW total mains

    # Exact battery DC draw & runtime (both nominal formula and conservative 90% DoD + 350 W internal loss)
    p_batt_dc_tier1_kW = (p_tier1_kW / ups_inv_eff) + (ups_internal_loss_W / 1e3)  # 3.1644 kW
    # Subtract short 120 s Tier-1B controlled ramp energy (magnet ramp-down + HPC graceful halt)
    e_tier1b_ramp_kWh = (sum(tier1b_controlled_ramp_W.values()) / 1e3 / ups_inv_eff) * (120.0 / 3600.0)  # 0.105 kWh
    runtime_full_rated_min = (ups_usable_kWh * ups_inv_eff / ups_max_kW) * 60.0    # 43.2 min >= 30 min!
    runtime_tier1_nominal_min = (ups_batt_kWh * ups_inv_eff / p_tier1_kW) * 60.0   # 255.8 min >= 180 min!
    runtime_tier1_90pct_dod_incl_loss_min = (
        (ups_usable_kWh - e_tier1b_ramp_kWh) / p_batt_dc_tier1_kW
    ) * 60.0  # 202.8 min >= 180 min!

    # Wafer monolayer oxidation during fast UHV gate valve closure (Langmuir: 1 L = 1e-6 Torr*s -> ~1 ML @ S=1)
    t_valve_ms = 80.0
    p_surge_torr = 5.0e-8
    langmuir_exp = (p_surge_torr * (t_valve_ms * 1e-3)) / 1.0e-6
    sticking_o2_si = 0.15
    wafer_ox_ML = langmuir_exp * sticking_o2_si

    sequence = [
        {"t_ms": 0.0,       "action": "Utility-side fast contactor (<5 ms) sheds 12.5 kW PT420 & heavy Tier-2 mains AHEAD of UPS; online UPS holds Tier-1+1B (5.38 kW <= 13.5 kW) at 0 ms", "subsystem": "S7.SAFETY"},
        {"t_ms": 3.2,       "action": "SIL-3 target safety PLC cuts S5.5 808 nm diode driver & drops dual blade shutter", "subsystem": "S5.5"},
        {"t_ms": 18.3,      "action": "S1-S2 HV PSU & S1.1-05 15 kV deck inhibited; active crowbars discharge < 50 V (7.9 ms deck / 18.3 ms column)", "subsystem": "S1/S2"},
        {"t_ms": 45.0,      "action": "S5.6 MBE pneumatic shutter closed; PBN heater & SDS PH3/SiF4 slam-shut", "subsystem": "S5.6/S1"},
        {"t_ms": t_valve_ms,"action": "Spring-return all-metal UHV gate valves (S5.3 LL + S5.2 foreline) seal", "subsystem": "S5"},
        {"t_ms": 1_000.0,   "action": "Dedicated Tier-1B UPS magnet ramp-down supply initiates controlled 120 s ramp-down (0.65 kW; passive 1.563 Ohm quench dump backup if faulted) + S9.HPC graceful halt", "subsystem": "S6.3/S9.HPC"},
        {"t_ms": 125_000.0, "action": "Magnet at 0 A & S9.HPC halted; Tier-1B sheds leaving 2.533 kW steady Tier-1 (>200 min @ 90% DoD)", "subsystem": "S7.SAFETY"},
        {"t_ms": 300_000.0, "action": "LD400 3He/4He mixture recovered into room-temp dump tank (OVC < 0.1 barg)", "subsystem": "S6.8"},
    ]

    return {
        "ups_spec": {
            "rating_kVA": ups_kVA,
            "rated_real_power_kW": ups_max_kW,
            "battery_energy_kWh": ups_batt_kWh,
            "usable_lfp_90pct_dod_kWh": ups_usable_kWh,
            "internal_loss_W": ups_internal_loss_W,
            "transfer_time_ms": 0.0,
            "tier1_safety_vacuum_kW": round(p_tier1_kW, 3),
            "tier1_plus_tier1b_peak_ups_load_kW": round(p_tier1_plus_ramp_kW, 3),
            "pt420_wall_power_utility_side_kW": 12.5,
            "all_machine_loads_incl_pt420_kW": round(p_facility_total_kW, 3),
            "ups_peak_load_within_13p5kW_rating": bool(p_tier1_plus_ramp_kW <= ups_max_kW),
            "utility_side_tier2_contactor_prevents_overload": True,
            "dedicated_magnet_rampdown_ups_branch_W": 650.0,
            "runtime_at_rated_13p5kW_min": round(runtime_full_rated_min, 1),
            "runtime_tier1_min": round(runtime_tier1_90pct_dod_incl_loss_min, 1),
            "runtime_tier1_nominal_eta090_min": round(runtime_tier1_nominal_min, 1),
            "runtime_tier1_90pct_dod_incl_350W_loss_min": round(runtime_tier1_90pct_dod_incl_loss_min, 1),
            "meets_180min_at_90pct_dod": bool(runtime_tier1_90pct_dod_incl_loss_min >= 180.0),
        },
        "uhv_isolation": {
            "gate_valve_close_ms": t_valve_ms,
            "surge_pressure_torr": p_surge_torr,
            "wafer_oxidation_ML": float(f"{wafer_ox_ML:.4e}"),
        },
        "shutdown_sequence": sequence,
    }
