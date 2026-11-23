"""Exp144 Module 1: Exact GF(2) Bivariate Bicycle (BB) CSS Codes (Bravyi et al., Nature 2024),
Exact Symplectic Logical Basis, Verified Zero-Kickback Syndrome Schedule, Thickness-2 M4
NbTiN Resonator Layout (in um), and Exp136/139 Defective-Block Yield Model.

Codes implemented (Bravyi et al., Nature 627, 778-782, 2024, Table 1):
  - [[72,  12,  6]]: l=6,  m=6, A = x^3 + y + y^2,  B = y^3 + x + x^2
  - [[90,   8, 10]]: l=15, m=3, A = x^9 + y + y^2,  B = 1 + x^2 + x^7
  - [[144, 12, 12]]: l=12, m=6, A = x^3 + y + y^2,  B = y^3 + x + x^2  (Gross Code)

Epistemic scope: {Model} / {Sayisal-Simulasyon} / {Literatur}. no_lab_measurement=True.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


# =============================================================================
# 1. Exact GF(2) Linear Algebra (Bit-Packed / Exact uint8 Gaussian Elimination)
# =============================================================================
def gf2_rref(mat: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """Compute exact Reduced Row Echelon Form over GF(2) and return (rref, pivot_cols)."""
    M = (np.asarray(mat, dtype=np.uint8) & 1).copy()
    nrows, ncols = M.shape
    pivots: List[int] = []
    row = 0
    for col in range(ncols):
        if row >= nrows:
            break
        # Find first nonzero entry at or below `row`
        nz = np.flatnonzero(M[row:, col])
        if nz.size == 0:
            continue
        piv = row + int(nz[0])
        if piv != row:
            M[[row, piv]] = M[[piv, row]]
        # Eliminate all other rows in this column via vectorized XOR
        mask = M[:, col].astype(bool)
        mask[row] = False
        if np.any(mask):
            M[mask] ^= M[row]
        pivots.append(col)
        row += 1
    return M, pivots


def gf2_rank(mat: np.ndarray) -> int:
    _, pivs = gf2_rref(mat)
    return len(pivs)


def gf2_nullspace(mat: np.ndarray) -> np.ndarray:
    """Return basis rows of ker(mat) over GF(2) as shape (dim_ker, ncols) uint8 array."""
    R, pivots = gf2_rref(mat)
    ncols = R.shape[1]
    piv_set = set(pivots)
    free_cols = [c for c in range(ncols) if c not in piv_set]
    basis = np.zeros((len(free_cols), ncols), dtype=np.uint8)
    for k, fc in enumerate(free_cols):
        basis[k, fc] = 1
        for r_idx, pc in enumerate(pivots):
            if R[r_idx, fc]:
                basis[k, pc] = 1
    return basis


def gf2_rowspace_complement(ker_basis: np.ndarray, row_mat: np.ndarray) -> np.ndarray:
    """Extract basis rows of ker_basis modulo rowspace(row_mat) over GF(2)."""
    R_row, piv_row = gf2_rref(row_mat)
    selected: List[np.ndarray] = []
    cur_rows = R_row[: len(piv_row)].copy()
    for v in ker_basis:
        # Reduce v against cur_rows
        cand = v.copy()
        test = np.vstack([cur_rows, cand[None, :]]) if cur_rows.size > 0 else cand[None, :]
        R_new, piv_new = gf2_rref(test)
        if len(piv_new) > cur_rows.shape[0]:
            selected.append(v.copy())
            cur_rows = R_new[: len(piv_new)].copy()
    return np.array(selected, dtype=np.uint8)


def build_symplectic_logical_basis(H_X: np.ndarray, H_Z: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Construct exact CSS logical operators L_X, L_Z (shape k x n) satisfying:
      H_Z @ L_X.T == 0, H_X @ L_Z.T == 0, and L_X @ L_Z.T == I_k (mod 2).
    """
    ker_Z = gf2_nullspace(H_Z)  # X-type operators commuting with all Z checks
    ker_X = gf2_nullspace(H_X)  # Z-type operators commuting with all X checks
    L_X_raw = gf2_rowspace_complement(ker_Z, H_X)
    L_Z_raw = gf2_rowspace_complement(ker_X, H_Z)
    k = L_X_raw.shape[0]
    assert k == L_Z_raw.shape[0], f"CSS logical count mismatch: {k} vs {L_Z_raw.shape[0]}"

    # Symplectic Gram-Schmidt pairing over GF(2) so L_X @ L_Z.T == I_k
    L_X = L_X_raw.copy()
    L_Z = L_Z_raw.copy()
    for i in range(k):
        # Find j >= i such that <L_X[i], L_Z[j]> == 1
        found = -1
        for j in range(i, k):
            if int(np.dot(L_X[i], L_Z[j]) & 1) == 1:
                found = j
                break
        if found < 0:
            raise RuntimeError(f"Failed symplectic pairing at logical index {i}")
        if found != i:
            L_Z[[i, found]] = L_Z[[found, i]]
        # Eliminate overlaps with all other logicals
        for j in range(k):
            if j != i and int(np.dot(L_X[j], L_Z[i]) & 1) == 1:
                L_X[j] ^= L_X[i]
            if j != i and int(np.dot(L_X[i], L_Z[j]) & 1) == 1:
                L_Z[j] ^= L_Z[i]

    # Strict algebraic assertions
    assert np.all((H_Z @ L_X.T) % 2 == 0)
    assert np.all((H_X @ L_Z.T) % 2 == 0)
    assert np.array_equal((L_X @ L_Z.T) % 2, np.eye(k, dtype=np.uint8))
    return L_X, L_Z


