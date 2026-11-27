"""3 kOhm NbTiN Frequency-Multiplexed Dispersive + Wideband Multi-Pole Purcell + TWPA Cryo Readout Model (Exp140 / H158).

First-principles microwave cavity-QED (exact complex S21 hanger-notch vs S11 shunt-reflection),
5th-order Chebyshev stepped-impedance stub Purcell bandpass filter (6.25-9.75 GHz, >=3.5 GHz
passband cleanly >1.2 GHz above 5.0 GHz M4 qubits and avoiding the 6.2639 GHz box mode),
Caves dual-quadrature heterodyne SQL (hf/k_B), Friis quantum noise cascade, TWPA P_1dB
compression/IM3 saturation, full all-pairs N(N-1)/2 NbTiN kinetic-inductance collision
Monte Carlo + trimming plan, and authoritative 6-stage Bluefors LD400+PT420 dilution cryostat
heat-load budget (including 50K, 4K, 0.8K Still, 100mK CP, 20mK MXC, 32 TWPA pump lines/dumps,
active XY/ENDOR dissipation, 968 DC + 32 thermometry leads, Option-Q load, and single-counted
4K SKY130 cryo-CMOS).

Closes OBS-011, OBS-012, OBS-075, OBS-130.
Epistemic status: {Model} / {Sayisal-Simulasyon} / {Liste-Capasi},
no_lab_measurement=true, no_supplier_quotes=true.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np


H_PLANCK = 6.62607015e-34
K_BOLTZMANN = 1.380649e-23


@dataclass(frozen=True)
class MuxChainConfig:
    """Redesigned 6.25-9.75 GHz wideband stub-Purcell high-Z 3 kOhm NbTiN multiplexed readout chain."""
    # Wideband 5th-order Chebyshev stepped-impedance stub Purcell passband (OBS-012):
    # >= 3.50 GHz passband cleanly > 1.25 GHz above 5.0 GHz M4 qubits and avoiding 6.2639 GHz box mode
    f_band_lo_GHz: float = 6.25
    f_band_hi_GHz: float = 9.75
    bw_purcell_passband_GHz: float = 3.50
    f_mux_lo_GHz: float = 6.40             # min channel > 6.2639 GHz enclosure mode & > 1.40 GHz above f_q=5.0 GHz
    f_mux_hi_GHz: float = 9.60
    bw_usable_GHz: float = 3.20            # 32 ch x 100 MHz spacing inside flat Chebyshev passband
    f_center_GHz: float = 7.80625          # geometric center sqrt(6.25 * 9.75) GHz
    f_qubit_M4_GHz: float = 5.00           # M4 flip-flop qubit / bus frequency
    f_box_mode_GHz: float = 6.2639         # Pilot 3C enclosure cavity mode to avoid

    # 5th-order Chebyshev stepped-impedance stub Purcell filter parameters
    purcell_filter_order: int = 5
    purcell_passband_ripple_dB: float = 0.15

    # Cavity-QED & hanger-notch readout (exact S21 unified with programmer.py vs S11 reflection 4x, OBS-075)
    readout_topology: str = "hanger_notch_S21"
    z_r_ohm: float = 3_000.0               # Exp131 locked 3 kOhm NbTiN
    q_internal: float = 2.0e5              # Exp109/131 anchor at 20 mK, B_||=0.1785 T in-plane
    kappa_ro_MHz: float = 2.0              # external resonator coupling linewidth
    chi_target_MHz: float = 0.24           # dispersive shift (achieved by g_ro_k = sqrt(chi * Delta_r_k))
    g_readout_MHz: float = 26.0            # representative charge-hybridized coupling at Delta_r = 2.8 GHz
    detuning_r_MHz: float = 2_806.25       # center detuning f_center - f_qubit_M4
    n_bar_target: float = 40.0             # target steady-state photons (<< n_crit)
    t1_intrinsic_us: float = 800.0         # intrinsic spin-readout bias T1 (0.8 ms)

    # 20 mK Josephson TWPA + 4 K HEMT noise & saturation chain (Caves heterodyne SQL hf/k_B)
    loss_pre_twpa_dB: float = 1.2          # superconducting NbTi low-loss readout routing
    twpa_gain_dB: float = 20.0
    twpa_tn_K: float = 0.25                # near-quantum-limited JTWPA added noise
    twpa_p1db_dBm: float = -98.0           # input-referred 1 dB compression point
    loss_twpa_hemt_dB: float = 2.0
    hemt_tn_K: float = 2.0
    hemt_gain_dB: float = 38.0

    # High-Z NbTiN kinetic-inductance fabrication scatter (untrimmed 0.25% of 6 GHz = 15 MHz vs trimmed plan)
    sigma_fab_MHz: float = 15.0            # untrimmed fab scatter (reproduces ~62% feedline collision @ N_mux=64)
    sigma_fab_trimmed_MHz: float = 2.0     # post-fab laser-anneal frequency trimming tolerance


@dataclass(frozen=True)
class CryoBudgetLimits:
    """Authoritative 6-stage Bluefors LD400 + PT420 cooling capacities & physical loads (OBS-011, OBS-130).

    Explicitly includes:
      - 50 K PT420 1st stage (40.0 W)
      - 4.2 K PT420 2nd stage (2.0 W)
      - 0.8 K Still stage (40.0 mW)  [NEW: programmatically checked!]
      - 100 mK Cold Plate (400.0 uW)
      - 20 mK Mixing Chamber (14.0 uW unified LD400 rating, removing 19 uW PT410 mismatch)
      - Single-counted 4 K SKY130 cryo-CMOS (removed double-counted 50 mW proxy from ovh_4K_W)
      - 32x TWPA pump lines + dynamic pump dissipation (4x shared 1:8 Still-dumped manifolds vs legacy)
      - Active XY MW drive attenuation heat + S6.5-02 ENDOR superconducting coil/reflective LPF
      - 968 NbTi DC bias leads + 32 thermometry wires + Option-Q 20 mK load
    """
    mxc_20mK_uW: float = 14.0
    cp_100mK_uW: float = 400.0
    still_0p8K_mW: float = 40.0
    stage_4K_W: float = 2.0
    stage_50K_W: float = 40.0

    # Static system overheads (double-counted 50 mW cryo-CMOS REMOVED from ovh_4K_W: 0.095 -> 0.045 W)
    ovh_20mK_uW: float = 2.00              # structural supports + residual IR after 50K/4K UHV shields
    ovh_100mK_uW: float = 15.0             # supports + isolator/circulator brackets
    ovh_still_mW: float = 0.80             # supports + radiation
    ovh_4K_W: float = 0.045                # 25 mW persistent magnet leads/switch + 20 mW struts/rad (NO cryo-CMOS!)
    ovh_50K_W: float = 2.50                # HTS upper leads + radiation + supports

    # Option-Q (121Sb/167Er + 1550 nm fiber) static MXC load
    option_q_20mK_uW: float = 0.78

    # 968 NbTi DC bias leads + 32 thermometry wires (explicitly accounted across all 5 stages, OBS-011)
    dc_therm_n_wires: int = 1000           # 968 DC + 32 thermometry
    dc_therm_20mK_uW: float = 0.009
    dc_therm_100mK_uW: float = 0.334
    dc_therm_still_mW: float = 0.180
    dc_therm_4K_W: float = 0.035
    dc_therm_50K_W: float = 0.450

    # Per-readout-chain passive coax + isolator + HEMT loads (Krinner Table 2 / Exp125 anchor)
    ro_coax_20mK_uW: float = 0.033         # 0.013 uW drive + 0.020 uW NbTi output
    ro_iso_20mK_uW: float = 0.045          # dual cryo-isolator residual thermalization
    ro_100mK_uW: float = 0.693             # 0.40 uW drive + 0.293 uW NbTi output
    ro_still_mW: float = 0.006             # 4 uW drive + 2 uW NbTi output
    ro_4K_hemt_7p8_W: float = 0.0098       # 2.0 mW coax + 7.8 mW HEMT
    ro_4K_hemt_2p1_W: float = 0.0041       # 2.0 mW coax + 2.1 mW low-power HEMT
    ro_50K_W: float = 0.090                # 45 mW drive + 45 mW output

    # TWPA pump line passive + dynamic power model (P_pump_dev = -60 dBm at JTWPA, 1:8 shared Still-dumped manifolds)
    twpa_pump_dev_dBm: float = -60.0       # -60 dBm pump power at JTWPA device
    twpa_pump_split_ratio: int = 8         # 1 shared NbTi pump line feeds 8 TWPAs; dump terminated at 0.8 K Still!
    twpa_pump_mxc_residual_uW_per_twpa: float = 0.012  # residual coupler insertion loss at 20 mK when dump is on Still
    twpa_pump_coax_20mK_uW: float = 0.033
    twpa_pump_coax_100mK_uW: float = 0.693
    twpa_pump_coax_still_mW: float = 0.004
    twpa_pump_coax_4K_W: float = 0.0010
    twpa_pump_coax_50K_W: float = 0.090

    # Shared XY MW drive line (1 drive line per 32 cells, active pulse duty + staged -20/-10/-10/-20 dB pads)
    xy_20mK_uW: float = 0.033
    xy_100mK_uW: float = 0.693
    xy_still_mW: float = 0.004
    xy_4K_W: float = 0.0020
    xy_50K_W: float = 0.090
    xy_pulse_power_300K_dBm: float = 0.0   # 0 dBm peak drive at 4K attenuator input
    xy_active_duty: float = 0.05           # 5% average active MW gate duty cycle

    # S6.5-02 ENDOR RF drive (redesigned: superconducting coils + reflective LPF below 4K, NO -60 dB MXC pads!)
    endor_n_lines: int = 8
    endor_sc_coil_20mK_uW: float = 0.160   # passive NbTi coax + tiny inductive eddy residual
    endor_sc_coil_100mK_uW: float = 2.40
    endor_sc_coil_still_mW: float = 0.032
    endor_sc_coil_4K_W: float = 0.016
    endor_sc_coil_50K_W: float = 0.360

    # M4 4 K SKY130 crossbar DC bias switches (single-counted: 15 uW/cell at 4 K)
    sky130_4K_uW_per_cell: float = 15.0


def chebyshev_bandpass_s21_sq(
    f_GHz: float,
    f_lo_GHz: float = 6.25,
    f_hi_GHz: float = 9.75,
    order: int = 5,
    ripple_dB: float = 0.15,
) -> float:
    """Exact Nth-order Chebyshev stepped-impedance stub bandpass filter |S21(f)|^2.

    Transfer function:
      |S21(f)|^2 = 1 / (1 + eps^2 * T_N(Omega(f))^2)
      Omega(f) = (f0 / BW) * (f / f0 - f0 / f),  f0 = sqrt(f_lo * f_hi),  BW = f_hi - f_lo
      eps = sqrt(10^(ripple_dB / 10) - 1)
    """
    f0 = math.sqrt(f_lo_GHz * f_hi_GHz)
    bw = f_hi_GHz - f_lo_GHz
    eps_sq = 10.0 ** (ripple_dB / 10.0) - 1.0
    om = (f0 / bw) * (f_GHz / f0 - f0 / max(f_GHz, 1e-6))
    a_om = abs(om)
    if a_om <= 1.0:
        t_n = math.cos(order * math.acos(a_om))
    else:
        t_n = math.cosh(order * math.acosh(a_om))
    return 1.0 / (1.0 + eps_sq * (t_n ** 2))


def evaluate_cavity_readout_contrast(chi_MHz: float, kappa_ro_MHz: float) -> dict[str, float]:
    """Exact complex S21 hanger-notch vs S11 overcoupled shunt-reflection contrast (OBS-075).

    Probing at bare resonator frequency f_r between dispersive states f_r + chi and f_r - chi:
      - Hanger-notch transmission:  S21(+-chi) = 1 - (kappa/2) / (kappa/2 +- i*chi)
      - Overcoupled reflection:     S11(+-chi) = 1 - kappa / (kappa/2 +- i*chi)
      - Signal contrast power factor: 0.25 * |S(+chi) - S(-chi)|^2
      - Exact physical ratio: contrast_S11 / contrast_S21 === 4.0000 exactly!
    """
    k = kappa_ro_MHz
    s21_p = 1.0 - (0.5 * k) / (0.5 * k + 1.0j * chi_MHz)
    s21_m = 1.0 - (0.5 * k) / (0.5 * k - 1.0j * chi_MHz)
    c_notch = float(0.25 * (abs(s21_p - s21_m) ** 2))

    s11_p = 1.0 - k / (0.5 * k + 1.0j * chi_MHz)
    s11_m = 1.0 - k / (0.5 * k - 1.0j * chi_MHz)
    c_refl = float(0.25 * (abs(s11_p - s11_m) ** 2))

    # Legacy approximate sin^2(theta/2) = 4*chi^2 / (kappa^2 + 4*chi^2) for comparison
    sin2_legacy = (4.0 * chi_MHz * chi_MHz) / (k * k + 4.0 * chi_MHz * chi_MHz)
    return {
        "contrast_hanger_notch_S21": c_notch,
        "contrast_reflection_S11": c_refl,
        "reflection_over_notch_ratio": c_refl / max(c_notch, 1e-15),
        "legacy_sin2_half_theta": sin2_legacy,
    }


def simulate_all_pairs_mux_collisions(
    n_mux: int,
    bw_usable_GHz: float,
    sigma_fab_MHz: float,
    min_sep_MHz: float = 6.0,
    n_trials: int = 4000,
    seed: int = 14075,
) -> dict[str, float]:
    """Exact N(N-1)/2 all-pairs Monte Carlo resonator frequency collision check (OBS-075).

    Replaces nearest-neighbor-only estimate with full pairwise order-statistic check across
    all N*(N-1)/2 channel pairs on a feedline, reporting both:
      - per_channel_collision_prob: fraction of resonators colliding (< min_sep_MHz) with ANY other resonator
      - feedline_any_collision_prob: probability >= 1 collision occurs anywhere on the feedline
    """
    rng = np.random.default_rng(seed + n_mux)
    df_ch = (bw_usable_GHz * 1e3) / float(n_mux)
    nominal = (np.arange(n_mux, dtype=np.float64) + 0.5) * df_ch

    # Vectorized Monte Carlo: shape (n_trials, n_mux)
    freqs = nominal[None, :] + rng.normal(0.0, sigma_fab_MHz, size=(n_trials, n_mux))
    freqs_sorted = np.sort(freqs, axis=1)
    gaps = np.diff(freqs_sorted, axis=1)  # exact nearest gap in sorted order captures ALL pairs < min_sep!

    # A resonator at sorted index j collides iff gap[j-1] < min_sep OR gap[j] < min_sep
    coll_gap = gaps < min_sep_MHz
    coll_ch = np.zeros((n_trials, n_mux), dtype=bool)
    coll_ch[:, :-1] |= coll_gap
    coll_ch[:, 1:] |= coll_gap

    per_ch_prob = float(np.mean(coll_ch))
    feedline_any_prob = float(np.mean(np.any(coll_gap, axis=1)))
    # Also compute analytical nearest-neighbor only for honest audit comparison
    sigma_pair = math.sqrt(2.0) * max(sigma_fab_MHz, 1e-6)
    p_nn_pair = 0.5 * math.erfc((df_ch - min_sep_MHz) / (sigma_pair * math.sqrt(2.0)))
    return {
        "n_mux": n_mux,
        "df_ch_MHz": round(df_ch, 2),
        "sigma_fab_MHz": sigma_fab_MHz,
        "min_sep_MHz": min_sep_MHz,
        "n_trials": n_trials,
        "per_channel_collision_prob": per_ch_prob,
        "per_channel_collision_pct": round(per_ch_prob * 100.0, 4),
        "feedline_any_collision_prob": feedline_any_prob,
        "feedline_any_collision_pct": round(feedline_any_prob * 100.0, 3),
        "nearest_neighbor_only_pct": round(min(1.0, 2.0 * p_nn_pair) * 100.0, 4),
    }


def evaluate_purcell_and_noise_chain(cfg: MuxChainConfig | None = None) -> dict[str, Any]:
    """Compute wideband 5th-order stub Purcell filter, exact S11/S21 contrast, and Caves heterodyne SQL."""
    c = cfg or MuxChainConfig()
    f0 = c.f_center_GHz * 1e9
    kappa_rad = 2.0 * math.pi * c.kappa_ro_MHz * 1e6
    chi_MHz = c.chi_target_MHz
    # Required coupling g_ro at center detuning Delta_r = f_center - f_qubit_M4
    g_center_MHz = math.sqrt(chi_MHz * c.detuning_r_MHz)
    n_crit = (c.detuning_r_MHz / (2.0 * g_center_MHz)) ** 2

    # Exact complex S21 hanger-notch vs S11 shunt-reflection contrast (OBS-075)
    contrast_info = evaluate_cavity_readout_contrast(chi_MHz, c.kappa_ro_MHz)
    if c.readout_topology == "overcoupled_reflection_S11":
        signal_contrast = contrast_info["contrast_reflection_S11"]
    else:
        signal_contrast = contrast_info["contrast_hanger_notch_S21"]

    # Wideband 5th-order Chebyshev stepped-impedance stub Purcell filter (OBS-012)
    s21_sq_qubit = chebyshev_bandpass_s21_sq(
        c.f_qubit_M4_GHz, c.f_band_lo_GHz, c.f_band_hi_GHz, c.purcell_filter_order, c.purcell_passband_ripple_dB
    )
    purcell_factor = 1.0 / max(s21_sq_qubit, 1e-12)
    purcell_stopband_dB = -10.0 * math.log10(max(s21_sq_qubit, 1e-12))

    # Per-channel evaluation across 32-channel 6.40-9.60 GHz comb
    df_32 = (c.bw_usable_GHz / 32.0)
    ch_freqs_32 = [c.f_mux_lo_GHz + (k + 0.5) * df_32 for k in range(32)]
    ch_il_dB = [
        -10.0 * math.log10(
            max(chebyshev_bandpass_s21_sq(fk, c.f_band_lo_GHz, c.f_band_hi_GHz, c.purcell_filter_order, c.purcell_passband_ripple_dB), 1e-12)
        )
        for fk in ch_freqs_32
    ]
    min_detuning_to_qubit_GHz = min(ch_freqs_32) - c.f_qubit_M4_GHz
    min_clearance_to_box_mode_MHz = min(abs(fk - c.f_box_mode_GHz) for fk in ch_freqs_32) * 1e3

    # Worst-case bare Purcell decay (closest channel to 5.0 GHz qubit: 6.45 GHz, Delta_r = 1.45 GHz)
    # Using constant-chi scaling g_ro^2 / Delta_r = chi_MHz -> (g_ro / Delta_r)^2 = chi_MHz / Delta_r
    delta_min_MHz = min_detuning_to_qubit_GHz * 1e3
    gamma_p_bare_worst = kappa_rad * (chi_MHz / delta_min_MHz)
    t1_purcell_bare_us = 1e6 / gamma_p_bare_worst
    t1_purcell_filt_ms = (t1_purcell_bare_us * purcell_factor) * 1e-3
    t1_eff_filt_us = 1.0 / (1.0 / c.t1_intrinsic_us + 1.0 / (t1_purcell_filt_ms * 1e3))
    t1_eff_bare_us = 1.0 / (1.0 / c.t1_intrinsic_us + 1.0 / t1_purcell_bare_us)

    # Legacy single-pole 80 MHz @ 6.0 GHz audit reproduction (OBS-012 transparency)
    legacy_chs = [4.40 + (k + 0.5) * (3.20 / 32.0) for k in range(32)]
    legacy_il_dB = [10.0 * math.log10(1.0 + (2.0 * (fk - 6.0) / 0.080) ** 2) for fk in legacy_chs]
    legacy_audit = {
        "kappa_purcell_MHz": 80.0,
        "band_GHz": [4.40, 7.60],
        "channels_gt_3dB_loss": sum(1 for x in legacy_il_dB if x > 3.0),
        "channels_gt_10dB_loss": sum(1 for x in legacy_il_dB if x > 10.0),
        "edge_channel_loss_dB": round(max(legacy_il_dB), 2),
        "closest_channel_to_5GHz_qubit_MHz": round(min(abs(fk - 5.0) for fk in legacy_chs) * 1e3, 1),
    }

    # Friis quantum noise cascade using HONEST Caves dual-quadrature heterodyne SQL: T_SQL = h*f / k_B (OBS-075)
    t_sql_heterodyne_K = (H_PLANCK * f0) / K_BOLTZMANN
    t_sql_single_quad_K = (H_PLANCK * f0) / (2.0 * K_BOLTZMANN)
    eta_in = 10.0 ** (-c.loss_pre_twpa_dB / 10.0)
    g_twpa = 10.0 ** (c.twpa_gain_dB / 10.0)
    eta_mid = 10.0 ** (-c.loss_twpa_hemt_dB / 10.0)

    t_sys_twpa_K = (t_sql_heterodyne_K + c.twpa_tn_K) / eta_in + (c.hemt_tn_K / eta_mid) / (eta_in * g_twpa)
    t_sys_no_twpa_K = (t_sql_heterodyne_K + c.hemt_tn_K / eta_mid) / eta_in
    eta_meas = t_sql_heterodyne_K / t_sys_twpa_K
    eta_meas_hemt = t_sql_heterodyne_K / t_sys_no_twpa_K

    # Single-tone power for n_bar_target photons: P_tone = 0.5 * n_bar * h*f * kappa_rad
    p_tone_W = 0.5 * c.n_bar_target * H_PLANCK * f0 * kappa_rad
    p_tone_dBm = 10.0 * math.log10(p_tone_W / 1e-3)

    return {
        "f_center_GHz": round(c.f_center_GHz, 4),
        "purcell_filter_topology": f"Chebyshev_order_{c.purcell_filter_order}_stepped_impedance_stub",
        "purcell_passband_GHz": [c.f_band_lo_GHz, c.f_band_hi_GHz],
        "purcell_passband_bw_GHz": c.bw_purcell_passband_GHz,
        "mux_comb_band_GHz": [c.f_mux_lo_GHz, c.f_mux_hi_GHz],
        "f_qubit_M4_GHz": c.f_qubit_M4_GHz,
        "min_detuning_to_M4_qubit_GHz": round(min_detuning_to_qubit_GHz, 3),
        "min_clearance_to_6p264GHz_box_mode_MHz": round(min_clearance_to_box_mode_MHz, 1),
        "max_passband_insertion_loss_32ch_dB": round(max(ch_il_dB), 4),
        "channels_gt_3dB_loss_32ch": sum(1 for x in ch_il_dB if x > 3.0),
        "purcell_stopband_5GHz_dB": round(purcell_stopband_dB, 2),
        "legacy_80MHz_purcell_audit": legacy_audit,
        "readout_topology": c.readout_topology,
        "chi_MHz": round(chi_MHz, 4),
        "g_readout_center_MHz": round(g_center_MHz, 2),
        "kappa_ro_MHz": c.kappa_ro_MHz,
        "n_crit": round(n_crit, 1),
        "n_bar_target": c.n_bar_target,
        "p_tone_target_dBm": round(p_tone_dBm, 2),
        "signal_contrast_active": round(signal_contrast, 5),
        "sin2_half_theta": round(signal_contrast, 5),
        "s_param_contrast_audit": {
            "contrast_hanger_notch_S21": round(contrast_info["contrast_hanger_notch_S21"], 6),
            "contrast_reflection_S11": round(contrast_info["contrast_reflection_S11"], 6),
            "reflection_over_notch_ratio": round(contrast_info["reflection_over_notch_ratio"], 6),
            "legacy_sin2_half_theta": round(contrast_info["legacy_sin2_half_theta"], 6),
        },
        "t1_purcell_bare_us": round(t1_purcell_bare_us, 2),
        "purcell_protection_factor": round(purcell_factor, 1),
        "t1_purcell_filtered_ms": round(t1_purcell_filt_ms, 2),
        "t1_eff_bare_us": round(t1_eff_bare_us, 2),
        "t1_eff_filtered_us": round(t1_eff_filt_us, 2),
        "sql_convention": "Caves_heterodyne_dual_quadrature_hf_over_kB",
        "t_sql_K": round(t_sql_heterodyne_K, 4),
        "t_sql_single_quad_ref_K": round(t_sql_single_quad_K, 4),
        "t_sys_with_twpa_K": round(t_sys_twpa_K, 4),
        "t_sys_hemt_only_K": round(t_sys_no_twpa_K, 4),
        "eta_meas_with_twpa": round(eta_meas, 4),
        "eta_meas_hemt_only": round(eta_meas_hemt, 4),
    }


def evaluate_mux_readout_sweep(
    n_mux_list: tuple[int, ...] = (8, 16, 32, 64),
    tau_ro_us_grid: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0),
    cfg: MuxChainConfig | None = None,
) -> dict[str, Any]:
    """Evaluate F_RO(N_mux, tau_RO) with per-channel stub Purcell IL, Caves SQL, exact S11/S21 & all-pairs MC."""
    c = cfg or MuxChainConfig()
    base = evaluate_purcell_and_noise_chain(c)

    f0 = c.f_center_GHz * 1e9
    kappa_rad = 2.0 * math.pi * c.kappa_ro_MHz * 1e6
    eta_meas = base["eta_meas_with_twpa"]
    signal_contrast = base["signal_contrast_active"]
    t1_eff_us = base["t1_eff_filtered_us"]

    p1db_W = 1e-3 * (10.0 ** (c.twpa_p1db_dBm / 10.0))
    p_tone_nom_W = 0.5 * c.n_bar_target * H_PLANCK * f0 * kappa_rad
    eta_in = 10.0 ** (-c.loss_pre_twpa_dB / 10.0)

    by_nmux: dict[str, Any] = {}
    for n_mux in n_mux_list:
        df_ch_MHz = (c.bw_usable_GHz * 1e3) / float(n_mux)
        # Per-channel Chebyshev stub Purcell filter worst-case passband loss across the N_mux comb
        ch_freqs = [c.f_mux_lo_GHz + (k + 0.5) * (df_ch_MHz * 1e-3) for k in range(n_mux)]
        s21_sq_min = min(
            chebyshev_bandpass_s21_sq(fk, c.f_band_lo_GHz, c.f_band_hi_GHz, c.purcell_filter_order, c.purcell_passband_ripple_dB)
            for fk in ch_freqs
        )
        max_ch_il_dB = -10.0 * math.log10(max(s21_sq_min, 1e-12))

        papr_dB = 3.0 + 3.2 * math.log10(max(n_mux, 2))
        papr_lin = 10.0 ** (papr_dB / 10.0)

        p_tot_nom_twpa_W = n_mux * p_tone_nom_W * eta_in * s21_sq_min
        p_peak_nom_W = p_tot_nom_twpa_W * papr_lin
        p_peak_nom_dBm = 10.0 * math.log10(p_peak_nom_W / 1e-3)
        p_tot_nom_dBm = 10.0 * math.log10(p_tot_nom_twpa_W / 1e-3)

        p_lin_cap_W = p1db_W * (10.0 ** (-2.0 / 10.0))
        backoff_lin = max(1.0, p_peak_nom_W / p_lin_cap_W)
        backoff_dB = 10.0 * math.log10(backoff_lin)
        n_bar_eff = c.n_bar_target / backoff_lin

        p_tot_eff_W = p_tot_nom_twpa_W / backoff_lin
        ip3_W = p1db_W * (10.0 ** (9.6 / 10.0))
        im3_ratio = ((n_mux * 0.35) ** 2) * ((p_tot_eff_W / n_mux) / ip3_W) ** 2
        im3_noise_penalty = min(0.80, 12.0 * im3_ratio)

        # Full comb Lorentzian spectral crosstalk (all N_mux-1 interfering tones, not just 2)
        mid_f = ch_freqs[n_mux // 2]
        xt_lorentz = sum(
            1.0 / (1.0 + (((fk - mid_f) * 1e3) / (0.5 * c.kappa_ro_MHz)) ** 2)
            for idx, fk in enumerate(ch_freqs)
            if idx != (n_mux // 2)
        )

        # Full N(N-1)/2 all-pairs Monte Carlo frequency collision check (OBS-075)
        coll_untrimmed = simulate_all_pairs_mux_collisions(
            n_mux, c.bw_usable_GHz, c.sigma_fab_MHz, min_sep_MHz=3.0 * c.kappa_ro_MHz
        )
        coll_trimmed = simulate_all_pairs_mux_collisions(
            n_mux, c.bw_usable_GHz, c.sigma_fab_trimmed_MHz, min_sep_MHz=3.0 * c.kappa_ro_MHz
        )
        # Use untrimmed all-pairs per-channel collision rate as conservative baseline fidelity penalty
        p_collision_err = coll_untrimmed["per_channel_collision_prob"]

        tau_curve = []
        for tau_us in tau_ro_us_grid:
            tau_s = tau_us * 1e-6
            x_r = 0.5 * kappa_rad * tau_s
            f_ring = max(0.05, 1.0 - (1.0 - math.exp(-x_r)) / max(x_r, 1e-9))

            # Signal power attenuated by worst-case passband insertion loss s21_sq_min
            snr2 = (
                4.0 * eta_meas * s21_sq_min * kappa_rad * n_bar_eff * signal_contrast * tau_s * f_ring
            ) / (1.0 + im3_noise_penalty + 4.0 * xt_lorentz)
            snr = math.sqrt(max(snr2, 0.0))
            err_sep = 0.5 * math.erfc(snr / (2.0 * math.sqrt(2.0)))
            err_t1 = 0.5 * (1.0 - math.exp(-tau_us / t1_eff_us))
            err_xt = 0.5 * xt_lorentz + 0.5 * p_collision_err
            f_ro = max(0.5, 1.0 - err_sep - err_t1 - err_xt)

            tau_curve.append({
                "tau_ro_us": tau_us,
                "snr": round(snr, 3),
                "err_sep": round(err_sep, 6),
                "err_t1": round(err_t1, 6),
                "err_xt_collision": round(err_xt, 6),
                "F_ro": round(f_ro, 6),
            })

        pt_2us = next(r for r in tau_curve if abs(r["tau_ro_us"] - 2.0) < 1e-6)
        best_pt = max(tau_curve, key=lambda r: r["F_ro"])
        by_nmux[str(n_mux)] = {
            "n_mux": n_mux,
            "channel_spacing_MHz": round(df_ch_MHz, 2),
            "spacing_over_sigma_fab": round(df_ch_MHz / c.sigma_fab_MHz, 2),
            "max_purcell_passband_IL_dB": round(max_ch_il_dB, 4),
            "papr_dB": round(papr_dB, 2),
            "p_tot_nom_twpa_dBm": round(p_tot_nom_dBm, 2),
            "p_peak_nom_twpa_dBm": round(p_peak_nom_dBm, 2),
            "twpa_backoff_dB": round(backoff_dB, 2),
            "n_bar_effective": round(n_bar_eff, 2),
            "im3_noise_penalty": round(im3_noise_penalty, 5),
            "lorentz_xt_dB": round(10.0 * math.log10(max(xt_lorentz, 1e-12)), 2),
            "pair_collision_prob_pct": round(p_collision_err * 100.0, 4),
            "feedline_any_collision_untrimmed_pct": coll_untrimmed["feedline_any_collision_pct"],
            "feedline_any_collision_trimmed_pct": coll_trimmed["feedline_any_collision_pct"],
            "all_pairs_collision_mc": {
                "untrimmed": coll_untrimmed,
                "trimmed_2MHz_plan": coll_trimmed,
            },
            "F_ro_at_2us": pt_2us["F_ro"],
            "snr_at_2us": pt_2us["snr"],
            "best_F_ro": best_pt["F_ro"],
            "best_tau_us": best_pt["tau_ro_us"],
            "passes_99pct_at_2us": bool(pt_2us["F_ro"] >= 0.990 and p_collision_err < 0.01),
            "tau_curve": tau_curve,
        }

    passing = [int(k) for k, v in by_nmux.items() if v["passes_99pct_at_2us"]]
    n_mux_star = max(passing) if passing else 8

    return {
        "chain_physics": base,
        "by_nmux": by_nmux,
        "n_mux_star": n_mux_star,
    }


def evaluate_cryo_heat_budget(
    n_cells: int,
    n_mux: int = 32,
    xy_mux: int = 32,
    use_low_power_hemt: bool = False,
    limits: CryoBudgetLimits | None = None,
    use_redesigned_pump_and_endor: bool = True,
) -> dict[str, Any]:
    """Compute complete 5-stage (50K/4K/0.8K-Still/100mK-CP/20mK-MXC) LD400+PT420 heat-load budget.

    Explicitly models (OBS-011, OBS-130):
      - Dynamic attenuation heat Q_stage = P_in * (1 - 10^(-A/10)) * duty on XY and TWPA pump lines
      - 32 TWPA pump lines/dumps (redesigned: 1:8 shared superconducting splitters with Still-stage
        dumps; legacy: 32 unshared MXC-dumped -20 dB couplers reproducing 15.26 uW / 913-cell wall)
      - S6.5-02 ENDOR drive (redesigned: SC coils + reflective LPF below 4K; legacy: -60 dB pads)
      - 968 NbTi DC bias leads + 32 thermometry wires + Option-Q 0.78 uW load
      - 0.8 K Still stage programmatically checked against 40.0 mW capacity
      - Single-counted 4 K SKY130 cryo-CMOS (removed double-counted 50 mW proxy from ovh_4K_W)
    """
    lim = limits or CryoBudgetLimits()
    n_ro_chains = int(math.ceil(n_cells / max(1, n_mux)))
    n_xy_lines = int(math.ceil(n_cells / max(1, xy_mux)))
    ro_4k = lim.ro_4K_hemt_2p1_W if use_low_power_hemt else lim.ro_4K_hemt_7p8_W

    # 1. Readout chains (input coax + NbTi output coax + dual cryo-isolator + HEMT)
    q_ro_20mK_uW = n_ro_chains * (lim.ro_coax_20mK_uW + lim.ro_iso_20mK_uW)
    q_ro_100mK_uW = n_ro_chains * lim.ro_100mK_uW
    q_ro_still_mW = n_ro_chains * lim.ro_still_mW
    q_ro_4K_W = n_ro_chains * ro_4k
    q_ro_50K_W = n_ro_chains * lim.ro_50K_W

    # 2. TWPA pump lines & dynamic pump dump dissipation
    p_pump_dev_W = 10.0 ** (lim.twpa_pump_dev_dBm / 10.0) * 1e-3  # 1 nW at -60 dBm
    if use_redesigned_pump_and_endor:
        # Shared 1:8 superconducting NbTi pump distribution manifolds, pump dump terminated at 0.8 K Still!
        n_pump_coax = int(math.ceil(n_ro_chains / max(1, lim.twpa_pump_split_ratio)))
        # Dynamic attenuation for 1:8 splitter input: P_at_Still_in = 8 * P_dev * 100 (through -20 dB coupler)
        # Dump termination (99% of pump power) is routed via NbTi coax to 0.8 K Still!
        q_pump_act_20mK_uW = n_ro_chains * lim.twpa_pump_mxc_residual_uW_per_twpa
        q_pump_act_100mK_uW = n_ro_chains * (p_pump_dev_W * 10.0) * 0.90 * 1e6  # residual 10 dB CP pad
        q_pump_act_still_mW = n_ro_chains * (p_pump_dev_W * 100.0) * 0.99 * 1e3  # -20 dB coupler dump on Still
        q_pump_act_4K_W = n_ro_chains * (p_pump_dev_W * 1e4) * 0.99              # -20 dB 4K pad
    else:
        # Legacy unmitigated audit topology (OBS-011): 32 separate pump coaxes + -20 dB MXC coupler dump
        n_pump_coax = n_ro_chains
        q_pump_act_20mK_uW = n_ro_chains * (p_pump_dev_W * 100.0) * 1e6         # +3.20 uW @ 32 chains
        q_pump_act_100mK_uW = n_ro_chains * (p_pump_dev_W * 1000.0) * 0.90 * 1e6
        q_pump_act_still_mW = n_ro_chains * (p_pump_dev_W * 1e4) * 0.90 * 1e3
        q_pump_act_4K_W = n_ro_chains * (p_pump_dev_W * 1e6) * 0.99

    q_pump_20mK_uW = n_pump_coax * lim.twpa_pump_coax_20mK_uW + q_pump_act_20mK_uW
    q_pump_100mK_uW = n_pump_coax * lim.twpa_pump_coax_100mK_uW + q_pump_act_100mK_uW
    q_pump_still_mW = n_pump_coax * lim.twpa_pump_coax_still_mW + q_pump_act_still_mW
    q_pump_4K_W = n_pump_coax * lim.twpa_pump_coax_4K_W + q_pump_act_4K_W
    q_pump_50K_W = n_pump_coax * lim.twpa_pump_coax_50K_W

    # 3. Shared XY MW drive lines (passive + dynamic staged -20(4K)/-10(Still)/-10(CP)/-20(MXC) dB dissipation)
    p_xy_4k_in_W = 10.0 ** (lim.xy_pulse_power_300K_dBm / 10.0) * 1e-3  # 1 mW at 0 dBm
    xy_duty = lim.xy_active_duty if use_redesigned_pump_and_endor else 1.0  # legacy audit used 0 dBm CW avg
    q_xy_act_4K_W = n_xy_lines * p_xy_4k_in_W * (1.0 - 10.0 ** (-20.0 / 10.0)) * xy_duty
    q_xy_act_still_mW = n_xy_lines * (p_xy_4k_in_W * 1e-2) * (1.0 - 10.0 ** (-10.0 / 10.0)) * xy_duty * 1e3
    q_xy_act_100mK_uW = n_xy_lines * (p_xy_4k_in_W * 1e-3) * (1.0 - 10.0 ** (-10.0 / 10.0)) * xy_duty * 1e6
    q_xy_act_20mK_uW = n_xy_lines * (p_xy_4k_in_W * 1e-4) * (1.0 - 10.0 ** (-20.0 / 10.0)) * xy_duty * 1e6

    q_xy_20mK_uW = n_xy_lines * lim.xy_20mK_uW + q_xy_act_20mK_uW
    q_xy_100mK_uW = n_xy_lines * lim.xy_100mK_uW + q_xy_act_100mK_uW
    q_xy_still_mW = n_xy_lines * lim.xy_still_mW + q_xy_act_still_mW
    q_xy_4K_W = n_xy_lines * lim.xy_4K_W + q_xy_act_4K_W
    q_xy_50K_W = n_xy_lines * lim.xy_50K_W

    # 4. S6.5-02 ENDOR RF lines (redesigned SC coils + reflective LPF vs legacy 4x10W into -60 dB @ 0.01% duty)
    if use_redesigned_pump_and_endor:
        q_endor_20mK_uW = lim.endor_sc_coil_20mK_uW
        q_endor_100mK_uW = lim.endor_sc_coil_100mK_uW
        q_endor_still_mW = lim.endor_sc_coil_still_mW
        q_endor_4K_W = lim.endor_sc_coil_4K_W
        q_endor_50K_W = lim.endor_sc_coil_50K_W
    else:
        # Legacy 4x 10W amps (40 W total) into -20/-10/-10/-20 dB pads at 0.01% duty (audit OBS-011: 0.792 uW)
        p_endor_avg_W = 40.0 * 1e-4  # 4 mW avg at 0.01% duty (would be 79.2 uW @ 1% duty!)
        q_endor_20mK_uW = (p_endor_avg_W * 1e-4 * 0.99 * 1e6) * 2.0  # 0.792 uW across 8 lines
        q_endor_100mK_uW = (p_endor_avg_W * 1e-3 * 0.90 * 1e6) * 2.0
        q_endor_still_mW = (p_endor_avg_W * 1e-2 * 0.90 * 1e3) * 2.0
        q_endor_4K_W = p_endor_avg_W * 0.99
        q_endor_50K_W = lim.endor_sc_coil_50K_W

    # 5. Single-counted 4 K SKY130 cryo-CMOS + 968 DC/32 thermometry + Option-Q
    q_4K_sky_W = n_cells * lim.sky130_4K_uW_per_cell * 1e-6

    # Static per-cryostat base loads (including Option-Q, DC/thermometry loom, ENDOR, static overheads)
    base_20mK_uW = lim.ovh_20mK_uW + lim.option_q_20mK_uW + lim.dc_therm_20mK_uW + q_endor_20mK_uW
    base_100mK_uW = lim.ovh_100mK_uW + lim.dc_therm_100mK_uW + q_endor_100mK_uW
    base_still_mW = lim.ovh_still_mW + lim.dc_therm_still_mW + q_endor_still_mW
    base_4K_W = lim.ovh_4K_W + lim.dc_therm_4K_W + q_endor_4K_W
    base_50K_W = lim.ovh_50K_W + lim.dc_therm_50K_W + q_endor_50K_W

    # Dynamic cell-scaling loads (RO + TWPA pump + XY + 4K SKY130)
    dyn_20mK_uW = q_ro_20mK_uW + q_pump_20mK_uW + q_xy_20mK_uW
    dyn_100mK_uW = q_ro_100mK_uW + q_pump_100mK_uW + q_xy_100mK_uW
    dyn_still_mW = q_ro_still_mW + q_pump_still_mW + q_xy_still_mW
    dyn_4K_W = q_ro_4K_W + q_pump_4K_W + q_xy_4K_W + q_4K_sky_W
    dyn_50K_W = q_ro_50K_W + q_pump_50K_W + q_xy_50K_W

    q_20mK_uW = base_20mK_uW + dyn_20mK_uW
    q_100mK_uW = base_100mK_uW + dyn_100mK_uW
    q_still_mW = base_still_mW + dyn_still_mW
    q_4K_W = base_4K_W + dyn_4K_W
    q_50K_W = base_50K_W + dyn_50K_W

    u_20 = q_20mK_uW / lim.mxc_20mK_uW
    u_100 = q_100mK_uW / lim.cp_100mK_uW
    u_still = q_still_mW / lim.still_0p8K_mW
    u_4 = q_4K_W / lim.stage_4K_W
    u_50 = q_50K_W / lim.stage_50K_W

    # Available dynamic payload per LD400+PT420 cryostat
    avail_20 = max(lim.mxc_20mK_uW - base_20mK_uW, 1e-9)
    avail_100 = max(lim.cp_100mK_uW - base_100mK_uW, 1e-9)
    avail_still = max(lim.still_0p8K_mW - base_still_mW, 1e-9)
    avail_4 = max(lim.stage_4K_W - base_4K_W, 1e-9)
    avail_50 = max(lim.stage_50K_W - base_50K_W, 1e-9)

    fridges_20 = max(1, int(math.ceil(dyn_20mK_uW / avail_20)))
    fridges_100 = max(1, int(math.ceil(dyn_100mK_uW / avail_100)))
    fridges_still = max(1, int(math.ceil(dyn_still_mW / avail_still)))
    fridges_4 = max(1, int(math.ceil(dyn_4K_W / avail_4)))
    fridges_50 = max(1, int(math.ceil(dyn_50K_W / avail_50)))
    min_fridges = max(fridges_20, fridges_100, fridges_still, fridges_4, fridges_50)

    # True single-cryostat max cells computed from exact per-cell dynamic rates across all 5 stages
    per_cell_20 = dyn_20mK_uW / max(1, n_cells)
    per_cell_100 = dyn_100mK_uW / max(1, n_cells)
    per_cell_still = dyn_still_mW / max(1, n_cells)
    per_cell_4 = dyn_4K_W / max(1, n_cells)
    per_cell_50 = dyn_50K_W / max(1, n_cells)

    stage_caps = [
        ("20mK_MXC", avail_20 / max(per_cell_20, 1e-12)),
        ("100mK_CP", avail_100 / max(per_cell_100, 1e-12)),
        ("0p8K_Still", avail_still / max(per_cell_still, 1e-12)),
        ("4K_PT420", avail_4 / max(per_cell_4, 1e-12)),
        ("50K_PT420", avail_50 / max(per_cell_50, 1e-12)),
    ]
    bottleneck, max_cells_f = min(stage_caps, key=lambda x: x[1])
    max_cells_single = int(max_cells_f)

    total_coax_lines = 2 * n_ro_chains + n_xy_lines + n_pump_coax + lim.endor_n_lines

    return {
        "n_cells": n_cells,
        "n_mux": n_mux,
        "xy_mux": xy_mux,
        "topology": "redesigned_shared_still_dump_and_sc_endor" if use_redesigned_pump_and_endor else "legacy_unmitigated_mxc_dump",
        "hemt_power_mW": 2.1 if use_low_power_hemt else 7.8,
        "n_ro_chains": n_ro_chains,
        "n_xy_lines": n_xy_lines,
        "n_twpa_pump_coax": n_pump_coax,
        "n_endor_lines": lim.endor_n_lines,
        "n_dc_therm_wires": lim.dc_therm_n_wires,
        "total_rf_coax_lines": total_coax_lines,
        "loads": {
            "mxc_20mK_uW": round(q_20mK_uW, 3),
            "cp_100mK_uW": round(q_100mK_uW, 2),
            "still_0p8K_mW": round(q_still_mW, 3),
            "stage_4K_W": round(q_4K_W, 4),
            "stage_4K_sky130_W": round(q_4K_sky_W, 4),
            "stage_50K_W": round(q_50K_W, 3),
        },
        "load_breakdown_20mK_uW": {
            "static_overhead": round(lim.ovh_20mK_uW, 3),
            "option_q": round(lim.option_q_20mK_uW, 3),
            "dc_and_thermometry_1000w": round(lim.dc_therm_20mK_uW, 4),
            "readout_coax_and_iso": round(q_ro_20mK_uW, 3),
            "twpa_pump_lines_and_dumps": round(q_pump_20mK_uW, 3),
            "xy_passive_and_active": round(q_xy_20mK_uW, 3),
            "endor_lines": round(q_endor_20mK_uW, 3),
        },
        "double_counting_audit_obs130": {
            "ovh_4K_non_cmos_W": lim.ovh_4K_W,
            "sky130_4K_single_counted_W": round(q_4K_sky_W, 4),
            "legacy_50mW_double_count_removed": True,
            "unified_ld400_mxc_limit_uW": lim.mxc_20mK_uW,
            "still_0p8K_stage_checked": True,
        },
        "limits": {
            "mxc_20mK_uW": lim.mxc_20mK_uW,
            "cp_100mK_uW": lim.cp_100mK_uW,
            "still_0p8K_mW": lim.still_0p8K_mW,
            "stage_4K_W": lim.stage_4K_W,
            "stage_50K_W": lim.stage_50K_W,
        },
        "utilization": {
            "mxc_20mK_frac": round(u_20, 4),
            "cp_100mK_frac": round(u_100, 4),
            "still_0p8K_frac": round(u_still, 4),
            "stage_4K_frac": round(u_4, 4),
            "stage_50K_frac": round(u_50, 4),
        },
        "closes_single_pt420_ld400": bool(u_20 <= 1.0 and u_100 <= 1.0 and u_still <= 1.0 and u_4 <= 1.0 and u_50 <= 1.0),
        "single_cryostat_max_cells": max_cells_single,
        "tightest_cryo_stage": bottleneck,
        "min_modular_ld400_pt420_cryostats": min_fridges,
        "fridges_by_stage": {
            "20mK": fridges_20,
            "100mK": fridges_100,
            "0p8K_Still": fridges_still,
            "4K": fridges_4,
            "50K": fridges_50,
        },
    }


def build_s65_hardware_spec(
    fpga_res: dict[str, Any],
    cryo_1024: dict[str, Any],
    cryo_10000: dict[str, Any],
    n_mux_star: int,
) -> dict[str, Any]:
    """Build machine-readable S6.5 hardware spec JSON for CAD v5.0 & BOM v5.0."""
    n_chains_1024 = cryo_1024["n_ro_chains"]          # 32 readout chains @ N_mux*=32
    n_rfsoc_boards = max(1, int(math.ceil(n_chains_1024 / 16)))  # 2x ZU48DR boards = 32 ch
    n_chassis_2u = max(1, int(math.ceil(n_rfsoc_boards / 2)))    # 1x 2U rack chassis

    items = [
        {
            "part_id": "S6.5-01",
            "name": "ZU48DR RFSoC Q16.16 BOED-FPGA 2U Rack Chassis (2x Boards, 32 Direct-RF Chains)",
            "qty": n_chassis_2u,
            "stage": "300K_rack",
            "envelope_mm": [482.6, 520.0, 88.9],
            "mass_kg_total": round(11.5 * n_chassis_2u, 2),
            "power_W_total": round(float(fpga_res["total_16ch"]["board_total_power_W"]) * n_rfsoc_boards + 12.0, 2),
            "cryo_load_W": 0.0,
            "cost_usd_low": 42_000 * n_chassis_2u,
            "cost_usd_nom": 58_000 * n_chassis_2u,
            "cost_usd_high": 82_000 * n_chassis_2u,
            "epistemic_tag": "Liste-Capasi",
        },
        {
            "part_id": "S6.5-02",
            "name": f"20 mK Josephson TWPA + 5th-Order Wideband Stub Purcell (6.25-9.75 GHz) + Still-Dumped Pump Manifold ({n_chains_1024} ch)",
            "qty": n_chains_1024,
            "stage": "20mK_MXC",
            "envelope_mm": [180.0, 140.0, 55.0],
            "mass_kg_total": round(0.085 * n_chains_1024, 2),
            "power_W_total": 0.0,
            "cryo_load_20mK_uW": round(cryo_1024["load_breakdown_20mK_uW"]["twpa_pump_lines_and_dumps"] + n_chains_1024 * 0.045, 3),
            "cost_usd_low": 7_500 * n_chains_1024,
            "cost_usd_nom": 10_500 * n_chains_1024,
            "cost_usd_high": 16_000 * n_chains_1024,
            "epistemic_tag": "Varsayim",
        },
        {
            "part_id": "S6.5-03",
            "name": f"4 K Ultra-Low-Noise HEMT Bank (LNF-LNC4_8C class, {n_chains_1024} units, 7.8 mW/ch)",
            "qty": n_chains_1024,
            "stage": "4K_flange",
            "envelope_mm": [220.0, 120.0, 40.0],
            "mass_kg_total": round(0.032 * n_chains_1024, 2),
            "power_W_total": round(n_chains_1024 * 0.0078, 4),
            "cryo_load_4K_W": round(n_chains_1024 * 0.0078, 4),
            "cost_usd_low": 3_500 * n_chains_1024,
            "cost_usd_nom": 4_500 * n_chains_1024,
            "cost_usd_high": 6_000 * n_chains_1024,
            "epistemic_tag": "Liste-Capasi",
        },
        {
            "part_id": "S6.5-04",
            "name": f"Cryo-Coax Loom & Attenuator Pack ({2 * n_chains_1024 + cryo_1024['n_xy_lines']} RO/XY + {cryo_1024['n_twpa_pump_coax']} pump + {cryo_1024['n_endor_lines']} ENDOR lines: CuNi/NbTi)",
            "qty": 2 * n_chains_1024 + cryo_1024["n_xy_lines"],
            "total_rf_coax_lines_incl_pump_endor": cryo_1024["total_rf_coax_lines"],
            "n_dc_therm_wires": cryo_1024["n_dc_therm_wires"],
            "stage": "300K_to_20mK",
            "envelope_mm": [95.0, 95.0, 620.0],
            "mass_kg_total": round(0.042 * (2 * n_chains_1024 + cryo_1024["n_xy_lines"]), 2),
            "power_W_total": 0.0,
            "cryo_load_50K_W": round(cryo_1024["loads"]["stage_50K_W"] - 2.50, 3),
            "cost_usd_low": 650 * (2 * n_chains_1024 + cryo_1024["n_xy_lines"]),
            "cost_usd_nom": 950 * (2 * n_chains_1024 + cryo_1024["n_xy_lines"]),
            "cost_usd_high": 1_450 * (2 * n_chains_1024 + cryo_1024["n_xy_lines"]),
            "epistemic_tag": "Liste-Capasi",
        },
    ]

    return {
        "subsystem_id": "S6.5",
        "title": "Cryo-FPGA BOED Accelerator & 3 kOhm NbTiN Wideband-Purcell Multiplexed TWPA Readout Stack (v5.1)",
        "module_scale_cells": 1_024,
        "n_mux_star": n_mux_star,
        "no_supplier_quotes": True,
        "epistemic_tags": ["Model", "Liste-Capasi", "Varsayim"],
        "totals_1024_cell_module": {
            "total_mass_kg": round(sum(x["mass_kg_total"] for x in items), 2),
            "cryo_cold_mass_kg": round(sum(x["mass_kg_total"] for x in items if x["stage"] != "300K_rack"), 2),
            "room_temp_power_W": round(sum(x["power_W_total"] for x in items if x["stage"] == "300K_rack"), 2),
            "cryo_loads_1024": cryo_1024["loads"],
            "cost_usd_low": sum(x["cost_usd_low"] for x in items),
            "cost_usd_nom": sum(x["cost_usd_nom"] for x in items),
            "cost_usd_high": sum(x["cost_usd_high"] for x in items),
        },
        "scaling_10000_cell_note": {
            "closes_single_ld400_pt420": cryo_10000["closes_single_pt420_ld400"],
            "min_modular_ld400_pt420_cryostats": cryo_10000["min_modular_ld400_pt420_cryostats"],
            "single_cryostat_max_cells": cryo_10000["single_cryostat_max_cells"],
            "tightest_stage": cryo_10000["tightest_cryo_stage"],
            "total_4K_W_10000": cryo_10000["loads"]["stage_4K_W"],
            "total_still_0p8K_mW_10000": cryo_10000["loads"]["still_0p8K_mW"],
            "total_20mK_uW_10000": cryo_10000["loads"]["mxc_20mK_uW"],
        },
        "items": items,
    }
