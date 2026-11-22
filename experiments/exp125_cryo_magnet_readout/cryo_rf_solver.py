"""Exp125 Module 2: Unified 5-Stage Cryogenic Thermal Balance (50K -> 4K -> Still -> CP -> MXC 20 mK
vs 1 K Hot-Readout), Dispersive RF SNR Budget & End-to-End Throughput Solver.

Anchors:
  - Krinner et al., arXiv:1806.07862 Table 2 (measured passive line loads & stage cooling powers)
  - Exp109 (NL_eff, Q_i), Exp110 (thermal baseline), Exp111 (PT410/415/420 & Rebelo 2026 2.1 mW InP HEMT)
  - Exp112 (NL spec 110-160, 56-82 lines), Exp113 (tone <= -100 dBm, LNF-LNC4_8C 10.5 mW)
  - Exp116 (20 mK DR baseline S6.8=D), Exp117 (1.5 K PSB hot readout S6.8=C, 3.165x overhead)

All values labeled {Model} / {Literatür} / {Varsayım}; no_lab_measurement=True.
"""
from __future__ import annotations

import math
from typing import Dict, List

KB = 1.380649e-23      # J/K
H_PLANCK = 6.62607015e-34  # J*s

# Krinner et al. (arXiv:1806.07862) Table 2 measured passive loads per coax line
KRINNER_DRIVE = {
    "50K_mW": 45.0,
    "4K_mW": 1.0,
    "Still_uW": 4.0,
    "CP_uW": 0.40,
    "MXC_uW": 0.013,
}
KRINNER_OUTPUT = {
    "50K_mW": 45.0,   # UT085 SS-SS above 4K (symmetry assumption, matching Exp110)
    "4K_mW": 1.0,     # UT085 SS-SS above 4K (symmetry assumption, matching Exp110)
    "Still_uW": 2.0,  # NbTi 4K->0.88K (Flachbart 1978 conductivity ratio; sensitivity 4.0 uW)
    "CP_uW": 0.29,    # Measured NbTi Table 2
    "MXC_uW": 0.020,  # Measured NbTi Table 2
}

# Stage cooling capacities (Bluefors/Cryomech PT410 baseline + DR class, Krinner measured MXC)
CAPACITIES_20MK_PT410 = {
    "50K_W": 40.0,
    "4K_W": 1.0,
    "Still_mW": 40.0,
    "CP_uW": 200.0,
    "MXC_20mK_uW": 19.0,
    "MXC_100mK_uW": 540.0,
}

# Non-readout steady-state cryostat loads (labeled engineering inputs)
# Persistent-mode superconducting magnet (I_leads=0), 4K SKY130 cryo-CMOS DC mux (Exp33/58),
# G10 structural supports & thermal radiation shields.
SYSTEM_OVERHEAD_20MK = {
    "50K_W": 2.50,     # HTS magnet current leads upper stage + radiation + supports
    "4K_W": 0.095,     # 25 mW persistent magnet leads/switch + 50 mW 4K cryo-CMOS + 20 mW struts/rad
    "Still_mW": 0.80,  # Structural supports + NbTi DC looms + radiation
    "CP_uW": 15.0,     # Supports + isolator/circulator mounting
    "MXC_uW": 2.00,    # Structural supports + residual IR/radiation + sample dissipation
}

# 1 K closed-cycle hot-readout stage (S6.8=C on S6.1 PT410/420)
CAPACITIES_1K_PT410 = {
    "50K_W": 40.0,
    "4K_W": 1.0,
    "stage1K_mW": 100.0,  # Closed-cycle 1K JT / He-4 cooler class @ 1.5 K
}
SYSTEM_OVERHEAD_1K = {
    "50K_W": 2.50,
    "4K_W": 0.095,
    "stage1K_mW": 5.0,    # Structural supports + radiation + sample dissipation at 1.5 K
}
LINE_1K_PASSIVE_MW = 0.12  # 0.08 mW SS drive + 0.04 mW NbTi/CuNi output (4K->1.5K conduction, assumption)