# =============================================================================
# 2. Bivariate Bicycle Code Family (Bravyi et al., Nature 2024)
# =============================================================================
@dataclass
class BBCodeSpec:
    name: str
    l: int
    m: int
    d_lit: int
    A_terms: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]  # (pow_x, pow_y)
    B_terms: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]


BB_CODE_SPECS: Dict[str, BBCodeSpec] = {
    "BB_72_12_6": BBCodeSpec(
        name="[[72, 12, 6]]", l=6, m=6, d_lit=6,
        A_terms=((3, 0), (0, 1), (0, 2)),
        B_terms=((0, 3), (1, 0), (2, 0)),
    ),
    "BB_90_8_10": BBCodeSpec(
        name="[[90, 8, 10]]", l=15, m=3, d_lit=10,
        A_terms=((9, 0), (0, 1), (0, 2)),
        B_terms=((0, 0), (2, 0), (7, 0)),
    ),
    "BB_144_12_12": BBCodeSpec(
        name="[[144, 12, 12]]", l=12, m=6, d_lit=12,
        A_terms=((3, 0), (0, 1), (0, 2)),
        B_terms=((0, 3), (1, 0), (2, 0)),
    ),
}


def _cyclic_shift(size: int, power: int) -> np.ndarray:
    S = np.zeros((size, size), dtype=np.uint8)
    p = power % size
    for i in range(size):
        S[i, (i + p) % size] = 1
    return S


def monomial_matrix(l: int, m: int, px: int, py: int) -> np.ndarray:
    """Return x^px * y^py of size (l*m, l*m) over GF(2)."""
    return np.kron(_cyclic_shift(l, px), _cyclic_shift(m, py)).astype(np.uint8)


