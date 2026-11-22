"""Exp127: Physical Circuit & Monte Carlo Simulation of the 8-Channel IBIC Detector Front-End.

Runs first-principles modeling of ``src/board/detector_frontend.py`` (v2.0):
  1. Lindhard nuclear/electronic stopping partition for 31P+ in Si (5, 10, 20 keV).
  2. Exact Laplace transfer function H(s) (finite op-amp GBP, Cf, Rf, CR-RC shaper).
  3. Time-domain transient pulse simulation (signal.lsim / FFT cross-checked) +
     hysteresis comparator digital COUNT_HIT output.
  4. Exact Parseval noise quadrature ENC(C_det, tau_s, T) decomposing series,
     1/f flicker, Rf Johnson, leakage/current shot, and shaper thermal noise.
  5. Rice threshold-upcrossing false-trigger rate per 1 ms blanker watchdog window.
  6. 50,000-ion Monte Carlo detection efficiency eta(C_det) across C_det in [0.2, 2.0] pF
     comparing RT-300K/200ns baseline vs RT-300K/1.2us vs Cold-100K/1.2us in-cryo CSA.
  7. Automated ERC check on generated KiCad .net and SPICE .cir artifacts.
  8. Refreshes v2.24 factory & CellISA program demo certificates (100% populated lines_Hz).

Epistemic status: {Model}, no_lab_measurement=true.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from board.detector_frontend import (  # noqa: E402
    CHANNELS,
    CIRCUIT_PARAMS,
    build_board_design,
    generate_board_artifacts,
    validate_netlist,
)
from machine_control.config import MachineConfig  # noqa: E402
from machine_control.factory import Factory  # noqa: E402
from machine_control.programmer import AtomCellProgrammer, builtin_program  # noqa: E402

OUT = ROOT / "results" / "exp127_detector_frontend_sim"

# Fundamental constants (SI)
Q_E = 1.602176634e-19
K_B = 1.380649e-23
A0_NM = 0.05291772109
E2_EV_NM = 1.43996454784
FANO_SI = 0.115


# ---------------------------------------------------------------------------
# 1. First-Principles Lindhard Electronic/Nuclear Partition (31P+ in Si)
# ---------------------------------------------------------------------------

def lindhard_31p_in_si(energy_keV: float, temp_K: float = 300.0) -> dict[str, float]:
    """Exact Lindhard universal stopping partition for 31P (Z1=15, M1=30.974) in Si."""
    Z1, M1 = 15.0, 30.973762
    Z2, M2 = 14.0, 28.085
    z_term = Z1 ** (2.0 / 3.0) + Z2 ** (2.0 / 3.0)
    a_L = 0.8853 * A0_NM / math.sqrt(z_term)
    k_L = (
        0.0793
        * (Z1 ** (2.0 / 3.0))
        * math.sqrt(Z2)
        * ((M1 + M2) ** 1.5)
        / ((z_term ** 0.75) * (M1 ** 1.5) * math.sqrt(M2))
    )
    eps = (float(energy_keV) * 1e3) * a_L * M2 / (Z1 * Z2 * E2_EV_NM * (M1 + M2))
    g_eps = 3.0 * (eps ** 0.15) + 0.7 * (eps ** 0.6) + eps
    y_e = (k_L * g_eps) / (1.0 + k_L * g_eps)
    # Pair creation energy in Si: ~3.62 eV at 300 K, ~3.72 eV at 100 K (Canali/Knoll)
    w_eV = 3.62 if temp_K >= 200.0 else 3.72
    e_elec_eV = y_e * float(energy_keV) * 1e3
    mean_pairs = e_elec_eV / w_eV
    straggle_rel = 0.18 if energy_keV <= 6.0 else 0.15
    return {
        "energy_keV": float(energy_keV),
        "temp_K": float(temp_K),
        "epsilon_L": float(eps),
        "k_L": float(k_L),
        "g_epsilon": float(g_eps),
        "Y_e_lindhard": float(y_e),
        "w_Si_eV": float(w_eV),
        "E_elec_eV": float(e_elec_eV),
        "mean_e_pairs": float(mean_pairs),
        "charge_fC": float(mean_pairs * Q_E * 1e15),
        "straggle_rel": float(straggle_rel),
        "fano_sigma_e": float(math.sqrt(FANO_SI * mean_pairs)),
    }


# ---------------------------------------------------------------------------
# 2. Exact Laplace Transfer Function & Parseval Noise Integral
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrontendOperatingPoint:
    name: str
    temp_K: float
    tau_s_s: float
    cf_F: float = 0.25e-12
    rf_Ohm: float = 100e6
    c_par_F: float = 0.25e-12
    c_in_F: float = 0.45e-12        # LTC6268 input capacitance
    en_csa_VrtHz: float = 4.3e-9    # LTC6268 @ 300 K (cold ~2.5 nV/rtHz)
    in_csa_ArtHz: float = 5.5e-15   # LTC6268 input current noise
    fc_1f_Hz: float = 5e3           # 1/f voltage noise corner
    i_leak_A: float = 10e-12        # Pixel diode dark current @ 300 K
    gbp_csa_Hz: float = 500e6       # LTC6268 unity-gain stable GBP
    a0_csa: float = 1e5             # Open-loop DC gain
    g_stage: float = 136.0          # ADA4817-1 non-inverting gain (G/e = 50.03)
    gbp_shp_Hz: float = 1.05e9      # ADA4817-1 GBP
    en_shp_VrtHz: float = 4.0e-9    # ADA4817-1 voltage noise
    rs1_Ohm: float = 2.0e3          # CR resistor (scaled with tau_s if cs fixed)
    rg1_Ohm: float = 100.0
    rg2_Ohm: float = 13.5e3
    rs2_Ohm: float = 2.0e3


def transfer_components(s: np.ndarray, op: FrontendOperatingPoint, c_det_F: float):
    """Evaluate exact Laplace blocks Z_csa(s), H_shp(s), H_total(s), and CSA noise gain."""
    c_in_tot = c_det_F + op.c_par_F + op.c_in_F
    z_f = op.rf_Ohm / (1.0 + s * op.rf_Ohm * op.cf_F)
    y_in = s * c_in_tot
    w_p_csa = 2.0 * math.pi * op.gbp_csa_Hz / op.a0_csa
    a_ol = op.a0_csa / (1.0 + s / w_p_csa)
    # Closed-loop transimpedance of CSA with finite GBP & input capacitance loading
    loop_factor = 1.0 + (1.0 + z_f * y_in) / a_ol
    z_csa = z_f / loop_factor

    # Noise gain from CSA input-referred voltage noise to CSA output
    # V_csa / v_n = (1 + z_f * y_in) / loop_factor
    ng_csa = (1.0 + z_f * y_in) / loop_factor

    # Buffered CR-RC active shaper: CR(tau_s) * Gain(G_stage, GBP) * RC(tau_s)
    h_cr = (s * op.tau_s_s) / (1.0 + s * op.tau_s_s)
    w_cl_shp = 2.0 * math.pi * (op.gbp_shp_Hz / op.g_stage)
    h_gain = op.g_stage / (1.0 + s / w_cl_shp)
    h_rc = 1.0 / (1.0 + s * op.tau_s_s)
    h_shp = h_cr * h_gain * h_rc
    h_total = z_csa * h_shp
    return z_csa, ng_csa, h_shp, h_gain, h_rc, h_total


def transient_pulse(
    op: FrontendOperatingPoint,
    c_det_F: float,
    charge_C: float,
    tau_col_s: float = 1.5e-9,
    t_max_s: float | None = None,
    n_pts: int = 8192,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Compute exact time-domain shaper output V_shp(t) via zero-wraparound FFT.

    Uses an internal time window >= max(24 * tau_s, 10 * tau_f) so the slow CSA
    feedback tail exp(-t / (Rf*Cf)) decays below 5e-5 before periodic wraparound,
    then slices out the requested viewing window [0, t_view].
    """
    tau_f = op.rf_Ohm * op.cf_F
    t_view = t_max_s if t_max_s is not None else max(16.0 * op.tau_s_s, 2.5e-6)
    # Choose fine dt for the viewing window, and pad FFT length >= 10 * tau_f
    dt_target = t_view / 2048.0
    t_pad = max(t_view * 2.0, 10.0 * tau_f, 24.0 * op.tau_s_s)
    n_fft = 1 << int(math.ceil(math.log2(max(n_pts, int(math.ceil(t_pad / dt_target))))))
    n_fft = min(n_fft, 1 << 20)  # cap at 1M points (~40 ms runtime, exact to <1e-4)
    dt = t_pad / n_fft
    freqs = np.fft.rfftfreq(n_fft, d=dt)
    s = 1j * 2.0 * math.pi * freqs

    # Ion collection current I(t) = (Q / tau_col) exp(-t/tau_col) -> I(s) = Q / (1 + s * tau_col)
    i_s = charge_C / (1.0 + s * tau_col_s)
    _, _, _, _, _, h_tot = transfer_components(s, op, c_det_F)
    t0 = 50e-9
    v_full = np.fft.irfft(i_s * h_tot * np.exp(-s * t0), n=n_fft) / dt

    n_view = min(n_fft, max(256, int(math.ceil(t_view / dt))))
    t = np.arange(n_view, dtype=float) * dt
    v_t = v_full[:n_view]
    peak_idx = int(np.argmax(v_t))
    v_peak = float(v_t[peak_idx])
    t_peak_after_hit = float(t[peak_idx] - t0)
    return t, v_t, v_peak, t_peak_after_hit


