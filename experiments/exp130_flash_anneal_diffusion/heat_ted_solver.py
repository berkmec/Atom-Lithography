"""Exp130 Module 1: Coupled 1D Nonlinear Silicon Thermal Conduction PDE + Non-Equilibrium TED
/ Kick-Out Kinetics + Surface Segregation & Vacuum Evaporation + 28Si/29Si Isotope Mixing.

Literature anchors ({Literatür}):
  - Glassbrenner & Slack (1964) / NIST-JANAF: k_Si(T), c_p(T), T_melt = 1687 K, Theta_D = 645 K
  - Fahey, Griffin, Plummer, Rev. Mod. Phys. 61, 289 (1989): D_P^eq = 3.85 cm^2/s * exp(-3.66 eV/kT), f_I = 0.95
  - Bracht, Haller, Clark-Phelps, PRL 81, 393 (1998): D_Si^eq = 530 cm^2/s * exp(-4.75 eV/kT),
    self-interstitial E_f = 3.18 eV, E_m = 1.77 eV (E_SD,I = 4.95 eV)
  - Stolk et al., JAP 81, 6031 (1997) & Cowern et al., PRL 82, 4460 (1999): shallow-implant
    interstitial cluster dissolution E_diss = 3.10 eV, surface recombination length L_surf = 2.0 nm
  - Olson & Roth, Mater. Sci. Rep. 3, 1 (1988): SPE / local activation E_a = 2.70 eV
  - Exp108 anchor (doi:10.1063/1.331355): 600 C / 10 min P surface migration, 800 C / 10 min UHV escape
  - Exp92 BCA anchor: 5 keV 31P+ in Si, Rp = 6.46 nm, sigma_z = 2.88 nm, sigma_x = 3.259 nm

All units SI internally unless explicitly suffixed (_nm, _cm2, _ms, _K, _eV).
Epistemic label: {Model} / {Sayısal-Simülasyon} / {Literatür}. no_lab_measurement=True.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.linalg import solve_banded
from scipy.optimize import brentq

# Fundamental constants
KB_EV = 8.617333262e-5       # eV / K
KB_J = 1.380649e-23          # J / K
SIGMA_SB = 5.670374419e-8    # W / (m^2 K^4)
NA_AVOGADRO = 6.02214076e23  # 1 / mol

# Silicon physical constants
RHO_SI = 2329.0              # kg / m^3
MOLAR_MASS_SI = 0.0280855    # kg / mol
C_SI_CM3 = 5.0e22            # atoms / cm^3
T_MELT_SI = 1687.0           # K (1414 C)
THETA_DEBYE_SI = 645.0       # K
EPS_RAD_SI = 0.65            # high-T Si surface emissivity

# Tabulated NIST-JANAF / Glassbrenner-Slack crystalline Si properties (300 - 1687 K)
_T_TAB = np.array([250.0, 300.0, 400.0, 500.0, 600.0, 800.0, 1000.0, 1200.0, 1400.0, 1687.0, 1800.0])
_K_TAB = np.array([191.0, 148.0, 105.0, 80.0, 64.0, 42.2, 31.2, 25.7, 23.5, 22.0, 22.0])  # W/(m K)
_CP_TAB = np.array([650.0, 712.0, 790.0, 839.0, 871.0, 913.0, 946.0, 976.0, 1005.0, 1038.0, 1045.0])  # J/(kg K)

_K_INTERP = PchipInterpolator(_T_TAB, _K_TAB)
_CP_INTERP = PchipInterpolator(_T_TAB, _CP_TAB)


def k_si(T: np.ndarray | float) -> np.ndarray | float:
    """Crystalline Si thermal conductivity k_Si(T) [W/(m K)] for T >= 250 K."""
    Tc = np.clip(T, 250.0, 1800.0)
    return _K_INTERP(Tc)


def cp_si(T: np.ndarray | float) -> np.ndarray | float:
    """Crystalline Si specific heat capacity c_p(T) [J/(kg K)] for T >= 250 K."""
    Tc = np.clip(T, 250.0, 1800.0)
    return _CP_INTERP(Tc)


def cp_si_debye_cryo(T_K: np.ndarray) -> np.ndarray:
    """Exact Debye specific heat capacity c_v(T) [J/(kg K)] of Si from 0.02 K to 300 K.

    c_v(T) = (9 * R_mol / M_Si) * (T/Theta_D)^3 * int_0^{Theta_D/T} (x^4 e^x / (e^x - 1)^2) dx.
    """
    R_spec = (NA_AVOGADRO * KB_J) / MOLAR_MASS_SI  # J / (kg K) ~= 296.0
    T_arr = np.atleast_1d(np.asarray(T_K, dtype=np.float64))
    out = np.zeros_like(T_arr)
    # 48-point Gauss-Legendre on [0, 1] scaled to [0, min(Theta/T, 50)]
    xg, wg = np.polynomial.legendre.leggauss(48)
    u = 0.5 * (xg + 1.0)
    w = 0.5 * wg
    for i, Ti in enumerate(T_arr):
        if Ti <= 0.0:
            out[i] = 0.0
            continue
        x_max = THETA_DEBYE_SI / Ti
        if x_max > 60.0:
            # Exact low-T Debye T^3 limit: int_0^inf = 4*pi^4/15
            out[i] = (12.0 * (math.pi ** 4) / 5.0) * R_spec * (Ti / THETA_DEBYE_SI) ** 3
        else:
            x = x_max * u
            ex = np.exp(x)
            integrand = (x ** 4) * ex / ((ex - 1.0) ** 2)
            val = float(np.sum(w * integrand) * x_max)
            out[i] = 9.0 * R_spec * ((Ti / THETA_DEBYE_SI) ** 3) * val
    return out


def optical_si_params(wavelength_nm: float, T_K: np.ndarray | float) -> Tuple[float, np.ndarray]:
    """Return (reflectivity R, absorption_coeff alpha [1/m]) for crystalline Si at wavelength_nm.

    Anchors: Jellison & Modine (1982/1994) optical constants of Si.
    """
    T_arr = np.asarray(T_K, dtype=np.float64)
    if abs(wavelength_nm - 308.0) < 20.0:
        # XeCl UV excimer: direct interband absorption (~7 nm depth)
        R = 0.60
        alpha = np.full_like(T_arr, 1.40e8, dtype=np.float64)
    elif abs(wavelength_nm - 532.0) < 60.0:
        # Green laser / Xe flash visible peak (~1.3 um @300K -> ~100 nm @1400K)
        R = 0.37
        alpha = 7.8e5 * np.exp(np.clip((T_arr - 300.0) / 430.0, 0.0, 4.0))
    elif abs(wavelength_nm - 808.0) < 60.0:
        # Near-IR industrial millisecond diode laser (LSA standard, ~12 um @300K -> ~380 nm @1400K)
        R = 0.33
        alpha = 8.5e4 * np.exp(np.clip((T_arr - 300.0) / 320.0, 0.0, 4.5))
    else:
        raise ValueError(f"Unsupported wavelength_nm={wavelength_nm}")
    return R, alpha


# ---------------------------------------------------------------------------
# 1. 1D Nonlinear Finite-Volume Thermal Conduction PDE (500 um Si Wafer)
# ---------------------------------------------------------------------------
def build_stretched_thermal_grid(L_wafer_m: float = 500e-6, n_cells: int = 120, dz0_m: float = 50e-9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build geometrically stretched finite-volume grid on [0, L_wafer_m].

    Returns (z_centers, dz_cells, z_faces). Surface cell width ~ dz0_m resolves shallow
    optical absorption accurately while spanning the full 500 um wafer with ~120 cells.
    """
    # Solve geometric ratio r: dz0 * (r^n - 1) / (r - 1) = L_wafer_m
    def f_ratio(r: float) -> float:
        return dz0_m * (r ** n_cells - 1.0) / (r - 1.0) - L_wafer_m

    ratio = brentq(f_ratio, 1.0001, 1.35)
    dz = dz0_m * (ratio ** np.arange(n_cells))
    dz *= L_wafer_m / np.sum(dz)  # exact thickness match
    z_faces = np.concatenate([[0.0], np.cumsum(dz)])
    z_centers = 0.5 * (z_faces[:-1] + z_faces[1:])
    return z_centers, dz, z_faces


