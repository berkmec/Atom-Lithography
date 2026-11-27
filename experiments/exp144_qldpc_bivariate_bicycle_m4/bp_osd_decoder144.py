"""Exp144 Module 2: Pure-NumPy Vectorized Normalized Min-Sum Belief Propagation +
Bit-Packed GF(2) Gauss-Jordan OSD-0 / OSD-2 Decoder, plus Exact 3D Space-Time
Circuit-Level Detector Error Model (DEM) Builder for Bravyi Depth-7 BB Schedules.

Zero external QEC packages required (pure NumPy/SciPy).
Epistemic scope: {Model} / {Sayisal-Simulasyon}. no_lab_measurement=True.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.sparse import csr_matrix

try:
    from .bb_codes_and_layout144 import (
        BB_CODE_SPECS,
        build_bb_code,
        find_verified_commuting_schedule,
    )
except ImportError:
    from bb_codes_and_layout144 import (
        BB_CODE_SPECS,
        build_bb_code,
        find_verified_commuting_schedule,
    )


# =============================================================================
# 1. Pure-NumPy Vectorized Normalized Min-Sum BP + Bit-Packed GF(2) OSD-0/OSD-2
# =============================================================================
class BPOSDDecoder:
    """Fast pure-NumPy Normalized Min-Sum BP + bit-packed GF(2) OSD-0/OSD-2 decoder.

    Solves H @ e == s (mod 2) minimizing sum_j e_j * log((1 - p_j) / p_j).
    """

    def __init__(
        self,
        H: np.ndarray,
        priors: np.ndarray,
        bp_max_iter: int = 35,
        ms_alpha: float = 0.625,
        osd_order: int = 2,
        osd_lambda: int = 28,
    ) -> None:
        self.H = (np.asarray(H, dtype=np.uint8) & 1).copy()
        self.M, self.N = self.H.shape
        self.priors = np.clip(np.asarray(priors, dtype=np.float64), 1e-12, 0.499999)
        self.llr = np.log((1.0 - self.priors) / self.priors)
        self.bp_max_iter = bp_max_iter
        self.ms_alpha = ms_alpha
        self.osd_order = osd_order
        self.osd_lambda = osd_lambda

        # Sparse CSR representation for fast syndrome checks
        self.H_csr = csr_matrix(self.H)

        # Build edge list & padded (M, d_c_max) / (N, d_v_max) tables for vectorized BP
        rows, cols = np.nonzero(self.H)
        self.n_edges = int(rows.size)
        self.edge_c = rows.astype(np.int32)
        self.edge_v = cols.astype(np.int32)

        row_counts = np.bincount(rows, minlength=self.M)
        col_counts = np.bincount(cols, minlength=self.N)
        self.dc_max = int(np.max(row_counts)) if self.M > 0 else 1
        self.dv_max = int(np.max(col_counts)) if self.N > 0 else 1

        # Padded tables pointing to edge indices (sentinel = n_edges)
        self.c_edges = np.full((self.M, self.dc_max), self.n_edges, dtype=np.int32)
        self.c_mask = np.zeros((self.M, self.dc_max), dtype=bool)
        c_pos = np.zeros(self.M, dtype=np.int32)
        for e_id, c in enumerate(rows):
            k = c_pos[c]
            self.c_edges[c, k] = e_id
            self.c_mask[c, k] = True
            c_pos[c] = k + 1

        self.v_edges = np.full((self.N, self.dv_max), self.n_edges, dtype=np.int32)
        self.v_mask = np.zeros((self.N, self.dv_max), dtype=bool)
        v_pos = np.zeros(self.N, dtype=np.int32)
        for e_id, v in enumerate(cols):
            k = v_pos[v]
            self.v_edges[v, k] = e_id
            self.v_mask[v, k] = True
            v_pos[v] = k + 1

        # Precompute bit-packed column representation of H for ultra-fast GF(2) OSD elimination
        # Each column j of H (length M) packed into n_words uint64 integers
        self.n_words = (self.M + 63) // 64
        self.H_col_bits = np.zeros((self.N, self.n_words), dtype=np.uint64)
        for j in range(self.N):
            r_nz = np.flatnonzero(self.H[:, j])
            for r in r_nz:
                self.H_col_bits[j, r >> 6] |= np.uint64(1) << np.uint64(r & 63)

        # Precompute bit positions (word, bit) for rows 0..M-1
        self._row_words = np.arange(self.M, dtype=np.int32) >> 6
        self._row_masks = (np.uint64(1) << (np.arange(self.M, dtype=np.uint64) & np.uint64(63)))

    def bp_decode_batch(self, syndromes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run batched Normalized Min-Sum BP on syndromes (shape B x M).

        Returns (e_hat [B, N], converged [B], posterior_llr [B, N]).
        """
        S = (np.asarray(syndromes, dtype=np.uint8) & 1)
        B = S.shape[0]
        e_hat = np.zeros((B, self.N), dtype=np.uint8)
        L_post = np.broadcast_to(self.llr[None, :], (B, self.N)).copy()

        # Trivial zero-syndrome shots converge immediately in 0 iterations!
        nz_s = np.any(S != 0, axis=1)
        converged = ~nz_s
        if not np.any(nz_s):
            return e_hat, converged, L_post

        # Only run BP on active (non-zero syndrome) shots
        act_idx = np.flatnonzero(nz_s)
        Ba = act_idx.size
        S_act = S[act_idx]  # (Ba, M)
        s_sign = np.where(S_act == 1, -1.0, 1.0)  # (Ba, M)

        # Edge messages padded by 1 sentinel slot at index n_edges
        q_msg = np.zeros((Ba, self.n_edges + 1), dtype=np.float64)
        q_msg[:, : self.n_edges] = self.llr[self.edge_v][None, :]
        m_msg = np.zeros((Ba, self.n_edges + 1), dtype=np.float64)

        active = np.ones(Ba, dtype=bool)
        L_act = np.broadcast_to(self.llr[None, :], (Ba, self.N)).copy()
        e_act = np.zeros((Ba, self.N), dtype=np.uint8)

        c_edges = self.c_edges
        c_mask = self.c_mask
        v_edges = self.v_edges
        edge_c = self.edge_c
        edge_v = self.edge_v
        alpha = self.ms_alpha
        H_csr = self.H_csr

        for _ in range(self.bp_max_iter):
            a_loc = np.flatnonzero(active)
            if a_loc.size == 0:
                break

            # 1. Check-to-variable normalized min-sum update (vectorized over active batch & all checks)
            # q_c: (B_cur, M, dc_max)
            q_c = q_msg[a_loc][:, c_edges]
            abs_q = np.abs(q_c)
            abs_q[:, ~c_mask] = 1e9  # sentinel ignored in min
            # Two smallest magnitudes per check
            idx_min1 = np.argmin(abs_q, axis=2)  # (B_cur, M)
            b_ar = np.arange(a_loc.size)[:, None]
            m_ar = np.arange(self.M)[None, :]
            min1 = abs_q[b_ar, m_ar, idx_min1]
            abs_q_copy = abs_q.copy()
            abs_q_copy[b_ar, m_ar, idx_min1] = 1e9
            min2 = np.min(abs_q_copy, axis=2)

            # Sign product per check
            sgn_q = np.where(q_c < 0.0, -1.0, 1.0)
            sgn_q[:, ~c_mask] = 1.0
            tot_sgn = s_sign[a_loc] * np.prod(sgn_q, axis=2)  # (B_cur, M)

            # Message magnitude = min2 at idx_min1, else min1
            mag_out = np.broadcast_to(min1[:, :, None], q_c.shape).copy()
            mag_out[b_ar, m_ar, idx_min1] = min2
            out_c = alpha * (tot_sgn[:, :, None] * sgn_q) * mag_out

            # Scatter back to edge array m_msg
            m_cur = np.zeros((a_loc.size, self.n_edges + 1), dtype=np.float64)
            m_cur[:, c_edges[c_mask]] = out_c[:, c_mask]
            m_msg[a_loc] = m_cur

            # 2. Variable-to-check update & posterior LLR
            sum_m = np.sum(m_cur[:, v_edges], axis=2)  # sentinel slot is 0.0
            L_cur = self.llr[None, :] + sum_m
            L_act[a_loc] = L_cur

            hard = (L_cur < 0.0).astype(np.uint8)
            e_act[a_loc] = hard

            # Check syndrome convergence: (hard @ H^T) % 2 == S_act
            syn_chk = (hard @ H_csr.T) & 1
            ok = np.all(syn_chk == S_act[a_loc], axis=1)
            if np.any(ok):
                done_loc = a_loc[ok]
                active[done_loc] = False
                if not np.any(active):
                    break

            # Prepare next q_msg for still-active shots
            still_mask = ~ok
            if np.any(still_mask):
                s_loc = a_loc[still_mask]
                q_next = np.clip(L_cur[still_mask][:, edge_v] - m_cur[still_mask, : self.n_edges], -40.0, 40.0)
                q_msg[s_loc, : self.n_edges] = q_next

        e_hat[act_idx] = e_act
        L_post[act_idx] = L_act
        converged[act_idx] = ~active
        return e_hat, converged, L_post

    def osd_decode_single(self, syndrome: np.ndarray, post_llr: np.ndarray, order: int | None = None) -> np.ndarray:
        """Exact GF(2) Gauss-Jordan OSD-0 / OSD-2 combination sweep on one non-convergent shot."""
        ord_use = self.osd_order if order is None else order
        s = (np.asarray(syndrome, dtype=np.uint8) & 1)
        if not np.any(s):
            return np.zeros(self.N, dtype=np.uint8)

        # Sort variables by ascending posterior LLR (most likely error bits first!)
        col_order = np.argsort(post_llr, kind="mergesort")

        M = self.M

        def _solve_prefix(K: int) -> Tuple[bool, np.ndarray, List[int], List[int], int]:
            H_ord = self.H[:, col_order[:K]]  # (M, K)
            n_w = (K + 1 + 63) // 64
            aug_bits = np.zeros((M, n_w * 64), dtype=np.uint8)
            aug_bits[:, :K] = H_ord
            aug_bits[:, K] = s
            packed_bytes = np.packbits(aug_bits, axis=1, bitorder="little")
            mat = packed_bytes.view(np.uint64).copy()

            piv_cols: List[int] = []
            non_piv: List[int] = []
            row = 0
            for j in range(K):
                if row >= M:
                    non_piv.append(j)
                    if len(non_piv) >= self.osd_lambda:
                        break
                    continue
                w_idx = j >> 6
                bit_mask = np.uint64(1) << np.uint64(j & 63)
                col_vals = mat[row:, w_idx] & bit_mask
                nz = np.flatnonzero(col_vals)
                if nz.size == 0:
                    non_piv.append(j)
                    continue
                piv_r = row + int(nz[0])
                if piv_r != row:
                    mat[[row, piv_r]] = mat[[piv_r, row]]
                elim_mask = (mat[:, w_idx] & bit_mask) != 0
                elim_mask[row] = False
                if np.any(elim_mask):
                    mat[elim_mask] ^= mat[row]
                piv_cols.append(j)
                row += 1

            s_w = K >> 6
            s_bit = np.uint64(1) << np.uint64(K & 63)
            consistent = not np.any((mat[row:, s_w] & s_bit) != 0)
            enough_t = (len(non_piv) >= self.osd_lambda) or (K == self.N)
            return bool(consistent and enough_t), mat, piv_cols, non_piv, row

        # Exact prefix Gauss-Jordan: bit-for-bit identical to full width whenever consistent & >= osd_lambda non-pivots
        K_fast = min(self.N, M + max(256, 4 * self.osd_lambda))
        ok_fast, mat, piv_cols_ord, non_piv_ord, rank = _solve_prefix(K_fast)
        K_used = K_fast
        if not ok_fast and K_fast < self.N:
            _, mat, piv_cols_ord, non_piv_ord, rank = _solve_prefix(self.N)
            K_used = self.N

        # Extract OSD-0 solution on pivot columns (from column K_used of mat[:rank])
        s_w = K_used >> 6
        s_bit = np.uint64(1) << np.uint64(K_used & 63)
        e_S0 = ((mat[:rank, s_w] & s_bit) != 0).astype(np.uint8)

        piv_orig = col_order[piv_cols_ord]
        llr_S = self.llr[piv_orig]
        best_cost = float(np.dot(e_S0, llr_S))
        best_e_S = e_S0
        best_T_flips: Tuple[int, ...] = ()

        if ord_use >= 1 and len(non_piv_ord) > 0:
            lam = min(self.osd_lambda, len(non_piv_ord))
            t_ord_cols = non_piv_ord[:lam]
            t_orig = col_order[t_ord_cols]
            llr_T = self.llr[t_orig]

            # Extract reduced H_S^{-1} H_{T_top} (shape lam x rank)
            T_vecs = np.zeros((lam, rank), dtype=np.uint8)
            for k_t, j_col in enumerate(t_ord_cols):
                w_idx = j_col >> 6
                b_mask = np.uint64(1) << np.uint64(j_col & 63)
                T_vecs[k_t] = ((mat[:rank, w_idx] & b_mask) != 0).astype(np.uint8)

            # Weight-1 sweep (vectorized over all lam candidates)
            cand1 = e_S0[None, :] ^ T_vecs  # (lam, rank)
            costs1 = cand1 @ llr_S + llr_T
            idx1 = int(np.argmin(costs1))
            if float(costs1[idx1]) < best_cost:
                best_cost = float(costs1[idx1])
                best_e_S = cand1[idx1].copy()
                best_T_flips = (int(t_orig[idx1]),)

            # Weight-2 combination sweep (OSD-2, vectorized over all lam*(lam-1)/2 pairs)
            if ord_use >= 2 and lam >= 2:
                iu, iv = np.triu_indices(lam, k=1)
                cand2 = e_S0[None, :] ^ T_vecs[iu] ^ T_vecs[iv]  # (n_pairs, rank)
                costs2 = cand2 @ llr_S + llr_T[iu] + llr_T[iv]
                idx2 = int(np.argmin(costs2))
                if float(costs2[idx2]) < best_cost:
                    best_cost = float(costs2[idx2])
                    best_e_S = cand2[idx2].copy()
                    best_T_flips = (int(t_orig[iu[idx2]]), int(t_orig[iv[idx2]]))

        e_out = np.zeros(self.N, dtype=np.uint8)
        e_out[piv_orig] = best_e_S
        for tf in best_T_flips:
            e_out[tf] = 1
        return e_out

    def decode_batch(self, syndromes: np.ndarray, use_osd: bool = True, osd_order: int | None = None) -> Dict[str, Any]:
        """Decode batch of syndromes with Min-Sum BP (+ OSD fallback when use_osd=True)."""
        e_hat, conv, L_post = self.bp_decode_batch(syndromes)
        n_osd = 0
        if use_osd:
            fail_idx = np.flatnonzero(~conv)
            n_osd = int(fail_idx.size)
            for idx in fail_idx:
                e_hat[idx] = self.osd_decode_single(syndromes[idx], L_post[idx], order=osd_order)
        return {
            "e_hat": e_hat,
            "bp_converged_mask": conv,
            "bp_converged_frac": float(np.mean(conv)),
            "n_osd_triggered": n_osd,
        }