def simulate_comparator_trace(
    t: np.ndarray,
    v_shp: np.ndarray,
    v_thr: float,
    v_hys: float = 3.3e-3,
    v_high: float = 3.3,
    t_pd_s: float = 4.5e-9,
) -> np.ndarray:
    """Behavioral hysteresis comparator (TLV3501: v_hys=3.3 mV, t_pd=4.5 ns)."""
    dt = float(t[1] - t[0])
    out = np.zeros_like(v_shp)
    state = False
    v_hi = v_thr + 0.5 * v_hys
    v_lo = v_thr - 0.5 * v_hys
    for i, v in enumerate(v_shp):
        if not state and v >= v_hi:
            state = True
        elif state and v <= v_lo:
            state = False
        out[i] = v_high if state else 0.0
    shift = int(round(t_pd_s / dt))
    if shift > 0 and shift < len(out):
        out = np.concatenate([np.zeros(shift), out[:-shift]])
    return out


def cross_check_analytical_lsim(op: FrontendOperatingPoint, c_det_F: float, charge_C: float) -> float:
    """Independent time-domain ODE cross-check using scipy.signal.TransferFunction (ideal op-amp limit)."""
    # H_ideal(s) = (Rf / (1 + s*Rf*Cf)) * (s*tau_s / (1 + s*tau_s)) * G / (1 + s*tau_s) * (1 / (1 + s*tau_col))
    tau_f = op.rf_Ohm * op.cf_F
    tau_s = op.tau_s_s
    tau_cl = op.g_stage / (2.0 * math.pi * op.gbp_shp_Hz)
    tau_col = 1.5e-9
    num = [op.rf_Ohm * tau_s * op.g_stage * charge_C, 0.0]
    den = np.polymul([tau_f, 1.0], [tau_s, 1.0])
    den = np.polymul(den, [tau_s, 1.0])
    den = np.polymul(den, [tau_cl, 1.0])
    den = np.polymul(den, [tau_col, 1.0])
    sys_tf = signal.TransferFunction(num, den)
    t_ode = np.linspace(0.0, 12.0 * tau_s, 4000)
    _, y_ode = signal.impulse(sys_tf, T=t_ode)
    return float(np.max(y_ode))


