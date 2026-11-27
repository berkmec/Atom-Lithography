"""Exact multi-Ornstein-Uhlenbeck colored 1/f^alpha noise generator & DD filter functions (Exp137).

Generates statistically exact real-time colored charge-detuning trajectories delta_eps(t)
matching one-sided PSD S_eps(f) = S_0^2 * (1 Hz / f)^alpha over [f_ir = 1 Hz, f_uv = 100 MHz]
for alpha in {0.8, 1.0, 1.2}, using M logarithmically spaced Ornstein-Uhlenbeck fluctuators
with exact analytical continuum normalization sin(pi * alpha / 2).

Also computes exact Cywinski et al. (PRB 77, 174509, 2008) dynamical-decoupling filter
function integrals for Bare, FF-Echo (N=2), and XY4 (N=4) cross-validation.

Epistemic scope: {Model} / {Sayisal-Simulasyon}. No laboratory measurement.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# Exact SI constant: 1 ueV / h = 0.2417989242 GHz
H_PLANCK = 6.62607015e-34
E_CHARGE = 1.602176634e-19
GHZ_PER_UEV = (E_CHARGE * 1e-6) / H_PLANCK / 1e9

# Consistent 12-decade [1e-2, 1e10] Hz band matching Exp131 ONE_OVER_F_RMS_FACTOR = sqrt(ln(10^12)) = 5.2565 (OBS-111)
DEFAULT_F_IR_HZ = 1.0e-2
DEFAULT_F_UV_HZ = 1.0e10
DEFAULT_N_FLUCT = 60


def build_ou_bank_params(
    alpha: float = 1.0,
    s0_uev: float = 1.0,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
    n_fluct: int = DEFAULT_N_FLUCT,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (corner_freqs_hz, sigma_m_uev) for M independent OU fluctuators.

    Each fluctuator m obeys dx_m = -2*pi*f_m*x_m*dt + sqrt(4*pi*f_m)*sigma_m*dW_m,
    with stationary variance sigma_m^2 and one-sided Lorentzian PSD:
        S_m(f) = (2 * sigma_m^2 / (pi * f_m)) / (1 + (f / f_m)^2),  int_0^inf S_m(f) df = sigma_m^2.

    Using exact continuum identity int_0^inf u^(alpha-1)/(1+u^2) du = pi / (2 * sin(pi*alpha/2)),
    setting sigma_m^2 = s0^2 * sin(pi*alpha/2) * f_m^(1-alpha) * d(ln f) reproduces
    S_sum(f) = s0^2 / f^alpha across [10 Hz, 10 MHz] within <10% and total band RMS within <2%.
    """
    if not (0.2 < alpha < 1.8):
        raise ValueError(f"alpha must lie in (0.2, 1.8), got {alpha}")
    f_m = np.geomspace(f_ir_hz, f_uv_hz, n_fluct)
    dlnf = math.log(f_uv_hz / f_ir_hz) / (n_fluct - 1)
    c_alpha = math.sin(0.5 * math.pi * alpha)
    var_m = (s0_uev ** 2) * c_alpha * (f_m ** (1.0 - alpha)) * dlnf
    return f_m, np.sqrt(var_m)


def exact_band_rms_uev(
    alpha: float = 1.0,
    s0_uev: float = 1.0,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
) -> float:
    """Analytical RMS sqrt(int_{f_ir}^{f_uv} s0^2 / f^alpha df) in ueV."""
    if abs(alpha - 1.0) < 1e-9:
        var = (s0_uev ** 2) * math.log(f_uv_hz / f_ir_hz)
    else:
        var = (s0_uev ** 2) * (f_uv_hz ** (1.0 - alpha) - f_ir_hz ** (1.0 - alpha)) / (1.0 - alpha)
    return math.sqrt(max(0.0, var))


def verify_ou_psd_spectrum(
    alphas: list[float] | None = None,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
    n_fluct: int = DEFAULT_N_FLUCT,
) -> dict[str, Any]:
    """Analytically verify multi-OU PSD fidelity and band RMS for alpha in {0.8, 1.0, 1.2}."""
    if alphas is None:
        alphas = [0.8, 1.0, 1.2]
    f_eval = np.geomspace(f_ir_hz * 10.0, f_uv_hz / 10.0, 25)
    f_plot = np.geomspace(f_ir_hz, f_uv_hz, 41)
    results: dict[str, Any] = {}
    worst_psd_err = 0.0
    worst_rms_err = 0.0

    for alpha in alphas:
        f_m, sig_m = build_ou_bank_params(alpha=alpha, s0_uev=1.0, f_ir_hz=f_ir_hz, f_uv_hz=f_uv_hz, n_fluct=n_fluct)
        var_m = sig_m ** 2
        s_num = np.sum((2.0 * var_m[:, None] / (math.pi * f_m[:, None])) / (1.0 + (f_eval[None, :] / f_m[:, None]) ** 2), axis=0)
        s_tgt = f_eval ** (-alpha)
        max_psd_err = float(np.max(np.abs(s_num - s_tgt) / s_tgt))

        s_plot = np.sum((2.0 * var_m[:, None] / (math.pi * f_m[:, None])) / (1.0 + (f_plot[None, :] / f_m[:, None]) ** 2), axis=0)
        rms_ou = math.sqrt(float(np.sum(var_m)))
        rms_ex = exact_band_rms_uev(alpha=alpha, s0_uev=1.0, f_ir_hz=f_ir_hz, f_uv_hz=f_uv_hz)
        rms_rel = abs(rms_ou - rms_ex) / max(rms_ex, 1e-12)

        worst_psd_err = max(worst_psd_err, max_psd_err)
        worst_rms_err = max(worst_rms_err, rms_rel)

        results[f"alpha_{alpha:.1f}"] = {
            "alpha": float(alpha),
            "n_fluctuators": int(n_fluct),
            "max_psd_rel_err_10Hz_10MHz": max_psd_err,
            "rms_ou_uev_at_S1": rms_ou,
            "rms_exact_uev_at_S1": rms_ex,
            "rms_rel_err": float(rms_rel),
            "f_plot_hz": [float(x) for x in f_plot],
            "psd_ou_plot": [float(x) for x in s_plot],
            "psd_ideal_plot": [float(x) for x in (f_plot ** (-alpha))],
        }

    return {
        "f_ir_hz": float(f_ir_hz),
        "f_uv_hz": float(f_uv_hz),
        "worst_psd_rel_err": float(worst_psd_err),
        "worst_rms_rel_err": float(worst_rms_err),
        "by_alpha": results,
    }