# =============================================================================
# 2. Exact 3D Space-Time Circuit-Level Detector Error Model (DEM) for BB Codes
# =============================================================================
def build_bb_circuit_dem(
    code: Dict[str, Any],
    schedule: Dict[str, Any],
    n_noisy_rounds: int,
    p_2q: float,
    p_meas: float,
    p_1q_idle_step: float,
    p_prep: float = 0.0,
    p_data_ro_idle: float = 0.0,
    memory_basis: str = "Z",
    p2q_pauli_weights: Dict[str, float] | None = None,
    include_boundary_noise: bool = True,
    p_1q_hadamard: float = 0.0,
) -> Dict[str, Any]:
    """Build exact 3D space-time Circuit-Level Detector Error Model (H_dem, L_dem, p_fault)
    from the verified depth-7 zero-kickback Bravyi CNOT schedule.

    memory_basis = 'Z': tracks all X/Y faults detected by Z-checks across (n_noisy_rounds + 1)
                        detector rounds and evaluates logical Z observable flips L_Z.
    memory_basis = 'X': tracks all Z/Y faults detected by X-checks across (n_noisy_rounds + 1)
                        detector rounds and evaluates logical X observable flips L_X.

    Faithfully implements Bravyi et al. (Nature 2024) circuit-level noise:
      - 2-qubit CNOT Pauli faults (15 non-trivial 2Q Paulis, uniform or Exp137-weighted),
      - 1-qubit idle faults on inactive qubits during each of the 7 CNOT layers,
      - 1-qubit data-qubit idle faults during the ancilla readout & reset window,
      - ancilla preparation (p_prep) + measurement (p_meas) flips each round,
      - noisy initial data prep (r=0) and final transversal data readout (r=R) when include_boundary_noise=True.
    """
    nh = code["n_checks_X"]
    n_data = code["n_data"]
    n_qubits = 4 * nh  # [0..nh-1: L], [nh..2nh-1: R], [2nh..3nh-1: X_chk], [3nh..4nh-1: Z_chk]
    step_cnots: List[List[Tuple[int, int]]] = schedule["step_cnots"]
    n_steps = len(step_cnots)

    H_check = code["H_Z"] if memory_basis == "Z" else code["H_X"]
    L_obs = code["L_Z"] if memory_basis == "Z" else code["L_X"]
    anc_offset = 3 * nh if memory_basis == "Z" else 2 * nh
    k_log = code["k"]
    n_det_rounds = n_noisy_rounds + 1
    M_det = n_det_rounds * nh

    def _propagate_to_round_end(init_qubits: List[int], after_step: int) -> Tuple[np.ndarray, np.ndarray]:
        err = np.zeros(n_qubits, dtype=np.uint8)
        for q in init_qubits:
            err[q] ^= 1
        for st_rem in range(after_step + 1, n_steps):
            for ctrl, tgt in step_cnots[st_rem]:
                if memory_basis == "Z":
                    if err[ctrl]:
                        err[tgt] ^= 1
                else:
                    if err[tgt]:
                        err[ctrl] ^= 1
        data_err = err[:n_data].copy()
        anc_err = err[anc_offset : anc_offset + nh].copy()
        return data_err, anc_err

    if p2q_pauli_weights is None:
        p_c_only = (4.0 / 15.0) * p_2q
        p_t_only = (4.0 / 15.0) * p_2q
        p_both = (4.0 / 15.0) * p_2q
    else:
        # Note: CNOT = (I x H) CZ (I x H), so post-CZ Pauli P_c x P_t becomes P_c x (H P_t H)
        # where H X H = Z, H Z H = X, H Y H = -Y.
        # The 3 disjoint 4-element sets plus the 3 untouched Paulis partition all 15 non-trivial Paulis!
        if memory_basis == "Z":
            # Need output X-component: P_c in {X,Y}, P_t in {Z,Y} (disjoint partition of 12 Paulis)
            w_c = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("XI", "XX", "YI", "YX"))
            w_t = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("IZ", "ZZ", "IY", "ZY"))
            w_b = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("XZ", "XY", "YZ", "YY"))
        else:
            # Need output Z-component: P_c in {Z,Y}, P_t in {X,Y} (disjoint partition of 12 Paulis)
            w_c = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("ZI", "ZZ", "YI", "YZ"))
            w_t = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("IX", "XX", "IY", "XY"))
            w_b = sum(p2q_pauli_weights.get(lbl, 0.0) for lbl in ("ZX", "ZY", "YX", "YY"))
        tot_pauli_weight = sum(v for k, v in p2q_pauli_weights.items() if k != "II")
        scale = p_2q / max(tot_pauli_weight, 1e-15)
        p_c_only = w_c * scale
        p_t_only = w_t * scale
        p_both = w_b * scale

    single_round_faults: Dict[Tuple[bytes, bytes, bytes], float] = {}

    def _add_sr_fault(data_err: np.ndarray, anc_err: np.ndarray, prob: float) -> None:
        if prob <= 1e-15:
            return
        syn_next = (H_check @ data_err) & 1
        d_r = anc_err
        d_r1 = anc_err ^ syn_next
        log_fl = (L_obs @ data_err) & 1
        if not (np.any(d_r) or np.any(d_r1) or np.any(log_fl)):
            return
        key = (d_r.tobytes(), d_r1.tobytes(), log_fl.tobytes())
        p_old = single_round_faults.get(key, 0.0)
        single_round_faults[key] = p_old * (1.0 - prob) + (1.0 - p_old) * prob

    # 1a. CNOT gate faults, mid-cycle Hadamard CZ->CNOT conversion faults (OBS-106), & per-step idle faults
    p_h_flip = (2.0 / 3.0) * p_1q_hadamard
    for st, pairs in enumerate(step_cnots):
        active_q = set()
        for ctrl, tgt in pairs:
            active_q.add(ctrl)
            active_q.add(tgt)
            # OBS-106 FIX: Native M4 CZ -> CNOT requires H before and after CZ on the target qubit
            # (for X-check CNOTs, target `tgt` is a data qubit < n_data; each H injects (2/3)*p_1q flip!)
            if p_h_flip > 1e-15 and tgt < n_data:
                # Pre-CZ Hadamard error (propagates through step `st` CNOT via after_step=st-1)
                d_h_pre, a_h_pre = _propagate_to_round_end([tgt], st - 1)
                _add_sr_fault(d_h_pre, a_h_pre, p_h_flip)
                # Post-CZ Hadamard error (after step `st`)
                d_h_post, a_h_post = _propagate_to_round_end([tgt], st)
                _add_sr_fault(d_h_post, a_h_post, p_h_flip)
            d_c, a_c = _propagate_to_round_end([ctrl], st)
            _add_sr_fault(d_c, a_c, p_c_only)
            d_t, a_t = _propagate_to_round_end([tgt], st)
            _add_sr_fault(d_t, a_t, p_t_only)
            d_b, a_b = _propagate_to_round_end([ctrl, tgt], st)
            _add_sr_fault(d_b, a_b, p_both)
        if p_1q_idle_step > 1e-15:
            for q in range(n_qubits):
                if q not in active_q:
                    d_i, a_i = _propagate_to_round_end([q], st)
                    _add_sr_fault(d_i, a_i, p_1q_idle_step)

    # 1b. Data-qubit idle faults during ancilla readout & reset window at end of round r
    # (occurs after all CNOTs of round r -> leaves anc_err=0, persists into round r+1 -> flips D(r+1)!)
    if p_data_ro_idle > 1e-15:
        zero_anc = np.zeros(nh, dtype=np.uint8)
        for q_d in range(n_data):
            dv = np.zeros(n_data, dtype=np.uint8)
            dv[q_d] = 1
            _add_sr_fault(dv, zero_anc, p_data_ro_idle)

    # 1c. Ancilla prep (before step 0; commutes with checked ancilla role) + measurement flip
    p_anc_eff = p_meas * (1.0 - p_prep) + (1.0 - p_meas) * p_prep
    if p_anc_eff > 1e-15:
        zero_data = np.zeros(n_data, dtype=np.uint8)
        for a_i in range(nh):
            anc_v = np.zeros(nh, dtype=np.uint8)
            anc_v[a_i] = 1
            _add_sr_fault(zero_data, anc_v, p_anc_eff)

    # Step 2: Tile the single-round fault catalog across rounds r = 0 .. n_noisy_rounds - 1
    dem_cols: Dict[Tuple[bytes, bytes], float] = {}

    def _add_dem_col(det_vec: np.ndarray, log_b: bytes, prob: float) -> None:
        if prob <= 1e-15 or not np.any(det_vec):
            return
        d_key = (det_vec.tobytes(), log_b)
        p_old = dem_cols.get(d_key, 0.0)
        dem_cols[d_key] = p_old * (1.0 - prob) + (1.0 - p_old) * prob

    for (dr_b, dr1_b, log_b), prob in single_round_faults.items():
        dr = np.frombuffer(dr_b, dtype=np.uint8)
        dr1 = np.frombuffer(dr1_b, dtype=np.uint8)
        for r in range(n_noisy_rounds):
            det_vec = np.zeros(M_det, dtype=np.uint8)
            det_vec[r * nh : (r + 1) * nh] = dr
            det_vec[(r + 1) * nh : (r + 2) * nh] = dr1
            _add_dem_col(det_vec, log_b, prob)

    # Step 3: Boundary noise (initial data-qubit prep before r=0 -> flips D(0) & L;
    # final transversal data readout after r=R-1 -> flips D(R) & L)
    if include_boundary_noise:
        if p_prep > 1e-15:
            for q_d in range(n_data):
                det_vec = np.zeros(M_det, dtype=np.uint8)
                det_vec[0:nh] = H_check[:, q_d]
                log_b = L_obs[:, q_d].astype(np.uint8).tobytes()
                _add_dem_col(det_vec, log_b, p_prep)
        if p_meas > 1e-15:
            for q_d in range(n_data):
                det_vec = np.zeros(M_det, dtype=np.uint8)
                det_vec[n_noisy_rounds * nh : (n_noisy_rounds + 1) * nh] = H_check[:, q_d]
                log_b = L_obs[:, q_d].astype(np.uint8).tobytes()
                _add_dem_col(det_vec, log_b, p_meas)

    n_faults = len(dem_cols)
    H_dem = np.zeros((M_det, n_faults), dtype=np.uint8)
    L_dem = np.zeros((k_log, n_faults), dtype=np.uint8)
    p_dem = np.zeros(n_faults, dtype=np.float64)

    for j, ((det_b, log_b), prob) in enumerate(dem_cols.items()):
        H_dem[:, j] = np.frombuffer(det_b, dtype=np.uint8)
        L_dem[:, j] = np.frombuffer(log_b, dtype=np.uint8)
        p_dem[j] = prob

    return {
        "memory_basis": memory_basis,
        "n_noisy_rounds": n_noisy_rounds,
        "M_detectors": M_det,
        "N_fault_mechanisms": n_faults,
        "H_dem": H_dem,
        "L_dem": L_dem,
        "p_dem": p_dem,
    }