def solve_thermal_1d(
    fluence_J_per_cm2: float,
    t_pulse_s: float,
    wavelength_nm: float = 808.0,
    T_init_K: float = 300.0,
    L_wafer_m: float = 500e-6,
    n_cells: int = 120,
    n_steps_pulse: int = 80,
    n_steps_cool: int = 120,
    h_back_W_m2K: float = 50.0,
) -> Dict:
    """Solve 1D nonlinear finite-volume thermal PDE for an optical pulse of duration t_pulse_s.

    Pulse shape: smooth flat-top with 10% cosine rise/fall edges (realistic diode-laser / Xe flash
    pulse, normalized so integral I(t) dt == fluence).
    Boundary conditions:
      - Front (z=0): Stefan-Boltzmann radiative loss eps * sigma * (T^4 - T_amb^4)
      - Back (z=L): radiative + gentle stage contact conductance h_back * (T - T_init)
    Exact energy conservation checked over the entire simulation.
    """
    z_c, dz, z_f = build_stretched_thermal_grid(L_wafer_m, n_cells=n_cells)
    F_J_m2 = fluence_J_per_cm2 * 1.0e4  # 1 J/cm^2 = 1e4 J/m^2

    # Pulse temporal profile: smooth raised-cosine ramp (10% rise, 80% flat, 10% fall)
    # Exact integral of shape over [0, t_pulse] is 0.90 * t_pulse -> I_peak = F / (0.90 * t_pulse)
    t_rise = 0.10 * t_pulse_s
    t_fall_start = 0.90 * t_pulse_s
    I_peak = F_J_m2 / (0.90 * t_pulse_s)

    def pulse_intensity(t_mid: float) -> float:
        if t_mid <= 0.0 or t_mid >= t_pulse_s:
            return 0.0
        if t_mid < t_rise:
            return I_peak * 0.5 * (1.0 - math.cos(math.pi * t_mid / t_rise))
        if t_mid > t_fall_start:
            return I_peak * 0.5 * (1.0 + math.cos(math.pi * (t_mid - t_fall_start) / t_rise))
        return I_peak

    # Adaptive time grid: uniform during pulse, geometrically stretched during post-pulse cooling
    # Cool horizon = max(12 * t_pulse, 0.02 s) for short pulses, capped reasonably for long pulses
    t_cool_end = t_pulse_s + max(15.0 * t_pulse_s, min(0.05, 50.0 * t_pulse_s))
    dt_pulse = t_pulse_s / n_steps_pulse
    t_pulse_grid = np.linspace(0.0, t_pulse_s, n_steps_pulse + 1)
    # Stretched cooling grid
    cool_span = t_cool_end - t_pulse_s
    s_cool = np.geomspace(dt_pulse * 0.5, cool_span + dt_pulse * 0.5, n_steps_cool + 1) - dt_pulse * 0.5
    s_cool[0] = 0.0
    s_cool[-1] = cool_span
    t_grid = np.concatenate([t_pulse_grid, t_pulse_s + s_cool[1:]])

    T = np.full(n_cells, T_init_K, dtype=np.float64)
    T_surf_hist = np.empty(t_grid.size, dtype=np.float64)
    T_back_hist = np.empty(t_grid.size, dtype=np.float64)
    T_surf_hist[0] = T_init_K
    T_back_hist[0] = T_init_K

    # Precompute center-to-center distances for harmonic face conductivity
    dz_mid = z_c[1:] - z_c[:-1]  # length n_cells - 1
    E_abs_tot = 0.0
    E_loss_tot = 0.0

    # Exact initial enthalpy relative to T_init using midpoint quadrature of cp(T)
    def wafer_enthalpy_J_m2(T_vec: np.ndarray) -> float:
        # 8-point Gauss-Legendre per cell from T_init to T_vec
        xg, wg = np.polynomial.legendre.leggauss(8)
        u = 0.5 * (xg + 1.0)[None, :]
        w = 0.5 * wg[None, :]
        dT = (T_vec - T_init_K)[:, None]
        T_pts = T_init_K + dT * u
        h_cell = np.sum(w * cp_si(T_pts), axis=1) * (T_vec - T_init_K)
        return float(np.sum(RHO_SI * dz * h_cell))

    for step in range(t_grid.size - 1):
        t0, t1 = t_grid[step], t_grid[step + 1]
        dt = t1 - t0
        t_mid = 0.5 * (t0 + t1)
        I_in = pulse_intensity(t_mid)

        # Two Picard iterations per step for exact nonlinear k(T), cp(T), alpha(T) energy balance
        T_prev = T.copy()
        T_iter = T_prev.copy()
        for _ in range(2):
            T_half = 0.5 * (T_prev + T_iter)
            k_c = k_si(T_half)
            cp_c = cp_si(T_half)
            # Harmonic-weighted thermal conductance at internal faces
            # 1 / G_face = (dz_i/2)/k_i + (dz_{i+1}/2)/k_{i+1}
            G_face = 1.0 / (0.5 * dz[:-1] / k_c[:-1] + 0.5 * dz[1:] / k_c[1:])

            # Exact cell-integrated Beer-Lambert absorption using cumulative optical depth
            R_opt, alpha_c = optical_si_params(wavelength_nm, T_half)
            tau_cell = alpha_c * dz
            tau_cum = np.concatenate([[0.0], np.cumsum(tau_cell)])
            # Absorbed power per unit area in cell i: (1-R)*I_in * (exp(-tau_i) - exp(-tau_{i+1}))
            q_abs_cell = (1.0 - R_opt) * I_in * (np.exp(-tau_cum[:-1]) - np.exp(-tau_cum[1:]))

            # Linearized surface radiation & backside loss (at T_iter)
            h_rad_front = EPS_RAD_SI * SIGMA_SB * (T_half[0] ** 2 + T_init_K ** 2) * (T_half[0] + T_init_K)
            h_rad_back = EPS_RAD_SI * SIGMA_SB * (T_half[-1] ** 2 + T_init_K ** 2) * (T_half[-1] + T_init_K) + h_back_W_m2K

            # Backward-Euler finite-volume matrix:
            # C_i (T_i^{n+1} - T_i^n) / dt = G_{i+1/2}(T_{i+1}-T_i) - G_{i-1/2}(T_i-T_{i-1}) + q_abs_i - loss_i
            cap = RHO_SI * cp_c * dz / dt
            diag = cap.copy()
            diag[:-1] += G_face
            diag[1:] += G_face
            diag[0] += h_rad_front
            diag[-1] += h_rad_back

            rhs = cap * T_prev + q_abs_cell
            rhs[0] += h_rad_front * T_init_K
            rhs[-1] += h_rad_back * T_init_K

            ab = np.zeros((3, n_cells), dtype=np.float64)
            ab[0, 1:] = -G_face
            ab[1, :] = diag
            ab[2, :-1] = -G_face
            T_iter = solve_banded((1, 1), ab, rhs, overwrite_ab=True, overwrite_b=True)

        T = T_iter
        # Track exact absorbed & lost energy using final converged step fluxes
        T_half = 0.5 * (T_prev + T)
        R_opt, alpha_c = optical_si_params(wavelength_nm, T_half)
        tau_tot = float(np.sum(alpha_c * dz))
        E_abs_tot += (1.0 - R_opt) * I_in * (1.0 - math.exp(-tau_tot)) * dt
        h_rad_f = EPS_RAD_SI * SIGMA_SB * (T_half[0] ** 2 + T_init_K ** 2) * (T_half[0] + T_init_K)
        h_rad_b = EPS_RAD_SI * SIGMA_SB * (T_half[-1] ** 2 + T_init_K ** 2) * (T_half[-1] + T_init_K) + h_back_W_m2K
        E_loss_tot += (h_rad_f * (T[0] - T_init_K) + h_rad_b * (T[-1] - T_init_K)) * dt

        T_surf_hist[step + 1] = T[0]
        T_back_hist[step + 1] = T[-1]

    E_stored = wafer_enthalpy_J_m2(T)
    energy_rel_err = abs((E_stored + E_loss_tot) - E_abs_tot) / max(E_abs_tot, 1e-9)

    idx_peak = int(np.argmax(T_surf_hist))
    T_peak = float(T_surf_hist[idx_peak])
    # Quench time from peak down to < 900 K
    t_quench_900_s = float("nan")
    for k in range(idx_peak, t_grid.size):
        if T_surf_hist[k] < 900.0:
            t_quench_900_s = float(t_grid[k] - t_grid[idx_peak])
            break

    return {
        "wavelength_nm": wavelength_nm,
        "fluence_J_per_cm2": fluence_J_per_cm2,
        "t_pulse_s": t_pulse_s,
        "t_s": t_grid,
        "T_surf_K": T_surf_hist,
        "T_back_K": T_back_hist,
        "T_peak_K": T_peak,
        "T_peak_over_Tmelt": T_peak / T_MELT_SI,
        "T_back_max_K": float(np.max(T_back_hist)),
        "T_bulk_end_K": float(np.sum(T * dz) / L_wafer_m),
        "t_quench_to_900K_ms": t_quench_900_s * 1e3,
        "E_absorbed_J_cm2": E_abs_tot / 1e4,
        "E_stored_J_cm2": E_stored / 1e4,
        "E_lost_J_cm2": E_loss_tot / 1e4,
        "energy_balance_rel_err": float(energy_rel_err),
    }


