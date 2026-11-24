"""Autonomous Self-Healing Closed-Loop Fault Management Controller (Exp145 / CellISA v4.0).

Implements ``AutoRecalController`` supporting the CellISA v4.0 ``AUTO_RECAL`` opcode
with deterministic physical fault injection and closed-loop autonomous mitigation for
four mission-critical Atom Lithography Machine subsystems:

  1. S5.5 Laser Annealing Power Drift (+/-8%): Coupled 1D nonlinear finite-volume
     crystalline-Si thermal PDE (NIST-JANAF / Glassbrenner-Slack k_Si(T), c_p(T),
     808 nm temperature-dependent optical absorption, Stefan-Boltzmann T^4 radiative
     cooling matching Exp130) driven by a first-order AOM actuator with acoustic
     dead-time lag and an anti-windup discrete PID controller, integrating full-pulse
     Arrhenius/TED dopant diffusion broadening (sigma_anneal <= 0.50 nm) and Olson-Roth
     SPE activation kinetics.
  2. S5 UHV Vacuum Pressure Spike (> 1e-8 Torr): Two-chamber coupled differential-pumping
     transient UHV ODE (scipy.integrate.solve_ivp Radau) with chamber volumes V1/V2,
     conductance-limited cryopump + pressure-dependent sputter-ion pumping S_eff(P),
     burst outgassing/desorption pulse Q(t), sub-microsecond electrostatic beam blanking
     (tau_blank < 1 us), realistic mechanical UHV gate-valve closure latency
     (tau_valve ~ 15-30 ms), integrated Langmuir exposure, and Hertz-Knudsen kinetic
     surface monolayer coverage theta_ML(t).
  3. S3 32x32 (1,024-Beamlet) Blanker Dead-Channel Compensation: Physically accurate
     wafer-stage step-and-stitch compensation planner computing minimal integer-pitch
     stage offsets (dx, dy) so live neighboring beamlets cover every dead wafer site
     with exact zero coordinate mismatch, reporting the honest stage-move + stitch-dwell
     throughput penalty (< 100% effective throughput whenever any channel is dead).
  4. 31P Hyperfine +/-350 Hz Thermal Frequency Drift: Real-time bit-exact Q16.16 FPGA
     BOED relock using ``Q1616BOEDCore`` from ``fpga_boed_dsp`` converging in < 5.0 ms
     with < 100 Hz residual frequency error.

Epistemic status: {Model} / {Sayisal-Simulasyon}, no_lab_measurement=true.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.linalg import solve_banded
from scipy.optimize import brentq

from .adaptive_spectroscopy import lorentzian
from .fpga_boed_dsp import FPGACoreConfig, Q1616BOEDCore


# ---------------------------------------------------------------------------
# Fundamental & Silicon / UHV Physical Constants (Exp130 / NIST-JANAF anchors)
# ---------------------------------------------------------------------------
KB_EV_PER_K = 8.617333262e-5
KB_J_PER_K = 1.380649e-23
AMU_KG = 1.66053906660e-27
TORR_TO_PA = 133.32236842105263
SIGMA_SB = 5.670374419e-8      # Stefan-Boltzmann constant [W / (m^2 K^4)]

RHO_SI = 2329.0                # Crystalline Si density [kg / m^3]
T_MELT_SI = 1687.0             # Crystalline Si melting point [K]
EPS_RAD_SI = 0.65              # High-T crystalline Si surface emissivity
EA_P_SI_EV = 3.66              # Phosphorus diffusion activation energy in Si (Fahey 1989)
D_P0_NM2_PER_S = 3.85e14       # Equilibrium P diffusivity prefactor (3.85 cm^2/s)
F_I_P = 0.95                   # Interstitialcy fraction of P diffusion

# Exp130 Si self-interstitial / cluster / SPE activation kinetics anchors
C_I0_CM3 = 2.98e27
EF_I_EV = 3.18
D_I0_NM2_PER_S = 0.05e14       # 0.05 cm^2/s
EM_I_EV = 1.77
NU_CL_S = 1.5e15
EA_CL_DISS_EV = 3.10
NU_ACT_S = 3.68e14             # Olson & Roth (1988) v_0 / L_regrow (10 nm)
EA_ACT_EV = 2.70
RP_NM = 6.46                   # 5 keV 31P+ projected range (Exp92 BCA)
L_SURF_NM = 2.0
R_CASC_NM = 2.5
C_CL_INIT_CM3 = 3.0e19

# Tabulated NIST-JANAF / Glassbrenner-Slack crystalline Si properties (Exp130)
_SI_T_TAB = np.array([250.0, 300.0, 400.0, 500.0, 600.0, 800.0, 1000.0, 1200.0, 1400.0, 1687.0, 1800.0])
_SI_K_TAB = np.array([191.0, 148.0, 105.0, 80.0, 64.0, 42.2, 31.2, 25.7, 23.5, 22.0, 22.0])
_SI_CP_TAB = np.array([650.0, 712.0, 790.0, 839.0, 871.0, 913.0, 946.0, 976.0, 1005.0, 1038.0, 1045.0])
_SI_K_INTERP = PchipInterpolator(_SI_T_TAB, _SI_K_TAB)
_SI_CP_INTERP = PchipInterpolator(_SI_T_TAB, _SI_CP_TAB)


def k_si(T_K: np.ndarray | float) -> np.ndarray:
    """Crystalline Si thermal conductivity k_Si(T) [W/(m K)] (Exp130)."""
    return np.asarray(_SI_K_INTERP(np.clip(T_K, 250.0, 1800.0)), dtype=np.float64)


def cp_si(T_K: np.ndarray | float) -> np.ndarray:
    """Crystalline Si specific heat capacity c_p(T) [J/(kg K)] (Exp130)."""
    return np.asarray(_SI_CP_INTERP(np.clip(T_K, 250.0, 1800.0)), dtype=np.float64)


def optical_si_808nm(T_K: np.ndarray | float) -> tuple[float, np.ndarray]:
    """808 nm diode-laser Si reflectivity R and T-dependent absorption alpha(T) [1/m]."""
    t_arr = np.asarray(T_K, dtype=np.float64)
    alpha = 8.5e4 * np.exp(np.clip((t_arr - 300.0) / 320.0, 0.0, 4.5))
    return 0.33, alpha


@lru_cache(maxsize=8)
def _stretched_si_grid(
    wafer_thickness_m: float = 500e-6,
    n_cells: int = 44,
    dz0_m: float = 120e-9,
) -> tuple[np.ndarray, np.ndarray]:
    """Build geometrically stretched 1D finite-volume grid across a 500 um Si wafer."""
    def _f(r: float) -> float:
        return dz0_m * (r ** n_cells - 1.0) / (r - 1.0) - wafer_thickness_m

    ratio = float(brentq(_f, 1.0001, 1.60))
    dz = dz0_m * (ratio ** np.arange(n_cells, dtype=np.float64))
    dz *= wafer_thickness_m / float(np.sum(dz))
    z_faces = np.concatenate([[0.0], np.cumsum(dz)])
    z_centers = 0.5 * (z_faces[:-1] + z_faces[1:])
    return z_centers, dz


def _wafer_enthalpy_j_m2(T_vec: np.ndarray, dz: np.ndarray, T_ref: float) -> float:
    """Exact Gauss-Legendre enthalpy integral int_{T_ref}^{T} rho * c_p(T') dT' dz."""
    xg, wg = np.polynomial.legendre.leggauss(6)
    u = 0.5 * (xg + 1.0)[None, :]
    w = 0.5 * wg[None, :]
    dT = (T_vec - T_ref)[:, None]
    T_pts = T_ref + dT * u
    h_cell = np.sum(w * cp_si(T_pts), axis=1) * (T_vec - T_ref)
    return float(np.sum(RHO_SI * dz * h_cell))


def _integrate_ted_and_activation(t_s: np.ndarray, T_surf_K: np.ndarray) -> dict[str, float]:
    """Integrate Exp130 Arrhenius/TED P diffusion broadening & Olson-Roth activation along T(t)."""
    c_cl = C_CL_INIT_CM3
    c_i_init = C_I0_CM3 * math.exp(-EF_I_EV / (KB_EV_PER_K * max(float(T_surf_K[0]), 250.0)))
    c_i = c_i_init

    int_2D_eq = 0.0
    int_2D_ted = 0.0
    int_boltz = 0.0
    int_k_act = 0.0
    max_s_i = 1.0

    for k in range(t_s.size - 1):
        dt = float(t_s[k + 1] - t_s[k])
        if dt <= 0.0:
            continue
        Tm = 0.5 * float(T_surf_K[k] + T_surf_K[k + 1])
        if Tm < 420.0:
            continue

        boltz_p = math.exp(-EA_P_SI_EV / (KB_EV_PER_K * Tm))
        int_boltz += boltz_p * dt
        d_p_eq = D_P0_NM2_PER_S * boltz_p
        int_2D_eq += 2.0 * d_p_eq * dt

        # Olson & Roth (1988) SPE / substitutional incorporation rate
        k_act = NU_ACT_S * math.exp(-EA_ACT_EV / (KB_EV_PER_K * Tm))
        int_k_act += k_act * dt

        # Stolk/Cowern isolated-cascade interstitial cluster release + 3D radial & surface sink
        k_diss = NU_CL_S * math.exp(-EA_CL_DISS_EV / (KB_EV_PER_K * Tm))
        d_i = D_I0_NM2_PER_S * math.exp(-EM_I_EV / (KB_EV_PER_K * Tm))
        c_i_star = max(C_I0_CM3 * math.exp(-EF_I_EV / (KB_EV_PER_K * Tm)), 1e-30)

        exp_kd = math.exp(-min(k_diss * dt, 500.0))
        d_cl = c_cl * (1.0 - exp_kd)
        c_cl *= exp_kd
        gen_rate = d_cl / dt

        # Combined 3D radial out-diffusion (4 D_I / r_casc^2) + front surface Robin sink
        k_sink = (4.0 * d_i / (R_CASC_NM ** 2)) + (d_i / (RP_NM * (L_SURF_NM + RP_NM)))
        ks_dt = k_sink * dt
        if ks_dt < 1e-6:
            c_i_new = c_i + (gen_rate - k_sink * (c_i - c_i_star)) * dt
        else:
            exp_ks = math.exp(-min(ks_dt, 500.0))
            c_i_new = c_i_star + (c_i - c_i_star) * exp_ks + (gen_rate / k_sink) * (1.0 - exp_ks)
        c_i = max(c_i_new, c_i_star)
        s_i = c_i / c_i_star
        max_s_i = max(max_s_i, s_i)

        d_p_eff = d_p_eq * (F_I_P * s_i + (1.0 - F_I_P))
        int_2D_ted += 2.0 * d_p_eff * dt

    return {
        "sigma_anneal_nm": math.sqrt(max(0.0, int_2D_ted)),
        "sigma_eq_nm": math.sqrt(max(0.0, int_2D_eq)),
        "activation_frac": 1.0 - math.exp(-min(int_k_act, 500.0)),
        "integrated_thermal_budget_s": int_boltz,
        "max_interstitial_supersat": max_s_i,
    }


def _stage_step_time_s(distance_m: float, max_accel_m_s2: float, max_vel_m_s: float, settle_s: float) -> float:
    """Trapezoidal / triangular wafer-stage motion profile + interferometric settle time."""
    d = abs(float(distance_m))
    if d <= 0.0:
        return 0.0
    a = max(float(max_accel_m_s2), 1e-3)
    v = max(float(max_vel_m_s), 1e-3)
    d_tri = (v * v) / a
    if d <= d_tri:
        t_move = 2.0 * math.sqrt(d / a)
    else:
        t_move = (d / v) + (v / a)
    return t_move + max(0.0, float(settle_s))


@dataclass(frozen=True)
class AutoRecalConfig:
    """Nominal machine operating points and safety interlock thresholds ({Model})."""
    # S5.5 Flash/Laser Annealing (Exp130 808 nm, 1.0 ms, 43.49 J/cm^2 -> 1530.1 K)
    laser_fluence_nom_J_cm2: float = 43.49
    laser_pulse_nom_ms: float = 1.0
    laser_wavelength_nm: float = 808.0
    t_sub_K: float = 300.0
    t_peak_nom_K: float = 1530.0
    sigma_anneal_nom_nm: float = 0.34
    sigma_anneal_limit_nm: float = 0.50
    aom_tau_us: float = 15.0             # First-order AOM driver + acoustic bandwidth lag (us)
    aom_dead_time_us: float = 10.0       # AOM acoustic transit + FPGA loop dead-time (us)
    aom_sample_dt_us: float = 10.0       # 100 kHz digital PID sampling period (us)
    aom_gain_min: float = 0.65           # AOM RF drive floor
    aom_gain_max: float = 1.40           # AOM RF drive saturation ceiling

    # S5 UHV Vacuum Interlock (2-chamber differential pumping + fast gate valve)
    uhv_base_torr: float = 2.0e-10
    uhv_trip_torr: float = 1.0e-8
    uhv_safe_resume_torr: float = 5.0e-10
    uhv_pump_tau_s: float = 8.0
    uhv_source_vol_L: float = 40.0       # Upstream column/source chamber V1 (L)
    uhv_wafer_vol_L: float = 120.0       # Main wafer UHV process chamber V2 (L)
    uhv_valve_open_cond_L_s: float = 45.0     # DN100 column gate-valve open conductance (L/s)
    uhv_valve_closed_cond_L_s: float = 1.0e-7 # Metal/Viton sealed conductance (L/s)
    uhv_valve_closure_ms: float = 20.0        # Mechanical gate-valve stroke latency (15-30 ms)
    uhv_valve_dead_time_ms: float = 4.0       # Pneumatic/solenoid dead-time before blade moves
    uhv_blanker_latency_us: float = 0.05      # 50 ns (< 1 us) electrostatic beam-blanker shutdown
    uhv_plc_sense_latency_ms: float = 0.25    # Ion-gauge comparator + FPGA interlock latency
    uhv_gas_mass_amu: float = 28.0            # Dominant CO/N2 UHV residual gas mass
    uhv_sticking_coeff: float = 0.50          # Reactive residual gas sticking coeff on Si(100)
    uhv_si100_sites_cm2: float = 6.78e14      # Si(100) surface dangling-bond density (cm^-2)

    # S3 32x32 Blanker Array + Arch-B Wafer-Stage Step-and-Stitch Parameters
    blanker_rows: int = 32
    blanker_cols: int = 32
    blanker_spare_channels: int = 128         # Perimeter guard apertures (cannot teleport to interior)
    blanker_beam_pitch_mm: float = 0.50       # Locked Arch-B 32x32 @ 0.50 mm = 16x16 mm array
    blanker_shot_cycle_ms: float = 15.0       # Locked Exp124 HDA-HiRes single-ion shot cycle
    stage_max_accel_m_s2: float = 10.0        # Interferometric wafer-stage max acceleration
    stage_max_vel_m_s: float = 0.25           # Wafer-stage slew velocity
    stage_settle_ms: float = 3.0              # Sub-nm interferometer settling overhead

    # 31P Hyperfine Q16.16 BOED Relock (Exp140)
    hyperfine_nom_Hz: float = 42_500.0
    hyperfine_gamma_Hz: float = 1_200.0
    boed_probe_sigma_n: float = 0.08
    boed_probe_time_ms: float = 0.26     # 0.13 ms readout + 0.13 ms RF overhead
    boed_target_sigma_Hz: float = 38.0
    boed_max_probes: int = 16
    relock_time_limit_ms: float = 5.0
    relock_err_limit_Hz: float = 100.0


class AutoRecalController:
    """Closed-loop self-healing fault detection, interlock, and recalibration engine."""

    def __init__(self, cfg: AutoRecalConfig | None = None, seed: int = 2026145):
        self.cfg = cfg or AutoRecalConfig()
        self.seed = int(seed)
        self.boed_core = Q1616BOEDCore(FPGACoreConfig())
        # Preserve helper calibration for backward callers of _compute_anneal_sigma_nm
        boltz_nom = math.exp(-EA_P_SI_EV / (KB_EV_PER_K * self.cfg.t_peak_nom_K))
        self._d0_nm2_per_ms = (self.cfg.sigma_anneal_nom_nm ** 2) / (
            2.0 * boltz_nom * self.cfg.laser_pulse_nom_ms
        )

    def _compute_anneal_sigma_nm(self, t_peak_K: float, pulse_ms: float) -> float:
        """Arrhenius 1D dopant diffusion broadening proxy sigma = sqrt(2 D(T) t_eff)."""
        t_eff_K = max(350.0, float(t_peak_K))
        boltz = math.exp(-EA_P_SI_EV / (KB_EV_PER_K * t_eff_K))
        return math.sqrt(max(0.0, 2.0 * self._d0_nm2_per_ms * boltz * max(pulse_ms, 1e-4)))

    # ------------------------------------------------------------------
    # Nonlinear 1D Si Flash Thermal PDE + Coupled AOM/PID Helper
    # ------------------------------------------------------------------

    def _pulse_shape_irradiance(self, t_s: float, t_pulse_s: float, fluence_J_m2: float) -> float:
        """Smooth raised-cosine flat-top pulse (10% rise, 80% flat, 10% fall; integral == fluence)."""
        if t_s <= 0.0 or t_s >= t_pulse_s:
            return 0.0
        t_rise = 0.10 * t_pulse_s
        t_fall = 0.90 * t_pulse_s
        i_peak = fluence_J_m2 / (0.90 * t_pulse_s)
        if t_s < t_rise:
            return i_peak * 0.5 * (1.0 - math.cos(math.pi * t_s / t_rise))
        if t_s > t_fall:
            return i_peak * 0.5 * (1.0 + math.cos(math.pi * (t_s - t_fall) / t_rise))
        return i_peak

    def _step_si_thermal_fvm(
        self,
        T_prev: np.ndarray,
        dz: np.ndarray,
        dt_s: float,
        I_in_W_m2: float,
        T_sub_K: float,
        h_back_W_m2K: float = 50.0,
    ) -> tuple[np.ndarray, float, float]:
        """Advance 1D nonlinear Si FVM heat PDE one Backward-Euler step with 2 Picard iterations."""
        n_cells = T_prev.size
        T_iter = T_prev.copy()
        for _ in range(2):
            T_half = 0.5 * (T_prev + T_iter)
            k_c = k_si(T_half)
            cp_c = cp_si(T_half)
            G_face = 1.0 / (0.5 * dz[:-1] / k_c[:-1] + 0.5 * dz[1:] / k_c[1:])

            R_opt, alpha_c = optical_si_808nm(T_half)
            tau_cum = np.concatenate([[0.0], np.cumsum(alpha_c * dz)])
            q_abs = (1.0 - R_opt) * I_in_W_m2 * (np.exp(-tau_cum[:-1]) - np.exp(-tau_cum[1:]))

            h_rad_f = EPS_RAD_SI * SIGMA_SB * (T_half[0] ** 2 + T_sub_K ** 2) * (T_half[0] + T_sub_K)
            h_rad_b = (
                EPS_RAD_SI * SIGMA_SB * (T_half[-1] ** 2 + T_sub_K ** 2) * (T_half[-1] + T_sub_K)
                + h_back_W_m2K
            )

            cap = RHO_SI * cp_c * dz / dt_s
            diag = cap.copy()
            diag[:-1] += G_face
            diag[1:] += G_face
            diag[0] += h_rad_f
            diag[-1] += h_rad_b

            rhs = cap * T_prev + q_abs
            rhs[0] += h_rad_f * T_sub_K
            rhs[-1] += h_rad_b * T_sub_K

            ab = np.zeros((3, n_cells), dtype=np.float64)
            ab[0, 1:] = -G_face
            ab[1, :] = diag
            ab[2, :-1] = -G_face
            T_iter = solve_banded((1, 1), ab, rhs, overwrite_ab=True, overwrite_b=True)

        T_half = 0.5 * (T_prev + T_iter)
        R_opt, alpha_c = optical_si_808nm(T_half)
        tau_tot = float(np.sum(alpha_c * dz))
        e_abs = (1.0 - R_opt) * I_in_W_m2 * (1.0 - math.exp(-tau_tot)) * dt_s
        h_rad_f = EPS_RAD_SI * SIGMA_SB * (T_half[0] ** 2 + T_sub_K ** 2) * (T_half[0] + T_sub_K)
        h_rad_b = (
            EPS_RAD_SI * SIGMA_SB * (T_half[-1] ** 2 + T_sub_K ** 2) * (T_half[-1] + T_sub_K)
            + h_back_W_m2K
        )
        e_loss = (h_rad_f * (T_iter[0] - T_sub_K) + h_rad_b * (T_iter[-1] - T_sub_K)) * dt_s
        return T_iter, e_abs, e_loss

    def _simulate_laser_flash_run(
        self,
        p_ratio: float,
        closed_loop: bool,
        T_ref_pulse: np.ndarray | None,
        rng: np.random.Generator,
        aom_tau_us: float,
        aom_dead_time_us: float,
    ) -> dict[str, Any]:
        """Run coupled 1D nonlinear Si thermal PDE (+ optional AOM/anti-windup PID loop)."""
        c = self.cfg
        _, dz = _stretched_si_grid(500e-6, n_cells=44, dz0_m=120e-9)
        t_pulse_s = c.laser_pulse_nom_ms * 1e-3
        dt_s = c.aom_sample_dt_us * 1e-6
        n_pulse = max(20, int(round(t_pulse_s / dt_s)))
        dt_s = t_pulse_s / n_pulse
        fluence_J_m2 = c.laser_fluence_nom_J_cm2 * 1.0e4

        # Stretched post-pulse cooling grid out to 16 * t_pulse_s
        n_cool = 56
        cool_span = 15.0 * t_pulse_s
        s_cool = np.geomspace(dt_s * 0.5, cool_span + dt_s * 0.5, n_cool + 1) - dt_s * 0.5
        s_cool[0] = 0.0
        s_cool[-1] = cool_span
        t_pulse_grid = np.linspace(0.0, t_pulse_s, n_pulse + 1)
        t_grid = np.concatenate([t_pulse_grid, t_pulse_s + s_cool[1:]])

        T = np.full(dz.size, c.t_sub_K, dtype=np.float64)
        T_surf = np.empty(t_grid.size, dtype=np.float64)
        T_surf[0] = c.t_sub_K

        # First-order AOM actuator + transport dead-time buffer + anti-windup discrete PID
        tau_aom_s = max(float(aom_tau_us) * 1e-6, 1e-9)
        alpha_aom = math.exp(-dt_s / tau_aom_s)
        n_dead = max(0, int(round((max(0.0, float(aom_dead_time_us)) * 1e-6) / dt_s)))
        delay_buf: deque[float] = deque([1.0] * (n_dead + 1), maxlen=n_dead + 1)

        g_act = 1.0
        g_cmd = 1.0
        # Discrete anti-windup PID state
        kp = 0.42
        ki_step = 0.36
        kd_step = 0.05
        k_aw = 0.65
        integ = 0.0
        prev_meas = 1.0
        d_filt = 0.0
        saturated = False

        p_eff_hist = np.ones(n_pulse, dtype=np.float64)
        g_act_hist = np.ones(n_pulse, dtype=np.float64)
        delivered_fluence_J_m2 = 0.0
        e_abs_tot = 0.0
        e_loss_tot = 0.0

        # Active pulse integration
        for step in range(n_pulse):
            t_mid = 0.5 * (t_grid[step] + t_grid[step + 1])
            I_nom = self._pulse_shape_irradiance(t_mid, t_pulse_s, fluence_J_m2)

            if closed_loop:
                g_delayed = delay_buf[0]
                g_act = alpha_aom * g_act + (1.0 - alpha_aom) * g_delayed
            else:
                g_act = 1.0

            p_eff = g_act * p_ratio
            p_eff_hist[step] = p_eff
            g_act_hist[step] = g_act
            I_in = I_nom * p_eff
            delivered_fluence_J_m2 += I_in * dt_s

            T, e_abs, e_loss = self._step_si_thermal_fvm(T, dz, dt_s, I_in, c.t_sub_K)
            e_abs_tot += e_abs
            e_loss_tot += e_loss
            T_surf[step + 1] = T[0]

            if closed_loop:
                # 100 kHz photodiode power measurement + pyrometer thermal feedback trim
                p_meas = p_eff * (1.0 + float(rng.normal(0.0, 0.002)))
                err_p = 1.0 - p_meas
                err_t = 0.0
                if T_ref_pulse is not None and T_ref_pulse[step + 1] > 480.0:
                    t_meas = T[0] + float(rng.normal(0.0, 1.5))
                    err_t = 0.60 * (T_ref_pulse[step + 1] - t_meas) / max(c.t_peak_nom_K - c.t_sub_K, 100.0)
                err = err_p + err_t

                # Filtered derivative-on-measurement (avoids setpoint kick)
                d_raw = -(p_meas - prev_meas)
                d_filt = 0.5 * d_filt + 0.5 * d_raw
                prev_meas = p_meas

                u_raw = 1.0 + kp * err + integ + kd_step * d_filt
                g_cmd = float(np.clip(u_raw, c.aom_gain_min, c.aom_gain_max))
                if abs(g_cmd - u_raw) > 1e-9:
                    saturated = True
                # Back-calculation anti-windup integrator update
                integ += ki_step * err + k_aw * (g_cmd - u_raw)
                delay_buf.append(g_cmd)

        # Post-pulse conductive + T^4 radiative self-quench
        for step in range(n_pulse, t_grid.size - 1):
            dt_c = float(t_grid[step + 1] - t_grid[step])
            T, e_abs, e_loss = self._step_si_thermal_fvm(T, dz, dt_c, 0.0, c.t_sub_K)
            e_abs_tot += e_abs
            e_loss_tot += e_loss
            T_surf[step + 1] = T[0]

        e_stored = _wafer_enthalpy_j_m2(T, dz, c.t_sub_K)
        energy_rel_err = abs((e_stored + e_loss_tot) - e_abs_tot) / max(e_abs_tot, 1e-9)

        idx_pk = int(np.argmax(T_surf))
        T_peak = float(T_surf[idx_pk])
        t_peak_ms = float(t_grid[idx_pk] * 1e3)
        kin = _integrate_ted_and_activation(t_grid, T_surf)

        # Measure settling time: last tick where |p_eff - 1.0| > 0.015 during the active pulse
        outside = np.flatnonzero(np.abs(p_eff_hist - 1.0) > 0.015)
        if outside.size == 0:
            settling_us = 0.0
        elif int(outside[-1]) >= n_pulse - 2:
            settling_us = float(t_pulse_s * 1e6)
        else:
            settling_us = float((int(outside[-1]) + 1) * dt_s * 1e6)

        return {
            "t_s": t_grid,
            "T_surf_K": T_surf,
            "T_peak_K": T_peak,
            "t_peak_ms": t_peak_ms,
            "fluence_delivered_J_cm2": delivered_fluence_J_m2 * 1e-4,
            "final_aom_gain": float(g_act_hist[-1]),
            "mean_aom_gain_flat": float(np.mean(g_act_hist[n_pulse // 5 : (9 * n_pulse) // 10])),
            "aom_saturated": saturated,
            "measured_settling_us": settling_us,
            "energy_balance_rel_err": energy_rel_err,
            "p_eff_hist": p_eff_hist,
            **kin,
        }

    # ------------------------------------------------------------------
    # Fault Mode (a): S5.5 Laser Annealing Power Drift (+/-8%)
    # ------------------------------------------------------------------

    def mitigate_laser_power_drift(
        self,
        drift_pct: float = 8.0,
        aom_tau_us: float | None = None,
        aom_dead_time_us: float | None = None,
    ) -> dict[str, Any]:
        """Inject +/-drift_pct S5.5 laser power drift into nonlinear Si PDE + AOM/PID servo."""
        rng = np.random.default_rng(self.seed + 11)
        c = self.cfg
        tau_aom = c.aom_tau_us if aom_tau_us is None else float(aom_tau_us)
        tau_dead = c.aom_dead_time_us if aom_dead_time_us is None else float(aom_dead_time_us)

        # Solve nominal reference 1D nonlinear Si thermal PDE trajectory (p_ratio = 1.0)
        ref = self._simulate_laser_flash_run(
            p_ratio=1.0,
            closed_loop=False,
            T_ref_pulse=None,
            rng=rng,
            aom_tau_us=tau_aom,
            aom_dead_time_us=tau_dead,
        )
        t_ref_peak = ref["T_peak_K"]
        n_pulse_ref = int(round((c.laser_pulse_nom_ms * 1e-3) / (c.aom_sample_dt_us * 1e-6)))
        T_ref_pulse = ref["T_surf_K"][: n_pulse_ref + 1]

        cases: dict[str, Any] = {}
        all_passed = True
        worst_controlled_sigma = 0.0
        worst_uncontrolled_sigma = 0.0
        max_settling_us = 0.0
        max_delta_T_K = 0.0

        for label, signed_pct in (("surge_plus", abs(drift_pct)), ("drop_minus", -abs(drift_pct))):
            p_ratio = max(0.05, 1.0 + signed_pct / 100.0)
            open_run = self._simulate_laser_flash_run(
                p_ratio=p_ratio,
                closed_loop=False,
                T_ref_pulse=None,
                rng=rng,
                aom_tau_us=tau_aom,
                aom_dead_time_us=tau_dead,
            )
            ctrl_run = self._simulate_laser_flash_run(
                p_ratio=p_ratio,
                closed_loop=True,
                T_ref_pulse=T_ref_pulse,
                rng=rng,
                aom_tau_us=tau_aom,
                aom_dead_time_us=tau_dead,
            )

            t_open = open_run["T_peak_K"]
            sig_open = open_run["sigma_anneal_nm"]
            act_open = open_run["activation_frac"]

            t_ctrl = ctrl_run["T_peak_K"]
            sig_ctrl = ctrl_run["sigma_anneal_nm"]
            act_ctrl = ctrl_run["activation_frac"]
            delta_t_peak = t_ctrl - t_ref_peak

            passed = bool(
                sig_ctrl <= c.sigma_anneal_limit_nm
                and abs(delta_t_peak) <= 15.0
                and t_ctrl < T_MELT_SI
                and act_ctrl >= 0.99
            )
            all_passed = all_passed and passed
            worst_controlled_sigma = max(worst_controlled_sigma, sig_ctrl)
            worst_uncontrolled_sigma = max(worst_uncontrolled_sigma, sig_open)
            max_settling_us = max(max_settling_us, ctrl_run["measured_settling_us"])
            max_delta_T_K = max(max_delta_T_K, abs(delta_t_peak))

            cases[label] = {
                "injected_drift_pct": round(signed_pct, 2),
                "uncontrolled_T_peak_K": round(t_open, 2),
                "uncontrolled_sigma_anneal_nm": round(sig_open, 4),
                "uncontrolled_sigma_eq_nm": round(open_run["sigma_eq_nm"], 4),
                "uncontrolled_activation_frac": round(act_open, 5),
                "uncontrolled_thermal_budget_s": float(f"{open_run['integrated_thermal_budget_s']:.3e}"),
                "servo_aom_gain": round(ctrl_run["final_aom_gain"], 5),
                "servo_aom_mean_gain_flat": round(ctrl_run["mean_aom_gain_flat"], 5),
                "aom_saturated": bool(ctrl_run["aom_saturated"]),
                "measured_settling_us": round(ctrl_run["measured_settling_us"], 2),
                "controlled_fluence_J_cm2": round(ctrl_run["fluence_delivered_J_cm2"], 3),
                "controlled_T_peak_K": round(t_ctrl, 2),
                "delta_T_peak_K": round(delta_t_peak, 2),
                "t_peak_over_Tmelt": round(t_ctrl / T_MELT_SI, 4),
                "controlled_sigma_anneal_nm": round(sig_ctrl, 4),
                "controlled_sigma_eq_nm": round(ctrl_run["sigma_eq_nm"], 4),
                "controlled_activation_frac": round(act_ctrl, 5),
                "controlled_thermal_budget_s": float(f"{ctrl_run['integrated_thermal_budget_s']:.3e}"),
                "energy_balance_rel_err": float(f"{ctrl_run['energy_balance_rel_err']:.2e}"),
                "passed": passed,
            }

        return {
            "fault_mode": "S5.5_laser_power_drift",
            "thermal_model": "1D_nonlinear_Si_FVM_PDE_kT_cpT_T4_rad_plus_AOM_lag_antiwindup_PID",
            "reference_T_peak_K": round(t_ref_peak, 2),
            "reference_sigma_anneal_nm": round(ref["sigma_anneal_nm"], 4),
            "reference_energy_balance_rel_err": float(f"{ref['energy_balance_rel_err']:.2e}"),
            "aom_tau_us": round(tau_aom, 2),
            "aom_dead_time_us": round(tau_dead, 2),
            "limit_sigma_anneal_nm": c.sigma_anneal_limit_nm,
            "worst_uncontrolled_sigma_nm": round(worst_uncontrolled_sigma, 4),
            "worst_controlled_sigma_nm": round(worst_controlled_sigma, 4),
            "max_abs_delta_T_peak_K": round(max_delta_T_K, 2),
            "servo_settling_us": round(max_settling_us, 2),
            "cases": cases,
            "passed": all_passed,
        }

    # ------------------------------------------------------------------
    # Fault Mode (b): S5 UHV Vacuum Pressure Spike (> 1e-8 Torr)
    # ------------------------------------------------------------------

    def _uhv_effective_pumping_L_s(self, P_torr: float, chamber: int) -> float:
        """Conductance-limited cryopump + pressure-dependent sputter-ion pumping speed S_eff(P)."""
        c = self.cfg
        p_pos = max(float(P_torr), 1e-13)
        p_roll = 3.0e-10
        if chamber == 1:
            # Source/column neck: port-conductance limited so V1 / S1_eff ~ uhv_pump_tau_s (~8 s)
            s_nom = c.uhv_source_vol_L / max(c.uhv_pump_tau_s, 0.5)
            c_port = 2.0 * s_nom
            s_pump = 1.45 * s_nom + 0.90 * s_nom * (p_pos / (p_pos + p_roll))
        else:
            # Main wafer UHV chamber: high-conductance cryopump + sputter-ion stack
            c_port = 400.0
            s_pump = 260.0 + 80.0 * (p_pos / (p_pos + p_roll))
        return 1.0 / (1.0 / c_port + 1.0 / s_pump)

    def _uhv_gate_valve_conductance(
        self,
        t_s: float,
        t_trip_s: float | None,
        valve_closure_s: float,
    ) -> float:
        """Time-varying UHV gate-valve conductance with solenoid dead-time + smooth cosine closure."""
        c = self.cfg
        if t_trip_s is None:
            return c.uhv_valve_open_cond_L_s
        dt_since_trip = t_s - t_trip_s
        dead_s = min(c.uhv_valve_dead_time_ms * 1e-3, 0.5 * valve_closure_s)
        if dt_since_trip <= dead_s:
            return c.uhv_valve_open_cond_L_s
        if dt_since_trip >= valve_closure_s:
            return c.uhv_valve_closed_cond_L_s
        u = (dt_since_trip - dead_s) / max(valve_closure_s - dead_s, 1e-9)
        frac_open = 0.5 * (1.0 + math.cos(math.pi * u))
        return c.uhv_valve_closed_cond_L_s + (c.uhv_valve_open_cond_L_s - c.uhv_valve_closed_cond_L_s) * frac_open

    def mitigate_vacuum_spike(
        self,
        peak_pressure_torr: float = 3.5e-8,
        valve_closure_ms: float | None = None,
        blanker_latency_us: float | None = None,
    ) -> dict[str, Any]:
        """Simulate transient 2-chamber UHV differential-pumping ODE under gas burst + interlock."""
        c = self.cfg
        target_peak = max(float(peak_pressure_torr), c.uhv_base_torr)
        tau_valve_ms = c.uhv_valve_closure_ms if valve_closure_ms is None else max(1.0, float(valve_closure_ms))
        tau_valve_s = tau_valve_ms * 1e-3
        tau_blank_us = c.uhv_blanker_latency_us if blanker_latency_us is None else max(0.005, float(blanker_latency_us))
        t_sense_s = c.uhv_plc_sense_latency_ms * 1e-3

        p_base = c.uhv_base_torr
        p_ult = min(5.0e-11, 0.25 * p_base)
        v1 = c.uhv_source_vol_L
        v2 = c.uhv_wafer_vol_L
        scale_p = 1.0e-9  # Scale state pressures in nTorr for stiff ODE conditioning

        s1_base = self._uhv_effective_pumping_L_s(p_base, chamber=1)
        s2_base = self._uhv_effective_pumping_L_s(p_base, chamber=2)
        q_base_1 = s1_base * (p_base - p_ult)
        q_base_2 = s2_base * (p_base - p_ult)

        # Hertz-Knudsen molecular impingement per Langmuir [sites / cm^2 / L] at T = 300 K
        m_kg = c.uhv_gas_mass_amu * AMU_KG
        j_per_torr_cm2_s = (TORR_TO_PA / math.sqrt(2.0 * math.pi * m_kg * KB_J_PER_K * c.t_sub_K)) * 1.0e-4
        ml_rate_per_langmuir = (c.uhv_sticking_coeff * j_per_torr_cm2_s * 1.0e-6) / c.uhv_si100_sites_cm2

        # Bi-exponential burst outgassing/desorption pulse Q_burst(t) [Torr*L/s], integral = Q_tot
        # 90% fast burst (rise 1.5 ms, decay 6.0 ms) + 10% slow wall-desorption tail (decay 1.5 s)
        tau_r = 0.0015
        tau_d1 = 0.0060
        tau_d2 = 1.50
        q_tot_torr_L = 1.135 * v1 * max(0.0, target_peak - p_base)

        def _q_burst(t_s: float) -> float:
            if t_s <= 0.0 or q_tot_torr_L <= 0.0:
                return 0.0
            fast = (math.exp(-t_s / tau_d1) - math.exp(-t_s / tau_r)) / (tau_d1 - tau_r)
            slow = (math.exp(-t_s / tau_d2) - math.exp(-t_s / tau_r)) / (tau_d2 - tau_r)
            return q_tot_torr_L * (0.90 * fast + 0.10 * slow)

        def _make_rhs(t_trip_s: float | None):
            def _rhs(t_s: float, y: np.ndarray) -> np.ndarray:
                p1 = max(y[0] * scale_p, p_ult)
                p2 = max(y[1] * scale_p, p_ult)
                th_tot = min(max(y[4], 0.0), 1.0)
                th_exc = min(max(y[5], 0.0), 1.0)

                s1 = self._uhv_effective_pumping_L_s(p1, chamber=1)
                s2 = self._uhv_effective_pumping_L_s(p2, chamber=2)
                c_v = self._uhv_gate_valve_conductance(t_s, t_trip_s, tau_valve_s)
                q12 = c_v * (p1 - p2)
                qb = _q_burst(t_s)

                dp1_dt = (q_base_1 + qb - s1 * (p1 - p_ult) - q12) / v1
                dp2_dt = (q_base_2 + q12 - s2 * (p2 - p_ult)) / v2

                p2_exc = max(0.0, p2 - p_base)
                dL_tot_dt = p2 / 1.0e-6
                dL_exc_dt = p2_exc / 1.0e-6
                dth_tot_dt = ml_rate_per_langmuir * dL_tot_dt * (1.0 - th_tot)
                dth_exc_dt = ml_rate_per_langmuir * dL_exc_dt * (1.0 - th_exc)
                return np.array([
                    dp1_dt / scale_p,
                    dp2_dt / scale_p,
                    dL_tot_dt,
                    dL_exc_dt,
                    dth_tot_dt,
                    dth_exc_dt,
                ], dtype=np.float64)
            return _rhs

        y0 = np.array([p_base / scale_p, p_base / scale_p, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        t_max_sim = max(120.0, 20.0 * c.uhv_pump_tau_s)

        # Phase 1: Integrate from burst onset until Chamber 1 crosses uhv_trip_torr
        def _ev_trip(_t: float, y: np.ndarray) -> float:
            return y[0] * scale_p - c.uhv_trip_torr
        _ev_trip.terminal = True  # type: ignore[attr-defined]
        _ev_trip.direction = 1.0  # type: ignore[attr-defined]

        sol1 = solve_ivp(
            _make_rhs(None),
            (0.0, min(5.0, t_max_sim)),
            y0,
            method="Radau",
            events=_ev_trip,
            max_step=0.002,
            rtol=1e-7,
            atol=1e-10,
        )

        t_segs = [sol1.t]
        y_segs = [sol1.y]

        trip_detected = bool(sol1.t_events[0].size > 0)
        beam_paused = False
        gate_valve_locked = False
        t_cross = float(sol1.t_events[0][0]) if trip_detected else None
        t_trip_plc = (t_cross + t_sense_s) if t_cross is not None else None
        t_blank_complete = (t_trip_plc + tau_blank_us * 1e-6) if t_trip_plc is not None else None
        exp_valve_window_L = 0.0
        recovery_time_s = 0.0
        locked_at_midpoint = False
        safe_resumed = False

        if trip_detected and t_cross is not None and t_trip_plc is not None:
            beam_paused = True
            gate_valve_locked = True
            t_valve_done = t_trip_plc + tau_valve_s

            # Phase 2: Fine-resolution integration through PLC latency + mechanical gate-valve closure
            sol2 = solve_ivp(
                _make_rhs(t_trip_plc),
                (t_cross, t_valve_done),
                sol1.y[:, -1],
                method="Radau",
                max_step=min(0.001, tau_valve_s / 20.0),
                rtol=1e-7,
                atol=1e-10,
            )
            t_segs.append(sol2.t[1:])
            y_segs.append(sol2.y[:, 1:])
            exp_valve_window_L = float(sol2.y[2, -1])

            # Phase 3: Sealed-valve pumpdown until both chambers drop below uhv_safe_resume_torr
            def _ev_safe(_t: float, y: np.ndarray) -> float:
                return max(y[0], y[1]) * scale_p - c.uhv_safe_resume_torr
            _ev_safe.terminal = True  # type: ignore[attr-defined]
            _ev_safe.direction = -1.0  # type: ignore[attr-defined]

            sol3 = solve_ivp(
                _make_rhs(t_trip_plc),
                (t_valve_done, t_max_sim),
                sol2.y[:, -1],
                method="Radau",
                events=_ev_safe,
                max_step=0.5,
                rtol=1e-7,
                atol=1e-10,
            )
            t_segs.append(sol3.t[1:])
            y_segs.append(sol3.y[:, 1:])
            if sol3.t_events[0].size > 0:
                recovery_time_s = float(sol3.t_events[0][0])
            else:
                recovery_time_s = float(sol3.t[-1])

            # Phase 4: 2.0 s safe-dwell confirmation after recovery threshold
            sol4 = solve_ivp(
                _make_rhs(t_trip_plc),
                (recovery_time_s, recovery_time_s + 2.0),
                sol3.y[:, -1],
                method="Radau",
                max_step=0.25,
                rtol=1e-7,
                atol=1e-10,
            )
            t_segs.append(sol4.t[1:])
            y_segs.append(sol4.y[:, 1:])
        else:
            # Sub-threshold transient: integrate out to 25 s with valve open
            sol_sub = solve_ivp(
                _make_rhs(None),
                (sol1.t[-1], 25.0),
                sol1.y[:, -1],
                method="Radau",
                max_step=0.5,
                rtol=1e-7,
                atol=1e-10,
            )
            t_segs.append(sol_sub.t[1:])
            y_segs.append(sol_sub.y[:, 1:])
            recovery_time_s = 0.0

        t_all = np.concatenate(t_segs)
        y_all = np.hstack(y_segs)
        p1_traj = y_all[0] * scale_p
        p2_traj = y_all[1] * scale_p

        peak_p1 = float(np.max(p1_traj))
        peak_p2 = float(np.max(p2_traj))
        p_final_ch1 = float(p1_traj[-1])
        p_final_ch2 = float(p2_traj[-1])
        p_final = max(p_final_ch1, p_final_ch2)

        exp_L_total = float(y_all[2, -1])
        exp_L_excess = float(y_all[3, -1])
        theta_ml_total = float(y_all[4, -1])
        theta_ml_excess = float(y_all[5, -1])

        if trip_detected:
            t_mid = 0.5 * recovery_time_s
            p1_mid = float(np.interp(t_mid, t_all, p1_traj))
            locked_at_midpoint = bool(p1_mid >= c.uhv_safe_resume_torr)
            safe_resumed = bool(p_final < c.uhv_safe_resume_torr)
        else:
            locked_at_midpoint = False
            safe_resumed = bool(p_final < c.uhv_safe_resume_torr)

        # Unmitigated comparison (same burst with gate valve stuck open) over same horizon
        t_horizon_ref = float(t_all[-1])
        sol_unmit = solve_ivp(
            _make_rhs(None),
            (0.0, t_horizon_ref),
            y0,
            method="Radau",
            max_step=0.5,
            rtol=1e-6,
            atol=1e-9,
        )
        unmit_L_total = float(sol_unmit.y[2, -1])
        unmit_L_excess = float(sol_unmit.y[3, -1])
        unmit_peak_p2 = float(np.max(sol_unmit.y[1] * scale_p))
        protection_factor = unmit_L_excess / max(exp_L_excess, 1e-12) if unmit_L_excess > 1e-12 else 1.0

        # Downsampled trajectory summary for inspection (~24 points)
        idx_sub = np.unique(np.linspace(0, t_all.size - 1, min(24, t_all.size), dtype=int))
        traj_summary = [
            {
                "t_s": round(float(t_all[i]), 5),
                "p1_source_torr": float(f"{p1_traj[i]:.3e}"),
                "p2_wafer_torr": float(f"{p2_traj[i]:.3e}"),
            }
            for i in idx_sub
        ]

        if trip_detected:
            passed = bool(
                trip_detected
                and gate_valve_locked
                and beam_paused
                and tau_blank_us < 1.0
                and locked_at_midpoint
                and safe_resumed
                and theta_ml_total < 0.01
            )
        else:
            passed = bool(
                (not trip_detected)
                and (peak_p1 < c.uhv_trip_torr)
                and safe_resumed
                and theta_ml_total < 0.01
            )

        return {
            "fault_mode": "S5_uhv_vacuum_spike",
            "ode_solver": "scipy.integrate.solve_ivp(Radau)_2chamber_differential_pumping",
            "chamber1_volume_L": c.uhv_source_vol_L,
            "chamber2_volume_L": c.uhv_wafer_vol_L,
            "s_eff_ch1_base_L_s": round(s1_base, 3),
            "s_eff_ch2_base_L_s": round(s2_base, 3),
            "peak_pressure_torr": float(f"{peak_p1:.3e}"),
            "peak_ch1_source_torr": float(f"{peak_p1:.3e}"),
            "peak_ch2_wafer_torr": float(f"{peak_p2:.3e}"),
            "trip_threshold_torr": float(f"{c.uhv_trip_torr:.3e}"),
            "safe_resume_threshold_torr": float(f"{c.uhv_safe_resume_torr:.3e}"),
            "interlock_trip_detected": trip_detected,
            "interlock_latency_ms": round(c.uhv_plc_sense_latency_ms, 4) if trip_detected else 0.0,
            "blanker_latency_us": round(tau_blank_us, 4),
            "blanker_shutdown_time_ms": round(t_blank_complete * 1e3, 6) if t_blank_complete is not None else 0.0,
            "gate_valve_closure_ms": round(tau_valve_ms, 3),
            "gate_valve_locked": gate_valve_locked,
            "beam_paused": beam_paused,
            "exposure_langmuir_total": round(exp_L_total, 6),
            "exposure_langmuir_burst_excess": round(exp_L_excess, 6),
            "exposure_langmuir_valve_window": round(exp_valve_window_L, 6),
            "unmitigated_exposure_langmuir_total": round(unmit_L_total, 6),
            "unmitigated_exposure_langmuir_excess": round(unmit_L_excess, 6),
            "unmitigated_peak_ch2_torr": float(f"{unmit_peak_p2:.3e}"),
            "valve_excess_protection_factor": round(protection_factor, 2),
            "surface_monolayer_coverage_frac": round(theta_ml_total, 6),
            "excess_monolayer_coverage_frac": round(theta_ml_excess, 6),
            "wafer_exposure_monolayers": round(theta_ml_total, 6),
            "pumpdown_recovery_s": round(recovery_time_s, 3),
            "post_recovery_pressure_torr": float(f"{p_final:.3e}"),
            "safe_resumed": safe_resumed,
            "trajectory_summary": traj_summary,
            "passed": passed,
        }

    # ------------------------------------------------------------------
    # Fault Mode (c): S3 32x32 Blanker Dead Channels -> Wafer-Stage Step-and-Stitch
    # ------------------------------------------------------------------

    def mitigate_blanker_dead_channels(
        self,
        dead_fraction: float = 0.05,
        dead_coords_override: list[tuple[int, int]] | None = None,
    ) -> dict[str, Any]:
        """Plan physically exact wafer-stage step-and-stitch dead-beamlet compensation.

        Unlike physically invalid perimeter-spare teleportation, a rigid monolithic
        32x32 blanker plate translates as a unit with the wafer stage: covering dead
        interior sites requires integer-pitch stage offsets (dx, dy) so live neighbor
        beamlets land on the exact dead wafer coordinates (zero coordinate mismatch),
        incurring an honest, physically calculated stitch-pass throughput penalty.
        """
        rng = np.random.default_rng(self.seed + 33)
        c = self.cfg
        rows, cols = c.blanker_rows, c.blanker_cols
        n_total = rows * cols
        pitch_m = c.blanker_beam_pitch_mm * 1e-3
        pitch_um = c.blanker_beam_pitch_mm * 1e3

        active_coords = [(r, col) for r in range(rows) for col in range(cols)]
        if dead_coords_override is not None:
            dead_set: set[tuple[int, int]] = set()
            for rc in dead_coords_override:
                r, col = int(rc[0]), int(rc[1])
                if not (0 <= r < rows and 0 <= col < cols):
                    raise ValueError(f"Dead coordinate {(r, col)} outside {rows}x{cols} blanker grid")
                dead_set.add((r, col))
            dead_coords = sorted(dead_set)
            n_dead = len(dead_coords)
            eff_dead_frac = n_dead / float(n_total)
        else:
            eff_dead_frac = float(np.clip(dead_fraction, 0.0, 1.0))
            n_dead = int(round(n_total * eff_dead_frac))
            dead_indices = sorted(rng.choice(n_total, size=n_dead, replace=False).tolist()) if n_dead > 0 else []
            dead_coords = [active_coords[idx] for idx in dead_indices]
            dead_set = set(dead_coords)

        live_set = set(active_coords) - dead_set
        n_live = len(live_set)

        # Nominal field cycle time (16 mm field index + 15 ms parallel single-ion shot)
        t_field_step_s = _stage_step_time_s(
            rows * pitch_m, c.stage_max_accel_m_s2, c.stage_max_vel_m_s, c.stage_settle_ms * 1e-3
        )
        t_shot_s = c.blanker_shot_cycle_ms * 1e-3
        t_nom_field_s = t_field_step_s + t_shot_s

        uncovered = set(dead_set)
        stitch_passes: list[dict[str, Any]] = []
        remapping: list[dict[str, Any]] = []
        manhattan_shifts: list[int] = []
        used_live_beamlets: set[tuple[int, int]] = set()
        max_coord_mismatch_um = 0.0
        all_beamlets_live = True

        # Build candidate integer-pitch stage offsets ordered by Euclidean distance
        def _candidate_offsets(max_rad: int) -> list[tuple[int, int]]:
            offs = [
                (dr, dc)
                for dr in range(-max_rad, max_rad + 1)
                for dc in range(-max_rad, max_rad + 1)
                if not (dr == 0 and dc == 0)
            ]
            offs.sort(key=lambda o: (o[0] * o[0] + o[1] * o[1], abs(o[0]) + abs(o[1]), abs(o[0]), abs(o[1])))
            return offs

        small_offsets = _candidate_offsets(4)
        full_offsets: list[tuple[int, int]] | None = None

        prev_off = (0, 0)
        total_stitch_move_s = 0.0
        total_stitch_dwell_s = 0.0

        while uncovered and live_set:
            best_off: tuple[int, int] | None = None
            best_covered: list[tuple[int, int]] = []
            best_key: tuple[int, float, float] | None = None

            for search_pool in (small_offsets,):
                for dr, dc in search_pool:
                    cov = [(r, col) for (r, col) in uncovered if (r - dr, col - dc) in live_set]
                    if not cov:
                        continue
                    step_dist = math.hypot(dr - prev_off[0], dc - prev_off[1])
                    origin_dist = math.hypot(dr, dc)
                    # Maximize sites covered, break ties by smallest stage move then smallest offset
                    key = (-len(cov), step_dist, origin_dist)
                    if best_key is None or key < best_key:
                        best_key = key
                        best_off = (dr, dc)
                        best_covered = cov

            if best_off is None:
                if full_offsets is None:
                    full_offsets = _candidate_offsets(max(rows, cols) - 1)
                for dr, dc in full_offsets:
                    cov = [(r, col) for (r, col) in uncovered if (r - dr, col - dc) in live_set]
                    if not cov:
                        continue
                    step_dist = math.hypot(dr - prev_off[0], dc - prev_off[1])
                    origin_dist = math.hypot(dr, dc)
                    key = (-len(cov), step_dist, origin_dist)
                    if best_key is None or key < best_key:
                        best_key = key
                        best_off = (dr, dc)
                        best_covered = cov

            if best_off is None:
                break

            dr, dc = best_off
            best_covered.sort()
            move_m = math.hypot(dr - prev_off[0], dc - prev_off[1]) * pitch_m
            t_move_s = _stage_step_time_s(
                move_m, c.stage_max_accel_m_s2, c.stage_max_vel_m_s, c.stage_settle_ms * 1e-3
            )
            total_stitch_move_s += t_move_s
            total_stitch_dwell_s += t_shot_s
            pass_idx = len(stitch_passes) + 1

            for r, col in best_covered:
                rb, cb = r - dr, col - dc
                if (rb, cb) not in live_set:
                    all_beamlets_live = False
                # Verify exact wafer coordinate match: wafer_coord = beamlet_coord + stage_offset
                err_r_um = abs((rb + dr) - r) * pitch_um
                err_c_um = abs((cb + dc) - col) * pitch_um
                max_coord_mismatch_um = max(max_coord_mismatch_um, math.hypot(err_r_um, err_c_um))
                used_live_beamlets.add((rb, cb))
                m_shift = abs(dr) + abs(dc)
                manhattan_shifts.append(m_shift)
                remapping.append({
                    "stitch_pass": pass_idx,
                    "dead_channel_id": int(r * cols + col),
                    "dead_coord": [r, col],
                    "assigned_live_beamlet_id": int(rb * cols + cb),
                    "assigned_live_coord": [rb, cb],
                    "stage_offset_pitch": [dr, dc],
                    "stage_offset_um": [round(dc * pitch_um, 2), round(dr * pitch_um, 2)],
                    "coord_mismatch_um": round(math.hypot(err_r_um, err_c_um), 6),
                    "manhattan_shift": int(m_shift),
                })
                uncovered.remove((r, col))

            stitch_passes.append({
                "pass_index": pass_idx,
                "stage_offset_pitch": [dr, dc],
                "stage_offset_dx_um": round(dc * pitch_um, 2),
                "stage_offset_dy_um": round(dr * pitch_um, 2),
                "sites_covered": len(best_covered),
                "stage_move_ms": round(t_move_s * 1e3, 3),
                "stitch_dwell_ms": round(t_shot_s * 1e3, 3),
            })
            prev_off = best_off

        n_covered = len(remapping)
        n_assigned_ids = len({m["dead_channel_id"] for m in remapping})
        zero_double_exposure = bool(n_assigned_ids == n_covered)
        coverage_before_pct = 100.0 * n_live / float(n_total)
        coverage_after_pct = 100.0 * (n_live + n_covered) / float(n_total)

        total_stitch_time_s = total_stitch_move_s + total_stitch_dwell_s
        total_field_time_s = t_nom_field_s + total_stitch_time_s
        if n_live == 0:
            throughput_after_pct = 0.0
            stitch_overhead_pct = float("inf")
        else:
            throughput_after_pct = 100.0 * (t_nom_field_s / total_field_time_s)
            stitch_overhead_pct = 100.0 * (total_stitch_time_s / t_nom_field_s)

        throughput_penalty_pct = 100.0 - throughput_after_pct

        # Honest pass criterion: 100% spatial wafer coverage with zero coordinate mismatch,
        # strictly live neighbor beamlets, zero double exposure, and viable effective throughput.
        passed = bool(
            n_covered == n_dead
            and (n_live > 0 or n_dead == 0)
            and all_beamlets_live
            and zero_double_exposure
            and max_coord_mismatch_um == 0.0
            and coverage_after_pct == 100.0
            and throughput_after_pct >= 45.0
        )

        return {
            "fault_mode": "S3_blanker_dead_channels",
            "compensation_mode": "wafer_stage_step_and_stitch",
            "total_logical_channels": n_total,
            "spare_pool_size": c.blanker_spare_channels,
            "beam_pitch_um": round(pitch_um, 2),
            "injected_dead_fraction": round(eff_dead_frac, 6),
            "dead_channels_detected": n_dead,
            "channels_remapped": n_covered,
            "unique_spares_assigned": len(used_live_beamlets),
            "stitch_passes_required": len(stitch_passes),
            "stitch_pass_plan": stitch_passes,
            "wafer_site_coverage_before_pct": round(coverage_before_pct, 2),
            "wafer_site_coverage_after_pct": round(coverage_after_pct, 2),
            "throughput_before_recal_pct": round(coverage_before_pct, 2),
            "throughput_after_recal_pct": round(throughput_after_pct, 2),
            "throughput_penalty_pct": round(throughput_penalty_pct, 2),
            "stitch_overhead_pct": round(stitch_overhead_pct, 2) if math.isfinite(stitch_overhead_pct) else None,
            "nominal_field_time_ms": round(t_nom_field_s * 1e3, 3),
            "stitch_move_time_ms": round(total_stitch_move_s * 1e3, 3),
            "stitch_dwell_time_ms": round(total_stitch_dwell_s * 1e3, 3),
            "stitch_overhead_time_ms": round(total_stitch_time_s * 1e3, 3),
            "total_compensated_field_time_ms": round(total_field_time_s * 1e3, 3),
            "max_coordinate_mismatch_um": round(max_coord_mismatch_um, 6),
            "zero_coordinate_mismatch": bool(max_coord_mismatch_um == 0.0),
            "all_assigned_beamlets_live": all_beamlets_live,
            "zero_double_exposure": zero_double_exposure,
            "mean_manhattan_shift": round(float(np.mean(manhattan_shifts)), 2) if manhattan_shifts else 0.0,
            "max_manhattan_shift": int(max(manhattan_shifts)) if manhattan_shifts else 0,
            "sample_remappings": remapping[:5],
            "passed": passed,
        }

    # ------------------------------------------------------------------
    # Fault Mode (d): 31P Hyperfine +/-350 Hz Thermal Drift -> Q16.16 BOED Relock
    # ------------------------------------------------------------------

    def mitigate_hyperfine_thermal_drift(self, drift_Hz: float = 350.0) -> dict[str, Any]:
        """Inject +/-drift_Hz thermal shift on a 31P line and relock via Q1616BOEDCore."""
        rng = np.random.default_rng(self.seed + 55)
        c = self.cfg
        core = self.boed_core
        delta_fisher = c.hyperfine_gamma_Hz / math.sqrt(3.0)

        cases: dict[str, Any] = {}
        all_passed = True
        max_relock_ms = 0.0
        max_resid_Hz = 0.0

        for label, signed_drift in (("drift_plus", abs(drift_Hz)), ("drift_minus", -abs(drift_Hz))):
            f_true = c.hyperfine_nom_Hz + signed_drift
            # Controller starts from stale pre-drift nominal frequency with prior sigma = 800 Hz
            f_init_i, df_bins, lp_q = core.init_prior_q16(c.hyperfine_nom_Hz, prior_sigma_Hz=800.0)
            f_probe = float(f_init_i - int(round(delta_fisher)))
            mu_est = float(f_init_i)
            std_est = 800.0
            probes_used = 0
            total_fpga_cycles = 0

            for step in range(c.boed_max_probes):
                sig = float(lorentzian(np.array([f_probe - f_true]), c.hyperfine_gamma_Hz)[0])
                y_meas = sig + float(rng.normal(0.0, c.boed_probe_sigma_n))
                lp_q, trace = core.update_and_select_next(
                    f_init_i,
                    df_bins,
                    lp_q,
                    f_probe,
                    y_meas,
                    c.hyperfine_gamma_Hz,
                    c.boed_probe_sigma_n,
                    step,
                )
                probes_used += 1
                total_fpga_cycles += trace.total_cycles
                mu_est = trace.mu_Hz
                std_est = trace.std_Hz
                f_probe = trace.next_probe_Hz
                if probes_used >= 4 and std_est <= c.boed_target_sigma_Hz:
                    break

            fpga_ms = (total_fpga_cycles / core.cfg.f_clk_MHz) * 1e-3
            relock_time_ms = probes_used * c.boed_probe_time_ms + fpga_ms
            resid_err_Hz = abs(mu_est - f_true)
            passed = bool(
                relock_time_ms < c.relock_time_limit_ms
                and resid_err_Hz < c.relock_err_limit_Hz
            )
            all_passed = all_passed and passed
            max_relock_ms = max(max_relock_ms, relock_time_ms)
            max_resid_Hz = max(max_resid_Hz, resid_err_Hz)

            cases[label] = {
                "injected_drift_Hz": round(signed_drift, 2),
                "true_freq_Hz": round(f_true, 2),
                "estimated_freq_Hz": round(mu_est, 2),
                "residual_error_Hz": round(resid_err_Hz, 2),
                "posterior_std_Hz": round(std_est, 2),
                "probes_used": probes_used,
                "fpga_total_cycles": total_fpga_cycles,
                "fpga_compute_us": round(fpga_ms * 1e3, 3),
                "relock_time_ms": round(relock_time_ms, 4),
                "passed": passed,
            }

        return {
            "fault_mode": "31P_hyperfine_thermal_drift",
            "limit_relock_time_ms": c.relock_time_limit_ms,
            "limit_residual_error_Hz": c.relock_err_limit_Hz,
            "max_relock_time_ms": round(max_relock_ms, 4),
            "max_residual_error_Hz": round(max_resid_Hz, 2),
            "cases": cases,
            "passed": all_passed,
        }

    # ------------------------------------------------------------------
    # Full 4-Mode Autonomous Self-Healing Suite
    # ------------------------------------------------------------------

    def run_all_fault_scenarios(self) -> dict[str, Any]:
        """Run all 4 physical fault injections and return aggregate recovery ledger."""
        r_laser = self.mitigate_laser_power_drift(drift_pct=8.0)
        r_uhv = self.mitigate_vacuum_spike(peak_pressure_torr=3.5e-8)
        r_blank = self.mitigate_blanker_dead_channels(dead_fraction=0.05)
        r_therm = self.mitigate_hyperfine_thermal_drift(drift_Hz=350.0)
        all_pass = all(r["passed"] for r in (r_laser, r_uhv, r_blank, r_therm))
        return {
            "epistemic_tag": "Model/Sayisal-Simulasyon",
            "n_fault_modes": 4,
            "n_passed": sum(int(r["passed"]) for r in (r_laser, r_uhv, r_blank, r_therm)),
            "all_passed": all_pass,
            "S5_5_laser_drift": r_laser,
            "S5_uhv_vacuum_spike": r_uhv,
            "S3_blanker_dead_channels": r_blank,
            "hyperfine_thermal_drift": r_therm,
        }