def run_dem_monte_carlo(
    dem: Dict[str, Any],
    n_shots: int,
    seed: int,
    osd_order: int = 2,
    osd_lambda: int = 28,
    use_osd: bool = True,
    batch_size: int = 500,
    bp_max_iter: int = 50,
    ms_alpha: float = 0.625,
) -> Dict[str, Any]:
    """Run Monte Carlo fault sampling on a DEM and decode with BPOSDDecoder."""
    rng = np.random.default_rng(seed)
    H_dem = dem["H_dem"]
    L_dem = dem["L_dem"]
    p_dem = dem["p_dem"]
    n_rounds = dem["n_noisy_rounds"]
    dec = BPOSDDecoder(
        H_dem, p_dem, bp_max_iter=bp_max_iter, ms_alpha=ms_alpha, osd_order=osd_order, osd_lambda=osd_lambda
    )

    n_log_err = 0
    n_bp_conv = 0
    n_osd_trig = 0
    n_syndrome_valid = 0
    H_csr = dec.H_csr

    rem = n_shots
    while rem > 0:
        b = min(batch_size, rem)
        rem -= b
        faults = (rng.random((b, p_dem.size)) < p_dem[None, :]).astype(np.uint8)
        syndromes = (faults @ H_csr.T) & 1
        true_log = (faults @ L_dem.T) & 1

        res = dec.decode_batch(syndromes, use_osd=use_osd, osd_order=osd_order)
        e_hat = res["e_hat"]
        pred_log = (e_hat @ L_dem.T) & 1
        syn_check = (e_hat @ H_csr.T) & 1
        n_syndrome_valid += int(np.sum(np.all(syn_check == syndromes, axis=1)))
        n_bp_conv += int(np.sum(res["bp_converged_mask"]))
        n_osd_trig += int(res["n_osd_triggered"])
        # Logical block error: ANY of the k logical qubits flipped OR invalid syndrome
        shot_fail = np.any(pred_log != true_log, axis=1) | np.any(syn_check != syndromes, axis=1)
        n_log_err += int(np.sum(shot_fail))

    p_block = n_log_err / n_shots
    # Exact per-round logical error rate p_L,round = 1 - (1 - p_block)^(1 / R) (Bravyi 2024 Eq. 1)
    p_round = 1.0 - ((max(0.0, 1.0 - p_block)) ** (1.0 / max(n_rounds, 1)))
    # Wilson 95% confidence interval on p_block
    z95 = 1.95996
    denom = 1.0 + z95 * z95 / n_shots
    center = (p_block + z95 * z95 / (2.0 * n_shots)) / denom
    half = (z95 * math.sqrt((p_block * (1.0 - p_block) + z95 * z95 / (4.0 * n_shots)) / n_shots)) / denom
    ci_lo = max(0.0, center - half)
    ci_hi = min(1.0, center + half)

    return {
        "n_shots": n_shots,
        "n_logical_errors": n_log_err,
        "p_L_block": round(p_block, 6),
        "p_L_block_ci95": [round(ci_lo, 6), round(ci_hi, 6)],
        "p_L_round": round(p_round, 6),
        "p_L_round_per_logical": round(1.0 - (max(0.0, 1.0 - p_round)) ** (1.0 / L_dem.shape[0]), 6),
        "bp_converged_frac": round(n_bp_conv / n_shots, 5),
        "n_osd_triggered": n_osd_trig,
        "syndrome_valid_frac": round(n_syndrome_valid / n_shots, 6),
    }


