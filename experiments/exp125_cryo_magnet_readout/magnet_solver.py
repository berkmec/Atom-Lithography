"""Exp125 Module 1: Exact Axisymmetric Biot-Savart Multi-Coil Superconducting Magnet,
Active Bucking Coils, Coupled Nb Meissner Shield (BEM), Cryoperm Jacket & Engineering Margins.

All physics in SI units (m, T, A, J, Pa, K). Epistemic label: {Model} / {Analitik} / {Sayısal-Simülasyon}.
No laboratory measurements (no_lab_measurement=True).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.special import ellipe, ellipk

MU0 = 4.0e-7 * math.pi  # H/m


# ---------------------------------------------------------------------------
# 1. Exact Circular Current Filament Biot-Savart (ellipk / ellipe)
# ---------------------------------------------------------------------------
def filament_field_and_aphi(
    a: np.ndarray,
    z0: np.ndarray,
    I: np.ndarray,
    rho: np.ndarray,
    z: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact (Br, Bz, Aphi) from circular filaments (a, z0, I) at points (rho, z).

    Broadcast-friendly: filaments shape (F,), points shape (P,) -> returns (P,) sums
    evaluated in chunks if needed for memory efficiency.
    Uses exact complete elliptic integrals K(m), E(m) for m >= 1e-4 and exact 4-term
    analytical Taylor expansion for m < 1e-4 to avoid catastrophic cancellation near axis.
    """
    a = np.atleast_1d(np.asarray(a, dtype=np.float64))
    z0 = np.atleast_1d(np.asarray(z0, dtype=np.float64))
    I = np.atleast_1d(np.asarray(I, dtype=np.float64))
    rho_in = np.asarray(rho, dtype=np.float64)
    z_in = np.asarray(z, dtype=np.float64)
    orig_shape = np.broadcast(rho_in, z_in).shape
    rho_f = np.broadcast_to(rho_in, orig_shape).ravel()
    z_f = np.broadcast_to(z_in, orig_shape).ravel()

    n_pts = rho_f.size
    Br_tot = np.zeros(n_pts, dtype=np.float64)
    Bz_tot = np.zeros(n_pts, dtype=np.float64)
    Ap_tot = np.zeros(n_pts, dtype=np.float64)

    # Process in chunks to cap peak memory at ~32 MB
    chunk = max(1, min(n_pts, 500_000 // max(1, a.size)))
    for s in range(0, n_pts, chunk):
        e = min(n_pts, s + chunk)
        r = rho_f[s:e, None]          # (C, 1)
        dz = z_f[s:e, None] - z0[None, :]  # (C, F)
        aa = a[None, :]               # (1, F)
        ii = I[None, :]               # (1, F)

        alpha2 = (aa - r) ** 2 + dz ** 2
        beta2 = (aa + r) ** 2 + dz ** 2
        beta = np.sqrt(beta2)
        m = (4.0 * aa * r) / np.maximum(beta2, 1e-30)

        # Protect exact self-coincidence (handled separately in self-inductance)
        safe_alpha2 = np.maximum(alpha2, 1e-30)
        m_clamped = np.minimum(m, 1.0 - 1e-14)

        small = m < 1e-4
        m_eval = np.where(small, 0.0, m_clamped)
        K = ellipk(m_eval)
        E = ellipe(m_eval)

        # Exact Bz everywhere (no 1/rho singularity)
        Bz_ell = (MU0 * ii / (2.0 * math.pi * beta)) * (
            K + ((aa ** 2 - r ** 2 - dz ** 2) / safe_alpha2) * E
        )
        # Small-m exact series for Bz on/near axis
        r2_z2 = aa ** 2 + dz ** 2
        Bz_small = (MU0 * ii * aa ** 2) / (2.0 * r2_z2 ** 1.5) * (
            1.0
            + (3.0 / 4.0) * (r ** 2 / r2_z2) * (5.0 * dz ** 2 / r2_z2 - 1.0)
        )
        # Wait: Bz_ell is already nonsingular even at r=0 (K(0)=E(0)=pi/2)!
        # Verify: at r=0, (MU0*I/(2*pi*beta))*(pi/2 + (a^2-dz^2)/(a^2+dz^2)*pi/2)
        # = (MU0*I/(4*beta))*(2*a^2/(a^2+dz^2)) = MU0*I*a^2/(2*(a^2+dz^2)^1.5). Exact!
        Bz = np.where(r < 1e-12, (MU0 * ii * aa ** 2) / (2.0 * r2_z2 ** 1.5), Bz_ell)

        # Br: exact elliptic for m >= 1e-4, exact 3-term series for m < 1e-4
        r_safe = np.where(small, 1.0, r)
        Br_ell = (MU0 * ii * dz / (2.0 * math.pi * r_safe * beta)) * (
            -K + ((aa ** 2 + r ** 2 + dz ** 2) / safe_alpha2) * E
        )
        # Series: [-K + ((1 - m/2)/(1 - m)) E] = (3*pi/32)*m^2*(1 + 5/4 m + 175/128 m^2)
        # Plugging m = 4*a*r/beta^2 -> cancels r in denominator cleanly!
        Br_small = (
            (3.0 * MU0 * ii * dz * aa ** 2 * r)
            / (4.0 * beta ** 5)
            * (1.0 + 1.25 * m + (175.0 / 128.0) * m ** 2)
        )
        Br = np.where(small, Br_small, Br_ell)

        # Aphi: exact elliptic for m >= 1e-4, exact 3-term series for m < 1e-4
        k_safe = np.sqrt(np.where(small, 1.0, m_clamped))
        Ap_ell = (MU0 * ii / (math.pi * k_safe)) * np.sqrt(aa / r_safe) * (
            (1.0 - 0.5 * m_clamped) * K - E
        )
        # Series: (1 - m/2)K - E = (pi/32)*m^2*(1 + 3/4 m + 75/128 m^2)
        Ap_small = (
            (MU0 * ii * aa ** 2 * r)
            / (4.0 * beta ** 3)
            * (1.0 + 0.75 * m + (75.0 / 128.0) * m ** 2)
        )
        Ap = np.where(small, Ap_small, Ap_ell)

        Br_tot[s:e] = np.sum(Br, axis=1)
        Bz_tot[s:e] = np.sum(Bz, axis=1)
        Ap_tot[s:e] = np.sum(Ap, axis=1)

    return (
        Br_tot.reshape(orig_shape),
        Bz_tot.reshape(orig_shape),
        Ap_tot.reshape(orig_shape),
    )


def ring_mutual_inductance(a1: float, z1: float, a2: float, z2: float) -> float:
    """Exact mutual inductance M_12 = 2*pi*a2 * A_phi(from loop 1 at loop 2) / I1."""
    _, _, ap = filament_field_and_aphi(
        np.array([a1]), np.array([z1]), np.array([1.0]), np.array([a2]), np.array([z2])
    )
    return float(2.0 * math.pi * a2 * ap[0])


def ring_self_inductance_flat_strip(radius: float, strip_width: float) -> float:
    """Midpoint-collocation self-inductance of a thin flat circular ribbon of radius a and width w << a.

    Integrating mu0*a*[ln(8*a/|s|) - 2] over s in [-w/2, +w/2] divided by w gives:
      L_mid = mu0 * a * (ln(8*a / w) + ln(2) - 1) ~= mu0 * a * (ln(8*a / w) - 0.3068528).
    """
    return MU0 * radius * (math.log(8.0 * radius / strip_width) + math.log(2.0) - 1.0)


def ring_self_inductance_rect_cell(radius: float, dr: float, dz: float) -> float:
    """Self-inductance of a rectangular cross-section filament cell (dr x dz).

    GMD of a rectangle of sides (dr, dz) is r_GMD ~= 0.2235 * (dr + dz).
    L = mu0 * a * (ln(8*a / r_GMD) - 2).
    """
    r_gmd = 0.2235 * (dr + dz)
    return MU0 * radius * (math.log(8.0 * radius / r_gmd) - 2.0)


# ---------------------------------------------------------------------------
# 2. Finite Rectangular Coil Representation (2D Gauss-Legendre Quadrature)
# ---------------------------------------------------------------------------
@dataclass
class Coil:
    name: str
    r_in: float      # m
    r_out: float     # m
    z_min: float     # m (local coords, sample plane at z=0)
    z_max: float     # m
    n_turns: int
    current: float = 0.0  # A (signed: >0 main, <0 bucking)
    role: str = "main"

    @property
    def dr(self) -> float:
        return self.r_out - self.r_in

    @property
    def dz(self) -> float:
        return self.z_max - self.z_min

    @property
    def area(self) -> float:
        return self.dr * self.dz

    @property
    def r_mean(self) -> float:
        return 0.5 * (self.r_in + self.r_out)

    @property
    def z_center(self) -> float:
        return 0.5 * (self.z_min + self.z_max)

    @property
    def j_eng(self) -> float:
        """Engineering current density A/m^2."""
        return (self.n_turns * self.current) / self.area

    @property
    def conductor_length_m(self) -> float:
        return 2.0 * math.pi * self.r_mean * self.n_turns

    def quadrature_filaments(
        self, nr: int = 8, nz: int = 8, unit_current: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (a, z0, I_fil) for 2D Gauss-Legendre integration over coil cross-section."""
        xr, wr = np.polynomial.legendre.leggauss(nr)
        xz, wz = np.polynomial.legendre.leggauss(nz)
        r_nodes = 0.5 * (self.r_out - self.r_in) * xr + 0.5 * (self.r_out + self.r_in)
        z_nodes = 0.5 * (self.z_max - self.z_min) * xz + 0.5 * (self.z_max + self.z_min)
        # Weights sum to 1 over the cross-section
        w_r = 0.5 * wr
        w_z = 0.5 * wz
        RR, ZZ = np.meshgrid(r_nodes, z_nodes, indexing="ij")
        WW = np.outer(w_r, w_z)
        ni = float(self.n_turns) if unit_current else float(self.n_turns * self.current)
        return RR.ravel(), ZZ.ravel(), (WW.ravel() * ni)


def coil_field_unit(
    coil: Coil, rho: np.ndarray, z: np.ndarray, nr: int = 8, nz: int = 8
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(Br, Bz, Aphi) per 1 A of coil current."""
    a, z0, ifil = coil.quadrature_filaments(nr=nr, nz=nz, unit_current=True)
    return filament_field_and_aphi(a, z0, ifil, rho, z)


def coils_inductance_matrix(coils: Sequence[Coil], nr: int = 8, nz: int = 8) -> np.ndarray:
    """Exact mutual & self inductance matrix L_ij (H) for multi-coil array.

    Uses uniform sub-cell midpoint filaments with exact rectangular-cell GMD self-inductance
    on the diagonal to handle the logarithmic singularity cleanly without quadrature artifacts.
    """
    nc = len(coils)
    L = np.zeros((nc, nc), dtype=np.float64)
    fils = []
    for c in coils:
        dr_cell = c.dr / nr
        dz_cell = c.dz / nz
        r_mid = c.r_in + (np.arange(nr) + 0.5) * dr_cell
        z_mid = c.z_min + (np.arange(nz) + 0.5) * dz_cell
        RR, ZZ = np.meshgrid(r_mid, z_mid, indexing="ij")
        n_sub = nr * nz
        w_turn = float(c.n_turns) / n_sub
        fils.append((RR.ravel(), ZZ.ravel(), w_turn, dr_cell, dz_cell))

    for i in range(nc):
        ri, zi, wi, dri, dzi = fils[i]
        for j in range(i, nc):
            rj, zj, wj, _drj, _dzj = fils[j]
            if i == j:
                # Self-inductance: sum exact mutual between distinct sub-cells + exact cell self
                M_sum = 0.0
                n_sub = ri.size
                # Vectorized pairwise flux
                for k in range(n_sub):
                    mask = np.arange(n_sub) != k
                    _, _, ap = filament_field_and_aphi(
                        ri[mask], zi[mask], np.full(n_sub - 1, wi),
                        np.array([ri[k]]), np.array([zi[k]])
                    )
                    M_sum += wi * 2.0 * math.pi * ri[k] * ap[0]
                    M_sum += (wi ** 2) * ring_self_inductance_rect_cell(ri[k], dri, dzi)
                L[i, i] = M_sum
            else:
                _, _, ap = filament_field_and_aphi(
                    ri, zi, np.full(ri.size, wi), rj, zj
                )
                Mij = float(np.sum(wj * 2.0 * math.pi * rj * ap))
                L[i, j] = Mij
                L[j, i] = Mij
    return L


# ---------------------------------------------------------------------------
# 3. Axisymmetric Superconducting Meissner Shield BEM (Phi_total = 0, ZFC)
# ---------------------------------------------------------------------------
@dataclass
class NbShieldGeometry:
    """Open-port axisymmetric Nb superconducting Meissner cup with coax feedthrough chimney."""
    r_inner: float       # m, inner radius of cup
    z_bot: float         # m, bottom endcap plane
    z_top: float         # m, top cap plane
    r_port: float        # m, central coax feedthrough port radius
    h_chimney: float     # m, superconducting chimney height above z_top
    wall_thickness: float = 0.0025  # m (2.5 mm solid RRR>300 Nb)
    fillet_r: float = 0.004         # m (4 mm machined corner fillet)


def discretize_nb_cup(
    geom: NbShieldGeometry, n_wall: int = 36, n_cap: int = 24, n_chimney: int = 20, n_fillet: int = 8
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Discretize axisymmetric Nb cup contour into (rho, z, ds, nr_out, nz_out).

    Contour follows mid-wall surface with rounded corners (fillet_r) so surface current
    K_phi has no unphysical 90-deg mathematical singularity.
    """
    R = geom.r_inner + 0.5 * geom.wall_thickness
    zb = geom.z_bot - 0.5 * geom.wall_thickness
    zt = geom.z_top + 0.5 * geom.wall_thickness
    rp = geom.r_port + 0.5 * geom.wall_thickness
    rf = min(geom.fillet_r, 0.25 * (zt - zb), 0.25 * (R - rp))

    pts_r: List[float] = []
    pts_z: List[float] = []
    pts_ds: List[float] = []
    pts_nr: List[float] = []
    pts_nz: List[float] = []

    def add_segment(r0: float, z0: float, r1: float, z1: float, n: int, nr_o: float, nz_o: float):
        length = math.hypot(r1 - r0, z1 - z0)
        if length < 1e-9 or n < 1:
            return
        t = (np.arange(n) + 0.5) / n
        ds = length / n
        for ti in t:
            pts_r.append(r0 + ti * (r1 - r0))
            pts_z.append(z0 + ti * (z1 - z0))
            pts_ds.append(ds)
            pts_nr.append(nr_o)
            pts_nz.append(nz_o)

    def add_arc(rc: float, zc: float, rad: float, th0: float, th1: float, n: int, outward_sign: float):
        dth = (th1 - th0) / n
        ds = abs(dth) * rad
        for k in range(n):
            th = th0 + (k + 0.5) * dth
            pts_r.append(rc + rad * math.cos(th))
            pts_z.append(zc + rad * math.sin(th))
            pts_ds.append(ds)
            pts_nr.append(outward_sign * math.cos(th))
            pts_nz.append(outward_sign * math.sin(th))

    # 1. Bottom closed disk: rho from 0 to R - rf at z = zb (outward normal: -z)
    add_segment(0.0, zb, R - rf, zb, n_cap, 0.0, -1.0)
    # 2. Bottom-outer fillet: center (R-rf, zb+rf), th from -pi/2 to 0
    add_arc(R - rf, zb + rf, rf, -0.5 * math.pi, 0.0, n_fillet, +1.0)
    # 3. Outer cylindrical wall: z from zb+rf to zt-rf at rho = R (outward normal: +r)
    add_segment(R, zb + rf, R, zt - rf, n_wall, +1.0, 0.0)
    # 4. Top-outer fillet: center (R-rf, zt-rf), th from 0 to +pi/2
    add_arc(R - rf, zt - rf, rf, 0.0, 0.5 * math.pi, n_fillet, +1.0)
    # 5. Top annular cap: rho from R-rf to rp+rf at z = zt (outward normal: +z)
    add_segment(R - rf, zt, rp + rf, zt, max(8, n_cap - 4), 0.0, +1.0)
    # 6. Top-port inner fillet: center (rp+rf, zt+rf), th from -pi/2 to -pi (outward normal points away from interior -> toward -r,+z)
    add_arc(rp + rf, zt + rf, rf, -0.5 * math.pi, -math.pi, max(4, n_fillet // 2), -1.0)
    # 7. Superconducting coax feedthrough chimney: z from zt+rf to zt+h_chimney at rho = rp (outward normal: +r)
    if geom.h_chimney > rf:
        add_segment(rp, zt + rf, rp, zt + geom.h_chimney, n_chimney, +1.0, 0.0)

    return (
        np.asarray(pts_r, dtype=np.float64),
        np.asarray(pts_z, dtype=np.float64),
        np.asarray(pts_ds, dtype=np.float64),
        np.asarray(pts_nr, dtype=np.float64),
        np.asarray(pts_nz, dtype=np.float64),
    )


def build_shield_inductance_matrix(
    rho_s: np.ndarray, z_s: np.ndarray, ds_s: np.ndarray
) -> np.ndarray:
    """Exact axisymmetric BEM mutual/self inductance matrix M_ij for Meissner surface rings."""
    m = rho_s.size
    M = np.zeros((m, m), dtype=np.float64)
    for j in range(m):
        _, _, ap = filament_field_and_aphi(
            np.array([rho_s[j]]), np.array([z_s[j]]), np.array([1.0]), rho_s, z_s
        )
        M[:, j] = 2.0 * math.pi * rho_s * ap
        M[j, j] = ring_self_inductance_flat_strip(float(rho_s[j]), float(ds_s[j]))
    # Enforce exact symmetry (round-off < 1e-15)
    return 0.5 * (M + M.T)


def validate_superconducting_sphere_bem(
    radius: float = 0.04, B0: float = 0.10, n_rings: int = 160
) -> Dict[str, float]:
    """Analytical benchmark: zero-field-cooled superconducting sphere in uniform axial B0.

    Exact analytical solution:
      - Surface screening current K_phi(theta) = -(3 * B0 / (2 * mu0)) * sin(theta)
      - Internal field B_in = 0 everywhere for r < R
      - Exterior equatorial field B_z(R+, 0) = 1.5 * B0
    """
    th = (np.arange(n_rings) + 0.5) * math.pi / n_rings
    dth = math.pi / n_rings
    rho_s = radius * np.sin(th)
    z_s = radius * np.cos(th)
    ds_s = np.full(n_rings, radius * dth)

    M = build_shield_inductance_matrix(rho_s, z_s, ds_s)
    phi_ext = math.pi * (rho_s ** 2) * B0
    I_sh = -np.linalg.solve(M, phi_ext)
    K_num = I_sh / ds_s
    K_exact = -(1.5 * B0 / MU0) * np.sin(th)

    # Interior test points (r <= 0.7*R)
    r_in = np.linspace(0.0, 0.65 * radius, 8)
    z_in = np.linspace(-0.65 * radius, 0.65 * radius, 9)
    RR, ZZ = np.meshgrid(r_in, z_in, indexing="ij")
    mask = (RR ** 2 + ZZ ** 2) <= (0.70 * radius) ** 2
    Br_sh, Bz_sh, _ = filament_field_and_aphi(rho_s, z_s, I_sh, RR[mask], ZZ[mask])
    B_in_tot = np.hypot(Br_sh, B0 + Bz_sh)

    # Exterior equatorial test point at r = 1.05*R, z = 0:
    # Exact dipole + uniform field: Bz(r, 0) = B0 * (1 + 0.5 * (R/r)^3)
    r_ext = 1.05 * radius
    _, Bz_ext_sh, _ = filament_field_and_aphi(
        rho_s, z_s, I_sh, np.array([r_ext]), np.array([0.0])
    )
    Bz_ext_num = B0 + float(Bz_ext_sh[0])
    Bz_ext_exact = B0 * (1.0 + 0.5 * (radius / r_ext) ** 3)

    k_rel_err = float(np.max(np.abs(K_num - K_exact)) / np.max(np.abs(K_exact)))
    interior_leak = float(np.max(B_in_tot) / B0)
    ext_rel_err = abs(Bz_ext_num - Bz_ext_exact) / Bz_ext_exact
    return {
        "n_rings": n_rings,
        "K_phi_max_rel_err": k_rel_err,
        "interior_max_B_over_B0": interior_leak,
        "exterior_r1p05_rel_err": ext_rel_err,
        "K_equator_num_A_per_m": float(abs(K_num[n_rings // 2])),
        "K_equator_exact_A_per_m": float(1.5 * B0 / MU0),
    }


# ---------------------------------------------------------------------------
# 4. NbTi Critical Current Surface (Bottura 2000), Quench & Cryoperm-10
# ---------------------------------------------------------------------------
def nbti_jc_sc_A_per_m2(B_tesla: float, T_kelvin: float = 4.2) -> float:
    """Bottura (2000) LHC-grade NbTi superconductor J_c(B, T) [A/m^2].

    Normalized to standard commercial NbTi strand J_c(5 T, 4.2 K) = 2800 A/mm^2 = 2.8e9 A/m^2.
    Anchor: L. Bottura, IEEE Trans. Appl. Supercond. 10, 1054 (2000).
    """
    Tc0 = 9.2
    Bc20 = 14.5
    alpha, beta, gamma = 0.63, 1.0, 2.32
    if T_kelvin >= Tc0:
        return 0.0
    t = T_kelvin / Tc0
    bc2_t = Bc20 * (1.0 - t ** 1.7)
    B_eff = max(float(B_tesla), 0.15)  # floor avoids unphysical 1/B divergence at B->0
    if B_eff >= bc2_t:
        return 0.0
    # Normalization constant from Jc(5 T, 4.2 K) = 2.8e9 A/m^2
    t_ref = 4.2 / Tc0
    bc2_ref = Bc20 * (1.0 - t_ref ** 1.7)
    b_ref = 5.0 / bc2_ref
    shape_ref = (b_ref ** alpha) * ((1.0 - b_ref) ** beta) * ((1.0 - t_ref ** 1.7) ** gamma) / 5.0
    C0 = 2.8e9 / shape_ref

    b = B_eff / bc2_t
    return float((C0 / B_eff) * (b ** alpha) * ((1.0 - b) ** beta) * ((1.0 - t ** 1.7) ** gamma))


def nbti_jc_eng_A_per_m2(
    B_tesla: float, T_kelvin: float = 4.2, cu_sc_ratio: float = 2.0, packing: float = 0.70
) -> float:
    """Engineering critical current density J_c,eng [A/m^2] over winding cross-section."""
    return (packing / (1.0 + cu_sc_ratio)) * nbti_jc_sc_A_per_m2(B_tesla, T_kelvin)


def nbti_temp_margin_K(
    j_eng_op: float, B_peak: float, T_op: float = 4.2, cu_sc_ratio: float = 2.0, packing: float = 0.70
) -> float:
    """Compute current-sharing temperature T_cs and temperature margin (T_cs - T_op) [K]."""
    lo, hi = T_op, 9.19
    if nbti_jc_eng_A_per_m2(B_peak, T_op, cu_sc_ratio, packing) <= abs(j_eng_op):
        return 0.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if nbti_jc_eng_A_per_m2(B_peak, mid, cu_sc_ratio, packing) > abs(j_eng_op):
            lo = mid
        else:
            hi = mid
    return lo - T_op


def nb_bc1_tesla(T_kelvin: float) -> float:
    """Pure Nb lower critical field B_c1(T) = B_c1(0) * (1 - (T/Tc)^2).

    Anchor: B_c1(0) ~= 170 mT, Tc = 9.25 K (Nb RRR>300). At 4.2 K -> 135.0 mT; at 20 mK -> 170.0 mT.
    """
    Tc = 9.25
    if T_kelvin >= Tc:
        return 0.0
    return 0.170 * (1.0 - (T_kelvin / Tc) ** 2)


def cryoperm_cylindrical_sf(
    mu_r: float = 20000.0, thickness_m: float = 0.002, radius_m: float = 0.042, length_m: float = 0.056
) -> Dict[str, float]:
    """Analytical transverse & axial shielding factors for finite Cryoperm-10 cylinder (Mager 1970).

    Used as conservative outer pre-shield outside the Nb Meissner cup; saturation B_sat = 0.75 T.
    """
    sf_trans = 1.0 + 0.5 * mu_r * (thickness_m / radius_m)
    # Axial shielding factor for open-ended / capped cylinder (demagnetizing factor N_z)
    p = length_m / (2.0 * radius_m)
    # Approximate oblate/prolate demagnetizing factor for finite cylinder
    Nz = 1.0 / (1.0 + 1.6 * p) if p > 0 else 1.0
    sf_axial_open = 1.0 + 4.0 * Nz * (sf_trans - 1.0) / (1.0 + 2.0 * p)
    return {
        "mu_r_4K": mu_r,
        "B_sat_T": 0.75,
        "SF_transverse_analytical": float(sf_trans),
        "SF_axial_open_est": float(sf_axial_open),
    }


def quench_hotspot_temperature_K(
    J_cu_A_per_m2: float, L_eff_H: float, I_op_A: float, V_max_V: float = 400.0, t_detect_s: float = 0.030
) -> Dict[str, float]:
    """Adiabatic quench hot-spot estimate via Cu (RRR=100) MIITs curve (Wilson, Superconducting Magnets).

    During quench: constant current for t_detect, then exponential decay tau = L_eff / R_dump
    where R_dump = V_max / I_op. Integral Z = int J_cu^2 dt = J_cu^2 * (t_detect + tau / 2).
    """
    R_dump = V_max_V / max(abs(I_op_A), 1e-6)
    tau_decay = L_eff_H / R_dump
    miits_val = (J_cu_A_per_m2 ** 2) * (t_detect_s + 0.5 * tau_decay)  # A^2 s / m^4
    # Tabulated copper (RRR=100) Gamma(T) = int_{4.2}^T (C_v(T') / rho_Cu(T')) dT' in [1e16 A^2 s / m^4]
    # Standard NIST/Wilson cryogenic Cu RRR=100 integral values:
    T_tab = np.array([4.2, 20.0, 40.0, 60.0, 80.0, 100.0, 150.0, 200.0, 300.0])
    G_tab = np.array([0.0, 0.35, 1.85, 3.80, 5.45, 6.75, 9.10, 10.80, 13.40]) * 1e16
    T_hot = float(np.interp(miits_val, G_tab, T_tab))
    return {
        "R_dump_ohm": float(R_dump),
        "tau_decay_s": float(tau_decay),
        "V_max_V": float(V_max_V),
        "t_detect_s": float(t_detect_s),
        "MIITs_1e16_A2s_m4": float(miits_val / 1e16),
        "T_hotspot_K": T_hot,
    }


# ---------------------------------------------------------------------------
# 5. Baseline Multi-Coil Cryo-Magnet + Shield Architecture & Coupled Optimizer
# ---------------------------------------------------------------------------
def default_magnet_and_shield_geometry() -> Tuple[List[Coil], NbShieldGeometry]:
    """CAD v3.0-locked 8-coil actively-shielded NbTi split-pair + shim + bucking magnet & Nb Meissner cup.

    Coordinate convention (synced to CAD v3.0 research/atom_lithography_machine/cad/params.py):
      z_loc = 0 mm -> sample wafer plane (Z_WAFER = 500.0 mm in CAD v3.0)
      Midplane split gap: z_loc in [-18, +18] mm -> z_machine in [482, 518] mm (36 mm radial optical/wafer access)
      Clear inner bore radius: R_bore = 75 mm (phi 150 mm, clears 50 mm wafer / 80 mm carrier + thermal shield)
      Outer active-shielding coils: R_out = 168 mm (cryomagnet former OD 352 mm, R_out = 176 mm inside s=0.5 UHV chamber R_in = 182.0 mm -> 6.0 mm radial vacuum clearance)
      NbTiN resonator carrier center: z_res = -155 mm (z_machine = 345.0 mm, inside UHV chamber z=[285, 620] mm)
      Upper ion-column stray-field audit plane: z_loc = +268 mm (z_machine = 768.0 mm), protected by active outer shield!
    """
    coils = [
        # Main split pair (positive current)
        Coil("M_upper", r_in=0.078, r_out=0.112, z_min=+0.018, z_max=+0.072, n_turns=1600, role="main"),
        Coil("M_lower", r_in=0.078, r_out=0.112, z_min=-0.072, z_max=-0.018, n_turns=1600, role="main"),
        # Axial homogeneity compensation notches (cancel Z1..Z4 at sample z=0)
        Coil("S_upper", r_in=0.078, r_out=0.116, z_min=+0.076, z_max=+0.112, n_turns=1100, role="shim"),
        Coil("S_lower", r_in=0.078, r_out=0.116, z_min=-0.112, z_max=-0.076, n_turns=1100, role="shim"),
        # Outer active-shielding split pair (counter-wound dipole cancellation -> cuts stray field at column & resonators)
        Coil("A_upper", r_in=0.144, r_out=0.168, z_min=+0.020, z_max=+0.104, n_turns=960, role="active_shield"),
        Coil("A_lower", r_in=0.144, r_out=0.168, z_min=-0.104, z_max=-0.020, n_turns=960, role="active_shield"),
        # Local active bucking pair bracketing the Nb Meissner cup + coax chimney (z_res = -155 mm)
        Coil("B_upper", r_in=0.056, r_out=0.082, z_min=-0.145, z_max=-0.121, n_turns=400, role="bucking"),
        Coil("B_lower", r_in=0.056, r_out=0.082, z_min=-0.184, z_max=-0.160, n_turns=400, role="bucking"),
    ]
    shield = NbShieldGeometry(
        r_inner=0.032,         # 32 mm inner radius (clears r<=25 mm resonator carrier + 7 mm radial clearance)
        z_bot=-0.174,          # z_machine = 326.0 mm (41.0 mm above UHV chamber floor z=285.0 mm)
        z_top=-0.136,          # 38 mm internal height centered on z_res = -155 mm (z_machine = 345.0 mm)
        r_port=0.008,          # 8 mm coax feedthrough port (phi 16 mm for 56-82 micro-coaxes)
        h_chimney=0.011,       # 11 mm Nb evanescent chimney -> z_loc = -125 mm (z_machine = 375.0 mm)
        wall_thickness=0.0025, # 2.5 mm solid RRR>300 Nb wall
        fillet_r=0.004,        # 4 mm rounded corners
    )
    return coils, shield


def solve_coupled_magnet_system(
    coils: Sequence[Coil],
    shield: NbShieldGeometry,
    target_B_sample: float = 1.50,
    z_res: float = -0.155,
    r_res_max: float = 0.025,
    nr_quad: int = 8,
    nz_quad: int = 8,
    bem_scale: int = 1,
) -> Dict:
    """Solve coupled multi-coil currents + Nb Meissner shield BEM simultaneously.

    Because the ZFC Meissner shield currents I_sh = -M_sh^{-1} Phi_coils(I_c) are strictly
    linear in coil currents I_c, we assemble the exact coupled response matrices:
      B_total(pt) = (A_coil + A_sh @ (-M_sh^{-1} Phi_sh_unit)) @ I_c
    and solve a weighted constrained least-squares problem:
      - Exact constraint: Bz(0, 0) = target_B_sample (1.5000 T)
      - Minimize: sample homogeneity residual on r<=2.3 mm, |z|<=0.5 mm (heavy weight)
                + unshielded |B| on the Nb shield exterior contour (keeps B_surf << B_c1!)
                + unshielded |B| in resonator zone (strong active bucking even without shield)
                + gentle Tikhonov power regularization (keeps I_op/I_c low & stress minimal).
    """
    nc = len(coils)

    # 1. Discretize Nb Meissner shield & build exact BEM matrix
    rho_s, z_s, ds_s, nr_s, nz_s = discretize_nb_cup(
        shield,
        n_wall=32 * bem_scale,
        n_cap=20 * bem_scale,
        n_chimney=18 * bem_scale,
        n_fillet=6 * bem_scale,
    )
    M_sh = build_shield_inductance_matrix(rho_s, z_s, ds_s)
    M_sh_inv = np.linalg.inv(M_sh)

    # Flux on shield rings per 1 A of each coil -> shield current response matrix S_sh (M x nc)
    Phi_unit = np.zeros((rho_s.size, nc), dtype=np.float64)
    Br_sh_ext_unit = np.zeros((rho_s.size, nc), dtype=np.float64)
    Bz_sh_ext_unit = np.zeros((rho_s.size, nc), dtype=np.float64)
    for c_idx, c in enumerate(coils):
        br_u, bz_u, ap_u = coil_field_unit(c, rho_s, z_s, nr=nr_quad, nz=nz_quad)
        Phi_unit[:, c_idx] = 2.0 * math.pi * rho_s * ap_u
        Br_sh_ext_unit[:, c_idx] = br_u
        Bz_sh_ext_unit[:, c_idx] = bz_u

    # Shield screening current per 1 A of each coil: I_sh = S_sh @ I_coil
    S_sh = -M_sh_inv @ Phi_unit  # (M, nc)

    def coupled_field_matrices(pts_r: np.ndarray, pts_z: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return (Br_uncoupled, Bz_uncoupled, Br_coupled, Bz_coupled) matrices of shape (P, nc)."""
        n_p = pts_r.size
        Br_u = np.zeros((n_p, nc), dtype=np.float64)
        Bz_u = np.zeros((n_p, nc), dtype=np.float64)
        for c_idx, c in enumerate(coils):
            br_c, bz_c, _ = coil_field_unit(c, pts_r, pts_z, nr=nr_quad, nz=nz_quad)
            Br_u[:, c_idx] = br_c
            Bz_u[:, c_idx] = bz_c
        # Reaction field of shield rings at target points
        Br_sh_mat = np.zeros((n_p, rho_s.size), dtype=np.float64)
        Bz_sh_mat = np.zeros((n_p, rho_s.size), dtype=np.float64)
        for j in range(rho_s.size):
            br_j, bz_j, _ = filament_field_and_aphi(
                np.array([rho_s[j]]), np.array([z_s[j]]), np.array([1.0]), pts_r, pts_z
            )
            Br_sh_mat[:, j] = br_j
            Bz_sh_mat[:, j] = bz_j
        Br_c = Br_u + Br_sh_mat @ S_sh
        Bz_c = Bz_u + Bz_sh_mat @ S_sh
        return Br_u, Bz_u, Br_c, Bz_c

    # 2. Control points:
    # (a) Sample active zone: r in [0, 2.3 mm], z in [-0.5, +0.5 mm] (dense 7x7 grid)
    sr, sz = np.meshgrid(np.linspace(0.0, 0.0023, 7), np.linspace(-0.0005, 0.0005, 7), indexing="ij")
    sr, sz = sr.ravel(), sz.ravel()
    Br_s_u, Bz_s_u, Br_s_c, Bz_s_c = coupled_field_matrices(sr, sz)

    # Exact center point (0, 0)
    _, _, _, Bz_0_c = coupled_field_matrices(np.array([0.0]), np.array([0.0]))
    row_center = Bz_0_c[0]  # (nc,)

    # (b) Resonator carrier zone: r in [0, 25 mm], z in [z_res-3 mm, z_res+3 mm]
    rr, rz = np.meshgrid(np.linspace(0.0, r_res_max, 8), np.linspace(z_res - 0.003, z_res + 0.003, 5), indexing="ij")
    rr, rz = rr.ravel(), rz.ravel()
    Br_r_u, Bz_r_u, Br_r_c, Bz_r_c = coupled_field_matrices(rr, rz)

    # 3. Constrained KKT Linear Least-Squares Optimization:
    # min_I  w_hom * ||(Bz_s_c - B0)||^2 + w_hom_r * ||Br_s_c||^2
    #      + w_sh_surf * (||Br_sh_ext||^2 + ||Bz_sh_ext||^2)  [drives ambient field on Nb cup << B_c1!]
    #      + w_sh_K * ||mu0 * K_phi||^2                       [directly minimizes screened B_surf = mu0*|K|!]
    #      + w_res_u * (||Br_r_u||^2 + ||Bz_r_u||^2)          [active bucking quietness even without shield!]
    #      + w_reg * ||J_eng||^2                              [low current / low stress / low energy]
    # subject to: row_center @ I = target_B_sample
    n_s = sr.size
    n_sh = rho_s.size
    n_r = rr.size

    K_unit = (MU0 / ds_s[:, None]) * S_sh  # outer tangential field [T] on Nb cup per 1 A

    # Normalized current density scale (J_eng / 150 A/mm^2) + lens stray field suppression
    j_scale = np.array([c.n_turns / (c.area * 1.5e8) for c in coils], dtype=np.float64)
    # Stray field control points at lens plate (z=+268 mm) and outer radial fringe (r=220 mm)
    fringe_r = np.array([0.0, 0.005, 0.22, 0.22, 0.22])
    fringe_z = np.array([0.268, 0.268, -0.10, 0.0, +0.10])
    _, _, Br_fr_c, Bz_fr_c = coupled_field_matrices(fringe_r, fringe_z)
    n_fr = fringe_r.size

    A_blocks = [
        math.sqrt(2.5e9 / n_s) * Bz_s_c,
        math.sqrt(2.5e7 / n_s) * Br_s_c,
        math.sqrt(6.0e2 / n_sh) * Br_sh_ext_unit,
        math.sqrt(6.0e2 / n_sh) * Bz_sh_ext_unit,
        math.sqrt(3.0e3 / n_sh) * K_unit,
        math.sqrt(4.0e2 / n_r) * Br_r_u,
        math.sqrt(4.0e2 / n_r) * Bz_r_u,
        math.sqrt(2.5e2 / n_fr) * Br_fr_c,
        math.sqrt(2.5e2 / n_fr) * Bz_fr_c,
        math.sqrt(6.5e-1) * np.diag(j_scale),
    ]
    b_blocks = [
        math.sqrt(2.5e9 / n_s) * np.full(n_s, target_B_sample),
        np.zeros(n_s),
        np.zeros(n_sh),
        np.zeros(n_sh),
        np.zeros(n_sh),
        np.zeros(n_r),
        np.zeros(n_r),
        np.zeros(n_fr),
        np.zeros(n_fr),
        np.zeros(nc),
    ]
    A_ls = np.vstack(A_blocks)
    b_ls = np.concatenate(b_blocks)

    H = A_ls.T @ A_ls
    g = A_ls.T @ b_ls
    # KKT system: [H, c; c^T, 0] [I; lam] = [g; target_B_sample]
    KKT = np.zeros((nc + 1, nc + 1), dtype=np.float64)
    KKT[:nc, :nc] = H
    KKT[:nc, nc] = row_center
    KKT[nc, :nc] = row_center
    rhs = np.concatenate([g, [target_B_sample]])
    sol = np.linalg.solve(KKT, rhs)
    I_opt = sol[:nc]

    # Store currents into copy of coils
    opt_coils = [
        Coil(c.name, c.r_in, c.r_out, c.z_min, c.z_max, c.n_turns, float(I_opt[i]), c.role)
        for i, c in enumerate(coils)
    ]
    I_sh = S_sh @ I_opt
    K_phi = I_sh / ds_s
    B_surf_screened = MU0 * np.abs(K_phi)  # exact tangential field on outer Nb Meissner surface

    # 4. Evaluate fields at sample zone, resonator zone, shield exterior, and lens plate
    Bz_s_val = Bz_s_c @ I_opt
    Br_s_val = Br_s_c @ I_opt
    B_s_mag = np.hypot(Br_s_val, Bz_s_val)
    hom_rel_Bz = float(np.max(np.abs(Bz_s_val - target_B_sample)) / target_B_sample)
    hom_rel_Bmag = float(np.max(np.abs(B_s_mag - target_B_sample)) / target_B_sample)

    # Shield reaction contribution at sample center
    Bz_s_unshielded_0 = float((Bz_s_u[sr == 0.0][sz[sr == 0.0] == 0.0] @ I_opt)[0])
    shield_reaction_at_sample_mT = (target_B_sample - Bz_s_unshielded_0) * 1e3

    # Resonator carrier zone (unshielded vs Nb-shielded)
    Br_r_u_val = Br_r_u @ I_opt
    Bz_r_u_val = Bz_r_u @ I_opt
    B_r_u_mag = np.hypot(Br_r_u_val, Bz_r_u_val)

    Br_r_c_val = Br_r_c @ I_opt
    Bz_r_c_val = Bz_r_c @ I_opt
    B_r_c_mag = np.hypot(Br_r_c_val, Bz_r_c_val)

    # Unshielded field on Nb shield exterior
    Br_sh_u = Br_sh_ext_unit @ I_opt
    Bz_sh_u = Bz_sh_ext_unit @ I_opt
    B_sh_unshielded = np.hypot(Br_sh_u, Bz_sh_u)

    # Stray field at upper ion-column plane (z_loc = +268 mm -> z_machine = 768.0 mm in CAD v3.0, r <= 5 mm)
    lens_r = np.linspace(0.0, 0.005, 6)
    lens_z = np.full_like(lens_r, +0.268)
    _, _, Br_lens_c, Bz_lens_c = coupled_field_matrices(lens_r, lens_z)
    B_lens_max_mT = float(np.max(np.hypot(Br_lens_c @ I_opt, Bz_lens_c @ I_opt)) * 1e3)

    # 5. Inductance matrix, stored energy, peak winding field, NbTi margin, Lorentz stress & forces
    L_mat = coils_inductance_matrix(opt_coils, nr=nr_quad, nz=nz_quad)
    E_mag_coils = 0.5 * float(I_opt @ L_mat @ I_opt)
    # Include shield magnetic interaction energy: E_tot = 0.5 I_c^T L I_c + I_c^T M_{cs} I_sh + 0.5 I_sh^T M_sh I_sh
    # Since M_sh I_sh = -Phi_coils = -M_{cs}^T I_c, E_shield_delta = 0.5 * I_sh^T Phi_coils = -0.5 * I_sh^T M_sh I_sh
    E_shield_interaction = 0.5 * float(I_sh @ (Phi_unit @ I_opt))  # negative (diamagnetic energy reduction + work)
    E_mag_coupled = E_mag_coils + E_shield_interaction

    # Evaluate per-coil peak B, J_c(B_peak, 4.2K), hoop stress, axial force
    # Use a 6x6 internal grid per coil cross-section
    coil_metrics = []
    # Collect all filaments (coils + shield) for accurate internal winding field evaluation
    all_a_list, all_z_list, all_I_list = [rho_s], [z_s], [I_sh]
    for c in opt_coils:
        a_c, z_c, i_c = c.quadrature_filaments(nr=nr_quad, nz=nz_quad)
        all_a_list.append(a_c)
        all_z_list.append(z_c)
        all_I_list.append(i_c)
    all_a = np.concatenate(all_a_list)
    all_z = np.concatenate(all_z_list)
    all_I = np.concatenate(all_I_list)

    for c in opt_coils:
        # Staggered internal evaluation grid (10x10 midpoints, avoids exact coincidence with Gauss nodes)
        r_ev = c.r_in + (np.arange(10) + 0.5) * (c.dr / 10.0)
        z_ev = c.z_min + (np.arange(10) + 0.5) * (c.dz / 10.0)
        RR, ZZ = np.meshgrid(r_ev, z_ev, indexing="ij")
        Br_w, Bz_w, _ = filament_field_and_aphi(all_a, all_z, all_I, RR, ZZ)
        B_w_mag = np.hypot(Br_w, Bz_w)
        B_peak = float(np.max(B_w_mag))

        # Lorentz hoop stress sigma_hoop = r * J_phi * B_z (Pa)
        sigma_grid = RR * c.j_eng * Bz_w
        sigma_max_MPa = float(np.max(np.abs(sigma_grid)) / 1e6)
        sigma_signed_max_MPa = float(sigma_grid.ravel()[np.argmax(np.abs(sigma_grid))] / 1e6)
        sigma_mean_MPa = float(np.mean(sigma_grid) / 1e6)

        # Net axial Lorentz force F_z = integral 2*pi*r * (-J_phi * B_r) dr dz
        fz_density = -c.j_eng * Br_w  # N/m^3
        F_z_N = float(np.mean(2.0 * math.pi * RR * fz_density) * c.area)

        # NbTi critical current margin at 4.2 K (Cu:SC = 2:1, packing = 0.70)
        jc_eng = nbti_jc_eng_A_per_m2(B_peak, T_kelvin=4.2, cu_sc_ratio=2.0, packing=0.70)
        i_over_ic = abs(c.j_eng) / max(jc_eng, 1.0)
        t_margin = nbti_temp_margin_K(c.j_eng, B_peak, T_op=4.2, cu_sc_ratio=2.0, packing=0.70)

        coil_metrics.append({
            "name": c.name,
            "role": c.role,
            "r_in_mm": round(c.r_in * 1e3, 2),
            "r_out_mm": round(c.r_out * 1e3, 2),
            "z_min_loc_mm": round(c.z_min * 1e3, 2),
            "z_max_loc_mm": round(c.z_max * 1e3, 2),
            "z_min_machine_mm": round((c.z_min + 0.500) * 1e3, 2),
            "z_max_machine_mm": round((c.z_max + 0.500) * 1e3, 2),
            "n_turns": c.n_turns,
            "current_A": float(c.current),
            "ampere_turns_kAT": float(c.n_turns * c.current / 1e3),
            "j_eng_A_per_mm2": float(c.j_eng / 1e6),
            "B_peak_T": B_peak,
            "Jc_eng_4p2K_A_per_mm2": float(jc_eng / 1e6),
            "I_over_Ic": float(i_over_ic),
            "temp_margin_K": float(t_margin),
            "sigma_hoop_max_abs_MPa": sigma_max_MPa,
            "sigma_hoop_peak_signed_MPa": sigma_signed_max_MPa,
            "sigma_hoop_mean_MPa": sigma_mean_MPa,
            "axial_force_Fz_kN": float(F_z_N / 1e3),
            "wire_length_m": float(c.conductor_length_m),
        })

    # 6. Quench protection (worst-case coil / series-connected main bank)
    # Effective inductance seen at max current: E_mag = 0.5 * L_eff * I_ref^2
    I_ref = max(abs(c.current) for c in opt_coils)
    L_eff_system = 2.0 * E_mag_coils / (I_ref ** 2)
    # Cu current density in worst-loaded coil (Cu area fraction = (2/3) * packing = 0.4667)
    j_eng_max = max(abs(c.j_eng) for c in opt_coils)
    j_cu_max = j_eng_max / ((2.0 / 3.0) * 0.70)
    quench = quench_hotspot_temperature_K(j_cu_max, L_eff_system, I_ref, V_max_V=400.0, t_detect_s=0.030)

    # Cryoperm-10 outer sleeve (R=39-41 mm around Nb cup, pre-shield safety check)
    cryoperm = cryoperm_cylindrical_sf(mu_r=20000.0, thickness_m=0.002, radius_m=0.041, length_m=0.056)
    cryoperm["max_incident_B_T"] = float(np.max(B_sh_unshielded))
    cryoperm["saturation_margin_ratio"] = float(cryoperm["B_sat_T"] / max(np.max(B_sh_unshielded), 1e-9))

    return {
        "coils": opt_coils,
        "coil_metrics": coil_metrics,
        "shield": shield,
        "shield_rings": (rho_s, z_s, ds_s, I_sh, K_phi),
        "L_matrix_H": L_mat,
        "E_mag_coils_J": E_mag_coils,
        "E_mag_coupled_J": E_mag_coupled,
        "E_shield_interaction_J": E_shield_interaction,
        "sample": {
            "Bz_center_T": float(Bz_0_c[0] @ I_opt),
            "homogeneity_max_rel_Bz": hom_rel_Bz,
            "homogeneity_ppm_Bz": hom_rel_Bz * 1e6,
            "homogeneity_max_rel_Bmag": hom_rel_Bmag,
            "homogeneity_ppm_Bmag": hom_rel_Bmag * 1e6,
            "max_Br_mT": float(np.max(np.abs(Br_s_val)) * 1e3),
            "shield_reaction_mT": float(shield_reaction_at_sample_mT),
        },
        "resonator_zone": {
            "z_res_loc_mm": round(z_res * 1e3, 2),
            "z_res_machine_mm": round((z_res + 0.500) * 1e3, 2),
            "r_res_max_mm": round(r_res_max * 1e3, 2),
            "unshielded_max_B_T": float(np.max(B_r_u_mag)),
            "unshielded_max_Bz_T": float(np.max(np.abs(Bz_r_u_val))),
            "unshielded_max_Br_T": float(np.max(np.abs(Br_r_u_val))),
            "shielded_max_B_T": float(np.max(B_r_c_mag)),
            "shielded_max_B_mT": float(np.max(B_r_c_mag) * 1e3),
            "shielded_max_Bz_mT": float(np.max(np.abs(Bz_r_c_val)) * 1e3),
            "shielded_max_Br_mT": float(np.max(np.abs(Br_r_c_val)) * 1e3),
            "shield_attenuation_factor": float(np.max(B_r_u_mag) / max(np.max(B_r_c_mag), 1e-12)),
        },
        "nb_shield_check": {
            "n_bem_rings": int(rho_s.size),
            "unshielded_max_B_on_cup_mT": float(np.max(B_sh_unshielded) * 1e3),
            "screened_max_B_surf_mT": float(np.max(B_surf_screened) * 1e3),
            "Bc1_Nb_4p2K_mT": float(nb_bc1_tesla(4.2) * 1e3),
            "Bc1_Nb_1p0K_mT": float(nb_bc1_tesla(1.0) * 1e3),
            "Bc1_Nb_20mK_mT": float(nb_bc1_tesla(0.02) * 1e3),
            "meissner_vortex_free_4p2K": bool(np.max(B_surf_screened) < nb_bc1_tesla(4.2)),
        },
        "cryoperm_outer_sleeve": cryoperm,
        "stray_field_lens_plate_mT": B_lens_max_mT,
        "quench_protection": quench,
    }


def compute_volumetric_magnetic_energy(
    coils: Sequence[Coil],
    r_max: float = 0.55,
    z_min: float = -0.55,
    z_max: float = 0.45,
    nr_grid: int = 160,
    nz_grid: int = 240,
    nr_quad: int = 12,
    nz_quad: int = 12,
) -> float:
    """Direct volumetric energy integration E = (1/(2*mu0)) * int |B|^2 * 2*pi*r dr dz.

    Uses uniform sub-wire filaments with exact finite circular core regularization
    (r_core = sqrt(dr_fil*dz_fil/pi)) so grid points falling inside a coil cross-section
    evaluate the true finite solid-conductor Biot-Savart field rather than an unphysical
    zero-radius 1/d filament pole. Independent cross-check against 0.5 * I^T L I.
    """
    a_all, z_all, i_all, rc2_all = [], [], [], []
    for c in coils:
        dr_f = c.dr / nr_quad
        dz_f = c.dz / nz_quad
        r_m = c.r_in + (np.arange(nr_quad) + 0.5) * dr_f
        z_m = c.z_min + (np.arange(nz_quad) + 0.5) * dz_f
        RR_f, ZZ_f = np.meshgrid(r_m, z_m, indexing="ij")
        n_sub = nr_quad * nz_quad
        a_all.append(RR_f.ravel())
        z_all.append(ZZ_f.ravel())
        i_all.append(np.full(n_sub, c.n_turns * c.current / n_sub))
        # Exact uniform-current circular sub-wire radius^2 (area = dr_f * dz_f)
        rc2_all.append(np.full(n_sub, (dr_f * dz_f) / math.pi))
    a_f = np.concatenate(a_all)
    z_f = np.concatenate(z_all)
    i_f = np.concatenate(i_all)
    rc2_f = np.concatenate(rc2_all)

    dr = r_max / nr_grid
    dz = (z_max - z_min) / nz_grid
    r_pts = (np.arange(nr_grid) + 0.5) * dr
    z_pts = z_min + (np.arange(nz_grid) + 0.5) * dz
    RR, ZZ = np.meshgrid(r_pts, z_pts, indexing="ij")
    rho_flat = RR.ravel()
    z_flat = ZZ.ravel()
    n_pts = rho_flat.size
    Br_tot = np.zeros(n_pts, dtype=np.float64)
    Bz_tot = np.zeros(n_pts, dtype=np.float64)

    chunk = max(1, min(n_pts, 400_000 // max(1, a_f.size)))
    for s in range(0, n_pts, chunk):
        e = min(n_pts, s + chunk)
        r = rho_flat[s:e, None]
        dz_p = z_flat[s:e, None] - z_f[None, :]
        aa = a_f[None, :]
        ii = i_f[None, :]
        rc2 = rc2_f[None, :]

        alpha2_raw = (aa - r) ** 2 + dz_p ** 2
        # Inside sub-wire core (d^2 < r_c^2), solid wire field scales linearly with d/r_c^2
        # Equivalent smooth regularization: alpha2_eff = max(alpha2_raw, rc2) with exact core factor
        in_core = alpha2_raw < rc2
        alpha2 = np.where(in_core, rc2, alpha2_raw)
        beta2 = (aa + r) ** 2 + dz_p ** 2 + np.where(in_core, rc2 - alpha2_raw, 0.0)
        beta = np.sqrt(beta2)
        m = np.minimum((4.0 * aa * r) / np.maximum(beta2, 1e-30), 1.0 - 1e-13)
        K = ellipk(m)
        E = ellipe(m)

        Bz_fil = (MU0 * ii / (2.0 * math.pi * beta)) * (
            K + ((aa ** 2 - r ** 2 - dz_p ** 2) / alpha2) * E
        )
        Br_fil = (MU0 * ii * dz_p / (2.0 * math.pi * r * beta)) * (
            -K + ((aa ** 2 + r ** 2 + dz_p ** 2) / alpha2) * E
        )
        # Apply linear d/r_c ramp for points strictly inside sub-wire core
        core_scale = np.where(in_core, np.sqrt(alpha2_raw / rc2), 1.0)
        Br_tot[s:e] = np.sum(Br_fil * core_scale, axis=1)
        Bz_tot[s:e] = np.sum(Bz_fil * core_scale, axis=1)

    B2 = (Br_tot ** 2 + Bz_tot ** 2).reshape(RR.shape)
    return float(np.sum(B2 * 2.0 * math.pi * RR) * dr * dz / (2.0 * MU0))


def verify_maxwell_identities(coils: Sequence[Coil], shield_rings=None) -> Dict[str, float]:
    """Verify div(B)=0 and B = curl(A_phi e_phi) numerically via central finite differences."""
    all_a, all_z, all_i = [], [], []
    for c in coils:
        a_c, z_c, i_c = c.quadrature_filaments(nr=8, nz=8)
        all_a.append(a_c); all_z.append(z_c); all_i.append(i_c)
    if shield_rings is not None:
        all_a.append(shield_rings[0]); all_z.append(shield_rings[1]); all_i.append(shield_rings[3])
    all_a = np.concatenate(all_a); all_z = np.concatenate(all_z); all_i = np.concatenate(all_i)

    # Test at several off-axis, current-free points
    test_pts = [(0.015, 0.010), (0.045, -0.050), (0.020, -0.140), (0.080, 0.060)]
    h = 1e-6  # 1 um step
    max_div_rel = 0.0
    max_curl_rel = 0.0
    for r0, z0 in test_pts:
        pts_r = np.array([r0, r0 + h, r0 - h, r0, r0])
        pts_z = np.array([z0, z0, z0, z0 + h, z0 - h])
        Br, Bz, Ap = filament_field_and_aphi(all_a, all_z, all_i, pts_r, pts_z)
        B_scale = max(math.hypot(Br[0], Bz[0]), 1e-6)
        # div B = (1/r) d(r Br)/dr + dBz/dz
        d_rBr_dr = ((r0 + h) * Br[1] - (r0 - h) * Br[2]) / (2.0 * h)
        dBz_dz = (Bz[3] - Bz[4]) / (2.0 * h)
        div_B = d_rBr_dr / r0 + dBz_dz
        # Scale by B / (0.05 m)
        max_div_rel = max(max_div_rel, abs(div_B) * 0.05 / B_scale)

        # curl A: Bz = (1/r) d(r Aphi)/dr, Br = -dAphi/dz
        Bz_curl = ((r0 + h) * Ap[1] - (r0 - h) * Ap[2]) / (2.0 * h * r0)
        Br_curl = -(Ap[3] - Ap[4]) / (2.0 * h)
        err_curl = math.hypot(Bz_curl - Bz[0], Br_curl - Br[0]) / B_scale
        max_curl_rel = max(max_curl_rel, err_curl)

    return {"max_divB_rel": float(max_div_rel), "max_curlA_rel": float(max_curl_rel)}


def run_convergence_study(
    coils: Sequence[Coil], shield: NbShieldGeometry, z_res: float = -0.155
) -> Dict:
    """Test quadrature convergence (4x4, 8x8, 12x12) and BEM mesh convergence (scale 1, 2)."""
    # Keep fixed optimized currents from baseline (nr=8, bem=1) and re-evaluate sample & resonator
    # fields at refined quadrature & BEM discretizations to verify numerical convergence < 1e-5.
    res_base = solve_coupled_magnet_system(coils, shield, z_res=z_res, nr_quad=8, nz_quad=8, bem_scale=1)
    fixed_coils = res_base["coils"]

    quad_table = {}
    for nq in (4, 8, 12):
        # Evaluate coil-only Bz at sample center (0,0) and edge (2.3 mm, 0.5 mm)
        a_l, z_l, i_l = [], [], []
        for c in fixed_coils:
            ac, zc, ic = c.quadrature_filaments(nr=nq, nz=nq)
            a_l.append(ac); z_l.append(zc); i_l.append(ic)
        a_all, z_all, i_all = np.concatenate(a_l), np.concatenate(z_l), np.concatenate(i_l)
        _, bz_pts, _ = filament_field_and_aphi(
            a_all, z_all, i_all, np.array([0.0, 0.0023, 0.025]), np.array([0.0, 0.0005, z_res])
        )
        quad_table[f"{nq}x{nq}"] = {
            "Bz_center_T": float(bz_pts[0]),
            "Bz_edge_T": float(bz_pts[1]),
            "Bz_res_unshielded_T": float(bz_pts[2]),
        }

    quad_rel_err_8_vs_12 = abs(
        quad_table["8x8"]["Bz_center_T"] - quad_table["12x12"]["Bz_center_T"]
    ) / abs(quad_table["12x12"]["Bz_center_T"])

    # BEM convergence: solve shield currents at scale 1 (102 rings) vs scale 2 (204 rings) for fixed coils
    bem_table = {}
    for sc in (1, 2):
        rho_s, z_s, ds_s, _, _ = discretize_nb_cup(
            shield, n_wall=32 * sc, n_cap=20 * sc, n_chimney=18 * sc, n_fillet=6 * sc
        )
        M_sh = build_shield_inductance_matrix(rho_s, z_s, ds_s)
        a_l, z_l, i_l = [], [], []
        for c in fixed_coils:
            ac, zc, ic = c.quadrature_filaments(nr=8, nz=8)
            a_l.append(ac); z_l.append(zc); i_l.append(ic)
        a_all, z_all, i_all = np.concatenate(a_l), np.concatenate(z_l), np.concatenate(i_l)
        _, _, ap_s = filament_field_and_aphi(a_all, z_all, i_all, rho_s, z_s)
        I_sh = -np.linalg.solve(M_sh, 2.0 * math.pi * rho_s * ap_s)
        # Evaluate total shielded B at sample (0,0) and resonator zone center (0, z_res) & edge (25 mm, z_res)
        pts_r = np.array([0.0, 0.0, 0.025])
        pts_z = np.array([0.0, z_res, z_res])
        br_c, bz_c, _ = filament_field_and_aphi(a_all, z_all, i_all, pts_r, pts_z)
        br_s, bz_s, _ = filament_field_and_aphi(rho_s, z_s, I_sh, pts_r, pts_z)
        bz_tot = bz_c + bz_s
        br_tot = br_c + br_s
        bem_table[f"M{rho_s.size}"] = {
            "n_rings": int(rho_s.size),
            "Bz_sample_T": float(bz_tot[0]),
            "B_res_center_mT": float(math.hypot(br_tot[1], bz_tot[1]) * 1e3),
            "B_res_edge_mT": float(math.hypot(br_tot[2], bz_tot[2]) * 1e3),
            "total_shield_current_A": float(np.sum(np.abs(I_sh))),
        }

    keys = list(bem_table.keys())
    bem_sample_rel_err = abs(
        bem_table[keys[0]]["Bz_sample_T"] - bem_table[keys[1]]["Bz_sample_T"]
    ) / abs(bem_table[keys[1]]["Bz_sample_T"])
    bem_res_diff_mT = abs(
        bem_table[keys[0]]["B_res_edge_mT"] - bem_table[keys[1]]["B_res_edge_mT"]
    )

    return {
        "quadrature": quad_table,
        "quad_rel_err_8_vs_12": float(quad_rel_err_8_vs_12),
        "bem": bem_table,
        "bem_sample_rel_err": float(bem_sample_rel_err),
        "bem_res_edge_diff_mT": float(bem_res_diff_mT),
    }


def evaluate_2d_field_map(
    res: Dict,
    r_max: float = 0.190,
    z_min: float = -0.210,
    z_max: float = 0.170,
    nr: int = 120,
    nz: int = 200,
) -> Dict:
    """Evaluate 2D (r, z) field map + axial profile + resonator-plane radial profile for plotting."""
    coils = res["coils"]
    rho_s, z_s, _, I_sh, _ = res["shield_rings"]
    a_l, z_l, i_l = [], [], []
    for c in coils:
        ac, zc, ic = c.quadrature_filaments(nr=8, nz=8)
        a_l.append(ac); z_l.append(zc); i_l.append(ic)
    a_coils, z_coils, i_coils = np.concatenate(a_l), np.concatenate(z_l), np.concatenate(i_l)
    a_all = np.concatenate([a_coils, rho_s])
    z_all = np.concatenate([z_coils, z_s])
    i_all = np.concatenate([i_coils, I_sh])

    r_grid = np.linspace(0.0, r_max, nr)
    z_grid = np.linspace(z_min, z_max, nz)
    RR, ZZ = np.meshgrid(r_grid, z_grid, indexing="ij")
    Br, Bz, _ = filament_field_and_aphi(a_all, z_all, i_all, RR, ZZ)
    Bmag = np.hypot(Br, Bz)

    # Axial profile (r = 0): shielded vs unshielded
    z_ax = np.linspace(-0.220, 0.280, 300)
    r_ax = np.zeros_like(z_ax)
    _, Bz_ax_unsh, _ = filament_field_and_aphi(a_coils, z_coils, i_coils, r_ax, z_ax)
    _, Bz_ax_sh, _ = filament_field_and_aphi(a_all, z_all, i_all, r_ax, z_ax)

    # Resonator plane radial profile at z_res
    z_res = res["resonator_zone"]["z_res_loc_mm"] * 1e-3
    r_rp = np.linspace(0.0, 0.028, 80)
    z_rp = np.full_like(r_rp, z_res)
    Br_rp_u, Bz_rp_u, _ = filament_field_and_aphi(a_coils, z_coils, i_coils, r_rp, z_rp)
    Br_rp_s, Bz_rp_s, _ = filament_field_and_aphi(a_all, z_all, i_all, r_rp, z_rp)

    # Sample plane homogeneity profile at z=0, r in [0, 3.0 mm]
    r_sp = np.linspace(0.0, 0.003, 60)
    z_sp = np.zeros_like(r_sp)
    _, Bz_sp_s, _ = filament_field_and_aphi(a_all, z_all, i_all, r_sp, z_sp)

    return {
        "r_mm": (r_grid * 1e3).tolist(),
        "z_mm": (z_grid * 1e3).tolist(),
        "Bmag_T": np.round(Bmag, 6).tolist(),
        "axial_z_mm": (z_ax * 1e3).tolist(),
        "axial_Bz_unshielded_T": np.round(Bz_ax_unsh, 6).tolist(),
        "axial_Bz_shielded_T": np.round(Bz_ax_sh, 6).tolist(),
        "res_r_mm": (r_rp * 1e3).tolist(),
        "res_Bz_unshielded_mT": np.round(Bz_rp_u * 1e3, 4).tolist(),
        "res_Br_unshielded_mT": np.round(Br_rp_u * 1e3, 4).tolist(),
        "res_Bz_shielded_mT": np.round(Bz_rp_s * 1e3, 5).tolist(),
        "res_Br_shielded_mT": np.round(Br_rp_s * 1e3, 5).tolist(),
        "sample_r_mm": (r_sp * 1e3).tolist(),
        "sample_dB_ppm": np.round((Bz_sp_s - 1.50) / 1.50 * 1e6, 3).tolist(),
    }


if __name__ == "__main__":
    print("=== 1. Superconducting Sphere Analytical BEM Benchmark ===")
    sp = validate_superconducting_sphere_bem(n_rings=160)
    print(sp)

    print("\n=== 2. Coupled Multi-Coil + Nb Meissner Shield Optimization ===")
    coils0, shield0 = default_magnet_and_shield_geometry()
    res = solve_coupled_magnet_system(coils0, shield0, nr_quad=8, nz_quad=8, bem_scale=1)
    print("Sample:", res["sample"])
    print("Resonator zone:", res["resonator_zone"])
    print("Nb shield:", res["nb_shield_check"])
    print("Cryoperm sleeve:", res["cryoperm_outer_sleeve"])
    print("Lens stray field (mT):", round(res["stray_field_lens_plate_mT"], 2))
    print("Energy coils (kJ):", round(res["E_mag_coils_J"] / 1e3, 3),
          "coupled (kJ):", round(res["E_mag_coupled_J"] / 1e3, 3))
    print("Quench:", res["quench_protection"])
    for cm in res["coil_metrics"]:
        print(
            f"  {cm['name']:8s} I={cm['current_A']:+7.2f} A  J={cm['j_eng_A_per_mm2']:+6.1f} A/mm2  "
            f"Bp={cm['B_peak_T']:.2f} T  I/Ic={cm['I_over_Ic']:.3f}  dT={cm['temp_margin_K']:.2f} K  "
            f"hoop={cm['sigma_hoop_peak_signed_MPa']:+5.1f} MPa  Fz={cm['axial_force_Fz_kN']:+6.2f} kN"
        )
    print("Maxwell check:", verify_maxwell_identities(res["coils"], res["shield_rings"]))
    e_vol = compute_volumetric_magnetic_energy(res["coils"])
    print("Energy parity: L-matrix =", round(res["E_mag_coils_J"], 1), "J vs Vol =", round(e_vol, 1),
          "J, rel diff =", f"{abs(e_vol - res['E_mag_coils_J'])/res['E_mag_coils_J']:.4%}")