def replicate_exp110_exp112_gate() -> Dict:
    """Exact baseline replication check against Exp110 (NL=58) and Exp112 (NL=163) readout-only loads."""
    # Exp110 formula: lines = ceil(9000/58) = 156, active_mxc = lines*58*1e-11*0.99*1e6
    lines_58 = math.ceil(9000 / 58)
    mxc_pass_58 = lines_58 * (KRINNER_DRIVE["MXC_uW"] + KRINNER_OUTPUT["MXC_uW"])
    mxc_act_58 = lines_58 * 58 * (10.0 ** ((-100.0 + 20.0) / 10.0) * 1e-3) * 0.99 * 1e6
    mxc_tot_58 = mxc_pass_58 + mxc_act_58
    k4_58_7p5 = lines_58 * (KRINNER_DRIVE["4K_mW"] + KRINNER_OUTPUT["4K_mW"] + 7.5) / 1e3

    lines_163 = math.ceil(9000 / 163)
    k4_163_2p1 = lines_163 * (2.0 + 2.1) / 1e3
    k4_163_7p8 = lines_163 * (2.0 + 7.8) / 1e3

    ok = (
        abs(mxc_tot_58 - 5.2375752) < 1e-9
        and abs(k4_58_7p5 - 1.482) < 1e-9
        and abs(k4_163_2p1 - 0.2296) < 1e-9
        and abs(k4_163_7p8 - 0.5488) < 1e-9
    )
    return {
        "ok": ok,
        "exp110_NL58_lines": lines_58,
        "exp110_NL58_mxc_uW": mxc_tot_58,
        "exp110_NL58_4K_7p5mW_W": k4_58_7p5,
        "exp112_NL163_lines": lines_163,
        "exp112_NL163_4K_2p1mW_W": k4_163_2p1,
        "exp112_NL163_4K_7p8mW_W": k4_163_7p8,
    }


def thermal_5stage_20mk(
    n_channels: int,
    nl: int,
    hemt_mw: float,
    tone_dbm: float = -100.0,
    include_system_overhead: bool = True,
    still_out_uw: float = KRINNER_OUTPUT["Still_uW"],
) -> Dict:
    """Complete 5-stage thermal budget for 20 mK Elzerman baseline (S6.8=D)."""
    lines = math.ceil(n_channels / nl)
    # Active RF dissipation from staged 20 dB (4K) + 10 dB (Still) + 10 dB (CP) + 20 dB (MXC)
    p_dev_w = 10.0 ** (tone_dbm / 10.0) * 1e-3
    act_mxc_uW = n_channels * (p_dev_w * 100.0) * 0.99 * 1e6
    act_cp_uW = n_channels * (p_dev_w * 1000.0) * 0.90 * 1e6
    act_still_mW = n_channels * (p_dev_w * 1e4) * 0.90 * 1e3
    act_4k_W = n_channels * (p_dev_w * 1e6) * 0.99

    ro_50k_W = lines * (KRINNER_DRIVE["50K_mW"] + KRINNER_OUTPUT["50K_mW"]) / 1e3
    ro_4k_W = lines * (KRINNER_DRIVE["4K_mW"] + KRINNER_OUTPUT["4K_mW"] + hemt_mw) / 1e3 + act_4k_W
    ro_still_mW = lines * (KRINNER_DRIVE["Still_uW"] + still_out_uw) / 1e3 + act_still_mW
    ro_cp_uW = lines * (KRINNER_DRIVE["CP_uW"] + KRINNER_OUTPUT["CP_uW"]) + act_cp_uW
    ro_mxc_uW = lines * (KRINNER_DRIVE["MXC_uW"] + KRINNER_OUTPUT["MXC_uW"]) + act_mxc_uW

    ov = SYSTEM_OVERHEAD_20MK if include_system_overhead else {k: 0.0 for k in SYSTEM_OVERHEAD_20MK}
    tot_50k_W = ro_50k_W + ov["50K_W"]
    tot_4k_W = ro_4k_W + ov["4K_W"]
    tot_still_mW = ro_still_mW + ov["Still_mW"]
    tot_cp_uW = ro_cp_uW + ov["CP_uW"]
    tot_mxc_uW = ro_mxc_uW + ov["MXC_uW"]

    cap = CAPACITIES_20MK_PT410
    return {
        "mode": "20mK_Elzerman_S6.8_D",
        "n_channels": n_channels,
        "nl": nl,
        "lines": lines,
        "hemt_mw": hemt_mw,
        "tone_dbm": tone_dbm,
        "readout_only": {
            "50K_W": ro_50k_W,
            "4K_W": ro_4k_W,
            "Still_mW": ro_still_mW,
            "CP_uW": ro_cp_uW,
            "MXC_uW": ro_mxc_uW,
        },
        "total": {
            "50K_W": tot_50k_W,
            "4K_W": tot_4k_W,
            "Still_mW": tot_still_mW,
            "CP_uW": tot_cp_uW,
            "MXC_uW": tot_mxc_uW,
        },
        "utilization_pt410": {
            "50K_frac": tot_50k_W / cap["50K_W"],
            "4K_frac": tot_4k_W / cap["4K_W"],
            "Still_frac": tot_still_mW / cap["Still_mW"],
            "CP_frac": tot_cp_uW / cap["CP_uW"],
            "MXC_20mK_frac": tot_mxc_uW / cap["MXC_20mK_uW"],
            "MXC_100mK_frac": tot_mxc_uW / cap["MXC_100mK_uW"],
        },
        "closes_pt410_all_stages": bool(
            tot_50k_W < cap["50K_W"]
            and tot_4k_W < cap["4K_W"]
            and tot_still_mW < cap["Still_mW"]
            and tot_cp_uW < cap["CP_uW"]
            and tot_mxc_uW < cap["MXC_20mK_uW"]
        ),
        "closes_pt420_all_stages": bool(
            tot_50k_W < 55.0
            and tot_4k_W < 2.0
            and tot_still_mW < cap["Still_mW"]
            and tot_cp_uW < cap["CP_uW"]
            and tot_mxc_uW < cap["MXC_20mK_uW"]
        ),
    }