if __name__ == "__main__":
    t0 = time.perf_counter()
    print("=== Quick Benchmark: Code-Capacity & Circuit-Level BP-OSD on [[144,12,12]] ===")
    c144 = build_bb_code(BB_CODE_SPECS["BB_144_12_12"])
    sched = find_verified_commuting_schedule(c144)

    # 1. Code-capacity test at p = 0.04: BP only vs BP+OSD-0 vs BP+OSD-2
    H_Z, L_Z = c144["H_Z"], c144["L_Z"]
    cc_dem = {"H_dem": H_Z, "L_dem": L_Z, "p_dem": np.full(H_Z.shape[1], 0.04), "n_noisy_rounds": 1}
    r_bp = run_dem_monte_carlo(cc_dem, 1000, seed=11, use_osd=False)
    r_osd0 = run_dem_monte_carlo(cc_dem, 1000, seed=11, use_osd=True, osd_order=0)
    r_osd2 = run_dem_monte_carlo(cc_dem, 1000, seed=11, use_osd=True, osd_order=2)
    print(f"  Code-cap p=0.04: BP-only={r_bp['p_L_block']:.4f} | BP+OSD0={r_osd0['p_L_block']:.4f} | BP+OSD2={r_osd2['p_L_block']:.4f} (bp_conv={r_osd2['bp_converged_frac']:.3f})")

    # 2. Circuit-level DEM (R=3 rounds) at p = 0.003, 0.005, 0.007, 0.0092
    for p_val in (0.003, 0.005, 0.007, 0.0092):
        dem = build_bb_circuit_dem(c144, sched, n_noisy_rounds=3, p_2q=p_val, p_meas=p_val, p_1q_idle_step=0.1 * p_val, memory_basis="Z")
        t1 = time.perf_counter()
        mc = run_dem_monte_carlo(dem, 400, seed=77, use_osd=True, osd_order=2, osd_lambda=24)
        print(f"  Circuit R=3 p={p_val*100:4.2f}% (M={dem['M_detectors']}, N_f={dem['N_fault_mechanisms']}): p_L_blk={mc['p_L_block']:.4f}, p_L_rnd={mc['p_L_round']:.5f}, bp_conv={mc['bp_converged_frac']:.3f}, syn_ok={mc['syndrome_valid_frac']:.4f}, dt={time.perf_counter()-t1:.2f}s")
    print(f"Total benchmark time: {time.perf_counter()-t0:.2f} s")
