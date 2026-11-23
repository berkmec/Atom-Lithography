"""3 kOhm NbTiN Frequency-Multiplexed Dispersive + Purcell + TWPA Cryo Readout Model (Exp140 / H158).

First-principles microwave cavity-QED, Friis quantum noise cascade, TWPA P_1dB
compression/IM3 saturation, NbTiN kinetic-inductance channel-crowding crosstalk,
and Exp125-anchored 4-stage dilution cryostat heat-load budget for 1,024-cell
and 10,000-cell M4 arrays, plus S6.5 hardware engineering spec for CAD/BOM v5.0.

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
    """4.0-8.0 GHz high-Z 3 kOhm NbTiN multiplexed readout chain parameters."""
    f_band_lo_GHz: float = 4.0
    f_band_hi_GHz: float = 8.0
    bw_usable_GHz: float = 3.20            # usable band inside Purcell stop-bands
    f_center_GHz: float = 6.0
    z_r_ohm: float = 3_000.0               # Exp131 locked 3 kOhm NbTiN
    q_internal: float = 2.0e5              # Exp109/131 anchor at 20 mK, B_M4=0.1785 T
    kappa_ro_MHz: float = 2.0              # external resonator coupling linewidth
    g_readout_MHz: float = 12.0            # charge-hybridized readout dipole coupling
    detuning_r_MHz: float = 600.0          # dispersive detuning Delta_r
    n_bar_target: float = 40.0             # target steady-state photons (<< n_crit=625)
    t1_intrinsic_us: float = 800.0         # intrinsic spin-readout bias T1 (0.8 ms)

    # Common bandpass Purcell filter (Jeffrey et al. PRL 2014)
    kappa_purcell_MHz: float = 80.0
    delta_q_purcell_MHz: float = 1_000.0   # qubit-to-Purcell-passband detuning

    # 20 mK Josephson TWPA + 4 K HEMT noise & saturation chain
    loss_pre_twpa_dB: float = 1.5
    twpa_gain_dB: float = 20.0
    twpa_tn_K: float = 0.30
    twpa_p1db_dBm: float = -98.0           # input-referred 1 dB compression point
    loss_twpa_hemt_dB: float = 2.0
    hemt_tn_K: float = 2.0
    hemt_gain_dB: float = 38.0

    # High-Z NbTiN kinetic-inductance fabrication scatter (0.25% of 6 GHz = 15 MHz)
    sigma_fab_MHz: float = 15.0


@dataclass(frozen=True)
class CryoBudgetLimits:
    """Single-cryostat cooling capacities (Bluefors LD400 + PT420, Exp125 anchor)."""
    mxc_20mK_uW: float = 14.0
    cp_100mK_uW: float = 400.0
    stage_4K_W: float = 2.0
    stage_50K_W: float = 40.0

    # System static overheads (Exp125 system_overhead_20mK)
    ovh_20mK_uW: float = 2.0
    ovh_100mK_uW: float = 15.0
    ovh_4K_W: float = 0.095
    ovh_50K_W: float = 2.5

    # Per-feedline heat loads (Exp125 product_34ch_20mK + TWPA/isolator thermalization)
    # Readout chain = 1 attenuated input + 1 NbTi output + 1 TWPA pump/isolator + 1 HEMT
    ro_20mK_uW: float = 0.100              # 0.033 uW coax + 0.067 uW TWPA pump/iso residual
    ro_100mK_uW: float = 0.700             # Exp125 0.693 uW/chain
    ro_4K_hemt_7p8_W: float = 0.0098       # 2.0 mW coax + 7.8 mW HEMT (Exp125)
    ro_4K_hemt_2p1_W: float = 0.0041       # 2.0 mW coax + 2.1 mW low-power HEMT (Exp125)
    ro_50K_W: float = 0.090                # Exp125 0.090 W/chain

    # Shared XY MW drive line (1 drive line per 32 cells, no HEMT)
    xy_20mK_uW: float = 0.033
    xy_100mK_uW: float = 0.693
    xy_4K_W: float = 0.0020
    xy_50K_W: float = 0.090

    # M4 4 K SKY130 crossbar DC bias switches (Exp131: ~15 uW/cell at 4 K)
    sky130_4K_uW_per_cell: float = 15.0


def evaluate_purcell_and_noise_chain(cfg: MuxChainConfig | None = None) -> dict[str, Any]:
    """Compute exact dispersive shift, Purcell protection, and Friis noise temperature."""
    c = cfg or MuxChainConfig()
    f0 = c.f_center_GHz * 1e9
    kappa_rad = 2.0 * math.pi * c.kappa_ro_MHz * 1e6
    chi_MHz = (c.g_readout_MHz ** 2) / c.detuning_r_MHz
    n_crit = (c.detuning_r_MHz / (2.0 * c.g_readout_MHz)) ** 2
    sin2_half_theta = (4.0 * chi_MHz * chi_MHz) / (c.kappa_ro_MHz ** 2 + 4.0 * chi_MHz * chi_MHz)

    # Purcell protection
    gamma_p_bare = kappa_rad * ((c.g_readout_MHz / c.detuning_r_MHz) ** 2)
    t1_purcell_bare_us = 1e6 / gamma_p_bare
    purcell_factor = (2.0 * c.delta_q_purcell_MHz / c.kappa_purcell_MHz) ** 2
    t1_purcell_filt_ms = (t1_purcell_bare_us * purcell_factor) * 1e-3
    t1_eff_filt_us = 1.0 / (1.0 / c.t1_intrinsic_us + 1.0 / (t1_purcell_filt_ms * 1e3))
    t1_eff_bare_us = 1.0 / (1.0 / c.t1_intrinsic_us + 1.0 / t1_purcell_bare_us)

    # Friis quantum noise cascade (referenced to sample plane)
    t_sql_K = (H_PLANCK * f0) / (2.0 * K_BOLTZMANN)
    eta_in = 10.0 ** (-c.loss_pre_twpa_dB / 10.0)
    g_twpa = 10.0 ** (c.twpa_gain_dB / 10.0)
    eta_mid = 10.0 ** (-c.loss_twpa_hemt_dB / 10.0)

    t_sys_twpa_K = (t_sql_K + c.twpa_tn_K) / eta_in + (c.hemt_tn_K / eta_mid) / (eta_in * g_twpa)
    t_sys_no_twpa_K = (t_sql_K + c.hemt_tn_K / eta_mid) / eta_in
    eta_meas = t_sql_K / t_sys_twpa_K

    # Single-tone power for n_bar_target photons: P_tone = 0.5 * n_bar * h*f * kappa_rad
    p_tone_W = 0.5 * c.n_bar_target * H_PLANCK * f0 * kappa_rad
    p_tone_dBm = 10.0 * math.log10(p_tone_W / 1e-3)

    return {
        "f_center_GHz": c.f_center_GHz,
        "chi_MHz": round(chi_MHz, 4),
        "kappa_ro_MHz": c.kappa_ro_MHz,
        "n_crit": round(n_crit, 1),
        "n_bar_target": c.n_bar_target,
        "p_tone_target_dBm": round(p_tone_dBm, 2),
        "sin2_half_theta": round(sin2_half_theta, 5),
        "t1_purcell_bare_us": round(t1_purcell_bare_us, 2),
        "purcell_protection_factor": round(purcell_factor, 1),
        "t1_purcell_filtered_ms": round(t1_purcell_filt_ms, 2),
        "t1_eff_bare_us": round(t1_eff_bare_us, 2),
        "t1_eff_filtered_us": round(t1_eff_filt_us, 2),
        "t_sql_K": round(t_sql_K, 4),
        "t_sys_with_twpa_K": round(t_sys_twpa_K, 4),
        "t_sys_hemt_only_K": round(t_sys_no_twpa_K, 4),
        "eta_meas_with_twpa": round(eta_meas, 4),
        "eta_meas_hemt_only": round(t_sql_K / t_sys_no_twpa_K, 4),
    }


def evaluate_mux_readout_sweep(
    n_mux_list: tuple[int, ...] = (8, 16, 32, 64),
    tau_ro_us_grid: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0),
    cfg: MuxChainConfig | None = None,
) -> dict[str, Any]:
    """Evaluate F_RO(N_mux, tau_RO), TWPA P_1dB backoff, IM3 distortion & NbTiN crosstalk."""
    c = cfg or MuxChainConfig()
    base = evaluate_purcell_and_noise_chain(c)

    f0 = c.f_center_GHz * 1e9
    kappa_rad = 2.0 * math.pi * c.kappa_ro_MHz * 1e6
    eta_meas = base["eta_meas_with_twpa"]
    sin2_th = base["sin2_half_theta"]
    t1_eff_us = base["t1_eff_filtered_us"]

    p1db_W = 1e-3 * (10.0 ** (c.twpa_p1db_dBm / 10.0))
    # Linear operating ceiling keeping TWPA peak envelope <= P_1dB - 2 dB margin
    # Multi-tone statistical PAPR (99.9% crest factor for N_mux random-phase tones) ~= 2 * ln(N_mux) + 3 dB
    p_tone_nom_W = 0.5 * c.n_bar_target * H_PLANCK * f0 * kappa_rad
    # Reflected power reaching TWPA after pre-TWPA loss
    eta_in = 10.0 ** (-c.loss_pre_twpa_dB / 10.0)

    by_nmux: dict[str, Any] = {}
    for n_mux in n_mux_list:
        df_ch_MHz = (c.bw_usable_GHz * 1e3) / float(n_mux)
        # Random-phase multi-tone peak-to-average ratio (linear power factor)
        papr_dB = 3.0 + 3.2 * math.log10(max(n_mux, 2))
        papr_lin = 10.0 ** (papr_dB / 10.0)

        # Total nominal peak power at TWPA input (including ~2 dB pump-leakage/backoff reserve)
        p_tot_nom_twpa_W = n_mux * p_tone_nom_W * eta_in
        p_peak_nom_W = p_tot_nom_twpa_W * papr_lin
        p_peak_nom_dBm = 10.0 * math.log10(p_peak_nom_W / 1e-3)
        p_tot_nom_dBm = 10.0 * math.log10(p_tot_nom_twpa_W / 1e-3)

        # Backoff required so peak envelope stays <= P_1dB (plus residual soft compression / IM3)
        # Soft cubic compression when driving near P_1dB: optimal backoff trades photon number vs IM3
        p_lin_cap_W = p1db_W * (10.0 ** (-2.0 / 10.0))  # -100 dBm peak cap for clean IM3
        backoff_lin = max(1.0, p_peak_nom_W / p_lin_cap_W)
        backoff_dB = 10.0 * math.log10(backoff_lin)
        n_bar_eff = c.n_bar_target / backoff_lin

        # Effective TWPA gain compression & IM3 intermodulation noise floor (IP3 ~= P_1dB + 9.6 dB)
        p_tot_eff_W = p_tot_nom_twpa_W / backoff_lin
        ip3_W = p1db_W * (10.0 ** (9.6 / 10.0))
        # Third-order intermodulation ratio scaled by combinatorial tone count ~(N_mux/2)^2
        im3_ratio = ((n_mux * 0.35) ** 2) * ((p_tot_eff_W / n_mux) / ip3_W) ** 2
        im3_noise_penalty = min(0.80, 12.0 * im3_ratio)

        # Adjacent-channel Lorentzian spectral crosstalk + high-Z NbTiN kinetic-inductance collisions
        # Two neighbors at +/- df_ch_MHz with linewidth kappa_ro_MHz
        xt_lorentz = 2.0 / (1.0 + (df_ch_MHz / (0.5 * c.kappa_ro_MHz)) ** 2)
        # Probability a neighboring resonator collides within +/- 3*kappa (6 MHz) given sigma_fab scatter:
        # Pair separation d ~ N(df_ch, sqrt(2)*sigma_fab)
        sigma_pair = math.sqrt(2.0) * c.sigma_fab_MHz
        z_coll = (df_ch_MHz - 3.0 * c.kappa_ro_MHz) / sigma_pair
        p_pair_collision = 0.5 * math.erfc(z_coll / math.sqrt(2.0))
        # Each interior resonator has 2 neighbors -> expected collision error floor
        p_collision_err = min(0.25, 2.0 * p_pair_collision)

        tau_curve = []
        for tau_us in tau_ro_us_grid:
            tau_s = tau_us * 1e-6
            # Ring-up transient settling factor
            x_r = 0.5 * kappa_rad * tau_s
            f_ring = max(0.05, 1.0 - (1.0 - math.exp(-x_r)) / max(x_r, 1e-9))

            snr2 = (
                4.0 * eta_meas * kappa_rad * n_bar_eff * sin2_th * tau_s * f_ring
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
            "papr_dB": round(papr_dB, 2),
            "p_tot_nom_twpa_dBm": round(p_tot_nom_dBm, 2),
            "p_peak_nom_twpa_dBm": round(p_peak_nom_dBm, 2),
            "twpa_backoff_dB": round(backoff_dB, 2),
            "n_bar_effective": round(n_bar_eff, 2),
            "im3_noise_penalty": round(im3_noise_penalty, 5),
            "lorentz_xt_dB": round(10.0 * math.log10(max(xt_lorentz, 1e-12)), 2),
            "pair_collision_prob_pct": round(p_collision_err * 100.0, 4),
            "F_ro_at_2us": pt_2us["F_ro"],
            "snr_at_2us": pt_2us["snr"],
            "best_F_ro": best_pt["F_ro"],
            "best_tau_us": best_pt["tau_ro_us"],
            "passes_99pct_at_2us": bool(pt_2us["F_ro"] >= 0.990 and p_collision_err < 0.01),
            "tau_curve": tau_curve,
        }

    # Physical optimum N_mux*: largest N_mux passing >=99% at 2 us with <1% collision penalty
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
) -> dict[str, Any]:
    """Compute exact 4-stage dilution cryostat heat-load budget for an N-cell M4 array."""
    lim = limits or CryoBudgetLimits()
    n_ro_chains = int(math.ceil(n_cells / max(1, n_mux)))
    n_xy_lines = int(math.ceil(n_cells / max(1, xy_mux)))
    ro_4k = lim.ro_4K_hemt_2p1_W if use_low_power_hemt else lim.ro_4K_hemt_7p8_W

    q_20mK_uW = lim.ovh_20mK_uW + n_ro_chains * lim.ro_20mK_uW + n_xy_lines * lim.xy_20mK_uW
    q_100mK_uW = lim.ovh_100mK_uW + n_ro_chains * lim.ro_100mK_uW + n_xy_lines * lim.xy_100mK_uW
    q_4K_sky_W = n_cells * lim.sky130_4K_uW_per_cell * 1e-6
    q_4K_W = lim.ovh_4K_W + n_ro_chains * ro_4k + n_xy_lines * lim.xy_4K_W + q_4K_sky_W
    q_50K_W = lim.ovh_50K_W + (n_ro_chains + n_xy_lines) * lim.ro_50K_W

    u_20 = q_20mK_uW / lim.mxc_20mK_uW
    u_100 = q_100mK_uW / lim.cp_100mK_uW
    u_4 = q_4K_W / lim.stage_4K_W
    u_50 = q_50K_W / lim.stage_50K_W

    # Exact minimum number of modular LD400/PT420 cryostats needed (accounting for per-fridge overhead!)
    # Available payload per fridge = limit - overhead
    avail_20 = lim.mxc_20mK_uW - lim.ovh_20mK_uW
    avail_100 = lim.cp_100mK_uW - lim.ovh_100mK_uW
    avail_4 = lim.stage_4K_W - lim.ovh_4K_W
    avail_50 = lim.stage_50K_W - lim.ovh_50K_W

    dyn_20 = q_20mK_uW - lim.ovh_20mK_uW
    dyn_100 = q_100mK_uW - lim.ovh_100mK_uW
    dyn_4 = q_4K_W - lim.ovh_4K_W
    dyn_50 = q_50K_W - lim.ovh_50K_W

    fridges_20 = max(1, int(math.ceil(dyn_20 / avail_20)))
    fridges_100 = max(1, int(math.ceil(dyn_100 / avail_100)))
    fridges_4 = max(1, int(math.ceil(dyn_4 / avail_4)))
    fridges_50 = max(1, int(math.ceil(dyn_50 / avail_50)))
    min_fridges = max(fridges_20, fridges_100, fridges_4, fridges_50)

    # Max cells per single PT420/LD400 cryostat (limited by tightest stage)
    per_cell_20 = (lim.ro_20mK_uW / n_mux) + (lim.xy_20mK_uW / xy_mux)
    per_cell_4 = (ro_4k / n_mux) + (lim.xy_4K_W / xy_mux) + (lim.sky130_4K_uW_per_cell * 1e-6)
    per_cell_50 = (lim.ro_50K_W / n_mux) + (lim.xy_50K_W / xy_mux)
    max_cells_single = int(min(avail_20 / per_cell_20, avail_4 / per_cell_4, avail_50 / per_cell_50))
    bottleneck = min(
        [("20mK_MXC", avail_20 / per_cell_20), ("4K_PT420", avail_4 / per_cell_4), ("50K", avail_50 / per_cell_50)],
        key=lambda x: x[1],
    )[0]

    return {
        "n_cells": n_cells,
        "n_mux": n_mux,
        "xy_mux": xy_mux,
        "hemt_power_mW": 2.1 if use_low_power_hemt else 7.8,
        "n_ro_chains": n_ro_chains,
        "n_xy_lines": n_xy_lines,
        "total_rf_coax_lines": 2 * n_ro_chains + n_xy_lines,
        "loads": {
            "mxc_20mK_uW": round(q_20mK_uW, 3),
            "cp_100mK_uW": round(q_100mK_uW, 2),
            "stage_4K_W": round(q_4K_W, 4),
            "stage_4K_sky130_W": round(q_4K_sky_W, 4),
            "stage_50K_W": round(q_50K_W, 3),
        },
        "limits": {
            "mxc_20mK_uW": lim.mxc_20mK_uW,
            "cp_100mK_uW": lim.cp_100mK_uW,
            "stage_4K_W": lim.stage_4K_W,
            "stage_50K_W": lim.stage_50K_W,
        },
        "utilization": {
            "mxc_20mK_frac": round(u_20, 4),
            "cp_100mK_frac": round(u_100, 4),
            "stage_4K_frac": round(u_4, 4),
            "stage_50K_frac": round(u_50, 4),
        },
        "closes_single_pt420_ld400": bool(u_20 <= 1.0 and u_100 <= 1.0 and u_4 <= 1.0 and u_50 <= 1.0),
        "single_cryostat_max_cells": max_cells_single,
        "tightest_cryo_stage": bottleneck,
        "min_modular_ld400_pt420_cryostats": min_fridges,
        "fridges_by_stage": {
            "20mK": fridges_20,
            "100mK": fridges_100,
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
            "name": f"20 mK Josephson TWPA + Bandpass Purcell Filter + Dual Cryo-Isolator Pack ({n_chains_1024} ch)",
            "qty": n_chains_1024,
            "stage": "20mK_MXC",
            "envelope_mm": [180.0, 140.0, 55.0],
            "mass_kg_total": round(0.085 * n_chains_1024, 2),
            "power_W_total": 0.0,
            "cryo_load_20mK_uW": round(n_chains_1024 * 0.067, 3),
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
            "name": f"Cryo-Coax Loom & Attenuator Pack ({cryo_1024['total_rf_coax_lines']} lines: CuNi/NbTi, 0.86 mm)",
            "qty": cryo_1024["total_rf_coax_lines"],
            "stage": "300K_to_20mK",
            "envelope_mm": [95.0, 95.0, 620.0],
            "mass_kg_total": round(0.042 * cryo_1024["total_rf_coax_lines"], 2),
            "power_W_total": 0.0,
            "cryo_load_50K_W": round((n_chains_1024 + cryo_1024["n_xy_lines"]) * 0.090, 3),
            "cost_usd_low": 650 * cryo_1024["total_rf_coax_lines"],
            "cost_usd_nom": 950 * cryo_1024["total_rf_coax_lines"],
            "cost_usd_high": 1_450 * cryo_1024["total_rf_coax_lines"],
            "epistemic_tag": "Liste-Capasi",
        },
    ]

    return {
        "subsystem_id": "S6.5",
        "title": "Cryo-FPGA BOED Accelerator & 3 kOhm NbTiN Multiplexed TWPA Readout Stack (v5.0)",
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
            "total_20mK_uW_10000": cryo_10000["loads"]["mxc_20mK_uW"],
        },
        "items": items,
    }