def thermal_3stage_1k(
    n_channels: int,
    nl: int,
    hemt_mw: float,
    tone_dbm: float = -100.0,
    include_system_overhead: bool = True,
) -> Dict:
    """Complete 3-stage thermal budget for 1-1.5 K Hot-Readout PSB alternative (S6.8=C)."""
    lines = math.ceil(n_channels / nl)
    p_dev_w = 10.0 ** (tone_dbm / 10.0) * 1e-3
    # Staged attenuation: 20 dB @ 4 K + 20 dB @ 1 K
    act_1k_mW = n_channels * (p_dev_w * 100.0) * 0.99 * 1e3
    act_4k_W = n_channels * (p_dev_w * 1e4) * 0.99

    ro_50k_W = lines * (KRINNER_DRIVE["50K_mW"] + KRINNER_OUTPUT["50K_mW"]) / 1e3
    ro_4k_W = lines * (KRINNER_DRIVE["4K_mW"] + KRINNER_OUTPUT["4K_mW"] + hemt_mw) / 1e3 + act_4k_W
    ro_1k_mW = lines * LINE_1K_PASSIVE_MW + act_1k_mW

    ov = SYSTEM_OVERHEAD_1K if include_system_overhead else {k: 0.0 for k in SYSTEM_OVERHEAD_1K}
    tot_50k_W = ro_50k_W + ov["50K_W"]
    tot_4k_W = ro_4k_W + ov["4K_W"]
    tot_1k_mW = ro_1k_mW + ov["stage1K_mW"]

    cap = CAPACITIES_1K_PT410
    return {
        "mode": "1K_HotPSB_S6.8_C",
        "n_channels": n_channels,
        "nl": nl,
        "lines": lines,
        "hemt_mw": hemt_mw,
        "tone_dbm": tone_dbm,
        "readout_only": {"50K_W": ro_50k_W, "4K_W": ro_4k_W, "stage1K_mW": ro_1k_mW},
        "total": {"50K_W": tot_50k_W, "4K_W": tot_4k_W, "stage1K_mW": tot_1k_mW},
        "utilization_pt410": {
            "50K_frac": tot_50k_W / cap["50K_W"],
            "4K_frac": tot_4k_W / cap["4K_W"],
            "stage1K_frac": tot_1k_mW / cap["stage1K_mW"],
        },
        "closes_pt410_all_stages": bool(
            tot_50k_W < cap["50K_W"] and tot_4k_W < cap["4K_W"] and tot_1k_mW < cap["stage1K_mW"]
        ),
        "closes_pt420_all_stages": bool(
            tot_50k_W < 55.0 and tot_4k_W < 2.0 and tot_1k_mW < cap["stage1K_mW"]
        ),
    }