def build_bb_code(spec: BBCodeSpec) -> Dict[str, Any]:
    """Construct exact BB CSS code matrices, logical operators, and algebraic invariants."""
    l, m = spec.l, spec.m
    nh = l * m
    A_mats = [monomial_matrix(l, m, px, py) for (px, py) in spec.A_terms]
    B_mats = [monomial_matrix(l, m, px, py) for (px, py) in spec.B_terms]
    A = (A_mats[0] ^ A_mats[1] ^ A_mats[2]).astype(np.uint8)
    B = (B_mats[0] ^ B_mats[1] ^ B_mats[2]).astype(np.uint8)

    H_X = np.hstack([A, B]).astype(np.uint8)
    H_Z = np.hstack([B.T, A.T]).astype(np.uint8)
    n = 2 * nh

    # Verify CSS commutativity & weight-6 Tanner-graph regularity
    # (Each X-check and Z-check has row weight 6; each data qubit participates in 3 X-checks + 3 Z-checks = 6 checks)
    comm_ok = bool(np.all((H_X @ H_Z.T) % 2 == 0))
    row_w_X = np.sum(H_X, axis=1)
    col_w_X = np.sum(H_X, axis=0)
    row_w_Z = np.sum(H_Z, axis=1)
    col_w_Z = np.sum(H_Z, axis=0)
    all_weight_6 = bool(
        np.all(row_w_X == 6)
        and np.all(row_w_Z == 6)
        and np.all(col_w_X == 3)
        and np.all(col_w_Z == 3)
        and np.all((col_w_X + col_w_Z) == 6)
    )

    rank_X = gf2_rank(H_X)
    rank_Z = gf2_rank(H_Z)
    k = n - rank_X - rank_Z
    L_X, L_Z = build_symplectic_logical_basis(H_X, H_Z)

    return {
        "spec": spec,
        "name": spec.name,
        "l": l,
        "m": m,
        "n_data": n,
        "n_ancilla": n,
        "n_total_cells": 2 * n,
        "n_checks_X": nh,
        "n_checks_Z": nh,
        "rank_X": rank_X,
        "rank_Z": rank_Z,
        "k": k,
        "d_lit": spec.d_lit,
        "rate_k_over_n_total": k / (2.0 * n),
        "commutativity_H_X_H_ZT_zero": comm_ok,
        "all_row_col_weight_6": all_weight_6,
        "A_mats": A_mats,
        "B_mats": B_mats,
        "A": A,
        "B": B,
        "H_X": H_X,
        "H_Z": H_Z,
        "L_X": L_X,
        "L_Z": L_Z,
    }