def compute_enc_and_rice(
    op: FrontendOperatingPoint,
    c_det_F: float,
    thr_sigma: float = 5.5,
    shot_window_s: float = 1e-3,
) -> dict[str, float]:
    """Exact Parseval quadrature of output noise PSD -> ENC breakdown + Rice false trigger."""
    # Dense log-spaced frequency grid from 1 Hz to 500 MHz
    f = np.geomspace(1.0, 5e8, 8000)
    s = 1j * 2.0 * math.pi * f
    _, ng_csa, h_shp, h_gain, h_rc, h_tot = transfer_components(s, op, c_det_F)

    # 1) CSA white series voltage noise
    psd_series = (op.en_csa_VrtHz ** 2) * (np.abs(ng_csa * h_shp) ** 2)
    # 2) CSA 1/f flicker voltage noise
    psd_1f = (op.en_csa_VrtHz ** 2) * (op.fc_1f_Hz / f) * (np.abs(ng_csa * h_shp) ** 2)
    # 3) Feedback resistor Rf thermal Johnson current noise
    i2_rf = 4.0 * K_B * op.temp_K / op.rf_Ohm
    psd_rf = i2_rf * (np.abs(h_tot) ** 2)
    # 4) Diode leakage shot noise + op-amp input current noise
    i2_leak = 2.0 * Q_E * op.i_leak_A + (op.in_csa_ArtHz ** 2)
    psd_leak = i2_leak * (np.abs(h_tot) ** 2)
    # 5) Shaper stage thermal noise (RS1=2k fixed, CS/CP scaled for tau_s; RG1||RG2, ADA4817 e_n, RS2=2k)
    r_fb_eq = (op.rg1_Ohm * op.rg2_Ohm) / (op.rg1_Ohm + op.rg2_Ohm)
    v2_shp_in = (
        op.en_shp_VrtHz ** 2
        + 4.0 * K_B * op.temp_K * (r_fb_eq + op.rs1_Ohm / (1.0 + (2.0 * math.pi * f * op.tau_s_s) ** 2))
    )
    psd_shp = v2_shp_in * (np.abs(h_gain * h_rc) ** 2) + (
        4.0 * K_B * op.temp_K * op.rs2_Ohm * (np.abs(h_rc) ** 2)
    )

    psd_tot = psd_series + psd_1f + psd_rf + psd_leak + psd_shp

    def rms_from_psd(psd: np.ndarray) -> float:
        return float(math.sqrt(max(float(np.trapezoid(psd, f)), 0.0)))

    v_rms_series = rms_from_psd(psd_series)
    v_rms_1f = rms_from_psd(psd_1f)
    v_rms_rf = rms_from_psd(psd_rf)
    v_rms_leak = rms_from_psd(psd_leak)
    v_rms_shp = rms_from_psd(psd_shp)
    v_rms_tot = rms_from_psd(psd_tot)

    # Exact peak response to 1000 electrons -> single-electron sensitivity V_peak(1 e-)
    _, _, v_peak_1ke, t_peak_s = transient_pulse(op, c_det_F, charge_C=1000.0 * Q_E)
    v_per_e = v_peak_1ke / 1000.0

    enc_series = v_rms_series / v_per_e
    enc_1f = v_rms_1f / v_per_e
    enc_rf = v_rms_rf / v_per_e
    enc_leak = v_rms_leak / v_per_e
    enc_shp = v_rms_shp / v_per_e
    enc_tot = v_rms_tot / v_per_e

    # Rice formula for positive-slope threshold crossings of band-limited Gaussian noise
    m0 = float(np.trapezoid(psd_tot, f))
    m2 = float(np.trapezoid(((2.0 * math.pi * f) ** 2) * psd_tot, f))
    f_eff = math.sqrt(m2 / max(m0, 1e-30)) / (2.0 * math.pi)
    f_false_5s = f_eff * math.exp(-0.5 * (5.0 ** 2))
    f_false_thr = f_eff * math.exp(-0.5 * (thr_sigma ** 2))
    p_false_5s = 1.0 - math.exp(-f_false_5s * shot_window_s)
    p_false_thr = 1.0 - math.exp(-f_false_thr * shot_window_s)

    return {
        "c_det_pF": float(c_det_F * 1e12),
        "tau_s_ns": float(op.tau_s_s * 1e9),
        "temp_K": float(op.temp_K),
        "v_per_e_uV": float(v_per_e * 1e6),
        "gain_mV_per_fC": float((v_per_e / Q_E) * 1e-12),
        "t_peak_ns": float(t_peak_s * 1e9),
        "v_rms_mV": float(v_rms_tot * 1e3),
        "v_thr_mV": float(thr_sigma * v_rms_tot * 1e3),
        "enc_series_e": float(enc_series),
        "enc_1f_e": float(enc_1f),
        "enc_rf_e": float(enc_rf),
        "enc_leak_e": float(enc_leak),
        "enc_shaper_e": float(enc_shp),
        "enc_total_e": float(enc_tot),
        "f_eff_MHz": float(f_eff * 1e-6),
        "f_false_5sigma_Hz": float(f_false_5s),
        "p_false_5sigma_1ms": float(p_false_5s),
        "thr_sigma": float(thr_sigma),
        "f_false_thr_Hz": float(f_false_thr),
        "p_false_thr_1ms": float(p_false_thr),
    }


