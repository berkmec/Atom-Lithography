"""Exact 4x4 donor-interface flip-flop Hamiltonian & 3D straggle yield model (Exp131).

Anchored to:
- Tosi et al., Nat. Commun. 8, 450 (2017): 31P donor-interface flip-flop qubit.
- Harvey-Collard et al., Phys. Rev. X 12, 021026 (2022) & Samkharadze et al.,
  Science 359, 1123 (2018): high-impedance NbTiN Si cQED electric-dipole coupling.
- Calderon et al., Phys. Rev. Lett. 96, 096802 (2006): minimum donor-interface
  separation for a distinct double-well tunnel barrier.
- Repo anchor Exp124: 5 keV 31P+ BCA straggle (R_p=6.46 nm, sigma_z=2.88 nm,
  sigma_xy=3.67 nm, z_imp > 0.5 nm).
- Repo anchor Exp109: NbTiN resonator Q_i >= 2e5 at 7-20 mK, B_parallel <= 0.30 T.

Epistemic scope: {Model} / {Sayisal-Simulasyon} / {Literatur}. No lab measurement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any

import numpy as np

# Fundamental physical constants (SI exact 2019)
HBAR = 1.054571817e-34        # J*s
H_PLANCK = 6.62607015e-34     # J*s
E_CHARGE = 1.602176634e-19    # C
GHZ_PER_UEV = (E_CHARGE * 1e-6) / H_PLANCK / 1e9  # 0.2417989242 GHz/ueV

# Exp124 5 keV 31P+ implantation straggle anchor (legacy truncated Exp92 BCA)
EXP124_RP_NM = 6.46
EXP124_SIGMA_Z_NM = 2.88
EXP124_SIGMA_XY_NM = 3.67
EXP124_Z_MIN_IMP_NM = 0.50

# Actual Pilot 2B iradina 1.2.3 3D BCA 5 keV 31P+ straggle + Exp124 equip (OBS-047)
IRADINA_5KEV_RP_NM = 10.3107
IRADINA_5KEV_SIGMA_Z_NM = 5.098
IRADINA_5KEV_SIGMA_XY_NM = 4.718

# Si(001) monolayer lattice & 2-valley interference constants (Calderon 2006 / Tosi 2017, OBS-047)
A0_SI_NM = 0.5431
A_ML_SI_NM = A0_SI_NM / 4.0         # 0.135775 nm Si(001) monolayer spacing
K0_VALLEY_INV_NM = 0.85 * 2.0 * math.pi / A0_SI_NM  # pi/k0 = 0.3195 nm valley oscillation half-period

# Tosi 2017 / Si:P flip-flop physical parameters
A0_HYPERFINE_GHZ = 0.11753          # 117.53 MHz bulk 31P isotropic hyperfine
DELTA_G_INTERFACE_GHZ = +0.005      # +5.0 MHz Si/SiO2 interface g-factor shift (g_I > g_D)
TC_REF_GHZ = 11.0                   # Tunnel coupling at d_eff = 12.0 nm (Tosi 2017)
TC_REF_DEPTH_NM = 12.0
TC_DECAY_LEN_NM = 2.43              # Si donor Bohr-radius tunnel decay length
Z_MIN_DOUBLE_WELL_NM = 8.5          # Calderon 2006 / Tosi 2017 min barrier depth (~3.4 a_B)
LATERAL_STRAGGLE_WEIGHT = 0.20      # Effective path-length sensitivity to lateral offset
LEVER_ARM_AT_14NM = 0.20            # Capacitive resonator lever arm alpha_r(14 nm)
GAMMA_1_CHARGE_10GHZ_GHZ = 5.305e-3 # T_1,ch(10 GHz) = 30 ns -> Gamma/(2pi) = 5.305 MHz
GAMMA_1_SO_FLOOR_GHZ = 1.6e-8       # 16 Hz residual spin-orbit relaxation floor (~10 ms)
GAMMA_PHI_NUC_1PCT_GHZ = 0.5e-6     # Legacy 0.5 kHz Markovian floor (understates un-echoed Overhauser >1000x; see OBS-110)
OVERHAUSER_SIGMA_1PCT_KL_MHZ = 1.001     # Quasistatic Overhauser sigma_OH at f=1.0% (KL, T2*=0.225 us; OBS-110)
OVERHAUSER_SIGMA_1P5PCT_KL_MHZ = 1.281   # Quasistatic Overhauser sigma_OH at f=1.5% (KL, T2*=0.176 us; OBS-110)
OVERHAUSER_T2_STAR_1P5PCT_HM5962_US = 0.088
ROUTE_C_S_EPS_NOM_UEV = 0.3897      # Exp139 Route C nominal 1/f charge noise (OBS-111)
ROUTE_C_S_EPS_CONS_UEV = 0.5491     # Exp139 Route C conservative 1/f charge noise (OBS-111)
ONE_OVER_F_RMS_FACTOR = 5.2565      # sqrt(ln(10^12)) over 12 decades [1e-2, 1e10] Hz

# Pauli-like charge dipole operator tau_z = diag(-1, -1, +1, +1) in {|D,0>,|D,1>,|I,0>,|I,1>}
TAU_Z_4 = np.diag([-1.0, -1.0, +1.0, +1.0])


@dataclass
class CellResult:
    """Single-donor flip-flop qubit operating point metrics."""

    z_nm: float
    r_xy_nm: float
    d_eff_nm: float
    t_c_ghz: float
    eps_ghz: float
    omega_q_ghz: float
    p_donor: float
    p_exc_charge: float
    g_c_mhz: float
    g_eff_mhz: float
    d1_ghz_per_ghz: float
    d2_inv_ghz: float
    gamma_1_khz: float
    gamma_phi_khz: float
    gamma_tot_khz: float
    kappa_khz: float
    cooperativity: float
    m_res_merit: float
    valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def v_zpf_volts(f_r_ghz: float, z_r_ohm: float) -> float:
    """Zero-point voltage fluctuation V_zpf = omega_r * sqrt(hbar * Z_r / 2) in Volts."""
    omega_r = 2.0 * math.pi * f_r_ghz * 1e9
    return omega_r * math.sqrt(HBAR * z_r_ohm / 2.0)


def bare_charge_coupling_ghz(z_nm: float, f_r_ghz: float = 5.0, z_r_ohm: float = 3000.0) -> tuple[float, float]:
    """Return (g_c_ghz, delta_eps_r_ghz) for a donor-interface dipole at depth z_nm."""
    z_clamped = min(max(z_nm, 2.0), 25.0)
    alpha_r = LEVER_ARM_AT_14NM * (z_clamped / 14.0)
    vz = v_zpf_volts(f_r_ghz, z_r_ohm)
    delta_eps_r_ghz = alpha_r * (E_CHARGE * vz / H_PLANCK) / 1e9
    return 0.5 * delta_eps_r_ghz, delta_eps_r_ghz


def tunnel_coupling_ghz(
    z_nm: float,
    r_xy_nm: float = 0.0,
    include_valley_interference: bool = False,
    valley_phase_rad: float = 0.0,
    snap_monolayer: bool = True,
) -> tuple[float, float]:
    """Return (t_c_ghz, d_eff_nm) for a 31P donor at (r_xy, z).

    When `include_valley_interference=True` (OBS-047 fix), applies Si(001) monolayer-snapped
    2-valley donor-interface interference |cos(k0 * z_ml + phi0)| (Calderon 2006 / Tosi 2017).
    """
    z_use = round(z_nm / A_ML_SI_NM) * A_ML_SI_NM if (include_valley_interference and snap_monolayer) else z_nm
    d_eff = math.sqrt(z_use * z_use + LATERAL_STRAGGLE_WEIGHT * r_xy_nm * r_xy_nm)
    t_c = TC_REF_GHZ * math.exp(-(d_eff - TC_REF_DEPTH_NM) / TC_DECAY_LEN_NM)
    if include_valley_interference:
        t_c *= abs(math.cos(K0_VALLEY_INV_NM * z_use + valley_phase_rad))
    return t_c, d_eff


def build_flipflop_h4(
    eps_ghz: float,
    t_c_ghz: float,
    omega_ff_ghz: float = 5.0,
    a0_ghz: float = A0_HYPERFINE_GHZ,
    delta_g_ghz: float = DELTA_G_INTERFACE_GHZ,
) -> np.ndarray:
    """Build exact 4x4 Tosi donor-interface flip-flop Hamiltonian (cyclic GHz, h=1).

    Basis ordering: |D,0>, |D,1>, |I,0>, |I,1>, where |0>=|down_e, Up_n>, |1>=|up_e, Down_n>.
    Positive detuning eps > 0 favors donor ground state |D> (energy -eps/2).
    """
    h = np.zeros((4, 4), dtype=np.float64)
    h[0, 0] = -0.5 * eps_ghz - 0.5 * omega_ff_ghz - 0.25 * a0_ghz
    h[1, 1] = -0.5 * eps_ghz + 0.5 * omega_ff_ghz - 0.25 * a0_ghz
    h[2, 2] = +0.5 * eps_ghz - 0.5 * (omega_ff_ghz + delta_g_ghz)
    h[3, 3] = +0.5 * eps_ghz + 0.5 * (omega_ff_ghz + delta_g_ghz)
    h[0, 1] = h[1, 0] = 0.5 * a0_ghz
    h[0, 2] = h[2, 0] = 0.5 * t_c_ghz
    h[1, 3] = h[3, 1] = 0.5 * t_c_ghz
    return h


def evaluate_flipflop_cell(
    z_nm: float,
    r_xy_nm: float,
    eps_ghz: float,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_uev: float = 1.0,
    f_r_ghz: float = 5.0,
    omega_ff_ghz: float = 5.0,
    include_valley_interference: bool = False,
    valley_phase_rad: float = 0.0,
    gamma_phi_nuc_ghz: float = GAMMA_PHI_NUC_1PCT_GHZ,
) -> CellResult | None:
    """Evaluate exact 4x4 flip-flop qubit properties at fixed DC detuning eps_ghz.

    Returns None if the donor cannot form a valid spin-like flip-flop doublet
    (depth < Z_MIN_DOUBLE_WELL_NM, charge gap below spin anticrossing, or
    excited charge admixture > 0.25).
    """
    if z_nm < Z_MIN_DOUBLE_WELL_NM:
        return None
    t_c, d_eff = tunnel_coupling_ghz(
        z_nm, r_xy_nm,
        include_valley_interference=include_valley_interference,
        valley_phase_rad=valley_phase_rad,
    )
    e_ch = math.hypot(eps_ghz, t_c)
    if e_ch < omega_ff_ghz + 0.35:
        return None

    h = build_flipflop_h4(eps_ghz, t_c, omega_ff_ghz=omega_ff_ghz)
    evals, evecs = np.linalg.eigh(h)
    omega_q = float(evals[1] - evals[0])
    v0, v1 = evecs[:, 0], evecs[:, 1]

    # Bare excited charge state |e> = sin(theta/2)|D> + cos(theta/2)|I>
    theta = math.atan2(t_c, eps_ghz)
    s2, c2 = math.sin(0.5 * theta), math.cos(0.5 * theta)
    pe0 = (s2 * v0[0] + c2 * v0[2]) ** 2 + (s2 * v0[1] + c2 * v0[3]) ** 2
    pe1 = (s2 * v1[0] + c2 * v1[2]) ** 2 + (s2 * v1[1] + c2 * v1[3]) ** 2
    p_ec = float(max(pe0, pe1))
    if p_ec > 0.25 or abs(omega_q - omega_ff_ghz) > 0.50:
        return None

    p_donor = float(0.5 * (v0[0] ** 2 + v0[1] ** 2 + v1[0] ** 2 + v1[1] ** 2))
    g_c_ghz, de_r_ghz = bare_charge_coupling_ghz(z_nm, f_r_ghz=f_r_ghz, z_r_ohm=z_r_ohm)
    dip_elem = abs(float(v1 @ (TAU_Z_4 @ v0)))
    g_eff_ghz = 0.5 * de_r_ghz * dip_elem

    # Central finite-difference 1st and 2nd Stark derivatives of qubit frequency
    deps = 1e-4
    ev_p = np.linalg.eigvalsh(build_flipflop_h4(eps_ghz + deps, t_c, omega_ff_ghz=omega_ff_ghz))
    ev_m = np.linalg.eigvalsh(build_flipflop_h4(eps_ghz - deps, t_c, omega_ff_ghz=omega_ff_ghz))
    wq_p = float(ev_p[1] - ev_p[0])
    wq_m = float(ev_m[1] - ev_m[0])
    d1 = (wq_p - wq_m) / (2.0 * deps)
    d2 = (wq_p - 2.0 * omega_q + wq_m) / (deps * deps)

    # Conservative Markovian upper bound on 1/f Gaussian charge noise dephasing + nuclear bath term
    sigma_eps_ghz = ONE_OVER_F_RMS_FACTOR * s_eps_uev * GHZ_PER_UEV
    gamma_phi_ch_ghz = math.hypot(abs(d1) * sigma_eps_ghz / math.sqrt(2.0), 0.5 * abs(d2) * sigma_eps_ghz * sigma_eps_ghz)
    gamma_phi_ghz = gamma_phi_ch_ghz + gamma_phi_nuc_ghz

    # Acoustic phonon charge relaxation dressed by exact dipole matrix element + spin-orbit floor
    gamma_1_ch_ghz = GAMMA_1_CHARGE_10GHZ_GHZ * ((omega_q / 10.0) ** 3)
    gamma_1_ghz = (dip_elem * dip_elem) * gamma_1_ch_ghz + GAMMA_1_SO_FLOOR_GHZ

    gamma_tot_ghz = 0.5 * gamma_1_ghz + gamma_phi_ghz
    kappa_ghz = f_r_ghz / q_l
    coop = 4.0 * (g_eff_ghz * g_eff_ghz) / (kappa_ghz * gamma_tot_ghz)
    m_res = g_eff_ghz / (0.5 * kappa_ghz + gamma_tot_ghz)

    return CellResult(
        z_nm=float(z_nm),
        r_xy_nm=float(r_xy_nm),
        d_eff_nm=float(d_eff),
        t_c_ghz=float(t_c),
        eps_ghz=float(eps_ghz),
        omega_q_ghz=omega_q,
        p_donor=p_donor,
        p_exc_charge=p_ec,
        g_c_mhz=float(g_c_ghz * 1e3),
        g_eff_mhz=float(g_eff_ghz * 1e3),
        d1_ghz_per_ghz=float(d1),
        d2_inv_ghz=float(d2),
        gamma_1_khz=float(gamma_1_ghz * 1e6),
        gamma_phi_khz=float(gamma_phi_ghz * 1e6),
        gamma_tot_khz=float(gamma_tot_ghz * 1e6),
        kappa_khz=float(kappa_ghz * 1e6),
        cooperativity=float(coop),
        m_res_merit=float(m_res),
        valid=True,
    )


def optimize_cell_dc_bias(
    z_nm: float,
    r_xy_nm: float,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_uev: float = 1.0,
    f_r_ghz: float = 5.0,
    objective: str = "m_res",
    include_valley_interference: bool = False,
    valley_phase_rad: float = 0.0,
    gamma_phi_nuc_ghz: float = GAMMA_PHI_NUC_1PCT_GHZ,
) -> CellResult | None:
    """Optimize local DC gate detuning eps >= 0 (donor-bound side, p_D >= 0.5) for one donor.

    Performs a coarse sweep across eps in [0, 14] GHz followed by fine local refinement
    around the peak. objective='m_res' minimizes bus gate error (g_eff / (kappa/2 + gamma_tot));
    objective='cooperativity' maximizes C = 4 g_eff^2 / (kappa * gamma_tot).
    """
    if z_nm < Z_MIN_DOUBLE_WELL_NM:
        return None
    t_c, _ = tunnel_coupling_ghz(
        z_nm, r_xy_nm,
        include_valley_interference=include_valley_interference,
        valley_phase_rad=valley_phase_rad,
    )
    eps_min = 0.0
    if t_c < f_r_ghz + 0.35:
        eps_min = math.sqrt(max(0.0, (f_r_ghz + 0.36) ** 2 - t_c * t_c))
    if eps_min > 14.0:
        return None

    key_fn = (lambda r: r.m_res_merit) if objective == "m_res" else (lambda r: r.cooperativity)
    best: CellResult | None = None
    best_score = -1.0

    # Coarse grid (step 0.25 GHz)
    n_coarse = max(12, int(round((14.0 - eps_min) / 0.25)) + 1)
    for ep in np.linspace(eps_min, 14.0, n_coarse):
        res = evaluate_flipflop_cell(
            z_nm, r_xy_nm, float(ep), z_r_ohm, q_l, s_eps_uev, f_r_ghz, f_r_ghz,
            include_valley_interference=include_valley_interference,
            valley_phase_rad=valley_phase_rad,
            gamma_phi_nuc_ghz=gamma_phi_nuc_ghz,
        )
        if res is not None:
            sc = key_fn(res)
            if sc > best_score:
                best_score = sc
                best = res

    if best is None:
        return None

    # Fine refinement around best.eps_ghz (+/- 0.30 GHz, step 0.025 GHz)
    lo = max(eps_min, best.eps_ghz - 0.30)
    hi = min(14.0, best.eps_ghz + 0.30)
    for ep in np.linspace(lo, hi, 25):
        res = evaluate_flipflop_cell(
            z_nm, r_xy_nm, float(ep), z_r_ohm, q_l, s_eps_uev, f_r_ghz, f_r_ghz,
            include_valley_interference=include_valley_interference,
            valley_phase_rad=valley_phase_rad,
            gamma_phi_nuc_ghz=gamma_phi_nuc_ghz,
        )
        if res is not None:
            sc = key_fn(res)
            if sc > best_score:
                best_score = sc
                best = res

    return best


def sample_exp124_donors(n_samples: int, delta_z_cap_nm: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Draw 3D donor coordinates (z_nm, r_xy_nm) from legacy Exp92/124 5 keV 31P+ BCA straggle + capping."""
    z_list: list[np.ndarray] = []
    count = 0
    while count < n_samples:
        batch = rng.normal(EXP124_RP_NM, EXP124_SIGMA_Z_NM, size=max(n_samples * 2, 256))
        batch = batch[batch > EXP124_Z_MIN_IMP_NM]
        z_list.append(batch)
        count += len(batch)
    z_imp = np.concatenate(z_list)[:n_samples]
    z_total = z_imp + delta_z_cap_nm
    x = rng.normal(0.0, EXP124_SIGMA_XY_NM, size=n_samples)
    y = rng.normal(0.0, EXP124_SIGMA_XY_NM, size=n_samples)
    r_xy = np.hypot(x, y)
    return z_total, r_xy