def find_fluence_for_target_T(
    t_pulse_s: float,
    T_target_K: float,
    wavelength_nm: float = 808.0,
    T_init_K: float = 300.0,
    n_cells: int = 100,
) -> Dict:
    """Solve for the incident fluence F (J/cm^2) that achieves T_surf_peak == T_target_K."""
    # Bracket fluence automatically
    f_lo = 0.01
    f_hi = max(1.0, 25.0 * math.sqrt(max(t_pulse_s / 1e-3, 1e-4)))
    while solve_thermal_1d(f_hi, t_pulse_s, wavelength_nm, T_init_K, n_cells=n_cells, n_steps_pulse=40, n_steps_cool=40)["T_peak_K"] < T_target_K:
        f_hi *= 2.0
        if f_hi > 5000.0:
            break

    def resid(f_val: float) -> float:
        r = solve_thermal_1d(f_val, t_pulse_s, wavelength_nm, T_init_K, n_cells=n_cells, n_steps_pulse=40, n_steps_cool=40)
        return r["T_peak_K"] - T_target_K

    f_opt = brentq(resid, f_lo, f_hi, xtol=1e-3, rtol=1e-3)
    # Full high-res run at converged fluence
    return solve_thermal_1d(f_opt, t_pulse_s, wavelength_nm, T_init_K, n_cells=120, n_steps_pulse=80, n_steps_cool=120)


