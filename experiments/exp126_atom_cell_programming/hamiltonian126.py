"""Exp126 core physics: 32D 31P + 4x 29Si Hamiltonian, lattice atlas, and calibrated 1/omega^alpha bath noise.

Standalone portable module (zero hardcoded Windows paths) reproducing the exact
Exp25/42/48/59/62/63 Kohn-Luttinger + electron-nuclear dipolar + nuclear-nuclear dipolar
silicon spin register physics, extended to full 2^5 = 32-dimensional Hilbert space evolution,
exact D0 storage leakage, Lie algebra rank certification, and time-domain 1/omega^alpha
stochastic bath noise calibrated to Hahn-echo T2e(f).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import eigh

# ---------------------------------------------------------------------------
# Physical constants (exact Exp25 / Exp42 / Exp62 / Exp63 anchors)
# ---------------------------------------------------------------------------
A0_NM = 0.5431
A_T_NM = 2.5
B_L_NM = 1.4
K0_INV_NM = 0.844 * 2.0 * math.pi / A0_NM
GAMMA_N_HZ_PER_T = 8.465e6          # 29Si nuclear gyromagnetic ratio (Hz/T)
D_NN_HZ_NM3 = 4.748                 # Secular 29Si-29Si dipolar prefactor (Hz * nm^3)
MU0_OVER_4PI = 1e-7
GE_MUB = 2.0023 * 9.2740100783e-24  # J/T
T2E0_S = 0.010                      # 10 ms purified 28Si baseline (Exp62/63)
K_BATH_PER_FRAC = (1.0 / 0.0003 - 1.0 / T2E0_S) / 0.047  # T2e(4.7%) = 0.30 ms

DIRS = {
    "[001]": np.array([0.0, 0.0, 1.0], dtype=np.float64),
    "[110]": np.array([1.0, 1.0, 0.0], dtype=np.float64) / math.sqrt(2.0),
    "[111]": np.array([1.0, 1.0, 1.0], dtype=np.float64) / math.sqrt(3.0),
    "[123]": np.array([1.0, 2.0, 3.0], dtype=np.float64) / math.sqrt(14.0),
}
PRIMARY_DIR = "[123]"

# Spin-1/2 Pauli operators
I2 = np.eye(2, dtype=np.complex128)
PX = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
PY = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
PZ = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)
SX, SY, SZ = PX / 2.0, PY / 2.0, PZ / 2.0
HADAMARD_2 = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=np.complex128) / math.sqrt(2.0)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def t2e_bath_s(abundance_pct: float) -> float:
    """Exp62/63 two-anchor donor electron Hahn-echo T2e(f) model in seconds."""
    return float(1.0 / (1.0 / T2E0_S + K_BATH_PER_FRAC * (float(abundance_pct) / 100.0)))


# ---------------------------------------------------------------------------
# Diamond lattice + Kohn-Luttinger hyperfine atlas (cached singleton)
# ---------------------------------------------------------------------------
_ATLAS_CACHE: Optional[Tuple[np.ndarray, Dict[str, np.ndarray]]] = None


def _kl_envelope_S(r_nm: np.ndarray) -> np.ndarray:
    r = np.atleast_2d(np.asarray(r_nm, dtype=np.float64))
    out = np.zeros(r.shape[0], dtype=np.float64)
    r2_sum = np.sum(r * r, axis=1)
    for i in range(3):
        ri2 = r[:, i] * r[:, i]
        perp2 = np.maximum(0.0, r2_sum - ri2)
        F = np.exp(-np.sqrt(perp2 / (A_T_NM ** 2) + ri2 / (B_L_NM ** 2)))
        out += F * np.cos(K0_INV_NM * r[:, i])
    return out


def get_silicon_atlas(radius_nm: float = 6.0) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """Return (SITES [N,3] nm, A_BY_DIR dict of Hz arrays), exact match to Exp25/42/62."""
    global _ATLAS_CACHE
    if _ATLAS_CACHE is not None and abs(radius_nm - 6.0) < 1e-12:
        return _ATLAS_CACHE

    basis = np.array([
        [0.0, 0.0, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0],
        [0.25, 0.25, 0.25], [0.25, 0.75, 0.75], [0.75, 0.25, 0.75], [0.75, 0.75, 0.25],
    ], dtype=np.float64)
    n = int(math.ceil(radius_nm / A0_NM)) + 1
    g = np.arange(-n, n + 1)
    cells = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
    pts = (cells[:, None, :] + basis[None, :, :]).reshape(-1, 3) * A0_NM
    dists = np.linalg.norm(pts, axis=1)
    sites = pts[(dists > 1e-6) & (dists <= radius_nm)]

    c_cal = 2.981e6 / float(_kl_envelope_S(np.array([[0.0, 0.0, A0_NM]]))[0] ** 2)
    a_iso = c_cal * (_kl_envelope_S(sites) ** 2)

    r_m = np.linalg.norm(sites, axis=1) * 1e-9
    dip_scale = MU0_OVER_4PI * GE_MUB * GAMMA_N_HZ_PER_T / (r_m ** 3)
    r_hat = sites / np.linalg.norm(sites, axis=1, keepdims=True)
    a_by_dir: Dict[str, np.ndarray] = {}
    for name, bdir in DIRS.items():
        cos_th = r_hat @ bdir
        a_by_dir[name] = a_iso + dip_scale * (3.0 * cos_th * cos_th - 1.0)

    if abs(radius_nm - 6.0) < 1e-12:
        _ATLAS_CACHE = (sites, a_by_dir)
    return sites, a_by_dir


def dipolar_J_matrix(positions_nm: np.ndarray, bdir: Optional[np.ndarray] = None) -> np.ndarray:
    """Secular 29Si-29Si nuclear dipolar coupling matrix J_ij in Hz."""
    if bdir is None:
        bdir = DIRS[PRIMARY_DIR]
    pos = np.asarray(positions_nm, dtype=np.float64)
    n = pos.shape[0]
    if n < 2:
        return np.zeros((n, n), dtype=np.float64)
    diff = pos[:, None, :] - pos[None, :, :]
    r = np.linalg.norm(diff, axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_safe = np.where(r > 0.0, r, 1.0)
        cos = np.where(r > 0.0, (diff @ bdir) / r_safe, 0.0)
        J = np.where(r > 0.0, D_NN_HZ_NM3 * (1.0 - 3.0 * cos * cos) / (r_safe ** 3), 0.0)
    np.fill_diagonal(J, 0.0)
    return J


def register_gaps_hz(A_register_hz: np.ndarray, A_env_hz: np.ndarray, nu_hz: float = GAMMA_N_HZ_PER_T) -> np.ndarray:
    """Minimum transition frequency gap (Hz) for each register f_k^+ line in full environment."""
    a_env = np.asarray(A_env_hz, dtype=np.float64)
    k_len = len(A_register_hz)
    freqs = np.empty(2 * len(a_env), dtype=np.float64)
    freqs[0::2] = np.abs(nu_hz + a_env / 2.0)
    freqs[1::2] = np.abs(nu_hz - a_env / 2.0)
    order = np.argsort(freqs)
    sorted_f = freqs[order]
    inv_pos = np.empty(len(freqs), dtype=int)
    inv_pos[order] = np.arange(len(freqs))
    gaps = np.empty(k_len, dtype=np.float64)
    for k in range(k_len):
        p = inv_pos[2 * k]
        neigh = []
        if p > 0:
            neigh.append(sorted_f[p] - sorted_f[p - 1])
        if p + 1 < len(sorted_f):
            neigh.append(sorted_f[p + 1] - sorted_f[p])
        gaps[k] = float(min(neigh)) if neigh else float("inf")
    return gaps


def vandermonde_rank(A_hz: np.ndarray) -> Tuple[int, float]:
    """Rank and log10 condition number of A_k^2 Vandermonde matrix (Exp42 criterion)."""
    a = np.asarray(A_hz, dtype=np.float64)
    k = len(a)
    if k == 0:
        return 0, float("inf")
    scale = float(np.max(np.abs(a))) or 1.0
    x = (a / scale) ** 2
    M = np.vander(x, N=k, increasing=True).T
    s = np.linalg.svd(M, compute_uv=False)
    rank = int(np.sum(s > s[0] * 1e-12)) if s[0] > 0 else 0
    cond = float(s[0] / s[-1]) if s[-1] > 0 else float("inf")
    return rank, (math.log10(cond) if math.isfinite(cond) else float("inf"))


# ---------------------------------------------------------------------------
# Full 32D (1 electron + 4 nuclei) and 16D nuclear operators
# ---------------------------------------------------------------------------
def kron_list(mats: Sequence[np.ndarray]) -> np.ndarray:
    out = np.array([[1.0 + 0.0j]], dtype=np.complex128)
    for m in mats:
        out = np.kron(out, m)
    return out


def single_op(mat: np.ndarray, idx: int, n_qubits: int) -> np.ndarray:
    return kron_list([mat if k == idx else I2 for k in range(n_qubits)])


@dataclass
class SpinOperators:
    """Cached spin-1/2 operators for 1 electron + K_sub=4 nuclei (dim=32) and nuclear subspace (dim=16)."""
    k_nuc: int = 4
    # 16x16 nuclear-only operators
    Ix: List[np.ndarray] = field(default_factory=list)
    Iy: List[np.ndarray] = field(default_factory=list)
    Iz: List[np.ndarray] = field(default_factory=list)
    Ix_tot: np.ndarray = field(default_factory=lambda: np.empty(0))
    Iy_tot: np.ndarray = field(default_factory=lambda: np.empty(0))
    Iz_tot: np.ndarray = field(default_factory=lambda: np.empty(0))
    # 32x32 electron + 4 nuclei operators
    Se: List[np.ndarray] = field(default_factory=list)
    In: List[List[np.ndarray]] = field(default_factory=list)

    def __post_init__(self) -> None:
        k = self.k_nuc
        self.Ix = [single_op(SX, j, k) for j in range(k)]
        self.Iy = [single_op(SY, j, k) for j in range(k)]
        self.Iz = [single_op(SZ, j, k) for j in range(k)]
        self.Ix_tot = sum(self.Ix)
        self.Iy_tot = sum(self.Iy)
        self.Iz_tot = sum(self.Iz)
        self.Se = [single_op(s, 0, k + 1) for s in (SX, SY, SZ)]
        self.In = [[single_op(s, j + 1, k + 1) for s in (SX, SY, SZ)] for j in range(k)]


_OPS_4: Optional[SpinOperators] = None


def get_ops4() -> SpinOperators:
    global _OPS_4
    if _OPS_4 is None:
        _OPS_4 = SpinOperators(k_nuc=4)
    return _OPS_4


def nuclear_dipolar_hamiltonian(J_hz: np.ndarray, ops: Optional[SpinOperators] = None) -> np.ndarray:
    """Exact 16x16 secular nuclear dipolar Hamiltonian (rad/s)."""
    ops = ops or get_ops4()
    k = ops.k_nuc
    H = np.zeros((2 ** k, 2 ** k), dtype=np.complex128)
    for i in range(k):
        for j in range(i + 1, k):
            jij = float(J_hz[i, j])
            if jij != 0.0:
                H += 2.0 * math.pi * jij * (
                    ops.Iz[i] @ ops.Iz[j] - 0.5 * (ops.Ix[i] @ ops.Ix[j] + ops.Iy[i] @ ops.Iy[j])
                )
    return H


def full_32d_drift_hamiltonian(A_hz: np.ndarray, J_hz: np.ndarray, ops: Optional[SpinOperators] = None) -> np.ndarray:
    """Exact 32x32 rotating-frame drift Hamiltonian H0 = 2pi sum A_k S_z I_z^k + I_e x H_dip (rad/s)."""
    ops = ops or get_ops4()
    H_dip = nuclear_dipolar_hamiltonian(J_hz, ops)
    H = np.kron(I2, H_dip)
    for k in range(ops.k_nuc):
        H += 2.0 * math.pi * float(A_hz[k]) * (ops.Se[2] @ ops.In[k][2])
    return H


def lie_algebra_rank_k4(A_hz: np.ndarray, J_hz: Optional[np.ndarray] = None) -> Tuple[int, int]:
    """Compute exact real Lie algebra dimension of su(32) generated by drift + global ESR/RF controls."""
    ops = get_ops4()
    d = 32
    max_dim = d * d - 1  # 1023
    # Scale to MHz for clean numerical conditioning (same convention as Exp25/42)
    A_mhz = np.asarray(A_hz, dtype=np.float64) / 1e6
    H0 = sum(2.0 * math.pi * float(A_mhz[k]) * (ops.Se[2] @ ops.In[k][2]) for k in range(4))
    if J_hz is not None:
        H0 = H0 + np.kron(I2, nuclear_dipolar_hamiltonian(J_hz / 1e6, ops))
    gens = [
        H0,
        ops.Se[0],
        ops.Se[1],
        sum(ops.In[k][0] for k in range(4)),
        sum(ops.In[k][1] for k in range(4)),
    ]
    basis_mat = np.empty((max_dim, 2 * d * d), dtype=np.float64)
    n_basis = 0

    def try_add(M: np.ndarray) -> bool:
        nonlocal n_basis
        v = np.concatenate([M.real.ravel(), M.imag.ravel()])
        if n_basis > 0:
            B = basis_mat[:n_basis]
            v = v - (B @ v) @ B
        nv = float(np.linalg.norm(v))
        if nv > 1e-8:
            basis_mat[n_basis] = v / nv
            n_basis += 1
            return True
        return False

    def to_mat(v: np.ndarray) -> np.ndarray:
        h = d * d
        return (v[:h] + 1j * v[h:]).reshape(d, d)

    frontier: List[np.ndarray] = []
    for g in gens:
        M = 1j * g
        M = M - (np.trace(M) / d) * np.eye(d, dtype=np.complex128)
        if try_add(M):
            frontier.append(to_mat(basis_mat[n_basis - 1]))
    while frontier and n_basis < max_dim:
        nxt: List[np.ndarray] = []
        for M in frontier:
            for g in gens:
                ig = 1j * g
                C = M @ ig - ig @ M
                if np.linalg.norm(C) > 1e-9 and try_add(C):
                    nxt.append(to_mat(basis_mat[n_basis - 1]))
                    if n_basis >= max_dim:
                        break
            if n_basis >= max_dim:
                break
        frontier = nxt
    return n_basis, max_dim


def exact_d0_storage_leakage(
    A_hz: np.ndarray,
    J_hz: np.ndarray,
    horizons_s: Sequence[float] = (17.5, 175.0),
) -> Dict[str, Dict[str, float]]:
    """Exact 32D D0 free-evolution storage leakage across all 16 nuclear basis states (electron in |0_e>)."""
    ops = get_ops4()
    H_dip = nuclear_dipolar_hamiltonian(J_hz, ops)
    # Electron in |0_e> (m_s = +1/2): H_D0 = sum_k pi A_k Iz_k + H_dip
    H_d0 = H_dip.copy()
    for k in range(4):
        H_d0 += 2.0 * math.pi * (0.5 * float(A_hz[k])) * ops.Iz[k]
    evals, evecs = eigh(H_d0)
    dim = 16
    bits = np.array([[(i >> (3 - k)) & 1 for k in range(4)] for i in range(dim)], dtype=np.float64)
    out: Dict[str, Dict[str, float]] = {}
    for t in horizons_s:
        U = (evecs * np.exp(-1j * evals * float(t))) @ evecs.conj().T
        u_err = float(np.linalg.norm(U.conj().T @ U - np.eye(dim), ord="fro"))
        pop = np.abs(U) ** 2
        p_down = pop.T @ bits
        flips = np.where(bits == 0.0, p_down, 1.0 - p_down)
        out[f"{t:g}s"] = {
            "mean_leak": float(np.mean(flips)),
            "max_leak": float(np.max(flips)),
            "unitarity_fro_err": u_err,
        }
    return out


# ---------------------------------------------------------------------------
# Calibrated time-domain 1/omega^alpha stochastic bath noise generator
# ---------------------------------------------------------------------------
def calibrate_bath_noise_spectrum(
    t2e_s: float,
    alpha: float,
    dt_s: float,
    n_steps_sim: int,
    pad_factor: int = 16,
) -> Tuple[np.ndarray, int]:
    """Return calibrated one-sided FFT amplitude weights sqrt(S_k) (Hz) so 1-pulse Hahn echo decays to 1/e at T2e.

    Generates stationary zero-mean Gaussian frequency noise delta_e(t) (in Hz, Hamiltonian term 2*pi*delta_e(t)*S_z)
    with discrete power spectral density S(f) = C_alpha / f^alpha over [df, f_nyq].
    The scale C_alpha is solved analytically on the exact discrete Hahn-echo toggling function so that
    Var[phi_echo(T2e)] = 2.0  <=>  E[exp(-i phi_echo(T2e))] = exp(-1) = 1/e.
    """
    n_echo = max(4, int(round(t2e_s / dt_s)))
    if n_echo % 2 == 1:
        n_echo += 1
    n_fft = max(pad_factor * max(n_steps_sim, n_echo), 4096)
    # Round n_fft up to power of 2 for fast FFT
    n_fft = 1 << (n_fft - 1).bit_length()

    freqs = np.fft.rfftfreq(n_fft, d=dt_s)  # Hz, length n_fft//2 + 1
    psd = np.zeros_like(freqs)
    # Physical infrared cutoff at df = freqs[1] > 0; avoid DC infinity
    psd[1:] = 1.0 / (freqs[1:] ** float(alpha))

    # Exact discrete Hahn echo toggling function y(t) of length n_echo: +1 for first half, -1 for second half
    y = np.zeros(n_fft, dtype=np.float64)
    half = n_echo // 2
    y[:half] = 1.0
    y[half:n_echo] = -1.0
    # Phase phi = 2*pi*dt * sum_n y[n] delta_e[n].
    # If delta_e = irfft(W * Z) where Z_k ~ CN(0, 1) (for 0<k<N/2: Re,Im ~ N(0,1/2); for k=N/2: Re ~ N(0,1)),
    # by Parseval on rfft:
    # Var[sum_n y[n] delta_e[n]] = (1 / N^2) * [ sum_{0<k<N/2} 2 * |Y_k|^2 * W_k^2 + |Y_{N/2}|^2 * W_{N/2}^2 ]
    # Wait: let's match numpy.fft.irfft normalization explicitly!
    # For x = irfft(X, n=N), x[n] = (1/N) * (X[0] + 2 Re sum_{1..N/2-1} X[k] e^{i2pi kn/N} + (-1)^n X[N/2]).
    # If X[k] = W[k] * (a_k + i b_k)/sqrt(2) with a_k, b_k ~ N(0,1) for 1..N/2-1, and X[N/2] = W[N/2] * a_{N/2}:
    # Then sum_n y[n] x[n] = (1/N) * [ 2 sum_{1..N/2-1} (Re Y_k Re X_k + Im Y_k Im X_k) + Y[N/2] X[N/2] ]
    # Variance of term k (1..N/2-1): (4 / N^2) * (W[k]^2 / 2) * (Re(Y_k)^2 + Im(Y_k)^2) = (2 / N^2) * |Y_k|^2 * W[k]^2.
    # Variance of term N/2: (1 / N^2) * |Y[N/2]|^2 * W[N/2]^2.
    Y = np.fft.rfft(y)
    weights_sq = psd.copy()
    coeff = np.zeros_like(freqs)
    coeff[1:-1] = 2.0 / (n_fft ** 2)
    coeff[-1] = 1.0 / (n_fft ** 2)
    var_phi_unscaled = float(((2.0 * math.pi * dt_s) ** 2) * np.sum(coeff * (np.abs(Y) ** 2) * weights_sq))
    scale = math.sqrt(2.0 / var_phi_unscaled)
    amp_weights = scale * np.sqrt(weights_sq)
    return amp_weights, n_fft


def sample_bath_noise_hz(
    t2e_s: float,
    alpha: float,
    dt_s: float,
    n_steps: int,
    n_traj: int,
    rng: np.random.Generator,
    pad_factor: int = 16,
) -> np.ndarray:
    """Sample (n_traj, n_steps) calibrated 1/omega^alpha frequency noise trajectories delta_e(t) in Hz."""
    amp_w, n_fft = calibrate_bath_noise_spectrum(t2e_s, alpha, dt_s, n_steps, pad_factor=pad_factor)
    m_freq = len(amp_w)
    re = rng.standard_normal((n_traj, m_freq))
    im = rng.standard_normal((n_traj, m_freq))
    Z = (re + 1j * im) / math.sqrt(2.0)
    Z[:, 0] = 0.0
    Z[:, -1] = rng.standard_normal(n_traj)
    X = Z * amp_w[None, :]
    full = np.fft.irfft(X, n=n_fft, axis=1)
    # Random starting offset in stationary ring to eliminate any window edge correlation
    starts = rng.integers(0, n_fft - n_steps, size=n_traj)
    out = np.empty((n_traj, n_steps), dtype=np.float64)
    for i in range(n_traj):
        s = int(starts[i])
        out[i] = full[i, s : s + n_steps]
    return out


# ---------------------------------------------------------------------------
# Certified Silicon Atom Cell Specification & Loader / Sampler
# ---------------------------------------------------------------------------
@dataclass
class CellSpec:
    cell_id: str
    abundance_pct: float
    t2e_s: float
    global_indices_k4: List[int]
    A_hz: np.ndarray                 # (4,) Hz
    positions_nm: np.ndarray         # (4, 3) nm
    J_hz: np.ndarray                 # (4, 4) Hz
    A_spectators_hz: np.ndarray      # (M_spec,) Hz (remaining bath 29Si nuclei)
    min_gap_hz: float
    max_abs_J_hz: float
    min_pair_dist_nm: float
    vandermonde_rank_k4: int
    vandermonde_rank_k8: int
    lie_rank_k4: int
    parent_k8_globals: List[int] = field(default_factory=list)
    realization_seed: int = 0
    source: str = ""

    def to_metadata_dict(self) -> Dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "abundance_pct": float(self.abundance_pct),
            "t2e_ms": float(self.t2e_s * 1e3),
            "global_indices_k4": [int(x) for x in self.global_indices_k4],
            "parent_k8_globals": [int(x) for x in self.parent_k8_globals],
            "A_kHz": [float(x / 1e3) for x in self.A_hz],
            "min_gap_kHz": float(self.min_gap_hz / 1e3),
            "max_abs_J_Hz": float(self.max_abs_J_hz),
            "min_pair_dist_nm": float(self.min_pair_dist_nm),
            "n_bath_spectators": int(len(self.A_spectators_hz)),
            "vandermonde_rank_k4": int(self.vandermonde_rank_k4),
            "vandermonde_rank_k8": int(self.vandermonde_rank_k8),
            "lie_rank_k4": int(self.lie_rank_k4),
            "source": self.source,
        }


def _select_best_k4_from_k8(
    k8_globals: Sequence[int],
    cloud_globals: np.ndarray,
    A_all: np.ndarray,
) -> Tuple[List[int], float]:
    """Select best K=4 active subregister inside certified K=8 by Exp48/62 (min|A|, min_gap) criterion."""
    import itertools

    k8 = list(int(x) for x in k8_globals)
    A_cloud = A_all[cloud_globals]
    g2l = {int(g): i for i, g in enumerate(cloud_globals)}
    k8_local = [g2l[g] for g in k8]
    gaps_cloud = register_gaps_hz(A_cloud, A_cloud)

    best_key = None
    best_globals: List[int] = []
    for combo_l in itertools.combinations(k8_local, 4):
        cl = list(combo_l)
        key = (float(np.min(np.abs(A_cloud[cl]))), float(np.min(gaps_cloud[cl])))
        if best_key is None or key > best_key:
            best_key = key
            best_globals = [int(cloud_globals[i]) for i in cl]
    assert best_key is not None
    return best_globals, float(best_key[1])


def build_cell_from_globals(
    cell_id: str,
    abundance_pct: float,
    k4_globals: Sequence[int],
    k8_globals: Sequence[int],
    cloud_globals: Sequence[int],
    source: str,
    verify_lie: bool = True,
    realization_seed: int = 0,
) -> CellSpec:
    sites, a_by_dir = get_silicon_atlas()
    A_all = a_by_dir[PRIMARY_DIR]
    k4 = [int(x) for x in k4_globals]
    k8 = [int(x) for x in k8_globals]
    cloud = np.asarray(cloud_globals, dtype=int)
    spec_globals = np.array([g for g in cloud if g not in set(k4)], dtype=int)

    A_k4 = A_all[k4]
    pos_k4 = sites[k4]
    J_k4 = dipolar_J_matrix(pos_k4)
    A_spec = A_all[spec_globals]
    A_env = np.concatenate([A_k4, A_spec])
    gaps = register_gaps_hz(A_k4, A_env)
    min_gap = float(np.min(gaps))

    dmat = np.linalg.norm(pos_k4[:, None, :] - pos_k4[None, :, :], axis=2)
    iu = np.triu_indices(4, 1)
    min_d = float(np.min(dmat[iu]))
    max_J = float(np.max(np.abs(J_k4[iu])))
    vr4, _ = vandermonde_rank(A_k4)
    vr8, _ = vandermonde_rank(A_all[k8]) if len(k8) == 8 else (0, float("inf"))
    lie_r = lie_algebra_rank_k4(A_k4, J_k4)[0] if verify_lie else 1023

    return CellSpec(
        cell_id=cell_id,
        abundance_pct=float(abundance_pct),
        t2e_s=t2e_bath_s(abundance_pct),
        global_indices_k4=k4,
        A_hz=A_k4,
        positions_nm=pos_k4,
        J_hz=J_k4,
        A_spectators_hz=A_spec,
        min_gap_hz=min_gap,
        max_abs_J_hz=max_J,
        min_pair_dist_nm=min_d,
        vandermonde_rank_k4=vr4,
        vandermonde_rank_k8=vr8,
        lie_rank_k4=lie_r,
        parent_k8_globals=k8,
        realization_seed=realization_seed,
        source=source,
    )


def load_exp62_finalists(verify_lie: bool = True) -> Dict[str, CellSpec]:
    """Load the exact four Exp59/Exp62 epitaxial bath finalists (F0.5, F1, F2, F4.7)."""
    root = repo_root()
    b59 = json.loads((root / "results/exp59/bath59.json").read_text(encoding="utf-8"))["cells"]
    b62 = json.loads((root / "results/exp62/bath62.json").read_text(encoding="utf-8"))["cells"]
    f59 = json.loads((root / "results/exp59/finalist59.json").read_text(encoding="utf-8"))
    f62 = json.loads((root / "results/exp62/finalist62.json").read_text(encoding="utf-8"))

    out: Dict[str, CellSpec] = {}
    # F0.5
    fin05 = b59["F0.5"]["first_finalist"]
    k4_05 = f59["register_restricted_K4"]["global_indices"]
    out["F0.5"] = build_cell_from_globals(
        "F0.5", 0.5, k4_05, fin05["selected_global"], fin05["cloud_global_indices"],
        source="results/exp59/bath59.json + finalist59.json", verify_lie=verify_lie,
        realization_seed=int(fin05["realization"]),
    )
    # F1, F2, F4.7
    meta = [
        ("F1", 1.0, b59["F1"]["first_finalist"], "results/exp59/bath59.json + results/exp62/finalist62.json"),
        ("F2", 2.0, b62["F2"]["first_finalist"], "results/exp62/bath62.json + finalist62.json"),
        ("F4.7", 4.7, b62["F4.7"]["first_finalist"], "results/exp62/bath62.json + finalist62.json"),
    ]
    for key, f_pct, fin, src in meta:
        k4 = f62["audits"][key]["register_restricted_K4"]["global_indices"]
        out[key] = build_cell_from_globals(
            key, f_pct, k4, fin["selected_global"], fin["cloud_global_indices"],
            source=src, verify_lie=verify_lie, realization_seed=int(fin["realization"]),
        )
    return out


def sample_certified_f1_cells(
    n_cells: int = 16,
    abundance_pct: float = 1.0,
    min_gap_hz: float = 5_000.0,
    min_abs_A_hz: float = 150_000.0,
    max_abs_J_hz: float = 100.0,
    min_pair_dist_nm: float = 0.30,
    include_exp62_f1_first: bool = True,
) -> List[CellSpec]:
    """Sample n_cells distinct certified heterogeneous silicon atom cells from f=1% epitaxial bath.

    Each cell is drawn from a fresh independent random 29Si cloud (M=452 sites on the 45,214-site
    diamond lattice), screened through the exact Exp48/59/61 certification gates (min_gap >= 5 kHz,
    min_pair_dist >= 0.30 nm, max |J_ij| <= 100 Hz, K=8 Vandermonde rank 8, K=4 active Lie rank 1023/1023).
    """
    sites, a_by_dir = get_silicon_atlas()
    A_all = a_by_dir[PRIMARY_DIR]
    n_sites = len(sites)
    m_cloud = int(round(abundance_pct / 100.0 * n_sites))

    cells: List[CellSpec] = []
    seen_k4_sets = set()
    if include_exp62_f1_first:
        f1 = load_exp62_finalists(verify_lie=True)["F1"]
        f1.cell_id = "CELL_00_F1_ANCHOR"
        cells.append(f1)
        seen_k4_sets.add(tuple(sorted(f1.global_indices_k4)))

    # Deterministic scan over fresh f=1% clouds (seed formula disjoint from Exp59)
    trial = 0
    while len(cells) < n_cells and trial < 500:
        seed = 126_100_000 + trial
        trial += 1
        rng = np.random.default_rng(seed)
        cloud = np.sort(rng.choice(n_sites, size=m_cloud, replace=False))
        A_cloud = A_all[cloud]
        gaps = register_gaps_hz(A_cloud, A_cloud)
        # Eligible pool: spectral gap >= min_gap_hz and strong enough |A| to cleanly separate f+ and f- branches
        elig = np.where((gaps >= min_gap_hz) & (np.abs(A_cloud) >= 100_000.0))[0]
        if len(elig) < 8:
            continue

        # Sort eligible by spectral gap descending and greedily pick a valid 8-clique
        order = elig[np.argsort(-gaps[elig])]
        pos_cloud = sites[cloud]
        k8_local: List[int] = []
        for cand in order:
            if not k8_local:
                k8_local.append(int(cand))
                continue
            p_cand = pos_cloud[cand]
            p_sel = pos_cloud[k8_local]
            dists = np.linalg.norm(p_sel - p_cand[None, :], axis=1)
            if float(np.min(dists)) < min_pair_dist_nm:
                continue
            sub_pos = np.vstack([p_sel, p_cand[None, :]])
            J_sub = dipolar_J_matrix(sub_pos)
            if float(np.max(np.abs(J_sub))) > max_abs_J_hz:
                continue
            k8_local.append(int(cand))
            if len(k8_local) == 8:
                break

        if len(k8_local) < 8:
            continue
        k8_globals = [int(cloud[i]) for i in k8_local]
        vr8, _ = vandermonde_rank(A_all[k8_globals])
        if vr8 < 8:
            continue

        k4_globals, k4_gap = _select_best_k4_from_k8(k8_globals, cloud, A_all)
        if k4_gap < min_gap_hz or float(np.min(np.abs(A_all[k4_globals]))) < min_abs_A_hz:
            continue
        key_t = tuple(sorted(k4_globals))
        if key_t in seen_k4_sets:
            continue

        cell = build_cell_from_globals(
            cell_id=f"CELL_{len(cells):02d}_S{trial}",
            abundance_pct=abundance_pct,
            k4_globals=k4_globals,
            k8_globals=k8_globals,
            cloud_globals=cloud,
            source=f"exp126_f1_bath_seed_{seed}",
            verify_lie=True,
            realization_seed=seed,
        )
        if cell.lie_rank_k4 == 1023 and cell.vandermonde_rank_k4 == 4 and cell.max_abs_J_hz <= max_abs_J_hz:
            cells.append(cell)
            seen_k4_sets.add(key_t)

    if len(cells) < n_cells:
        raise RuntimeError(f"Only found {len(cells)} certified cells out of requested {n_cells}")
    return cells