def rf_readout_snr_budget(
    T_phys_K: float,
    T_lna_K: float,
    tone_dbm: float = -100.0,
    f_hz: float = 500e6,
    ql: float = 1000.0,
    delta_gamma: float = 0.05,
    insertion_loss_db: float = 1.5,
    target_snr: float = 10.0,
    n_freq_points: int = 200,
) -> Dict:
    """Dispersive / rf-SET reflectometry SNR & integration-time budget at -100 dBm/tone.

    Signal power at LNA input: P_sig = G_loss * P_tone * |Delta_Gamma|^2 / 4.
    System noise referred to resonator output: T_sys = T_phys + h*f/(2*kB) + T_LNA/G_loss.
    """
    p_tone_w = 10.0 ** (tone_dbm / 10.0) * 1e-3
    g_loss = 10.0 ** (-insertion_loss_db / 10.0)
    t_quantum = H_PLANCK * f_hz / (2.0 * KB)
    t_sys = T_phys_K + t_quantum + T_lna_K / g_loss
    p_sig_w = g_loss * p_tone_w * (delta_gamma ** 2) / 4.0
    noise_psd_w_per_hz = KB * t_sys
    # Amplitude SNR = sqrt(P_sig * tau / (kB * T_sys))
    tau_target_s = (target_snr ** 2) * noise_psd_w_per_hz / p_sig_w
    snr_at_1ms = math.sqrt(p_sig_w * 1e-3 / noise_psd_w_per_hz)
    sweep_time_ms = n_freq_points * tau_target_s * 1e3
    # Required fractional frequency shift delta_f/f0 = |Delta_Gamma| / (2 * Ql)
    req_df_over_f = delta_gamma / (2.0 * ql)
    return {
        "T_phys_K": T_phys_K,
        "T_lna_K": T_lna_K,
        "tone_dbm": tone_dbm,
        "f_MHz": f_hz / 1e6,
        "Ql": ql,
        "delta_gamma": delta_gamma,
        "req_df_over_f": req_df_over_f,
        "insertion_loss_db": insertion_loss_db,
        "T_sys_K": t_sys,
        "P_sig_fW": p_sig_w * 1e15,
        "tau_for_SNR10_ms": tau_target_s * 1e3,
        "SNR_at_1ms": snr_at_1ms,
        "sweep_200pt_SNR10_ms": sweep_time_ms,
    }


def throughput_comparison(
    n_channels: int = 9000,
    duty_cycle: float = 0.50,
    t_eff_20mk_s: float = 1.445,
    overhead_1k_exp117: float = 3.164952263941216,
    p_ancilla_1k_scenarios: Dict[str, float] | None = None,
) -> Dict:
    """Compare daily certified K=8 register throughput: 20 mK baseline vs 1 K hot-readout."""
    if p_ancilla_1k_scenarios is None:
        p_ancilla_1k_scenarios = {
            "optimistic_Exp118_p1.0": 1.0,
            "moderate_R8_p0.85": 0.85,
            "tight_R8_p0.50": 0.50,
        }
    active_s_per_day = 86400.0 * duty_cycle
    raw_meas_20mk = n_channels * active_s_per_day / t_eff_20mk_s
    t_eff_1k = t_eff_20mk_s * overhead_1k_exp117
    raw_meas_1k = n_channels * active_s_per_day / t_eff_1k

    out = {
        "n_channels": n_channels,
        "duty_cycle": duty_cycle,
        "baseline_20mK": {
            "t_eff_s": t_eff_20mk_s,
            "measurements_per_day": raw_meas_20mk,
            "certified_ModB_f1pct_per_day": raw_meas_20mk * 0.51,
            "certified_ModA_3p8nm_per_day": raw_meas_20mk * 0.693,
        },
        "hot_1K_scenarios": {},
    }
    for label, p_anc in p_ancilla_1k_scenarios.items():
        out["hot_1K_scenarios"][label] = {
            "p_ancilla": p_anc,
            "t_eff_s": t_eff_1k,
            "effective_time_per_usable_cell_s": t_eff_1k / max(p_anc, 1e-9),
            "slowdown_vs_20mK": overhead_1k_exp117 / max(p_anc, 1e-9),
            "certified_ModB_f1pct_per_day": raw_meas_1k * 0.51 * p_anc,
            "certified_ModA_3p8nm_per_day": raw_meas_1k * 0.693 * p_anc,
        }
    return out


if __name__ == "__main__":
    gate = replicate_exp110_exp112_gate()
    print("Replication gate:", gate)
    for nl in (110, 126, 160, 163):
        for hemt in (2.1, 7.8, 10.5):
            b20 = thermal_5stage_20mk(9000, nl, hemt)
            print(
                f"20mK NL={nl:3d} ({b20['lines']:2d} lines) HEMT={hemt:4.1f} mW -> "
                f"50K={b20['total']['50K_W']:.2f}W 4K={b20['total']['4K_W']:.3f}W "
                f"Still={b20['total']['Still_mW']:.2f}mW CP={b20['total']['CP_uW']:.1f}uW "
                f"MXC={b20['total']['MXC_uW']:.2f}uW PT410={b20['closes_pt410_all_stages']}"
            )
    b1k = thermal_3stage_1k(9000, 160, 7.8)
    print("1K NL=160 HEMT=7.8 mW:", b1k["total"], "PT410:", b1k["closes_pt410_all_stages"])
    print("SNR 20mK (1.4K LNA):", rf_readout_snr_budget(0.02, 1.4))
    print("SNR 1.5K (3.0K LNA):", rf_readout_snr_budget(1.5, 3.0))