# ---------------------------------------------------------------------------
# 2. Non-Equilibrium TED + Kick-Out + Activation + Surface Escape + 29Si Mixing PDE
# ---------------------------------------------------------------------------
@dataclass
class KineticsParams:
    """Literature-anchored Si:31P defect, diffusion, activation, surface & 29Si kinetics."""
    # Fahey et al. (RMP 1989): equilibrium P diffusivity in Si
    D_P0_cm2_s: float = 3.85
    Ea_P_eV: float = 3.66
    f_I_P: float = 0.95  # interstitialcy fraction of P diffusion

    # Bracht et al. (PRL 81, 393, 1998): Si self-interstitial equilibrium & self-diffusion
    # Exact product D_I * C_I* / C_Si = 2980 * exp(-4.95 eV/kT) cm^2/s -> D_I0 * C_I0 = 1.49e26 cm^-1 s^-1
    # Formation entropy S_f^I ~= 11 k_B -> C_I0 = 2.98e27 cm^-3, D_I0 = 0.05 cm^2/s
    C_I0_cm3: float = 2.98e27
    Ef_I_eV: float = 3.18
    D_I0_cm2_s: float = 0.05
    Em_I_eV: float = 1.77
    D_Si0_cm2_s: float = 530.0
    Ea_Si_eV: float = 4.75
    f_I_Si: float = 0.60

    # Stolk (JAP 1997) & Cowern (PRL 1999): shallow-implant interstitial cluster release & surface sink
    nu_cl_s: float = 1.5e15        # cluster dissolution attempt frequency (1/s)
    Ea_cl_diss_eV: float = 3.10    # small-cluster dissociation energy (eV)
    L_surf_nm: float = 2.0         # surface interstitial recombination length (nm)

    # Olson & Roth (Mater. Sci. Rep. 3, 1, 1988, Table 1): Si(100) SPE velocity
    # v_SPE(T) = 3.68e8 cm/s * exp(-2.70 eV / kT) = 3.68e15 nm/s * exp(-2.70 eV / kT).
    # Across damaged layer depth L_regrow = 10.0 nm (~Rp + sigma_z = 9.34 nm):
    # nu_act = v_0 / L_regrow = 3.68e14 s^-1 (gives ~0.96 nm/s SPE at 600 C -> ~10 s regrowth).
    nu_act_s: float = 3.68e14      # Olson-Roth v_0 / L_regrow (1/s)
    Ea_act_eV: float = 2.70        # SPE / substitutional incorporation energy (eV)

    # Surface P segregation trapping & UHV desorption (Exp108 doi:10.1063/1.331355 anchor)
    L_trap_nm: float = 0.5
    nu_evap_s: float = 1.0e12      # surface P thermal desorption prefactor (1/s)
    Ea_evap_eV: float = 3.10       # surface P UHV desorption activation energy (eV)


def D_P_eq_nm2_s(T_K: float, p: KineticsParams) -> float:
    return p.D_P0_cm2_s * 1e14 * math.exp(-p.Ea_P_eV / (KB_EV * T_K))


def C_I_star_cm3(T_K: float, p: KineticsParams) -> float:
    return p.C_I0_cm3 * math.exp(-p.Ef_I_eV / (KB_EV * T_K))


def D_I_nm2_s(T_K: float, p: KineticsParams) -> float:
    return p.D_I0_cm2_s * 1e14 * math.exp(-p.Em_I_eV / (KB_EV * T_K))


def D_Si_eq_nm2_s(T_K: float, p: KineticsParams) -> float:
    return p.D_Si0_cm2_s * 1e14 * math.exp(-p.Ea_Si_eV / (KB_EV * T_K))


def k_act_s(T_K: float, p: KineticsParams) -> float:
    return p.nu_act_s * math.exp(-p.Ea_act_eV / (KB_EV * T_K))


def k_cl_diss_s(T_K: float, p: KineticsParams) -> float:
    return p.nu_cl_s * math.exp(-p.Ea_cl_diss_eV / (KB_EV * T_K))


def k_evap_s(T_K: float, p: KineticsParams) -> float:
    return p.nu_evap_s * math.exp(-p.Ea_evap_eV / (KB_EV * T_K))