# =============================================================================
# 3. Exact Verified Zero-Kickback Syndrome-Extraction CNOT Schedule
# =============================================================================
def find_verified_commuting_schedule(code: Dict[str, Any]) -> Dict[str, Any]:
    """Find and algebraically verify a depth-7 (or 8) zero-collision, zero-kickback
    syndrome-extraction CNOT schedule for a Bivariate Bicycle code (Bravyi et al., Nature 2024).

    Qubit layout in symplectic frame (size 4*nh = 2*n):
      - L data:  0 .. nh-1
      - R data:  nh .. 2*nh-1
      - X checks: 2*nh .. 3*nh-1  (initialized |+>, measured X; CNOT control=X_chk, target=data)
      - Z checks: 3*nh .. 4*nh-1  (initialized |0>, measured Z; CNOT control=data, target=Z_chk)

    Exact verification: propagate every initial X_chk Pauli-X and Z_chk Pauli-Z through
    all CNOT layers and confirm:
      (1) Zero qubit collisions in any step;
      (2) X_chk(out) == X_chk * prod(X on H_X support) with ZERO Z_chk kickback;
      (3) Z_chk(out) == Z_chk * prod(Z on H_Z support) with ZERO X_chk kickback!
    """
    nh = code["n_checks_X"]
    A_mats = code["A_mats"]
    B_mats = code["B_mats"]

    # Named gate layers:
    # X-check layers: ("XL", idx) -> CNOT(X_i -> L_j) where A_mats[idx][i, j] == 1
    #                 ("XR", idx) -> CNOT(X_i -> R_j) where B_mats[idx][i, j] == 1
    # Z-check layers: ("ZL", idx) -> CNOT(L_j -> Z_i) where B_mats[idx].T[i, j] == 1
    #                 ("ZR", idx) -> CNOT(R_j -> Z_i) where A_mats[idx].T[i, j] == 1
    def _layer_pairs(tag: str, idx: int) -> List[Tuple[int, int]]:
        pairs: List[Tuple[int, int]] = []
        if tag == "XL":
            M = A_mats[idx]
            rows, cols = np.nonzero(M)
            for r, c in zip(rows, cols):
                pairs.append((2 * nh + int(r), int(c)))  # ctrl=X, tgt=L
        elif tag == "XR":
            M = B_mats[idx]
            rows, cols = np.nonzero(M)
            for r, c in zip(rows, cols):
                pairs.append((2 * nh + int(r), nh + int(c)))  # ctrl=X, tgt=R
        elif tag == "ZL":
            M = B_mats[idx].T
            rows, cols = np.nonzero(M)
            for r, c in zip(rows, cols):
                pairs.append((int(c), 3 * nh + int(r)))  # ctrl=L, tgt=Z
        elif tag == "ZR":
            M = A_mats[idx].T
            rows, cols = np.nonzero(M)
            for r, c in zip(rows, cols):
                pairs.append((nh + int(c), 3 * nh + int(r)))  # ctrl=R, tgt=Z
        return pairs

    def _verify_schedule(steps: List[List[Tuple[str, int]]]) -> Tuple[bool, List[List[Tuple[int, int]]]]:
        all_step_cnots: List[List[Tuple[int, int]]] = []
        # 1. Check zero qubit collision per step
        for st in steps:
            used = set()
            st_pairs: List[Tuple[int, int]] = []
            for tag, idx in st:
                pairs = _layer_pairs(tag, idx)
                for ctrl, tgt in pairs:
                    if ctrl in used or tgt in used:
                        return False, []
                    used.add(ctrl)
                    used.add(tgt)
                st_pairs.extend(pairs)
            all_step_cnots.append(st_pairs)

        # 2. Exact Heisenberg propagation of initial X_check = X_i and Z_check = Z_i!
        #    Under CNOT(c -> t): X_c -> X_c X_t, X_t -> X_t; Z_t -> Z_c Z_t, Z_c -> Z_c.
        #    For measuring X_checks initialized in |+>, propagate X_init (nh x 4*nh) forward:
        X_frame = np.zeros((nh, 4 * nh), dtype=np.uint8)
        for i in range(nh):
            X_frame[i, 2 * nh + i] = 1
        Z_frame = np.zeros((nh, 4 * nh), dtype=np.uint8)
        for i in range(nh):
            Z_frame[i, 3 * nh + i] = 1

        for st_pairs in all_step_cnots:
            # All gates in one step act on disjoint qubits -> vectorized update
            ctrls = np.array([c for c, _ in st_pairs], dtype=np.int32)
            tgts = np.array([t for _, t in st_pairs], dtype=np.int32)
            X_frame[:, tgts] ^= X_frame[:, ctrls]
            Z_frame[:, ctrls] ^= Z_frame[:, tgts]

        # Check X_frame: data part == H_X, X_chk part == I_nh, Z_chk part == 0 (zero kickback!)
        x_ok = (
            np.array_equal(X_frame[:, : 2 * nh], code["H_X"])
            and np.array_equal(X_frame[:, 2 * nh : 3 * nh], np.eye(nh, dtype=np.uint8))
            and np.all(X_frame[:, 3 * nh :] == 0)
        )
        # Check Z_frame: data part == H_Z, X_chk part == 0 (zero kickback!), Z_chk part == I_nh
        z_ok = (
            np.array_equal(Z_frame[:, : 2 * nh], code["H_Z"])
            and np.all(Z_frame[:, 2 * nh : 3 * nh] == 0)
            and np.array_equal(Z_frame[:, 3 * nh :], np.eye(nh, dtype=np.uint8))
        )
        return bool(x_ok and z_ok), all_step_cnots

    # Exact Bravyi et al. (Nature 2024, Lemma 5 / Extended Data Table 3) depth-7 zero-kickback
    # schedule: satisfies 1[t^X(A_p) < t^Z(B_q)] == 1[t^X(B_q) < t^Z(A_p)] for all 9 (p, q) pairs
    # with zero qubit collisions in every step (X and Z always act on opposite L/R data halves):
    #   t=1: XR(b0), ZL(b1)   |  t=2: ZL(b2)
    #   t=3: XL(a0), ZR(a0)   |  t=4: XL(a1), ZR(a1)   |  t=5: XL(a2), ZR(a2)
    #   t=6: XR(b1), ZL(b0)   |  t=7: XR(b2)
    cand_steps = [
        [("XR", 0), ("ZL", 1)],
        [("ZL", 2)],
        [("XL", 0), ("ZR", 0)],
        [("XL", 1), ("ZR", 1)],
        [("XL", 2), ("ZR", 2)],
        [("XR", 1), ("ZL", 0)],
        [("XR", 2)],
    ]
    ok, cnots = _verify_schedule(cand_steps)
    if not ok:
        raise RuntimeError(f"Bravyi depth-7 schedule failed Heisenberg verification for {code['name']}")
    return {
        "depth_cnot_layers": len(cand_steps),
        "total_cnots_per_round": sum(len(s) for s in cnots),
        "zero_collision_verified": True,
        "zero_kickback_verified": True,
        "step_labels": cand_steps,
        "step_cnots": cnots,
    }


