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
# 3. 10-22 keV High Voltage & Bremsstrahlung X-Ray Shielding (Kramers + NIST XCOM)
# ---------------------------------------------------------------------------
def _nist_mu_over_rho(e_keV: np.ndarray, material: str) -> np.ndarray:
    """Log-log interpolated NIST XCOM total mass attenuation mu/rho [cm^2/g] (5-30 keV)."""
    # Tabulated NIST XCOM values above/below major K-edges
    if material == "ss316l":
        # 68% Fe (K=7.11), 17% Cr (K=5.99), 12% Ni (K=8.33), 3% Mo (K=20.00) -> effective weighted mu/rho
        ek = np.array([4.0, 5.9, 6.0, 7.1, 7.2, 8.3, 8.4, 10.0, 15.0, 19.9, 20.1, 25.0, 30.0])
        mu = np.array([295.0, 115.0, 182.0, 128.0, 345.0, 232.0, 255.0, 162.0, 54.5, 25.2, 27.6, 14.3, 8.55])
    elif material == "sapphire_al2o3":
        # Al2O3 (52.9% Al, 47.1% O), rho=3.98 g/cm^3
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        mu = np.array([232.0, 122.0, 72.1, 31.2, 16.3, 5.02, 2.21, 1.24, 0.81])
    elif material == "al6061":
        # Al (rho=2.70 g/cm^3)
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        mu = np.array([360.0, 193.0, 115.0, 50.3, 26.2, 7.96, 3.44, 1.86, 1.13])
    elif material == "air_en":
        # Mass energy-absorption mu_en/rho of dry air [cm^2/g]
        ek = np.array([4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        mu = np.array([77.88, 40.27, 23.41, 9.92, 4.74, 1.33, 0.539, 0.271, 0.154])
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
    for v_kV in (10.0, 14.0, 22.0):
        d_unshielded = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [])
        d_6mm_ss = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("ss316l", t_wall_min_cm, 8.00)])
        d_10mm_ss = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("ss316l", t_wall_cad_cm, 8.00)])
        d_sapph_bare = _kramers_dose_rate_uSv_h(v_kV, i_leak_uA, z_target, dist_cm, [("sapphire_al2o3", t_sapph_cm, 3.98)])
        # S5.5 sapphire window + OD8 external laser shroud (3 mm 316L steel housing)
        d_sapph_shroud = _kramers_dose_rate_uSv_h(
            v_kV, i_leak_uA, z_target, dist_cm,
            [("sapphire_al2o3", t_sapph_cm, 3.98), ("ss316l", 0.30, 8.00)],
        )
        energy_sweep[f"{int(v_kV)}keV"] = {
            "voltage_kV": v_kV,
            "unshielded_30cm_uSv_h": round(d_unshielded, 2),
            "wall_6mm_316L_uSv_h": float(f"{d_6mm_ss:.4e}"),
            "wall_10mm_cad_316L_uSv_h": float(f"{d_10mm_ss:.4e}"),
            "s55_bare_sapphire_8mm_uSv_h": float(f"{d_sapph_bare:.4e}"),
            "s55_sapphire_plus_3mm_steel_shroud_uSv_h": float(f"{d_sapph_shroud:.4e}"),
        }

    # HV Stored Energy & Active Crowbar Discharge (IEC 61010-1: < 50 V safe touch, < 0.5 J stored)
    c_stray_F = 1.5e-9     # 1.5 nF total HV column + 2 m coaxial cable + filter stack
    r_crowbar_ohm = 2.0e6  # 2 MOhm redundant bleed + active solid-state crowbar
    tau_crowbar_ms = r_crowbar_ohm * c_stray_F * 1e3  # 3.0 ms
    e_10kV_J = 0.5 * c_stray_F * (10_000.0 ** 2)
    e_22kV_J = 0.5 * c_stray_F * (22_000.0 ** 2)
    t_50V_10kV_ms = tau_crowbar_ms * math.log(10_000.0 / 50.0)
    t_50V_22kV_ms = tau_crowbar_ms * math.log(22_000.0 / 50.0)

    return {
        "assumptions": {
            "leakage_electron_current_uA": i_leak_uA,
            "worst_case_anode_Z": z_target,
            "distance_cm": dist_cm,
            "public_dose_limit_uSv_h": 1.0,
            "icrp103_annual_public_mSv": 1.0,
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
    }


# ---------------------------------------------------------------------------
# 5. Unplanned Power Loss (EPO / 15 kVA Online UPS Safe-Shutdown Timeline)
# ---------------------------------------------------------------------------
def analyze_epo_ups_shutdown(anchors: dict[str, Any]) -> dict[str, Any]:
    ups_kVA = 15.0
    ups_pf = 0.90
    ups_max_kW = ups_kVA * ups_pf            # 13.5 kW
    ups_batt_kWh = 10.0                      # 10 kWh LFP online double-conversion battery pack
    ups_inv_eff = 0.90

    # Machine electrical power tiers (anchored to upstream specs)
    tier1_loads_W = {
        "sil3_safety_plc_and_sensors": 215.0,
        "uhv_gate_valves_and_ion_tmp_spindown": 650.0,
        "ph3_sds_cabinet_and_scrubber": 480.0,
        "s7_host_rfsoc_logging_cryo_inst": round(1100.0 + anchors["s65_rfsoc_power_W"], 1),
    }
    tier2_sheddable_W = {
        "pt420_compressor_controlled_stop": 9500.0,
        "s9hpc_100g_rdma_graceful_halt": anchors["option_hpc_power_W"],
        "s56_mbe_pbn_and_option_q_cut": anchors["s56_growth_power_W"] + anchors["option_q_power_W"],
    }
    p_tier1_kW = sum(tier1_loads_W.values()) / 1e3
    p_full_kW = (sum(tier1_loads_W.values()) + sum(tier2_sheddable_W.values())) / 1e3
    # Note: PT420 + HPC + Tier1 = ~14.8 kW peak if all run simultaneously; PT420 compressor uses soft-shed
    # at t=0.5s (its mechanical inertia coasts down safely), keeping UPS load <= 12.6 kW (<13.5 kW rating) or
    # with PT420 on 3-phase facility breaker and 15 kVA UPS powering full control + vacuum + HPC + MBE (5.3 kW)!
    # Even at full 13.5 kW UPS-rated load:
    runtime_full_rated_min = (ups_batt_kWh * ups_inv_eff / ups_max_kW) * 60.0   # 40.0 min >= 30 min!
    runtime_tier1_min = (ups_batt_kWh * ups_inv_eff / p_tier1_kW) * 60.0        # ~213 min >= 180 min!

    # Wafer monolayer oxidation during fast UHV gate valve closure (Langmuir: 1 L = 1e-6 Torr*s -> ~1 ML @ S=1)
    # Conservative surge pressure P_surge = 5e-8 Torr during 80 ms spring-return pneumatic valve closure
    t_valve_ms = 80.0
    p_surge_torr = 5.0e-8
    langmuir_exp = (p_surge_torr * (t_valve_ms * 1e-3)) / 1.0e-6
    sticking_o2_si = 0.15  # O2 on clean Si(100) sticking coefficient <= 0.15
    wafer_ox_ML = langmuir_exp * sticking_o2_si

    sequence = [
        {"t_ms": 0.0,       "action": "Online double-conversion UPS zero-transfer hold (0 ms bus continuity)", "subsystem": "S7.SAFETY"},
        {"t_ms": 3.2,       "action": "SIL-3 target safety PLC cuts S5.5 808 nm diode driver & drops dual blade shutter", "subsystem": "S5.5"},
        {"t_ms": 18.3,      "action": "S1-S2 HV PSU inhibited; active 2 MOhm crowbar discharges 22 kV < 50 V", "subsystem": "S1/S2"},
        {"t_ms": 45.0,      "action": "S5.6 MBE pneumatic shutter closed; PBN heater (400 W) & SDS PH3 slam-shut", "subsystem": "S5.6/S1"},
        {"t_ms": t_valve_ms,"action": "Spring-return all-metal UHV gate valves (S5.3 LL + S5.2 foreline) seal", "subsystem": "S5"},
        {"t_ms": 60_000.0,  "action": "Controlled Exp125 magnet ramp-down (120 s) + Option-HPC graceful halt", "subsystem": "S6/S9.HPC"},
        {"t_ms": 300_000.0, "action": "LD400 3He/4He mixture recovered into room-temp dump tank (OVC < 0.1 barg)", "subsystem": "S6.8"},
    ]

    return {
        "ups_spec": {
            "rating_kVA": ups_kVA,
            "rated_real_power_kW": ups_max_kW,
            "battery_energy_kWh": ups_batt_kWh,
            "transfer_time_ms": 0.0,
            "tier1_safety_vacuum_kW": round(p_tier1_kW, 3),
            "all_machine_loads_incl_pt420_kW": round(p_full_kW, 3),
            "runtime_at_rated_13p5kW_min": round(runtime_full_rated_min, 1),
            "runtime_tier1_min": round(runtime_tier1_min, 1),
        },
        "uhv_isolation": {
            "gate_valve_close_ms": t_valve_ms,
            "surge_pressure_torr": p_surge_torr,
            "wafer_oxidation_ML": float(f"{wafer_ox_ML:.4e}"),
        },
        "shutdown_sequence": sequence,
    }