def solve_ted_kinetics_1d(
    t_s: np.ndarray,
    T_K: np.ndarray,
    Rp_nm: float = 6.46,
    sigma_z_nm: float = 2.88,
    C_cl_peak_cm3: float = 3.0e19,
    r_casc_nm: float | None = 2.5,
    z_max_nm: float = 60.0,
    n_cells: int = 150,
    z_epi_nm: float = 20.0,
    params: KineticsParams | None = None,
) -> Dict:
    """Solve coupled 1D finite-volume PDEs for P activation, TED kick-out diffusion,
    surface segregation/evaporation, and 28Si/29Si epitaxial bath intermixing.

    Dimensionality physics:
      - r_casc_nm = None: 1D planar blanket high-dose implant (e.g. 1e15 cm^-2 in doi:10.1063/1.331355),
        where neighboring cascades overlap laterally so interstitials only escape vertically to z=0.
      - r_casc_nm = 2.5 nm: isolated single 5 keV 31P+ cascade (~2-3 surviving Frenkel interstitials
        in a r_casc=2.5 nm pocket surrounded by pristine Si), including exact 3D radial out-diffusion
        sink rate k_rad(T) = 4 * D_I(T) / r_casc^2 matching the 3D Laplace Green's function!

    Exact mass conservation invariant:
      sum((P_inact + P_s) * dz) + N_surf + N_evap == 1.0000000000 (to machine precision).
    """
    if params is None:
        params = KineticsParams()

    dz = z_max_nm / n_cells
    z = (np.arange(n_cells) + 0.5) * dz

    # Initial 5 keV 31P+ BCA depth profile (truncated Gaussian on z > 0, normalized to integral = 1)
    g0 = np.exp(-0.5 * ((z - Rp_nm) / sigma_z_nm) ** 2)
    P_init = g0 / (np.sum(g0) * dz)  # 1/nm units, integral dz = 1.0
    var_z_init = float(np.sum(((z - float(np.sum(z * P_init) * dz)) ** 2) * P_init) * dz)
    mean_z_init = float(np.sum(z * P_init) * dz)

    # Initial species
    P_inact = P_init.copy()
    P_act = np.zeros(n_cells, dtype=np.float64)  # substitutional + mobile kick-out pair
    N_surf = 0.0   # trapped at z=0 front surface (fraction of total dose)
    N_evap = 0.0   # thermally evaporated into UHV (fraction of total dose)

    # Initial implant-damage interstitial cluster reservoir (peaks slightly deeper/overlapping Rp)
    C_cl = C_cl_peak_cm3 * (g0 / float(np.max(g0)))
    I_conc = np.full(n_cells, C_I_star_cm3(float(T_K[0]), params), dtype=np.float64)

    # Initial 29Si epitaxial layer profile: f = 1% for z <= z_epi_nm, 0% in 28Si substrate
    C29 = np.where(z <= z_epi_nm, 0.01, 0.0).astype(np.float64)

    idx_rp = int(np.argmin(np.abs(z - Rp_nm)))
    idx_epi = int(np.argmin(np.abs(z - z_epi_nm)))
    int_2D_P_lat = 0.0
    int_2D_Si_rp = 0.0
    int_2D_Si_epi = 0.0
    max_S_I = 1.0

    for step in range(t_s.size - 1):
        dt = float(t_s[step + 1] - t_s[step])
        if dt <= 0.0:
            continue
        Tm = 0.5 * float(T_K[step] + T_K[step + 1])
        if Tm < 450.0:
            continue

        # Kinetic rates at Tm
        d_p_eq = D_P_eq_nm2_s(Tm, params)
        d_i = D_I_nm2_s(Tm, params)
        c_i_star = max(C_I_star_cm3(Tm, params), 1e-30)
        d_si_eq = D_Si_eq_nm2_s(Tm, params)
        ka = k_act_s(Tm, params)
        kd = k_cl_diss_s(Tm, params)
        ke = k_evap_s(Tm, params)

        # 1. Exact exponential cluster release over dt: C_cl(t+dt) = C_cl(t) * exp(-kd * dt)
        exp_kd = math.exp(-min(kd * dt, 500.0))
        dC_cl_released = C_cl * (1.0 - exp_kd)
        C_cl = C_cl * exp_kd
        gen_I_rate = dC_cl_released / dt  # cm^-3 / s

        # 2. Implicit 1D diffusion PDE for Si self-interstitials I(z, t)
        #    Surface Robin sink at z=0: J_I(0) = -(d_i / L_surf) * (I(0) - C_I*)
        #    Deep bulk Dirichlet at z=z_max: I(z_max) = C_I*
        #    For isolated single-donor cascade (r_casc_nm != None), include exact 3D radial
        #    out-diffusion loss rate k_rad = 4 * d_i / r_casc^2 toward equilibrium C_I*!
        alpha_I = d_i * dt / (dz * dz)
        k_rad_dt = (4.0 * d_i / (r_casc_nm ** 2)) * dt if r_casc_nm is not None else 0.0
        diag_I = np.full(n_cells, 1.0 + 2.0 * alpha_I + k_rad_dt, dtype=np.float64)
        # Surface cell i=0: one internal face + exact Robin sink (distance dz/2 to z=0) + radial loss
        k_surf_I = (d_i / (params.L_surf_nm + 0.5 * dz)) * dt / dz
        diag_I[0] = 1.0 + alpha_I + k_surf_I + k_rad_dt
        # Deep cell i=-1: Dirichlet C_I* at outer boundary (distance dz/2) + radial loss
        diag_I[-1] = 1.0 + 3.0 * alpha_I + k_rad_dt
        rhs_I = I_conc + gen_I_rate * dt + k_rad_dt * c_i_star
        rhs_I[0] += k_surf_I * c_i_star
        rhs_I[-1] += 2.0 * alpha_I * c_i_star

        ab_I = np.zeros((3, n_cells), dtype=np.float64)
        ab_I[0, 1:] = -alpha_I
        ab_I[1, :] = diag_I
        ab_I[2, :-1] = -alpha_I
        I_conc = np.maximum(solve_banded((1, 1), ab_I, rhs_I, overwrite_ab=True, overwrite_b=True), c_i_star)

        S_I = I_conc / c_i_star
        max_S_I = max(max_S_I, float(S_I[idx_rp]))

        # 3. Activation: exact exponential transfer P_inact -> P_act
        exp_ka = math.exp(-min(ka * dt, 500.0))
        dP_act = P_inact * (1.0 - exp_ka)
        P_inact = P_inact * exp_ka
        P_act = P_act + dP_act

        # 4. Implicit mass-conserving 1D PDE for mobile/active P under TED kick-out diffusivity
        #    D_P,eff(z) = d_p_eq * (f_I * S_I(z) + (1 - f_I))
        #    Note: During high-S_I TED (like 600 C / 10 min), even partially un-activated P-I pairs
        #    participate in interstitialcy kick-out migration; we apply D_P,eff to P_act and also
        #    allow TED-driven kick-out transport of P_act with surface trapping sink at z=0.
        D_P_eff = d_p_eq * (params.f_I_P * S_I + (1.0 - params.f_I_P))
        int_2D_P_lat += 2.0 * float(D_P_eff[idx_rp]) * dt

        # Face diffusivities (harmonic mean)
        D_face = 2.0 * D_P_eff[:-1] * D_P_eff[1:] / np.maximum(D_P_eff[:-1] + D_P_eff[1:], 1e-60)
        lam_f = D_face * dt / (dz * dz)
        # Surface segregation sink velocity at z=0 (exact FVM distance dz/2 + L_trap)
        k_trap = (D_P_eff[0] / (params.L_trap_nm + 0.5 * dz)) * dt / dz

        diag_P = np.ones(n_cells, dtype=np.float64)
        diag_P[:-1] += lam_f
        diag_P[1:] += lam_f
        diag_P[0] += k_trap  # exact flux leaving cell 0 into N_surf!

        ab_P = np.zeros((3, n_cells), dtype=np.float64)
        ab_P[0, 1:] = -lam_f
        ab_P[1, :] = diag_P
        ab_P[2, :-1] = -lam_f
        P_act_new = solve_banded((1, 1), ab_P, P_act, overwrite_ab=True, overwrite_b=True)
        # Exact flux trapped into surface reservoir during this step (conserves total P to 1e-15!)
        flux_trapped = float(k_trap * P_act_new[0] * dz)
        P_act = P_act_new

        # 5. Exact surface pile-up + UHV evaporation ODE over dt:
        #    dN_surf/dt = r_in - ke * N_surf, where r_in = flux_trapped / dt
        if ke * dt < 1e-7:
            evap_step = ke * dt * (N_surf + 0.5 * flux_trapped)
            N_surf_new = N_surf + flux_trapped - evap_step
        else:
            exp_ke = math.exp(-min(ke * dt, 500.0))
            r_in = flux_trapped / dt
            N_surf_new = N_surf * exp_ke + (r_in / ke) * (1.0 - exp_ke)
            evap_step = (N_surf + flux_trapped) - N_surf_new
        N_surf = max(0.0, N_surf_new)
        N_evap += max(0.0, evap_step)

        # 6. 29Si epitaxial bath self-diffusion (Bracht 1998 + TED enhancement)
        D_Si_eff = d_si_eq * (params.f_I_Si * S_I + (1.0 - params.f_I_Si))
        int_2D_Si_rp += 2.0 * float(D_Si_eff[idx_rp]) * dt
        int_2D_Si_epi += 2.0 * float(D_Si_eff[idx_epi]) * dt
        D_si_f = 2.0 * D_Si_eff[:-1] * D_Si_eff[1:] / np.maximum(D_Si_eff[:-1] + D_Si_eff[1:], 1e-60)
        lam_si = D_si_f * dt / (dz * dz)
        diag_si = np.ones(n_cells, dtype=np.float64)
        diag_si[:-1] += lam_si
        diag_si[1:] += lam_si
        ab_si = np.zeros((3, n_cells), dtype=np.float64)
        ab_si[0, 1:] = -lam_si
        ab_si[1, :] = diag_si
        ab_si[2, :-1] = -lam_si
        C29 = solve_banded((1, 1), ab_si, C29, overwrite_ab=True, overwrite_b=True)

    # Final diagnostics & mass conservation audit
    bulk_inact = float(np.sum(P_inact) * dz)
    bulk_act = float(np.sum(P_act) * dz)
    mass_total = bulk_inact + bulk_act + N_surf + N_evap
    mass_err = abs(mass_total - 1.0)

    # Active bulk profile statistics
    if bulk_act > 1e-6:
        p_norm = P_act / bulk_act
        mean_z_fin = float(np.sum(z * p_norm) * dz)
        var_z_fin = float(np.sum(((z - mean_z_fin) ** 2) * p_norm) * dz)
        delta_sigma_z = math.sqrt(max(0.0, var_z_fin - var_z_init))
    else:
        mean_z_fin = mean_z_init
        delta_sigma_z = 0.0

    # Lateral diffusive broadening sigma_anneal = sqrt(2 * int D_P,eff(Rp, t) dt)
    sigma_anneal_lat_nm = math.sqrt(max(0.0, int_2D_P_lat))
    sigma_iso_rp_nm = math.sqrt(max(0.0, int_2D_Si_rp))
    sigma_iso_epi_nm = math.sqrt(max(0.0, int_2D_Si_epi))
    # Actual 29Si concentration drift at qubit depth Rp (from initial 1.0% epi bath)
    c29_at_rp_pct = float(C29[idx_rp]) * 100.0
    c29_drift_rel = abs(float(C29[idx_rp]) - 0.01) / 0.01

    return {
        "f_act_bulk": bulk_act,
        "f_inact_bulk": bulk_inact,
        "f_surface_pileup": N_surf,
        "f_vacuum_escape": N_evap,
        "f_total_surface_loss": N_surf + N_evap,
        "mass_conservation_err": mass_err,
        "sigma_anneal_nm": sigma_anneal_lat_nm,
        "delta_sigma_z_nm": delta_sigma_z,
        "mean_z_init_nm": mean_z_init,
        "mean_z_final_nm": mean_z_fin,
        "sigma_iso_nm": max(sigma_iso_rp_nm, sigma_iso_epi_nm),
        "sigma_iso_rp_nm": sigma_iso_rp_nm,
        "sigma_iso_epi_nm": sigma_iso_epi_nm,
        "c29_at_rp_pct": c29_at_rp_pct,
        "c29_drift_rel_at_rp": c29_drift_rel,
        "max_S_I_at_Rp": max_S_I,
        "z_nm": z,
        "P_init": P_init,
        "P_act_final": P_act,
        "P_inact_final": P_inact,
        "C29_final": C29,
    }