# =============================================================================
# 4. Thickness-2 Folded-Torus 2D M4 NbTiN Bus Layout & Defect-Free Block Yield
# =============================================================================
def _fold_1d(idx: int, length: int) -> int:
    """Standard 2:1 folded-torus interleave mapping a periodic ring of length L onto [0..L-1]
    so every nearest-neighbor ring step becomes <= 2 grid units on a flat chip.
    """
    half = length // 2
    if idx < half:
        return 2 * idx
    return 2 * (length - 1 - idx) + 1


def build_thickness2_m4_layout(
    code: Dict[str, Any],
    pitches_um: Tuple[float, ...] = (20.0, 25.0, 30.0, 40.0, 50.0),
    l_res_nominal_um: float = 300.0,
    f_r_nominal_ghz: float = 5.0,
) -> Dict[str, Any]:
    """Embed [[144, 12, 12]] (l=12, m=6, 288 qubits) onto a 24 x 12 folded-torus 2D silicon grid
    with exact 2-layer superconducting NbTiN bus routing:
      - Layer 1 (Local Planar 2D Grid): 4 nearest-neighbor torus edges/check ({y, y^2, x, x^2}) = 576 edges
      - Layer 2 (Long-Range M4 Bus):    2 long-range shifts/check ({x^3, y^3}) = 288 edges

    Returns physical coordinates (in um at P_cell=20 um), exact edge-length statistics across
    pitches 20..50 um, frequency detuning/kinetic-inductance requirement, and airbridge count.
    """
    l, m = code["l"], code["m"]
    nh = l * m
    assert l == 12 and m == 6, "Thickness-2 24x12 folded torus specialized for [[144,12,12]]"

    # Exact Bravyi et al. (Nature 2024, Lemma 3) torus bijection on the 24 x 12 grid:
    #   X(a, b) -> (2a,     2b    ) mod (24, 12)   [even, even]
    #   L(a, b) -> (2a,     2b - 3) mod (24, 12)   [even, odd ]
    #   R(a, b) -> (2a - 3, 2b    ) mod (24, 12)   [odd,  even]
    #   Z(a, b) -> (2a - 3, 2b - 3) mod (24, 12)   [odd,  odd ]
    # Every single one of the 576 Layer-1 edges ({y, y^2, x, x^2}) has EXACT torus distance 1.0 (0 torus crossings!),
    # and every single one of the 288 Layer-2 edges ({x^3, y^3}) has exact torus vector (+-6, +-3) or (+-3, +-6)
    # (torus length sqrt(45) = 6.708 pitches). Folding via 2:1 ring interleave maps onto a flat 24x12 chip!
    coords_unfolded: Dict[int, Tuple[int, int]] = {}
    coords_folded: Dict[int, Tuple[int, int]] = {}
    qubit_types: Dict[int, str] = {}
    W_grid, H_grid = 2 * l, 2 * m  # 24, 12

    for a in range(l):
        for b in range(m):
            idx = a * m + b
            idx_L = idx
            idx_R = nh + idx
            idx_X = 2 * nh + idx
            idx_Z = 3 * nh + idx

            spec_pos = [
                (idx_X, "X", (2 * a) % W_grid, (2 * b) % H_grid),
                (idx_L, "L", (2 * a) % W_grid, (2 * b - 3) % H_grid),
                (idx_R, "R", (2 * a - 3) % W_grid, (2 * b) % H_grid),
                (idx_Z, "Z", (2 * a - 3) % W_grid, (2 * b - 3) % H_grid),
            ]
            for qid, qtype, gx, gy in spec_pos:
                coords_unfolded[qid] = (gx, gy)
                coords_folded[qid] = (_fold_1d(gx, W_grid), _fold_1d(gy, H_grid))
                qubit_types[qid] = qtype

    assert len(set(coords_unfolded.values())) == 288, "Unfolded torus coordinates must be a bijection"
    assert len(set(coords_folded.values())) == 288, "Folded flat-chip coordinates must be a bijection"

    # Extract all 864 Tanner graph edges split into Layer 1 (local: A_1,A_2=y,y^2 & B_1,B_2=x,x^2)
    # and Layer 2 (long-range: A_0=x^3 & B_0=y^3)
    layer1_edges: List[Tuple[int, int]] = []
    layer2_edges: List[Tuple[int, int]] = []
    A_mats = code["A_mats"]  # 0: x^3 (long), 1: y (local), 2: y^2 (local)
    B_mats = code["B_mats"]  # 0: y^3 (long), 1: x (local), 2: x^2 (local)

    for term_idx, M in enumerate(A_mats):
        rs, cs = np.nonzero(M)
        target_list = layer2_edges if term_idx == 0 else layer1_edges
        for r, c in zip(rs, cs):
            target_list.append((2 * nh + int(r), int(c)))          # X - L
            target_list.append((3 * nh + int(c), nh + int(r)))     # Z - R (A^T)

    for term_idx, M in enumerate(B_mats):
        rs, cs = np.nonzero(M)
        target_list = layer2_edges if term_idx == 0 else layer1_edges
        for r, c in zip(rs, cs):
            target_list.append((2 * nh + int(r), nh + int(c)))     # X - R
            target_list.append((3 * nh + int(c), int(r)))          # Z - L (B^T)

    # Compute folded Euclidean lengths (in grid pitch units) and exact Manhattan lengths
    def _edge_stats(edges: List[Tuple[int, int]]) -> Tuple[np.ndarray, np.ndarray]:
        eucl = []
        manh = []
        for u, v in edges:
            xu, yu = coords_folded[u]
            xv, yv = coords_folded[v]
            eucl.append(math.hypot(xu - xv, yu - yv))
            manh.append(abs(xu - xv) + abs(yu - yv))
        return np.array(eucl, dtype=np.float64), np.array(manh, dtype=np.float64)

    e1_grid, m1_grid = _edge_stats(layer1_edges)
    e2_grid, m2_grid = _edge_stats(layer2_edges)
    all_e_grid = np.concatenate([e1_grid, e2_grid])

    # Count exact 2D segment crossings inside Layer 1 vs Layer 2 on the flat folded chip
    # (for airbridge / superconducting crossover via budget!)
    def _count_proper_crossings(edges: List[Tuple[int, int]]) -> int:
        segs = [(coords_folded[u], coords_folded[v], u, v) for u, v in edges]
        cnt = 0
        for i in range(len(segs)):
            (x1, y1), (x2, y2), u1, v1 = segs[i]
            b1x0, b1x1 = (x1, x2) if x1 < x2 else (x2, x1)
            b1y0, b1y1 = (y1, y2) if y1 < y2 else (y2, y1)
            for j in range(i + 1, len(segs)):
                (x3, y3), (x4, y4), u2, v2 = segs[j]
                if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                    continue
                if max(x3, x4) < b1x0 or min(x3, x4) > b1x1 or max(y3, y4) < b1y0 or min(y3, y4) > b1y1:
                    continue
                # Standard CCW orientation test
                d1 = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
                d2 = (x4 - x3) * (y2 - y3) - (y4 - y3) * (x2 - x3)
                d3 = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
                d4 = (x2 - x1) * (y4 - y1) - (y2 - y1) * (x4 - x1)
                if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
                    cnt += 1
        return cnt

    # On the periodic torus, Layer 1 (degree-4 planar grid) has 0 crossings;
    # on a flat 2D folded chip, report exact planar folded crossings cleanly!
    xings_layer1_flat = _count_proper_crossings(layer1_edges)
    xings_layer2_flat = _count_proper_crossings(layer2_edges)

    pitch_sweep: List[Dict[str, Any]] = []
    for pitch in pitches_um:
        L_l1_max = float(np.max(e1_grid) * pitch)
        L_l2_max = float(np.max(e2_grid) * pitch)
        L_max = float(np.max(all_e_grid) * pitch)
        L_med_l2 = float(np.median(e2_grid) * pitch)
        # If L_max <= 300 um, resonator simply meanders to exact 300 um -> f_r = 5.00 GHz (0 shift!).
        # If L_max > 300 um at fixed L_sq=100 pH/sq, fundamental f_r = 5.0 * (300 / L_max) GHz,
        # OR adjusting NbTiN L_sq = 100 * (300 / L_max)^2 restores f_r = 5.00 GHz exactly!
        f_r_fixed_lsq = f_r_nominal_ghz if L_max <= l_res_nominal_um else f_r_nominal_ghz * (l_res_nominal_um / L_max)
        L_sq_needed_pH = 100.0 if L_max <= l_res_nominal_um else 100.0 * ((l_res_nominal_um / L_max) ** 2)
        pitch_sweep.append({
            "pitch_um": pitch,
            "block_size_um": [round(24.0 * pitch, 1), round(12.0 * pitch, 1)],
            "block_area_mm2": round((24.0 * pitch * 12.0 * pitch) / 1e6, 4),
            "layer1_max_eucl_um": round(L_l1_max, 1),
            "layer2_median_eucl_um": round(L_med_l2, 1),
            "layer2_max_eucl_um": round(L_l2_max, 1),
            "L_max_um": round(L_max, 1),
            "fits_300um_m4_resonator": bool(L_max <= l_res_nominal_um),
            "fits_500um_extended_m4": bool(L_max <= 500.0),
            "f_r_fixed_100pH_ghz": round(f_r_fixed_lsq, 3),
            "delta_f_r_fixed_100pH_ghz": round(f_r_fixed_lsq - f_r_nominal_ghz, 3),
            "L_sq_pH_for_5GHz": round(L_sq_needed_pH, 1),
        })

    return {
        "code_name": code["name"],
        "grid_shape": [24, 12],
        "n_qubits": 288,
        "n_edges_total": len(layer1_edges) + len(layer2_edges),
        "n_edges_layer1_local": len(layer1_edges),
        "n_edges_layer2_long_range": len(layer2_edges),
        "torus_thickness": 2,
        "layer1_torus_crossings": 0,
        "flat_folded_layer1_airbridges": xings_layer1_flat,
        "flat_folded_layer2_airbridges": xings_layer2_flat,
        "pitch_sweep": pitch_sweep,
        "coords_folded": coords_folded,
        "qubit_types": qubit_types,
        "layer1_edges": layer1_edges,
        "layer2_edges": layer2_edges,
    }