def monte_carlo_eta(
    lind: dict[str, float],
    noise: dict[str, float],
    n_ions: int = 50_000,
    v_hys_mV: float = 3.3,
    seed: int = 12700,
) -> dict[str, float]:
    """50,000-ion Monte Carlo detection efficiency with Lindhard straggle + Fano + ENC + hysteresis."""
    rng = np.random.default_rng(seed)
    S = lind["mean_e_pairs"]
    strag_sigma = lind["straggle_rel"] * S
    enc = noise["enc_total_e"]
    v_per_e_mV = noise["v_per_e_uV"] * 1e-3
    # SPI 16-bit DAC programs V_DAC = V_thr - 0.5*V_hys so comparator rising edge sits
    # accurately at V_thr = thr_sigma * sigma_V while falling edge resets at V_thr - V_hys.
    thr_e = noise["thr_sigma"] * enc

    # Sample electronic energy deposition (truncated positive normal for nuclear straggle)
    e_dep = np.maximum(rng.normal(S, strag_sigma, size=n_ions), 0.0)
    # Add Fano pair-creation fluctuation
    n_pairs = np.maximum(e_dep + rng.normal(0.0, np.sqrt(FANO_SI * np.maximum(e_dep, 1.0))), 0.0)
    # Add electronic noise at peak sample
    q_meas = n_pairs + rng.normal(0.0, enc, size=n_ions)

    detected = q_meas >= thr_e
    eta = float(np.mean(detected))
    # Wilson 95% binomial half-width
    se = math.sqrt(eta * (1.0 - eta) / n_ions)
    snr = S / enc
    return {
        "eta": eta,
        "eta_se": float(se),
        "snr": float(snr),
        "mean_signal_e": float(S),
        "enc_e": float(enc),
        "effective_thr_e": float(thr_e),
        "signal_peak_mV": float(S * v_per_e_mV),
        "thr_mV": float(thr_e * v_per_e_mV),
        "p_false_1ms": float(noise["p_false_thr_1ms"]),
    }


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    preds = json.loads((OUT / "predictions_exp127.json").read_text(encoding="utf-8"))

    # 1) Generate & ERC-validate locked COLD_100K board netlist + SPICE deck
    net_path, cir_path, design, erc_errors = generate_board_artifacts(profile="cold100k")
    assert len(erc_errors) == 0

    # 2) Operating points
    op_rt_200 = FrontendOperatingPoint(
        name="RT_300K_200ns_Rf100M",
        temp_K=300.0,
        tau_s_s=200e-9,
        rf_Ohm=100e6,
        en_csa_VrtHz=4.3e-9,
        i_leak_A=10e-12,
    )
    op_rt_1200 = FrontendOperatingPoint(
        name="RT_300K_1200ns_Rf1G",
        temp_K=300.0,
        tau_s_s=1200e-9,
        rf_Ohm=1e9,
        en_csa_VrtHz=4.3e-9,
        i_leak_A=5e-12,
    )
    op_cold_1200 = FrontendOperatingPoint(
        name="COLD_100K_1200ns_Rf1G",
        temp_K=100.0,
        tau_s_s=1200e-9,
        rf_Ohm=1e9,
        en_csa_VrtHz=2.0e-9,       # cooled JFET/CMOS front-end on cold island (UNSW/Melbourne class)
        in_csa_ArtHz=0.5e-15,      # cooled gate leakage shot noise <0.5 fA/rtHz
        fc_1f_Hz=2e3,
        i_leak_A=0.05e-12,         # pixel dark current frozen at 100 K
    )

    # 3) Lindhard table
    lindhard_rt = {str(int(E)): lindhard_31p_in_si(E, 300.0) for E in (5.0, 10.0, 20.0)}
    lindhard_cold = {str(int(E)): lindhard_31p_in_si(E, 100.0) for E in (5.0, 10.0, 20.0)}

    # 4) Laplace Bode & Transient cross-check (RT 200 ns baseline at C_det=0.5 pF)
    q_10_exp72 = 1111.111 * Q_E
    t_tr, v_tr_exp72, vpk_exp72, tpk_exp72 = transient_pulse(op_rt_200, 0.5e-12, q_10_exp72)
    vpk_ode = cross_check_analytical_lsim(op_rt_200, 0.5e-12, q_10_exp72)
    ode_rel_diff = abs(vpk_exp72 - vpk_ode) / max(vpk_ode, 1e-12)
    ideal_50x_mV = (q_10_exp72 / op_rt_200.cf_F) * 50.0 * 1e3

    # 5) Shaping-time sweep tau_s in [50 ns .. 2500 ns] at C_det=0.5 pF
    tau_grid_ns = [50, 100, 150, 200, 300, 500, 800, 1200, 1600, 2000, 2500]
    enc_vs_tau_rt = []
    enc_vs_tau_cold = []
    for tau_ns in tau_grid_ns:
        o_rt = FrontendOperatingPoint(
            name=f"rt_{tau_ns}", temp_K=300.0, tau_s_s=tau_ns * 1e-9, rf_Ohm=100e6
        )
        o_cd = FrontendOperatingPoint(
            name=f"cold_{tau_ns}",
            temp_K=100.0,
            tau_s_s=tau_ns * 1e-9,
            rf_Ohm=1e9,
            en_csa_VrtHz=2.0e-9,
            in_csa_ArtHz=0.5e-15,
            fc_1f_Hz=2e3,
            i_leak_A=0.05e-12,
        )
        enc_vs_tau_rt.append(compute_enc_and_rice(o_rt, 0.5e-12))
        enc_vs_tau_cold.append(compute_enc_and_rice(o_cd, 0.5e-12))

    best_rt = min(enc_vs_tau_rt, key=lambda r: r["enc_total_e"])
    best_cold = min(enc_vs_tau_cold, key=lambda r: r["enc_total_e"])
    enc_rt_200_05 = next(r for r in enc_vs_tau_rt if int(round(r["tau_s_ns"])) == 200)
    enc_cold_1200_05 = next(r for r in enc_vs_tau_cold if int(round(r["tau_s_ns"])) == 1200)

    # 6) Monte Carlo C_det sweep [0.2 .. 2.0 pF] for all 3 frontend configs & 5/10/20 keV
    cdet_grid_pF = [0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0]
    mc_results: dict[str, dict[str, list[dict]]] = {}
    for op in (op_rt_200, op_rt_1200, op_cold_1200):
        l_tbl = lindhard_rt if op.temp_K >= 200.0 else lindhard_cold
        mc_results[op.name] = {}
        for e_str in ("5", "10", "20"):
            rows = []
            for idx, c_pF in enumerate(cdet_grid_pF):
                n_info = compute_enc_and_rice(op, c_pF * 1e-12, thr_sigma=5.5)
                mc = monte_carlo_eta(
                    l_tbl[e_str], n_info, n_ions=50_000, v_hys_mV=3.3, seed=12700 + idx * 31 + int(e_str)
                )
                rows.append({"c_det_pF": c_pF, **mc})
            mc_results[op.name][f"{e_str}keV"] = rows

    # Extract key lookup metrics for verdicts
    def _lookup(op_name: str, e_key: str, c_pF: float) -> dict:
        return next(r for r in mc_results[op_name][e_key] if abs(r["c_det_pF"] - c_pF) < 1e-9)

    rt200_5_05 = _lookup("RT_300K_200ns_Rf100M", "5keV", 0.5)
    rt200_10_05 = _lookup("RT_300K_200ns_Rf100M", "10keV", 0.5)
    cold1200_5_05 = _lookup("COLD_100K_1200ns_Rf1G", "5keV", 0.5)
    cold1200_5_02 = _lookup("COLD_100K_1200ns_Rf1G", "5keV", 0.2)
    cold1200_10_05 = _lookup("COLD_100K_1200ns_Rf1G", "10keV", 0.5)

    verdicts = {
        "CZ1_LINDHARD_MONOTONIC": bool(
            lindhard_rt["20"]["Y_e_lindhard"]
            > lindhard_rt["10"]["Y_e_lindhard"]
            > lindhard_rt["5"]["Y_e_lindhard"]
            and 300.0 <= lindhard_rt["5"]["mean_e_pairs"] <= 420.0
            and lindhard_rt["5"]["Y_e_lindhard"] < 0.35
        ),
        "CZ2_LAPLACE_PEAK_AND_BALLISTIC": bool(
            abs(tpk_exp72 * 1e9 - 200.0) / 200.0 <= 0.15
            and abs(vpk_exp72 * 1e3 - ideal_50x_mV) / ideal_50x_mV <= 0.10
            and ode_rel_diff < 0.02
        ),
        "CZ3_ENC_NOISE_CORNER": bool(
            400.0 <= best_rt["tau_s_ns"] <= 2000.0
            and best_rt["enc_total_e"] <= 0.75 * enc_rt_200_05["enc_total_e"]
        ),
        "CZ4_RT200NS_5KEV_EXPOSED": bool(
            rt200_5_05["eta"] < 0.99 and rt200_10_05["eta"] >= 0.99
        ),
        "CZ5_COLD_OPT_5KEV_CLOSES": bool(
            enc_cold_1200_05["enc_total_e"] < 35.0
            and cold1200_5_05["eta"] >= 0.99
            and cold1200_5_02["eta"] >= 0.99
            and cold1200_5_05["p_false_1ms"] < 1e-3
        ),
        "CZ6_ERC_CLEAN": bool(len(erc_errors) == 0 and len(design.components) >= 180),
    }

    # 7) Generate refreshed v2.24 factory & CellISA program demo certificates (100% populated lines_Hz!)
    cfg_v224 = MachineConfig.v224_baseline(detector_eta=round(cold1200_5_05["eta"], 4))
    certs_path = OUT / "certs_v224_demo.jsonl"
    rep_v224 = Factory(cfg=cfg_v224).run(4000, cert_path=certs_path)

    prog_certs_path = OUT / "prog_certs_v224_demo.jsonl"
    programmer_g = AtomCellProgrammer(
        b_field_T=cfg_v224.b_sample_T,
        pulse_mode="grape",
        readout_visibility=cfg_v224.readout_visibility,
        pulse_error_eps=cfg_v224.pulse_error_eps,
    )
    prog_summary = {}
    all_pcerts = []
    for pname in ("bell", "ghz", "repcode3"):
        _sched, pcert = programmer_g.execute_and_certify(
            rep_v224.certificates[0], builtin_program(pname), verify_corners=True
        )
        all_pcerts.append(pcert)
        prog_summary[pname] = {
            "pulse_mode": pcert.pulse_mode,
            "pulse_count": pcert.pulse_count,
            "duration_us": pcert.total_duration_us,
            "F_nom": pcert.nominal_state_fidelity,
            "F_corner_min": pcert.corner_min_fidelity,
            "F_corner_mean": pcert.corner_mean_fidelity,
            "dd_coherence_gain": pcert.dd_coherence_gain,
            "certified": pcert.certified,
            "sha256_valid": pcert.verify_signature(),
        }
    # Also run qft3 (GRAPE) and save all 4 program certificates
    _sched_q, pcert_q = programmer_g.execute_and_certify(
        rep_v224.certificates[0], builtin_program("qft3"), verify_corners=True
    )
    all_pcerts.append(pcert_q)
    prog_summary["qft3"] = {
        "pulse_mode": pcert_q.pulse_mode,
        "pulse_count": pcert_q.pulse_count,
        "duration_us": pcert_q.total_duration_us,
        "F_nom": pcert_q.nominal_state_fidelity,
        "F_corner_min": pcert_q.corner_min_fidelity,
        "F_corner_mean": pcert_q.corner_mean_fidelity,
        "dd_coherence_gain": pcert_q.dd_coherence_gain,
        "certified": pcert_q.certified,
        "sha256_valid": pcert_q.verify_signature(),
    }
    from dataclasses import asdict
    with prog_certs_path.open("w", encoding="utf-8") as f:
        for pc in all_pcerts:
            f.write(json.dumps(asdict(pc)) + "\n")

    out_data = {
        "experiment": "exp127_detector_frontend_sim",
        "date": "2026-11-22",
        "no_lab_measurement": True,
        "epistemic_tag": "Model",
        "runtime_s": round(time.time() - t0, 2),
        "predictions": preds,
        "verdicts": verdicts,
        "success_rule_met": bool(
            all(verdicts[k] for k in ("CZ1_LINDHARD_MONOTONIC", "CZ2_LAPLACE_PEAK_AND_BALLISTIC",
                                       "CZ3_ENC_NOISE_CORNER", "CZ5_COLD_OPT_5KEV_CLOSES", "CZ6_ERC_CLEAN"))
        ),
        "board_erc": {
            "profile": design.profile,
            "channels": CHANNELS,
            "components": len(design.components),
            "nets": len(design.nets),
            "erc_errors": len(erc_errors),
            "netlist_file": str(net_path.relative_to(ROOT)),
            "spice_file": str(cir_path.relative_to(ROOT)),
        },
        "lindhard_300K": lindhard_rt,
        "lindhard_100K": lindhard_cold,
        "laplace_transient_check": {
            "charge_1111e_ideal_50x_mV": round(ideal_50x_mV, 3),
            "fft_peak_mV": round(vpk_exp72 * 1e3, 3),
            "ode_lsim_peak_mV": round(vpk_ode * 1e3, 3),
            "fft_vs_ode_rel_diff": round(ode_rel_diff, 5),
            "t_peak_ns": round(tpk_exp72 * 1e9, 2),
        },
        "enc_operating_points_C0p5": {
            "RT_300K_200ns_Rf100M": enc_rt_200_05,
            "RT_300K_optimal_tau": best_rt,
            "COLD_100K_1200ns_Rf1G": enc_cold_1200_05,
            "COLD_100K_optimal_tau": best_cold,
        },
        "enc_vs_tau_rt_C0p5": enc_vs_tau_rt,
        "enc_vs_tau_cold_C0p5": enc_vs_tau_cold,
        "monte_carlo_eta": mc_results,
        "v224_demo_factory": {
            "preset": cfg_v224.preset_name,
            "beamlets": cfg_v224.beamlets,
            "beam_pitch_mm": cfg_v224.beam_pitch_mm,
            "shot_cycle_s": cfg_v224.shot_cycle_s,
            "raw_write_shots_per_day": float(cfg_v224.beamlets / cfg_v224.shot_cycle_s * 86400.0 * cfg_v224.duty_cycle),
            "slots": rep_v224.slots,
            "certified": rep_v224.certified,
            "slot_success": round(rep_v224.slot_success, 4),
            "shots_per_register": round(rep_v224.shots_per_register, 4),
            "specs_per_register": round(rep_v224.specs_per_register, 4),
            "analytic_per_day": rep_v224.certified_per_day_analytic,
            "non_empty_lines_Hz": sum(1 for c in rep_v224.certificates if len(c.lines_Hz) == 8),
            "certs_file": str(certs_path.relative_to(ROOT)),
        },
        "v224_demo_cellisa": prog_summary,
    }
    (OUT / "exp127.json").write_text(json.dumps(out_data, indent=2), encoding="utf-8")

    # Export exact Bode & transient arrays for pure-stdlib/PyCairo plotting (plot127.py)
    f_bode = np.geomspace(1e2, 1e8, 300)
    s_bode = 1j * 2.0 * math.pi * f_bode
    _, _, _, _, _, h_rt200 = transfer_components(s_bode, op_rt_200, 0.5e-12)
    _, _, _, _, _, h_cold1200 = transfer_components(s_bode, op_cold_1200, 0.5e-12)
    # Transimpedance in dB relative to 1 Ohm (and normalized mV/fC scale)
    t_view_rt, v5_rt, _, _ = transient_pulse(op_rt_200, 0.5e-12, lindhard_rt["5"]["charge_fC"] * 1e-15, t_max_s=1.8e-6)
    _, v10_rt, _, _ = transient_pulse(op_rt_200, 0.5e-12, lindhard_rt["10"]["charge_fC"] * 1e-15, t_max_s=1.8e-6)
    _, v20_rt, _, _ = transient_pulse(op_rt_200, 0.5e-12, lindhard_rt["20"]["charge_fC"] * 1e-15, t_max_s=1.8e-6)
    t_view_cd, v5_cd, _, _ = transient_pulse(op_cold_1200, 0.5e-12, lindhard_cold["5"]["charge_fC"] * 1e-15, t_max_s=7.5e-6)
    _, v10_cd, _, _ = transient_pulse(op_cold_1200, 0.5e-12, lindhard_cold["10"]["charge_fC"] * 1e-15, t_max_s=7.5e-6)
    _, v20_cd, _, _ = transient_pulse(op_cold_1200, 0.5e-12, lindhard_cold["20"]["charge_fC"] * 1e-15, t_max_s=7.5e-6)
    vthr_cd = enc_cold_1200_05["v_thr_mV"] * 1e-3
    # DAC biased by -0.5*V_hys so rising edge sits at vthr_cd
    cmp_cd_5 = simulate_comparator_trace(t_view_cd, v5_cd, v_thr=vthr_cd - 0.5 * 3.3e-3, v_hys=3.3e-3)
    stride_cd = max(1, len(t_view_cd) // 500)
    stride_rt = max(1, len(t_view_rt) // 500)
    traces = {
        "bode": {
            "freq_Hz": [float(x) for x in f_bode],
            "mag_dBOhm_rt200": [float(20.0 * math.log10(max(abs(h), 1e-30))) for h in h_rt200],
            "phase_deg_rt200": [float(np.degrees(np.angle(h))) for h in h_rt200],
            "mag_dBOhm_cold1200": [float(20.0 * math.log10(max(abs(h), 1e-30))) for h in h_cold1200],
            "phase_deg_cold1200": [float(np.degrees(np.angle(h))) for h in h_cold1200],
        },
        "transient_cold1200": {
            "t_ns": [float(x * 1e9) for x in t_view_cd[::stride_cd]],
            "v5_mV": [float(x * 1e3) for x in v5_cd[::stride_cd]],
            "v10_mV": [float(x * 1e3) for x in v10_cd[::stride_cd]],
            "v20_mV": [float(x * 1e3) for x in v20_cd[::stride_cd]],
            "cmp5_V": [float(x) for x in cmp_cd_5[::stride_cd]],
            "v_thr_mV": float(enc_cold_1200_05["v_thr_mV"]),
            "v_hys_mV": 3.3,
        },
        "transient_rt200": {
            "t_ns": [float(x * 1e9) for x in t_view_rt[::stride_rt]],
            "v5_mV": [float(x * 1e3) for x in v5_rt[::stride_rt]],
            "v10_mV": [float(x * 1e3) for x in v10_rt[::stride_rt]],
            "v20_mV": [float(x * 1e3) for x in v20_rt[::stride_rt]],
            "v_thr_mV": float(enc_rt_200_05["v_thr_mV"]),
        },
    }
    (OUT / "exp127_traces.json").write_text(json.dumps(traces), encoding="utf-8")

    print("=== EXP127 VERDICTS ===")
    for k, v in verdicts.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"success_rule_met = {out_data['success_rule_met']} ({out_data['runtime_s']}s)")
    print(
        f"ENC(C=0.5pF): RT_200ns={enc_rt_200_05['enc_total_e']:.1f} e- | "
        f"RT_opt({best_rt['tau_s_ns']:.0f}ns)={best_rt['enc_total_e']:.1f} e- | "
        f"COLD_1200ns={enc_cold_1200_05['enc_total_e']:.1f} e-"
    )
    print(
        f"MC eta(C=0.5pF): RT200/5keV={rt200_5_05['eta']:.4f}, RT200/10keV={rt200_10_05['eta']:.4f}, "
        f"COLD1200/5keV={cold1200_5_05['eta']:.5f} (P_false={cold1200_5_05['p_false_1ms']:.2e}), "
        f"COLD1200/10keV={cold1200_10_05['eta']:.5f}"
    )


if __name__ == "__main__":
    main()