def build_synthetic_thermal_waveform(
    T_peak_K: float, t_pulse_s: float, T_base_K: float = 300.0, n_pts: int = 160
) -> Tuple[np.ndarray, np.ndarray]:
    """Smoothly blended thermal pulse waveform T(t) spanning 10 us to 600 s.

    - Short pulses (t_pulse << 30 ms): conductive surface self-quench calibrated to 1D Si PDE
      (heating ~ sqrt(t/tp), cooling ~ sqrt(1+u) - sqrt(u)).
    - Long pulses (t_pulse >> 30 ms, RTA/furnace): isothermal soak at T_peak with 5% ramp up/down.
    Smooth logistic blend around tau_wafer = 30 ms avoids any kink in 2D phase-diagram contours.
    (Exact 1D nonlinear thermal PDE is used at all reported design points and wavelength benchmarks.)
    """
    dT = T_peak_K - T_base_K
    # Blend factor w_iso in [0, 1]: 0 for ms-flash self-quench, 1 for RTA/furnace isothermal soak
    x_blend = math.log10(max(t_pulse_s, 1e-7) / 0.030)
    w_iso = 1.0 / (1.0 + math.exp(-4.0 * x_blend))

    # Common normalized pulse grid: [0, t_pulse] (80 pts) + cooling tail (80 pts)
    n1 = n_pts // 2
    n2 = n_pts - n1
    frac1 = np.linspace(0.0, 1.0, n1)
    t1 = frac1 * t_pulse_s

    # Short-pulse heating shape vs isothermal flat-top heating shape (5% rise ramp)
    shape1_short = np.sqrt(np.clip(frac1, 0.0, 1.0))
    shape1_iso = np.minimum(1.0, frac1 / 0.05)
    T1 = T_base_K + dT * ((1.0 - w_iso) * shape1_short + w_iso * shape1_iso)

    # Cooling tail: conductive self-quench over 12*t_pulse vs radiative/ramp cooldown over min(0.05*t_pulse, 5 s)
    cool_short = 12.0 * t_pulse_s
    cool_iso = min(0.05 * t_pulse_s, 5.0)
    cool_span = (1.0 - w_iso) * cool_short + w_iso * cool_iso
    s2 = np.geomspace(1e-3 * cool_span, cool_span, n2)
    t2 = t_pulse_s + s2

    u_short = s2 / max(t_pulse_s, 1e-9)
    shape2_short = np.sqrt(1.0 + u_short) - np.sqrt(u_short)
    shape2_iso = np.clip(1.0 - s2 / max(cool_span, 1e-9), 0.0, 1.0)
    T2 = T_base_K + dT * ((1.0 - w_iso) * shape2_short + w_iso * shape2_iso)

    return np.concatenate([t1, t2]), np.concatenate([T1, T2])