def compute_defective_block_yields(
    n_cells_block: int = 288,
    n_blocks_cryo: int = 10,
) -> Dict[str, Any]:
    """Compute exact defect-free 288-cell Gross Code block yield and full 10-block (120L)
    single-cryostat wafer yield across Exp136/138/139 fabrication regimes.

    Anchors (results/exp138_defective_surface_code_ft/summary_exp138.md):
      - f=1.0%, E_z=0:          p_slot = 0.5275 * 0.9770 * (1 - 0.002008) = 0.51433
      - f*=1.5% + 2 MV/m Stark: p_slot = 0.7750 * 0.9770 * (1 - 0.002008) = 0.75565
    """
    regimes = {
        "f1p0_Ez0_baseline": 0.5275 * 0.9770 * (1.0 - 0.002008),
        "f1p5_Ez2MVm_v5_star": 0.7750 * 0.9770 * (1.0 - 0.002008),
    }
    out: Dict[str, Any] = {}
    for rname, p_slot in regimes.items():
        rows = []
        for n_cand in (4, 5, 6, 7, 8, 9, 10):
            p_drop = (1.0 - p_slot) ** n_cand
            y_block = (1.0 - p_drop) ** n_cells_block
            y_10blocks = y_block ** n_blocks_cryo
            rows.append({
                "N_cand": n_cand,
                "p_drop": float(p_drop),
                "p_drop_pct": round(p_drop * 100.0, 5),
                "block_288_yield": round(y_block, 6),
                "block_288_yield_pct": round(y_block * 100.0, 3),
                "cryo_10block_120L_yield_pct": round(y_10blocks * 100.0, 3),
                "total_phys_candidates_per_block": n_cells_block * n_cand,
                "phys_candidates_per_logical": round((n_cells_block * n_cand) / 12.0, 2),
            })
        out[rname] = {"p_slot": round(p_slot, 5), "by_N_cand": rows}
    return out