def generate_ou_1f_trajectories_ghz(
    n_traj: int,
    dts_us: np.ndarray | list[float],
    s0_uev: float,
    alpha: float = 1.0,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
    n_fluct: int = DEFAULT_N_FLUCT,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate exact stationary colored 1/f^alpha charge-detuning trajectories delta_eps(t) in GHz.

    Supports arbitrary non-uniform step durations `dts_us` (length N_steps), evaluating
    exact Ornstein-Uhlenbeck transitions over each step duration dt_k:
        x_m(t_{k+1}) = exp(-2*pi*f_m*dt_k) * x_m(t_k) + sigma_m * sqrt(1 - exp(-4*pi*f_m*dt_k)) * N(0, 1).

    Returns array of shape (n_traj, len(dts_us)) in cyclic GHz.
    """
    n_steps = len(dts_us)
    if s0_uev <= 0.0:
        return np.zeros((n_traj, n_steps), dtype=np.float64)
    if rng is None:
        rng = np.random.default_rng()

    f_m, sig_m_uev = build_ou_bank_params(alpha=alpha, s0_uev=s0_uev, f_ir_hz=f_ir_hz, f_uv_hz=f_uv_hz, n_fluct=n_fluct)
    sig_m_ghz = sig_m_uev * GHZ_PER_UEV

    # Draw stationary initial state x_m(0) ~ N(0, sigma_m^2)
    x = rng.normal(0.0, 1.0, size=(n_traj, n_fluct)) * sig_m_ghz[None, :]
    out = np.empty((n_traj, n_steps), dtype=np.float64)

    for k in range(n_steps):
        out[:, k] = np.sum(x, axis=1)
        if k + 1 < n_steps:
            dt_s = float(dts_us[k]) * 1e-6
            if dt_s > 0.0:
                decay = np.exp(-2.0 * math.pi * f_m * dt_s)
                innov = sig_m_ghz * np.sqrt(np.maximum(0.0, 1.0 - decay * decay))
                x = x * decay[None, :] + rng.normal(0.0, 1.0, size=(n_traj, n_fluct)) * innov[None, :]

    return out


def compute_cywinski_filter_suppression(
    t_gate_us: float = 1.5,
    d1_ghz_per_ghz: float = 1.0e-4,
    s0_uev: float = 1.0,
    alphas: list[float] | None = None,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
) -> dict[str, Any]:
    """Exact Cywinski (2008) analytical phase-variance integrals for Bare, Echo-2, and XY4-4."""
    if alphas is None:
        alphas = [0.8, 1.0, 1.2]
    f_grid = np.geomspace(f_ir_hz, f_uv_hz, 24000)
    w_grid = 2.0 * np.pi * f_grid
    tg = t_gate_us * 1e-6
    z = w_grid * tg
    pref = (2.0 * math.pi * d1_ghz_per_ghz * s0_uev * GHZ_PER_UEV * 1e9) ** 2

    # Filter functions |y_N(w)|^2 / w^2:
    # Bare (N=0): 4 sin^2(z/2) / w^2
    y0 = 4.0 * (np.sin(0.5 * z) ** 2) / (w_grid ** 2)
    # 2-pulse symmetric CPMG/FF-Echo (pulses at t/4, 3t/4):
    y2_c = 1.0 - np.exp(1j * z) + 2.0 * (-np.exp(0.25j * z) + np.exp(0.75j * z))
    y2 = (np.abs(y2_c) ** 2) / (w_grid ** 2)
    # 4-pulse symmetric XY4/CPMG-4 (pulses at t/8, 3t/8, 5t/8, 7t/8):
    y4_c = 1.0 - np.exp(1j * z) + 2.0 * (
        -np.exp(0.125j * z) + np.exp(0.375j * z) - np.exp(0.625j * z) + np.exp(0.875j * z)
    )
    y4 = (np.abs(y4_c) ** 2) / (w_grid ** 2)

    out: dict[str, Any] = {}
    for alpha in alphas:
        sf = f_grid ** (-alpha)
        v0 = float(pref * np.trapezoid(sf * y0, f_grid))
        v2 = float(pref * np.trapezoid(sf * y2, f_grid))
        v4 = float(pref * np.trapezoid(sf * y4, f_grid))
        out[f"alpha_{alpha:.1f}"] = {
            "alpha": float(alpha),
            "var_bare": v0,
            "var_echo2": v2,
            "var_xy4": v4,
            "coherence_bare": math.exp(-0.5 * v0),
            "coherence_echo2": math.exp(-0.5 * v2),
            "coherence_xy4": math.exp(-0.5 * v4),
            "suppression_echo2_x": v0 / max(v2, 1e-15),
            "suppression_xy4_x": v0 / max(v4, 1e-15),
        }
    return out