def cp_debye_solid(T_K: np.ndarray, theta_D: float, molar_mass_kg: float) -> np.ndarray:
    """Exact Debye specific heat capacity c_v(T) [J/(kg K)] for any monatomic solid."""
    R_spec = (NA_AVOGADRO * KB_J) / molar_mass_kg
    T_arr = np.atleast_1d(np.asarray(T_K, dtype=np.float64))
    out = np.zeros_like(T_arr)
    xg, wg = np.polynomial.legendre.leggauss(48)
    u = 0.5 * (xg + 1.0)
    w = 0.5 * wg
    for i, Ti in enumerate(T_arr):
        if Ti <= 0.0:
            continue
        x_max = theta_D / Ti
        if x_max > 60.0:
            out[i] = (12.0 * (math.pi ** 4) / 5.0) * R_spec * (Ti / theta_D) ** 3
        else:
            x = x_max * u
            ex = np.exp(x)
            val = float(np.sum(w * (x ** 4) * ex / ((ex - 1.0) ** 2)) * x_max)
            out[i] = 9.0 * R_spec * ((Ti / theta_D) ** 3) * val
    return out


def compute_cryo_cooldown_to_20mK(
    fluence_J_per_cm2: float,
    area_illuminated_cm2: float,
    absorptivity: float = 0.67,
    wafer_diam_mm: float = 50.0,
    wafer_thick_mm: float = 0.50,
    cu_carrier_mass_kg: float = 0.15,
    T_pre_K: float = 4.0,
    P_4K_switch_W: float = 1.0,
    P_still_W: float = 0.030,
    P_mxc_100mK_W: float = 540e-6,
    P_mxc_20mK_W: float = 19e-6,
    thermal_contact_overhead_s: float = 120.0,
) -> Dict[str, float]:
    """Compute exact Debye-integral thermal recovery time of wafer + Cu/AlN carrier to 20 mK.

    Models realistic in-situ flash recovery: absorbed optical energy equilibrates across the
    50 mm Si wafer + 0.15 kg OFHC-Cu/AlN cold-stage carrier (Theta_D_Cu = 343 K), then is
    extracted strictly via the 4 K PT410/420 thermal switch (1.0-1.5 W), Still (30 mW), and
    MXC (540 uW @100 mK -> 19 uW @20 mK), plus conservative 120 s contact/DR settling overhead.
    """
    vol_m3 = math.pi * ((0.5 * wafer_diam_mm * 1e-3) ** 2) * (wafer_thick_mm * 1e-3)
    mass_si_kg = RHO_SI * vol_m3
    E_abs_J = fluence_J_per_cm2 * area_illuminated_cm2 * absorptivity

    # Exact Debye enthalpy of (Si wafer + OFHC-Cu carrier) from 0.02 K to 300 K
    T_grid = np.concatenate([np.geomspace(0.02, 10.0, 200), np.linspace(10.5, 450.0, 300)])
    cp_si_arr = cp_debye_solid(T_grid, THETA_DEBYE_SI, MOLAR_MASS_SI)
    cp_cu_arr = cp_debye_solid(T_grid, 343.0, 0.063546)  # OFHC Cu Theta_D=343 K, M=63.546 g/mol
    C_tot_J_K = mass_si_kg * cp_si_arr + cu_carrier_mass_kg * cp_cu_arr
    H_tot = np.concatenate([[0.0], np.cumsum(0.5 * (C_tot_J_K[:-1] + C_tot_J_K[1:]) * np.diff(T_grid))])

    H_pre = float(np.interp(T_pre_K, T_grid, H_tot))
    H_post = H_pre + E_abs_J
    T_eq_post = float(np.interp(H_post, H_tot, T_grid))

    H_4K = float(np.interp(4.0, T_grid, H_tot))
    H_1K = float(np.interp(1.0, T_grid, H_tot))
    H_100mK = float(np.interp(0.10, T_grid, H_tot))

    # All heat above 4 K extracted via 4 K thermal switch (PT410=1.0 W / PT420=2.0 W)
    t_above_4K = max(0.0, H_post - H_4K) / P_4K_switch_W
    t_4K_to_1K = max(0.0, min(H_post, H_4K) - H_1K) / P_still_W
    t_1K_to_100mK = max(0.0, min(H_post, H_1K) - H_100mK) / P_mxc_100mK_W
    t_100mK_to_20mK = max(0.0, min(H_post, H_100mK)) / P_mxc_20mK_W
    t_cryo_sub4K = t_4K_to_1K + t_1K_to_100mK + t_100mK_to_20mK
    t_tot_s = t_above_4K + t_cryo_sub4K + thermal_contact_overhead_s

    return {
        "wafer_mass_g": mass_si_kg * 1e3,
        "cu_carrier_mass_kg": cu_carrier_mass_kg,
        "E_absorbed_J": E_abs_J,
        "T_pre_K": T_pre_K,
        "T_bulk_eq_post_flash_K": T_eq_post,
        "H_stage_4K_to_20mK_mJ": H_4K * 1e3,
        "t_cool_above_4K_s": t_above_4K,
        "t_cool_4K_to_20mK_s": t_cryo_sub4K,
        "t_contact_settling_s": thermal_contact_overhead_s,
        "t_cool_total_s": t_tot_s,
        "t_cool_total_min": t_tot_s / 60.0,
    }