if __name__ == "__main__":
    print("=== Exp144 Module 1 Verification: BB Algebra, Schedules, Thickness-2 Layout ===")
    for key, spec in BB_CODE_SPECS.items():
        c = build_bb_code(spec)
        sched = find_verified_commuting_schedule(c)
        print(
            f"  {c['name']:16s}: n={c['n_data']:3d}, k={c['k']:2d}, rankX={c['rank_X']}, rankZ={c['rank_Z']}, "
            f"comm={c['commutativity_H_X_H_ZT_zero']}, wt6={c['all_row_col_weight_6']}, "
            f"sched_depth={sched['depth_cnot_layers']} (zero_kickback={sched['zero_kickback_verified']}, CNOTs={sched['total_cnots_per_round']})"
        )
        if key == "BB_144_12_12":
            lay = build_thickness2_m4_layout(c)
            print(f"  Layout [[144,12,12]]: L1={lay['n_edges_layer1_local']} edges, L2={lay['n_edges_layer2_long_range']} edges, flat airbridges L1={lay['flat_folded_layer1_airbridges']}, L2={lay['flat_folded_layer2_airbridges']}")
            for ps in lay["pitch_sweep"]:
                print(f"    pitch={ps['pitch_um']:4.0f}um: size={ps['block_size_um']}um, L_max={ps['L_max_um']:5.1f}um, fits_300um={ps['fits_300um_m4_resonator']}, f_r={ps['f_r_fixed_100pH_ghz']} GHz, L_sq_5G={ps['L_sq_pH_for_5GHz']} pH/sq")
    dy = compute_defective_block_yields()
    for rn, rv in dy.items():
        print(f"  Defect yield [{rn}] (p_slot={rv['p_slot']}):")
        for r in rv["by_N_cand"]:
            if r["N_cand"] in (6, 7, 8):
                print(f"    N_cand={r['N_cand']}: p_drop={r['p_drop_pct']:.4f}%, Y_288={r['block_288_yield_pct']:.2f}%, Y_10blk={r['cryo_10block_120L_yield_pct']:.2f}%")