def sample_iradina_5kev_donors(n_samples: int, delta_z_cap_nm: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Draw 3D donor coordinates (z_nm, r_xy_nm) from actual iradina 1.2.3 5 keV 3D BCA + Exp124 equip (OBS-047)."""
    z_list: list[np.ndarray] = []
    count = 0
    while count < n_samples:
        batch = rng.normal(IRADINA_5KEV_RP_NM, IRADINA_5KEV_SIGMA_Z_NM, size=max(n_samples * 2, 256))
        batch = batch[batch > EXP124_Z_MIN_IMP_NM]
        z_list.append(batch)
        count += len(batch)
    z_imp = np.concatenate(z_list)[:n_samples]
    z_total = z_imp + delta_z_cap_nm
    x = rng.normal(0.0, IRADINA_5KEV_SIGMA_XY_NM, size=n_samples)
    y = rng.normal(0.0, IRADINA_5KEV_SIGMA_XY_NM, size=n_samples)
    r_xy = np.hypot(x, y)
    return z_total, r_xy


def run_iradina_valley_audit(
    delta_z_caps_nm: list[float] | None = None,
    n_donors: int = 2000,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_uev: float = ROUTE_C_S_EPS_NOM_UEV,
    f_r_ghz: float = 5.0,
    seed: int = 13199,
) -> dict[str, Any]:
    """Quantify true p_ff(C>=100) and median g_eff under iradina 5 keV + Si(001) 2-valley interference (OBS-047)."""
    if delta_z_caps_nm is None:
        delta_z_caps_nm = [4.0, 8.0]
    rng = np.random.default_rng(seed)
    z_exp92, r_exp92 = sample_exp124_donors(n_donors, 0.0, rng)
    z_ira, r_ira = sample_iradina_5kev_donors(n_donors, 0.0, rng)
    phi_step = rng.uniform(0.0, math.pi, size=n_donors)

    def _eval_mode(z_base: np.ndarray, r_base: np.ndarray, dz: float, valley: bool) -> dict[str, Any]:
        z_arr = z_base + dz
        c_arr = np.zeros(n_donors, dtype=np.float64)
        g_arr = np.zeros(n_donors, dtype=np.float64)
        shallow_frac = float(np.mean(z_arr < Z_MIN_DOUBLE_WELL_NM))
        for i in range(n_donors):
            rt = optimize_cell_dc_bias(
                float(z_arr[i]), float(r_base[i]),
                z_r_ohm=z_r_ohm, q_l=q_l, s_eps_uev=s_eps_uev, f_r_ghz=f_r_ghz,
                objective="m_res",
                include_valley_interference=valley,
                valley_phase_rad=float(phi_step[i]) if valley else 0.0,
            )
            if rt is not None:
                c_arr[i] = rt.cooperativity
                g_arr[i] = rt.g_eff_mhz
        m100 = c_arr >= 100.0
        return {
            "delta_z_cap_nm": float(dz),
            "valley_interference": bool(valley),
            "mean_z_nm": float(np.mean(z_arr)),
            "frac_below_8p5nm_double_well": shallow_frac,
            "yield_C_ge_100": float(np.mean(m100)),
            "median_g_eff_mhz_all": float(np.median(g_arr)),
            "median_g_eff_mhz_certified": float(np.median(g_arr[m100])) if np.any(m100) else 0.0,
            "median_C_all": float(np.median(c_arr)),
        }

    rows: dict[str, Any] = {}
    for dz in delta_z_caps_nm:
        kdz = f"cap_{dz:g}nm"
        rows[f"exp92_smooth_{kdz}"] = _eval_mode(z_exp92, r_exp92, dz, valley=False)
        rows[f"exp92_valley2_{kdz}"] = _eval_mode(z_exp92, r_exp92, dz, valley=True)
        rows[f"iradina5keV_smooth_{kdz}"] = _eval_mode(z_ira, r_ira, dz, valley=False)
        rows[f"iradina5keV_valley2_{kdz}"] = _eval_mode(z_ira, r_ira, dz, valley=True)

    p_ff_honest = rows["iradina5keV_valley2_cap_8nm"]["yield_C_ge_100"]
    # Downstream BB_144 (288-cell, N_cand=8) and BB_288 (576-cell, N_cand=9) impact at f*=1.5%+2MV/m
    fnr = 0.002008
    p_slot_unfilt = 0.7750 * p_ff_honest * (1.0 - fnr)
    p_slot_ddrf = 0.5400 * p_ff_honest * (1.0 - fnr)
    return {
        "n_donors": int(n_donors),
        "s_eps_uev": float(s_eps_uev),
        "q_l": float(q_l),
        "z_r_ohm": float(z_r_ohm),
        "iradina_5keV_params_nm": {
            "Rp_nm": IRADINA_5KEV_RP_NM,
            "sigma_z_nm": IRADINA_5KEV_SIGMA_Z_NM,
            "sigma_xy_nm": IRADINA_5KEV_SIGMA_XY_NM,
        },
        "regimes": rows,
        "honest_p_ff_iradina_8nm_valley2": float(p_ff_honest),
        "downstream_qldpc_impact_at_f1p5_Ez2MVm": {
            "p_slot_unfiltered_bath_x_honest_pff": float(p_slot_unfilt),
            "bb144_Ncand8_yield_pct_unfiltered_bath": round(100.0 * ((1.0 - (1.0 - p_slot_unfilt) ** 8) ** 288), 3),
            "bb288_Ncand9_yield_pct_unfiltered_bath": round(100.0 * ((1.0 - (1.0 - p_slot_unfilt) ** 9) ** 576), 3),
            "p_slot_ddrf6893_bath_x_honest_pff": float(p_slot_ddrf),
            "bb144_Ncand8_yield_pct_ddrf6893": round(100.0 * ((1.0 - (1.0 - p_slot_ddrf) ** 8) ** 288), 5),
            "bb288_Ncand9_yield_pct_ddrf6893": round(100.0 * ((1.0 - (1.0 - p_slot_ddrf) ** 9) ** 576), 5),
        },
    }


def run_capping_and_tuning_sweep(
    delta_z_caps_nm: list[float] | None = None,
    n_donors: int = 2000,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_uev: float = 1.0,
    f_r_ghz: float = 5.0,
    seed: int = 13101,
) -> dict[str, Any]:
    """Run Exp124 3D straggle yield & DC sweet-spot cooperativity sweep across Delta_z_cap."""
    if delta_z_caps_nm is None:
        delta_z_caps_nm = [0.0, 4.0, 6.0, 8.0, 10.0, 12.0]

    rng = np.random.default_rng(seed)
    # Use common random numbers (same underlying implanted donors) across capping values for low-variance comparison
    z_imp_base, r_xy_base = sample_exp124_donors(n_donors, 0.0, rng)

    sweep_results: list[dict[str, Any]] = []
    tuned_ensembles: dict[float, list[CellResult]] = {}

    for dz in delta_z_caps_nm:
        z_arr = z_imp_base + dz
        c_tuned = np.zeros(n_donors, dtype=np.float64)
        c_fixed0 = np.zeros(n_donors, dtype=np.float64)
        g_tuned = np.zeros(n_donors, dtype=np.float64)
        gphi_tuned = np.zeros(n_donors, dtype=np.float64)
        mres_tuned = np.zeros(n_donors, dtype=np.float64)
        valid_cells: list[CellResult] = []

        for i in range(n_donors):
            zi = float(z_arr[i])
            ri = float(r_xy_base[i])
            r0 = evaluate_flipflop_cell(zi, ri, 0.0, z_r_ohm, q_l, s_eps_uev, f_r_ghz, f_r_ghz)
            if r0 is not None:
                c_fixed0[i] = r0.cooperativity
            rt = optimize_cell_dc_bias(zi, ri, z_r_ohm, q_l, s_eps_uev, f_r_ghz, objective="m_res")
            if rt is not None:
                c_tuned[i] = rt.cooperativity
                g_tuned[i] = rt.g_eff_mhz
                gphi_tuned[i] = rt.gamma_phi_khz
                mres_tuned[i] = rt.m_res_merit
                if rt.cooperativity >= 100.0:
                    valid_cells.append(rt)

        tuned_ensembles[dz] = valid_cells
        mask_c100 = c_tuned >= 100.0
        mask_c10 = c_tuned >= 10.0
        mask_f0_c100 = c_fixed0 >= 100.0

        med_c_tuned = float(np.median(c_tuned))
        med_c_fixed0 = float(np.median(c_fixed0))
        # Gain over fixed eps=0: if fixed eps=0 median is 0 (more than half invalid!), report exact finite floor ratio & conditional ratio
        cond_med_f0 = float(np.median(c_fixed0[c_fixed0 > 0.0])) if np.any(c_fixed0 > 0.0) else 0.0
        cond_med_tuned = float(np.median(c_tuned[mask_c100])) if np.any(mask_c100) else 0.0
        gain_uncond = (med_c_tuned / med_c_fixed0) if med_c_fixed0 > 1e-6 else (float("inf") if med_c_tuned > 0 else 1.0)
        gain_cond = (cond_med_tuned / cond_med_f0) if cond_med_f0 > 1e-6 else 1.0

        sweep_results.append({
            "delta_z_cap_nm": float(dz),
            "n_donors": int(n_donors),
            "mean_z_nm": float(np.mean(z_arr)),
            "std_z_nm": float(np.std(z_arr)),
            "yield_C_ge_10_tuned": float(np.mean(mask_c10)),
            "yield_C_ge_100_tuned": float(np.mean(mask_c100)),
            "yield_C_ge_100_fixed_eps0": float(np.mean(mask_f0_c100)),
            "median_C_tuned": med_c_tuned,
            "p25_C_tuned": float(np.percentile(c_tuned, 25)),
            "p75_C_tuned": float(np.percentile(c_tuned, 75)),
            "median_C_fixed_eps0": med_c_fixed0,
            "conditional_median_C_fixed_eps0": cond_med_f0,
            "conditional_median_C_tuned_C100": cond_med_tuned,
            "median_C_gain_vs_eps0": float(gain_uncond) if math.isfinite(gain_uncond) else 9999.0,
            "median_C_gain_is_infinite_zero_baseline": not math.isfinite(gain_uncond),
            "conditional_C_gain_vs_eps0": float(gain_cond),
            "certified_median_g_eff_mhz": float(np.median(g_tuned[mask_c100])) if np.any(mask_c100) else 0.0,
            "certified_p10_g_eff_mhz": float(np.percentile(g_tuned[mask_c100], 10)) if np.any(mask_c100) else 0.0,
            "certified_p90_g_eff_mhz": float(np.percentile(g_tuned[mask_c100], 90)) if np.any(mask_c100) else 0.0,
            "certified_median_gamma_phi_khz": float(np.median(gphi_tuned[mask_c100])) if np.any(mask_c100) else 0.0,
            "certified_median_m_res": float(np.median(mres_tuned[mask_c100])) if np.any(mask_c100) else 0.0,
        })

    # Identify optimal capping maximizing yield_C_ge_100_tuned (tie-break by certified_median_m_res)
    opt_entry = max(sweep_results, key=lambda d: (d["yield_C_ge_100_tuned"], d["certified_median_m_res"]))

    # Also build deterministic depth profile z = 8.5..20.0 nm (r_xy = 0) for plotting
    depth_profile: list[dict[str, Any]] = []
    for zv in np.linspace(8.5, 20.0, 24):
        r0 = evaluate_flipflop_cell(float(zv), 0.0, 0.0, z_r_ohm, q_l, s_eps_uev, f_r_ghz, f_r_ghz)
        rt = optimize_cell_dc_bias(float(zv), 0.0, z_r_ohm, q_l, s_eps_uev, f_r_ghz, objective="m_res")
        depth_profile.append({
            "z_nm": float(zv),
            "t_c_ghz": float(tunnel_coupling_ghz(float(zv), 0.0)[0]),
            "C_fixed_eps0": float(r0.cooperativity) if r0 else 0.0,
            "C_tuned": float(rt.cooperativity) if rt else 0.0,
            "g_eff_mhz_tuned": float(rt.g_eff_mhz) if rt else 0.0,
            "gamma_phi_khz_tuned": float(rt.gamma_phi_khz) if rt else 0.0,
            "eps_opt_ghz": float(rt.eps_ghz) if rt else 0.0,
        })

    return {
        "operating_point": {
            "z_r_ohm": float(z_r_ohm),
            "q_l": float(q_l),
            "s_eps_uev": float(s_eps_uev),
            "f_r_ghz": float(f_r_ghz),
            "n_donors_per_cap": int(n_donors),
        },
        "sweep": sweep_results,
        "optimal_capping": opt_entry,
        "depth_profile": depth_profile,
        "ensembles": tuned_ensembles,
    }