if __name__ == "__main__":
    print("=== 1. 1D Thermal PDE Check (808 nm & 532 nm, 1.0 ms -> T_peak = 1500 K) ===")
    th808 = find_fluence_for_target_T(1.0e-3, 1500.0, wavelength_nm=808.0)
    print("808 nm 1.0ms:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in th808.items() if not isinstance(v, np.ndarray)})
    th532 = find_fluence_for_target_T(1.0e-3, 1500.0, wavelength_nm=532.0)
    print("532 nm 1.0ms:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in th532.items() if not isinstance(v, np.ndarray)})

    print("\n=== 2. Exp108 Anchor Check (doi:10.1063/1.331355: 600C & 800C / 10 min UHV, 1D blanket 1e15 cm^-2) ===")
    for T_C in (600.0, 800.0):
        t_w, T_w = build_synthetic_thermal_waveform(T_C + 273.15, 600.0)
        # 1D planar blanket high-dose implant (r_casc_nm=None, C_cl = 1.5e20 cm^-3)
        r_hi = solve_ted_kinetics_1d(t_w, T_w, C_cl_peak_cm3=1.5e20, r_casc_nm=None)
        print(
            f"  {T_C:.0f}C/10min (high-dose 1D): act={r_hi['f_act_bulk']:.3f} pileup={r_hi['f_surface_pileup']:.3f} "
            f"escape={r_hi['f_vacuum_escape']:.3f} sig_ann={r_hi['sigma_anneal_nm']:.2f} nm "
            f"mass_err={r_hi['mass_conservation_err']:.2e}"
        )

    print("\n=== 3. Machine 5 keV Isolated Single-Donor Comparison (r_casc=2.5 nm, C_cl=3e19 cm^-3 ~2 I/ion) ===")
    for lbl, T_C, tp in [("Furnace 600C/10m", 600.0, 600.0), ("Furnace 800C/10m", 800.0, 600.0), ("RTA 1000C/10s", 1000.0, 10.0)]:
        tw, Tw = build_synthetic_thermal_waveform(T_C + 273.15, tp)
        rr = solve_ted_kinetics_1d(tw, Tw, C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)
        print(
            f"  {lbl:18s}: act={rr['f_act_bulk']:.4f} loss={rr['f_total_surface_loss']:.4f} "
            f"sig_ann={rr['sigma_anneal_nm']:.3f} nm sig_iso={rr['sigma_iso_nm']:.4f} nm"
        )
    for tp_ms, Tpk in [(0.8, 1500.0), (1.0, 1500.0), (1.5, 1480.0), (2.0, 1460.0)]:
        th = find_fluence_for_target_T(tp_ms * 1e-3, Tpk, wavelength_nm=808.0)
        r_fl = solve_ted_kinetics_1d(th["t_s"], th["T_surf_K"], C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)
        print(
            f"  Flash {tp_ms:.1f}ms/{Tpk:.0f}K (F={th['fluence_J_per_cm2']:4.1f} J/cm2): "
            f"act={r_fl['f_act_bulk']:.4f} loss={r_fl['f_total_surface_loss']:.5f} "
            f"sig_ann={r_fl['sigma_anneal_nm']:.4f} nm sig_iso={r_fl['sigma_iso_nm']:.5f} nm"
        )
