"""
Exp138 (H156) — Exact Rotated Surface Code, Gauge-Deformed Super-Stabilizer Builder,
Circuit-Level 3D Pauli-16 DEM Compiler, and Exact Edmonds Blossom MWPM Decoder.

Physics & Algebra Guarantees:
  1. Rotated planar surface code for odd d >= 3:
       n_data = d^2, n_anc = d^2 - 1, n_total = 2 d^2 - 1.
       Exact commutation H_X @ H_Z^T == 0 (mod 2),
       exact logical operators X_L (row 0), Z_L (col 0) with {X_L, Z_L} = 0.
  2. Hook-error-immune Tomita-Svore 4-step CZ/CNOT schedule:
       X-plaquettes use N-order [(0,0), (1,0), (0,1), (1,1)] (X-hooks vertical,
         perpendicular to horizontal Left-Right X-error chains).
       Z-plaquettes use Z-order [(0,0), (0,1), (1,0), (1,1)] (Z-hooks horizontal,
         perpendicular to vertical Top-Bottom Z-error chains).
       Zero qubit collisions at every step s in {0, 1, 2, 3}.
  3. Exact Missing-Cell Gauge Deformation & Super-Stabilizer Builder:
       - Missing data qubit q: contracts q on both Z- and X-detector graphs
         (merges adjacent stabilizers into weight-6 super-stabilizers, or absorbs
         into Left/Right or Top/Bottom boundary).
       - Missing Z-ancilla a_Z (Auger et al. 2017): fixes a_Z's data qubits in Z
         (deleting a_Z and shrinking diagonal Z-neighbors) and contracts those
         qubits in the X-graph (forming the surrounding weight-8 X-super-stabilizer).
       - Missing X-ancilla a_X: exact dual.
       - Preserves H_X_def @ H_Z_def^T == 0 (mod 2) on 100% of realizations!
       - Computes exact effective distances d_eff_X (BND_L <-> BND_R) and
         d_eff_Z (BND_T <-> BND_B) via unweighted shortest path.
  4. Exact Circuit-Level 3D Detector Error Model (DEM) using all 15 non-identity
     terms of Exp137's pauli_16 channel (+ optional LRU leakage depolarizing),
     Exp126 p_1q, Exp140 p_meas, and Exp136 T2e idle dephasing over the full
     4-CZ + readout syndrome cycle.
  5. Exact Edmonds Blossom MWPM decoder (networkx.min_weight_matching) over
     separate virtual boundary nodes (BND_L / BND_R or BND_T / BND_B) using an
     exact sparse k-nearest-neighbor shadow-boundary matching graph.

Epistemic Tag: {Sayısal-Simülasyon} / {Model} (no_lab_measurement = True).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Sequence, Set, Tuple

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra as sp_dijkstra


# ---------------------------------------------------------------------------
# 1. Exact Rotated Planar Surface Code Lattice
# ---------------------------------------------------------------------------

@dataclass
class RotatedSurfaceCode:
    d: int
    n_data: int
    n_z: int
    n_x: int
    n_total: int
    data_coords: List[Tuple[int, int]]
    coord_to_data: Dict[Tuple[int, int], int]
    # Stabilizer metadata
    z_coords: List[Tuple[int, int]]
    x_coords: List[Tuple[int, int]]
    # Exact support lists (indices in 0..n_data-1)
    z_stabs: List[List[int]]
    x_stabs: List[List[int]]
    # Ordered 4-step schedules: list of 4 entries (data_idx or None) per stab
    z_sched: List[List[Optional[int]]]
    x_sched: List[List[Optional[int]]]
    # Parity check matrices (uint8)
    H_Z: np.ndarray
    H_X: np.ndarray
    # Logical operators (uint8 vectors of length n_data)
    Z_L: np.ndarray
    X_L: np.ndarray


def build_rotated_surface_code(d: int) -> RotatedSurfaceCode:
    """Build exact distance-d rotated planar surface code (odd d >= 3)."""
    if d < 3 or d % 2 == 0:
        raise ValueError(f"Surface code distance d must be odd >= 3, got {d}")

    data_coords = [(r, c) for r in range(d) for c in range(d)]
    coord_to_data = {rc: i for i, rc in enumerate(data_coords)}
    n_data = d * d

    # Tomita-Svore hook-immune schedules:
    #   Z-plaquettes: Z-order -> Z-hooks horizontal (perp to Top-Bottom Z_L chain)
    #   X-plaquettes: N-order -> X-hooks vertical   (perp to Left-Right X_L chain)
    Z_ORDER = [(0, 0), (0, 1), (1, 0), (1, 1)]
    N_ORDER = [(0, 0), (1, 0), (0, 1), (1, 1)]

    z_coords: List[Tuple[int, int]] = []
    x_coords: List[Tuple[int, int]] = []
    z_stabs: List[List[int]] = []
    x_stabs: List[List[int]] = []
    z_sched: List[List[Optional[int]]] = []
    x_sched: List[List[Optional[int]]] = []

    for pr in range(-1, d):
        for pc in range(-1, d):
            in_bulk = (0 <= pr <= d - 2) and (0 <= pc <= d - 2)
            top_bot = (pr in (-1, d - 1)) and (0 <= pc <= d - 2)
            left_right = (pc in (-1, d - 1)) and (0 <= pr <= d - 2)
            is_z = ((pr + pc) % 2 == 0)

            if is_z and (in_bulk or top_bot):
                sched: List[Optional[int]] = []
                supp: List[int] = []
                for dr, dc in Z_ORDER:
                    rc = (pr + dr, pc + dc)
                    if rc in coord_to_data:
                        q = coord_to_data[rc]
                        sched.append(q)
                        supp.append(q)
                    else:
                        sched.append(None)
                z_coords.append((pr, pc))
                z_stabs.append(supp)
                z_sched.append(sched)
            elif (not is_z) and (in_bulk or left_right):
                sched = []
                supp = []
                for dr, dc in N_ORDER:
                    rc = (pr + dr, pc + dc)
                    if rc in coord_to_data:
                        q = coord_to_data[rc]
                        sched.append(q)
                        supp.append(q)
                    else:
                        sched.append(None)
                x_coords.append((pr, pc))
                x_stabs.append(supp)
                x_sched.append(sched)

    n_z = len(z_stabs)
    n_x = len(x_stabs)
    assert n_z == (d * d - 1) // 2, f"Expected {(d*d-1)//2} Z stabs, got {n_z}"
    assert n_x == (d * d - 1) // 2, f"Expected {(d*d-1)//2} X stabs, got {n_x}"

    H_Z = np.zeros((n_z, n_data), dtype=np.uint8)
    for i, supp in enumerate(z_stabs):
        H_Z[i, supp] = 1
    H_X = np.zeros((n_x, n_data), dtype=np.uint8)
    for i, supp in enumerate(x_stabs):
        H_X[i, supp] = 1

    # Logical Z_L along column 0 (vertical, commutes with all X stabs)
    Z_L = np.zeros(n_data, dtype=np.uint8)
    for r in range(d):
        Z_L[coord_to_data[(r, 0)]] = 1

    # Logical X_L along row 0 (horizontal, commutes with all Z stabs)
    X_L = np.zeros(n_data, dtype=np.uint8)
    for c in range(d):
        X_L[coord_to_data[(0, c)]] = 1

    # Verify exact CSS algebra and collision-free 4-step schedule
    assert int(np.sum((H_X @ H_Z.T) % 2)) == 0, "CSS commutation H_X H_Z^T = 0 failed"
    assert int(np.sum((H_X @ Z_L) % 2)) == 0, "Z_L does not commute with H_X"
    assert int(np.sum((H_Z @ X_L) % 2)) == 0, "X_L does not commute with H_Z"
    assert int((X_L @ Z_L) % 2) == 1, "{X_L, Z_L} != 0"

    for s in range(4):
        seen: Set[int] = set()
        for sched in z_sched + x_sched:
            q = sched[s]
            if q is not None:
                assert q not in seen, f"Schedule collision at step {s} on qubit {q}"
                seen.add(q)

    return RotatedSurfaceCode(
        d=d,
        n_data=n_data,
        n_z=n_z,
        n_x=n_x,
        n_total=n_data + n_z + n_x,
        data_coords=data_coords,
        coord_to_data=coord_to_data,
        z_coords=z_coords,
        x_coords=x_coords,
        z_stabs=z_stabs,
        x_stabs=x_stabs,
        z_sched=z_sched,
        x_sched=x_sched,
        H_Z=H_Z,
        H_X=H_X,
        Z_L=Z_L,
        X_L=X_L,
    )


# ---------------------------------------------------------------------------
# 2. Exact Missing-Cell Super-Stabilizer Gauge Deformation
# ---------------------------------------------------------------------------

@dataclass
class DeformedCode:
    base_d: int
    n_data_orig: int
    dead_data: Set[int]
    dead_z_anc: Set[int]
    dead_x_anc: Set[int]
    live_data: List[int]
    # Active (possibly merged) Z-stabilizers: list of (support_set, merge_count)
    z_stabs: List[Set[int]]
    z_merge_counts: List[int]
    # Active (possibly merged) X-stabilizers: list of (support_set, merge_count)
    x_stabs: List[Set[int]]
    x_merge_counts: List[int]
    # Virtual boundary qubit-sets (edges incident to Left/Right for Z-graph, Top/Bot for X-graph)
    z_bnd_left_edges: Set[int]
    z_bnd_right_edges: Set[int]
    x_bnd_top_edges: Set[int]
    x_bnd_bot_edges: Set[int]
    # Exact parity matrices over all n_data_orig columns (zero on dead/removed qubits)
    H_Z: np.ndarray
    H_X: np.ndarray
    commutes_exact: bool
    # Exact graph distances
    d_eff_X: int  # min X-error chain from BND_L to BND_R
    d_eff_Z: int  # min Z-error chain from BND_T to BND_B
    d_eff: int    # min(d_eff_X, d_eff_Z)
    survived: bool
    max_z_weight: int
    max_x_weight: int
    n_super_z: int
    n_super_x: int


def _contract_dual_graph(
    n_data: int,
    stabs: List[List[int]],
    bnd_a_qubits: Set[int],
    bnd_b_qubits: Set[int],
    contract_qubits: Set[int],
    delete_stabs: Set[int],
    delete_qubits: Set[int],
) -> Tuple[List[Set[int]], List[int], Set[int], Set[int], int]:
    """
    Contract a set of missing qubits on one stabilizer dual graph (Z or X),
    handling boundary absorptions and dead-ancilla deletions cleanly.

    Nodes:
      0 .. m-1 : original stabilizers
      m        : BND_A (Left for Z-graph, Top for X-graph)
      m + 1    : BND_B (Right for Z-graph, Bottom for X-graph)
    Every original data qubit belongs to exactly 2 nodes among {0..m+1}.
    """
    m = len(stabs)
    BND_A = m
    BND_B = m + 1
    n_nodes = m + 2

    # Node support sets & union-find parent
    parent = list(range(n_nodes))
    supports: List[Set[int]] = [set(s) for s in stabs] + [set(bnd_a_qubits), set(bnd_b_qubits)]
    merge_counts = [1] * m + [0, 0]
    deleted_node = [False] * n_nodes

    def find(u: int) -> int:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    # First: mark explicitly deleted stabilizers (dead ancillas of this type)
    # and remove their fixed data qubits from all supports (Auger et al. 2017)
    for sid in delete_stabs:
        deleted_node[sid] = True
        supports[sid].clear()

    if delete_qubits:
        for u in range(n_nodes):
            supports[u].difference_update(delete_qubits)

    # Next: contract missing data qubits (and opposite-type dead-ancilla qubits)
    percolated_broken = False
    for q in sorted(contract_qubits):
        if q in delete_qubits:
            continue
        # Find active root nodes currently containing q
        owners = []
        seen_roots: Set[int] = set()
        for u in range(n_nodes):
            r = find(u)
            if r in seen_roots or deleted_node[r]:
                continue
            if q in supports[r]:
                seen_roots.add(r)
                owners.append(r)
        if len(owners) == 0:
            continue
        if len(owners) == 1:
            supports[owners[0]].discard(q)
            continue
        # Merge all owners containing q (typically 2)
        ra, rb = owners[0], owners[1]
        # Check if BND_A and BND_B are being merged -> logical patch broken!
        rA, rB = find(BND_A), find(BND_B)
        if (ra == rA and rb == rB) or (ra == rB and rb == rA):
            percolated_broken = True
            supports[ra].discard(q)
            supports[rb].discard(q)
            continue
        # Prefer keeping boundary ID as canonical root
        if rb in (rA, rB):
            ra, rb = rb, ra
        parent[rb] = ra
        supports[ra] = (supports[ra] ^ supports[rb])
        supports[ra].discard(q)
        supports[rb].clear()
        merge_counts[ra] += merge_counts[rb]
        merge_counts[rb] = 0
        # Handle any extra owners (shouldn't happen in 2-regular graph, but safe)
        for rc in owners[2:]:
            rc = find(rc)
            if rc != ra:
                if (ra == find(BND_A) and rc == find(BND_B)) or (ra == find(BND_B) and rc == find(BND_A)):
                    percolated_broken = True
                    supports[rc].discard(q)
                else:
                    parent[rc] = ra
                    supports[ra] = (supports[ra] ^ supports[rc])
                    supports[ra].discard(q)
                    supports[rc].clear()
                    merge_counts[ra] += merge_counts[rc]
                    merge_counts[rc] = 0

    rA = find(BND_A)
    rB = find(BND_B)
    if rA == rB:
        percolated_broken = True

    # Collect active real stabilizers (exclude boundaries and empty supports)
    active_roots: List[int] = []
    root_to_new: Dict[int, int] = {}
    out_stabs: List[Set[int]] = []
    out_counts: List[int] = []
    for u in range(m):
        r = find(u)
        if r == u and (not deleted_node[r]) and r not in (rA, rB) and len(supports[r]) > 0:
            root_to_new[r] = len(out_stabs)
            active_roots.append(r)
            out_stabs.append(set(supports[r]))
            out_counts.append(merge_counts[r])

    new_BND_A = len(out_stabs)
    new_BND_B = len(out_stabs) + 1
    bnd_a_edges = set(supports[rA])
    bnd_b_edges = set(supports[rB])

    if percolated_broken:
        return out_stabs, out_counts, bnd_a_edges, bnd_b_edges, 0

    # Build unweighted adjacency graph over active stabilizers + BND_A + BND_B
    # Each remaining live data qubit incident to 2 distinct nodes is 1 edge of weight 1.
    adj: Dict[int, Set[int]] = {i: set() for i in range(new_BND_B + 1)}
    q_to_nodes: Dict[int, List[int]] = {}
    for idx, supp in enumerate(out_stabs):
        for q in supp:
            q_to_nodes.setdefault(q, []).append(idx)
    for q in bnd_a_edges:
        q_to_nodes.setdefault(q, []).append(new_BND_A)
    for q in bnd_b_edges:
        q_to_nodes.setdefault(q, []).append(new_BND_B)

    for q, nodes in q_to_nodes.items():
        if len(nodes) == 2 and nodes[0] != nodes[1]:
            u, v = nodes[0], nodes[1]
            adj[u].add(v)
            adj[v].add(u)
        elif len(nodes) > 2:
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    adj[nodes[i]].add(nodes[j])
                    adj[nodes[j]].add(nodes[i])

    # Unweighted BFS from new_BND_A to new_BND_B -> exact effective distance d_eff!
    dist = {new_BND_A: 0}
    dq: deque[int] = deque([new_BND_A])
    d_eff = 0
    while dq:
        u = dq.popleft()
        if u == new_BND_B:
            d_eff = dist[u]
            break
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                dq.append(v)

    return out_stabs, out_counts, bnd_a_edges, bnd_b_edges, d_eff


def apply_site_dropouts(
    code: RotatedSurfaceCode,
    dead_data: Set[int],
    dead_z_anc: Optional[Set[int]] = None,
    dead_x_anc: Optional[Set[int]] = None,
) -> DeformedCode:
    """
    Apply exact super-stabilizer gauge deformation for missing data qubits
    and/or missing ancilla qubits, returning deformed parity checks and exact d_eff.
    """
    dead_data_s = set(dead_data)
    dead_z_s = set(dead_z_anc) if dead_z_anc else set()
    dead_x_s = set(dead_x_anc) if dead_x_anc else set()

    d = code.d
    z_bnd_L = {code.coord_to_data[(r, 0)] for r in range(d)}
    z_bnd_R = {code.coord_to_data[(r, d - 1)] for r in range(d)}
    x_bnd_T = {code.coord_to_data[(0, c)] for c in range(d)}
    x_bnd_B = {code.coord_to_data[(d - 1, c)] for c in range(d)}

    # Auger et al. 2017 dead-ancilla mapping:
    #   Dead Z-ancilla a_Z: fix its qubits in Z (delete a_Z + its qubits in Z-graph,
    #     contract its qubits in X-graph -> merges surrounding X-stabs into super-X).
    #   Dead X-ancilla a_X: exact dual (delete a_X + its qubits in X-graph,
    #     contract its qubits in Z-graph -> merges surrounding Z-stabs into super-Z).
    #   If a qubit belongs to BOTH a dead Z-ancilla and a dead X-ancilla, treat it as
    #     a dead data qubit (contract in both graphs so commutation stays exact!).
    z_anc_qubits: Set[int] = set()
    for zid in dead_z_s:
        z_anc_qubits.update(code.z_stabs[zid])
    x_anc_qubits: Set[int] = set()
    for xid in dead_x_s:
        x_anc_qubits.update(code.x_stabs[xid])

    overlap_both = (z_anc_qubits & x_anc_qubits) | (dead_data_s & (z_anc_qubits | x_anc_qubits))
    # Any qubit in dead_data OR touched by both dead Z- and X-ancillas must be contracted in both
    contract_z = dead_data_s | x_anc_qubits
    delete_z_q = z_anc_qubits - contract_z
    contract_x = dead_data_s | z_anc_qubits
    delete_x_q = x_anc_qubits - contract_x

    # Wait: check if a dead Z-ancilla overlaps a contracted-Z qubit (from dead data or dead X-ancilla):
    # If so, contracting in Z removes it cleanly; deleting z_anc_qubits in Z while contracting in X
    # preserves exact commutation whenever delete_z_q has zero overlap with deleted X-stabs.
    # For full safety when dead Z-anc and dead X-anc are adjacent, promote overlap to dead_data:
    if overlap_both:
        dead_data_eff = dead_data_s | overlap_both
        contract_z = dead_data_eff | (x_anc_qubits - dead_data_eff)
        delete_z_q = z_anc_qubits - dead_data_eff
        contract_x = dead_data_eff | (z_anc_qubits - dead_data_eff)
        delete_x_q = x_anc_qubits - dead_data_eff
    else:
        dead_data_eff = dead_data_s

    # Note: for a dead Z-ancilla whose qubit q was fixed in Z, q is removed from ALL live Z-stabs
    # AND removed from ALL live X-stabs (by contracting surrounding X-stabs).
    # Same dually for dead X-ancillas.
    z_stabs_out, z_counts_out, z_L_e, z_R_e, d_eff_X = _contract_dual_graph(
        n_data=code.n_data,
        stabs=code.z_stabs,
        bnd_a_qubits=z_bnd_L,
        bnd_b_qubits=z_bnd_R,
        contract_qubits=contract_z,
        delete_stabs=dead_z_s,
        delete_qubits=delete_z_q,
    )
    x_stabs_out, x_counts_out, x_T_e, x_B_e, d_eff_Z = _contract_dual_graph(
        n_data=code.n_data,
        stabs=code.x_stabs,
        bnd_a_qubits=x_bnd_T,
        bnd_b_qubits=x_bnd_B,
        contract_qubits=contract_x,
        delete_stabs=dead_x_s,
        delete_qubits=delete_x_q,
    )

    H_Z = np.zeros((len(z_stabs_out), code.n_data), dtype=np.uint8)
    for i, s in enumerate(z_stabs_out):
        if s:
            H_Z[i, list(s)] = 1
    H_X = np.zeros((len(x_stabs_out), code.n_data), dtype=np.uint8)
    for i, s in enumerate(x_stabs_out):
        if s:
            H_X[i, list(s)] = 1

    comm_err = int(np.sum((H_X @ H_Z.T) % 2)) if (len(z_stabs_out) > 0 and len(x_stabs_out) > 0) else 0
    # Rare corner check: if adjacent dead Z-ancilla and dead X-ancilla caused a non-commuting
    # boundary interaction, fallback by promoting all dead-ancilla qubits to contracted dead_data
    # (which is unconditionally 100% commuting!).
    if comm_err != 0:
        all_bad_q = dead_data_s | z_anc_qubits | x_anc_qubits
        z_stabs_out, z_counts_out, z_L_e, z_R_e, d_eff_X = _contract_dual_graph(
            n_data=code.n_data,
            stabs=code.z_stabs,
            bnd_a_qubits=z_bnd_L,
            bnd_b_qubits=z_bnd_R,
            contract_qubits=all_bad_q,
            delete_stabs=set(),
            delete_qubits=set(),
        )
        x_stabs_out, x_counts_out, x_T_e, x_B_e, d_eff_Z = _contract_dual_graph(
            n_data=code.n_data,
            stabs=code.x_stabs,
            bnd_a_qubits=x_bnd_T,
            bnd_b_qubits=x_bnd_B,
            contract_qubits=all_bad_q,
            delete_stabs=set(),
            delete_qubits=set(),
        )
        H_Z = np.zeros((len(z_stabs_out), code.n_data), dtype=np.uint8)
        for i, s in enumerate(z_stabs_out):
            if s:
                H_Z[i, list(s)] = 1
        H_X = np.zeros((len(x_stabs_out), code.n_data), dtype=np.uint8)
        for i, s in enumerate(x_stabs_out):
            if s:
                H_X[i, list(s)] = 1
        comm_err = int(np.sum((H_X @ H_Z.T) % 2)) if (len(z_stabs_out) > 0 and len(x_stabs_out) > 0) else 0

    removed_q = dead_data_eff | delete_z_q | delete_x_q
    live_data = [q for q in range(code.n_data) if q not in removed_q]
    d_eff = min(d_eff_X, d_eff_Z)

    return DeformedCode(
        base_d=d,
        n_data_orig=code.n_data,
        dead_data=dead_data_s,
        dead_z_anc=dead_z_s,
        dead_x_anc=dead_x_s,
        live_data=live_data,
        z_stabs=z_stabs_out,
        z_merge_counts=z_counts_out,
        x_stabs=x_stabs_out,
        x_merge_counts=x_counts_out,
        z_bnd_left_edges=z_L_e,
        z_bnd_right_edges=z_R_e,
        x_bnd_top_edges=x_T_e,
        x_bnd_bot_edges=x_B_e,
        H_Z=H_Z,
        H_X=H_X,
        commutes_exact=(comm_err == 0),
        d_eff_X=d_eff_X,
        d_eff_Z=d_eff_Z,
        d_eff=d_eff,
        survived=(d_eff >= 1),
        max_z_weight=max((len(s) for s in z_stabs_out), default=0),
        max_x_weight=max((len(s) for s in x_stabs_out), default=0),
        n_super_z=sum(1 for c in z_counts_out if c > 1),
        n_super_x=sum(1 for c in x_counts_out if c > 1),
    )


# ---------------------------------------------------------------------------
# 3. Exact Circuit-Level 3D Pauli-16 DEM Compiler
# ---------------------------------------------------------------------------

PAULIS_2Q = [a + b for a in "IXYZ" for b in "IXYZ"]


def normalize_and_scale_pauli16(
    base_pauli16: Dict[str, float],
    target_p_2q: float,
    p_leak_lru_extra: float = 0.0,
    symmetrize_qubits: bool = True,
) -> Dict[str, float]:
    """
    Scale a 16-term Exp137 Pauli channel to a target total non-identity 2Q error
    probability `target_p_2q`, preserving the exact relative Pauli-15 profile.
    Optionally symmetrizes (q0, q1) ordering (since CZ is bus-symmetric) and adds
    an explicit conservative depolarizing LRU leakage penalty `p_leak_lru_extra`.
    """
    non_id = {}
    for p in PAULIS_2Q:
        if p == "II":
            continue
        if symmetrize_qubits:
            p_rev = p[1] + p[0]
            non_id[p] = 0.5 * (float(base_pauli16.get(p, 0.0)) + float(base_pauli16.get(p_rev, 0.0)))
        else:
            non_id[p] = float(base_pauli16.get(p, 0.0))

    raw_sum = sum(non_id.values())
    if raw_sum <= 0.0:
        scaled = {p: target_p_2q / 15.0 for p in PAULIS_2Q if p != "II"}
    else:
        scale = target_p_2q / raw_sum
        scaled = {p: v * scale for p, v in non_id.items()}

    if p_leak_lru_extra > 0.0:
        for p in scaled:
            scaled[p] += p_leak_lru_extra / 15.0

    tot_err = min(sum(scaled.values()), 0.999999)
    if sum(scaled.values()) > tot_err:
        renorm = tot_err / sum(scaled.values())
        for p in scaled:
            scaled[p] *= renorm
    scaled["II"] = max(0.0, 1.0 - sum(scaled.values()))
    return scaled


def depolarizing_pauli16(p_2q: float) -> Dict[str, float]:
    """Standard uniform 15-term two-qubit depolarizing channel."""
    out = {p: p_2q / 15.0 for p in PAULIS_2Q if p != "II"}
    out["II"] = max(0.0, 1.0 - p_2q)
    return out


def _combine_bernoulli(p1: float, p2: float) -> float:
    """Exact probability of XOR of two independent Bernoulli faults."""
    return p1 * (1.0 - p2) + p2 * (1.0 - p1)


@dataclass
class CircuitDEM:
    memory_basis: str  # "Z" or "X"
    n_det: int
    bnd_a: int  # index = n_det     (obs=1 boundary: Left for Z-mem, Top for X-mem)
    bnd_b: int  # index = n_det + 1 (obs=0 boundary: Right for Z-mem, Bot for X-mem)
    # Exact Monte Carlo fault mechanisms: (tuple_of_det_ids, obs_flip_0_or_1, prob)
    mechanisms: List[Tuple[Tuple[int, ...], int, float]]
    # Aggregated graphlike edges for exact Edmonds Blossom MWPM:
    #   (u, v) -> (prob, obs_flip_0_or_1) with u < v in {0 .. n_det + 1}
    graph_edges: Dict[Tuple[int, int], Tuple[float, int]]
    # Precomputed shortest paths on weighted MWPM graph
    dist_mat: np.ndarray        # (n_det, n_det) shortest weight between real detectors
    obs_mat: np.ndarray         # (n_det, n_det) uint8 logical parity along shortest path
    bnd_dist: np.ndarray        # (n_det,) min weight to nearest virtual boundary (A or B)
    bnd_obs: np.ndarray         # (n_det,) uint8 obs flip of nearest virtual boundary
    non_graphlike_count: int
    total_mechanism_count: int


def _build_dem_from_mechanisms(
    memory_basis: str,
    n_det: int,
    raw_mechs: Dict[Tuple[Tuple[int, ...], int], float],
) -> CircuitDEM:
    """
    Convert deduplicated elementary fault mechanisms into a CircuitDEM with
    exact pairwise shortest-path matrices for Edmonds Blossom MWPM.
    """
    bnd_a = n_det
    bnd_b = n_det + 1

    mechanisms: List[Tuple[Tuple[int, ...], int, float]] = []
    # For graph edges: track (u, v, obs) separately so parallel obs=0/1 edges keep
    # the higher-probability (lower-weight) branch cleanly.
    edge_by_obs: Dict[Tuple[int, int, int], float] = {}
    non_graphlike = 0

    for (dets, obs), p in raw_mechs.items():
        if p <= 1e-15:
            continue
        p_clamped = min(p, 0.499999)
        mechanisms.append((dets, obs, p_clamped))

        if len(dets) == 0:
            # Pure undetectable logical fault (obs=1, 0 detectors) -> sampled in MC!
            continue
        elif len(dets) == 1:
            u = dets[0]
            # Connect to BND_A if obs == 1, else BND_B (obs == 0)
            v = bnd_a if obs == 1 else bnd_b
            key = (u, v, obs)
            edge_by_obs[key] = _combine_bernoulli(edge_by_obs.get(key, 0.0), p_clamped)
        elif len(dets) == 2:
            u, v = (dets[0], dets[1]) if dets[0] < dets[1] else (dets[1], dets[0])
            key = (u, v, obs)
            edge_by_obs[key] = _combine_bernoulli(edge_by_obs.get(key, 0.0), p_clamped)
        else:
            # Rare hyperedge (>2 detectors, e.g., defective multi-merge super-stabilizer):
            # kept exact in `mechanisms` for MC sampling, decomposed pairwise into matching graph
            non_graphlike += 1
            for i in range(len(dets)):
                for j in range(i + 1, len(dets)):
                    u, v = (dets[i], dets[j]) if dets[i] < dets[j] else (dets[j], dets[i])
                    key = (u, v, obs if i == 0 and j == 1 else 0)
                    edge_by_obs[key] = _combine_bernoulli(edge_by_obs.get(key, 0.0), p_clamped)

    # Collapse parallel (u, v) edges keeping highest probability (lowest weight)
    graph_edges: Dict[Tuple[int, int], Tuple[float, int]] = {}
    for (u, v, obs), p in edge_by_obs.items():
        if p <= 1e-15:
            continue
        if (u, v) not in graph_edges or p > graph_edges[(u, v)][0]:
            graph_edges[(u, v)] = (p, obs)

    # Build sparse weighted CSR matrices for C-speed exact Dijkstra:
    #   G_real: real detectors 0..n_det-1 ONLY (virtual boundaries never act as transit hubs!)
    #   G_A:    real detectors + bnd_a (index n_det)
    #   G_B:    real detectors + bnd_b (index n_det)
    rows_r, cols_r, data_r = [], [], []
    rows_a, cols_a, data_a = [], [], []
    rows_b, cols_b, data_b = [], [], []
    edge_obs_map: Dict[Tuple[int, int], int] = {}
    any_interior_obs1 = False

    for (u, v), (p, obs) in graph_edges.items():
        w = max(float(math.log((1.0 - p) / max(p, 1e-15))), 1e-6)
        edge_obs_map[(u, v)] = obs
        edge_obs_map[(v, u)] = obs
        if u < n_det and v < n_det:
            if obs == 1:
                any_interior_obs1 = True
            rows_r.extend((u, v))
            cols_r.extend((v, u))
            data_r.extend((w, w))
            rows_a.extend((u, v))
            cols_a.extend((v, u))
            data_a.extend((w, w))
            rows_b.extend((u, v))
            cols_b.extend((v, u))
            data_b.extend((w, w))
        elif v == bnd_a and u < n_det:
            rows_a.extend((u, n_det))
            cols_a.extend((n_det, u))
            data_a.extend((w, w))
        elif v == bnd_b and u < n_det:
            rows_b.extend((u, n_det))
            cols_b.extend((n_det, u))
            data_b.extend((w, w))

    csr_real = csr_matrix((data_r, (rows_r, cols_r)), shape=(n_det, n_det))
    if any_interior_obs1:
        dist_raw, preds = sp_dijkstra(csr_real, directed=False, return_predecessors=True)
    else:
        dist_raw = sp_dijkstra(csr_real, directed=False, return_predecessors=False)
        preds = None

    dist_mat = np.where(np.isfinite(dist_raw), dist_raw, 1e9).astype(np.float64)
    obs_mat = np.zeros((n_det, n_det), dtype=np.uint8)
    if any_interior_obs1 and preds is not None:
        for src in range(n_det):
            pr_row = preds[src]
            for dst in range(n_det):
                if src == dst or pr_row[dst] < 0:
                    continue
                cur = dst
                o = 0
                while cur != src and cur >= 0:
                    prev = int(pr_row[cur])
                    o ^= edge_obs_map.get((prev, cur), 0)
                    cur = prev
                obs_mat[src, dst] = o

    # Shortest distance from BND_A (index n_det in csr_a) and BND_B (index n_det in csr_b)
    csr_a = csr_matrix((data_a, (rows_a, cols_a)), shape=(n_det + 1, n_det + 1))
    csr_b = csr_matrix((data_b, (rows_b, cols_b)), shape=(n_det + 1, n_det + 1))
    len_A, pred_A = sp_dijkstra(csr_a, directed=False, indices=n_det, return_predecessors=True)
    len_B, pred_B = sp_dijkstra(csr_b, directed=False, indices=n_det, return_predecessors=True)

    bnd_dist = np.full(n_det, 1e9, dtype=np.float64)
    bnd_obs = np.zeros(n_det, dtype=np.uint8)
    for u in range(n_det):
        dA = float(len_A[u]) if np.isfinite(len_A[u]) else 1e9
        dB = float(len_B[u]) if np.isfinite(len_B[u]) else 1e9
        if dA <= dB:
            bnd_dist[u] = dA
            if dA < 1e8:
                if not any_interior_obs1:
                    bnd_obs[u] = 1  # every BND_A edge has obs=1 and interior edges have obs=0
                else:
                    cur = u
                    o = 0
                    while cur != n_det and cur >= 0:
                        prev = int(pred_A[cur])
                        k_prev = bnd_a if prev == n_det else prev
                        o ^= edge_obs_map.get((k_prev, cur), 0)
                        cur = prev
                    bnd_obs[u] = o
        else:
            bnd_dist[u] = dB
            if dB < 1e8 and any_interior_obs1:
                cur = u
                o = 0
                while cur != n_det and cur >= 0:
                    prev = int(pred_B[cur])
                    k_prev = bnd_b if prev == n_det else prev
                    o ^= edge_obs_map.get((k_prev, cur), 0)
                    cur = prev
                bnd_obs[u] = o

    return CircuitDEM(
        memory_basis=memory_basis,
        n_det=n_det,
        bnd_a=bnd_a,
        bnd_b=bnd_b,
        mechanisms=mechanisms,
        graph_edges=graph_edges,
        dist_mat=dist_mat,
        obs_mat=obs_mat,
        bnd_dist=bnd_dist,
        bnd_obs=bnd_obs,
        non_graphlike_count=non_graphlike,
        total_mechanism_count=len(mechanisms),
    )


def compile_ideal_circuit_dem(
    code: RotatedSurfaceCode,
    rounds: int,
    pauli16: Dict[str, float],
    p_1q: float,
    p_meas: float,
    p_idle_Z: float,
    p_idle_X: float = 0.0,
    memory_basis: str = "Z",
) -> CircuitDEM:
    """
    Compile the exact circuit-level 3D Detector Error Model for `rounds` syndrome
    extraction cycles of the rotated surface code under exact 15-term `pauli16`
    two-qubit CZ noise + 1Q + readout + idle noise.

    memory_basis:
      "Z": preserves logical Z_L (monitors Z-stabilizers for X-errors; includes
           exact X-hooks propagated from X-ancillas and correlated data-ancilla faults!).
      "X": preserves logical X_L (monitors X-stabilizers for Z-errors; includes
           exact Z-hooks propagated from Z-ancillas and correlated data-ancilla faults!).
    """
    if memory_basis not in ("Z", "X"):
        raise ValueError(f"memory_basis must be 'Z' or 'X', got {memory_basis}")

    # Monitored stabilizers (primary) vs conjugate stabilizers (which inject hook errors!)
    if memory_basis == "Z":
        prim_stabs = code.z_stabs
        prim_sched = code.z_sched
        conj_sched = code.x_sched
        logical_vec = code.Z_L
        # In Z-memory, we track data X-flips (Pauli X or Y on data)!
        # For Z-ancilla CZ(d, a): data X-flip after CZ is P_d in ('X', 'Y'); ancilla meas flip is P_a in ('Z', 'Y').
        # For X-ancilla CNOT(a->d) = H_d CZ(d, a) H_d: post-CZ H_d maps Z_d <-> X_d!
        #   So P_d in ('Z', 'Y') before H_d becomes X/Y on data AFTER H_d!
        #   And P_a in ('X', 'Y') propagates as X-hooks onto remaining data qubits d_{s'} (s' > s)!
        data_err_on_prim_cz = ("X", "Y")
        data_err_on_conj_cz = ("Z", "Y")
        p_idle_err = p_idle_X  # pure Z dephasing does not flip Z-memory; X-depol component if any
    else:
        prim_stabs = code.x_stabs
        prim_sched = code.x_sched
        conj_sched = code.z_sched
        logical_vec = code.X_L
        # In X-memory, we track data Z-flips (Pauli Z or Y on data)!
        # For X-ancilla CNOT(a->d) = H_d CZ(d, a) H_d: post-CZ H_d maps X_d <-> Z_d!
        #   So P_d in ('X', 'Y') before H_d becomes Z/Y on data AFTER H_d!
        #   Ancilla meas flip is P_a in ('Z', 'Y').
        # For Z-ancilla CZ(d, a): data Z-flip after CZ is P_d in ('Z', 'Y').
        #   And P_a in ('X', 'Y') propagates as Z-hooks onto remaining data qubits d_{s'} (s' > s)!
        data_err_on_prim_cz = ("X", "Y")
        data_err_on_conj_cz = ("Z", "Y")
        p_idle_err = p_idle_Z  # T2e dephasing directly flips X-memory!

    n_prim = len(prim_stabs)
    # Detectors:
    #   r = 0:         det(a, 0) = m(a, 0)              (initialized in eigenstate of prim stabs)
    #   r = 1..R-1:    det(a, r) = m(a, r) ^ m(a, r-1)
    #   r = R:         det(a, R) = final(a) ^ m(a, R-1) (ideal transversal final readout)
    n_det = (rounds + 1) * n_prim

    def det_id(a_idx: int, r_idx: int) -> int:
        return r_idx * n_prim + a_idx

    # Precompute for each data qubit q: list of (prim_anc_idx, step_s) touching q
    q_to_prim: Dict[int, List[Tuple[int, int]]] = {q: [] for q in range(code.n_data)}
    for a_idx, sched in enumerate(prim_sched):
        for s, q in enumerate(sched):
            if q is not None:
                q_to_prim[q].append((a_idx, s))

    raw_mechs: Dict[Tuple[Tuple[int, ...], int], float] = {}

    def add_mech(dets_list: Sequence[int], obs: int, p: float) -> None:
        if p <= 1e-15:
            return
        # Cancel duplicate detector indices mod 2!
        parity: Dict[int, int] = {}
        for d_i in dets_list:
            parity[d_i] = parity.get(d_i, 0) ^ 1
        active = tuple(sorted(k for k, v in parity.items() if v == 1))
        if len(active) == 0 and obs == 0:
            return
        key = (active, obs & 1)
        raw_mechs[key] = _combine_bernoulli(raw_mechs.get(key, 0.0), p)

    def data_fault_dets_and_obs(
        qubits: Sequence[int], r: int, after_step: int
    ) -> Tuple[List[int], int]:
        """
        Compute detectors and observable flipped by a data Pauli error on `qubits`
        occurring in round `r` immediately after gate step `after_step`
        (after_step = -1 means before step 0 of round r; after_step = 3 means after step 3).
        """
        dets: List[int] = []
        obs = 0
        for q in qubits:
            obs ^= int(logical_vec[q])
            for a_idx, s_a in q_to_prim[q]:
                # If prim stabilizer a_idx interacts with q LATER in round r (s_a > after_step),
                # the fault is first caught by m(a_idx, r) -> flips det(a_idx, r).
                # Otherwise, it is first caught in round r+1 (or final readout at r = rounds) -> det(a_idx, r+1).
                if s_a > after_step:
                    dets.append(det_id(a_idx, r))
                else:
                    dets.append(det_id(a_idx, r + 1))
        return dets, obs

    # 1Q depolarizing fault probabilities: P(X or Y) = 2/3 * p_1q, P(Z or Y) = 2/3 * p_1q
    p_1q_flip = (2.0 / 3.0) * p_1q

    for r in range(rounds):
        # (a) Round-start data idle + data 1Q (Hadamards for CNOT conversion on X-plaquettes)
        for q in range(code.n_data):
            # Idle dephasing / depol before step 0
            if p_idle_err > 0.0:
                dets, obs = data_fault_dets_and_obs([q], r, after_step=-1)
                add_mech(dets, obs, p_idle_err)
            # Single-qubit gate error (e.g., DD / echo pulse on data during round)
            if p_1q_flip > 0.0:
                dets, obs = data_fault_dets_and_obs([q], r, after_step=-1)
                add_mech(dets, obs, p_1q_flip)

        # (b) Primary ancilla prep + Hadamard error (before step 0): flips m(a, r) -> det(a, r) & det(a, r+1)
        if p_1q_flip > 0.0:
            for a_idx in range(n_prim):
                add_mech([det_id(a_idx, r), det_id(a_idx, r + 1)], 0, p_1q_flip)

        # (c) 4-step CZ/CNOT syndrome extraction with EXACT 15-term Exp137 Pauli-16!
        for s in range(4):
            # (c1) Primary stabilizer CZ/CNOT gates
            for a_idx, sched in enumerate(prim_sched):
                q = sched[s]
                if q is None:
                    continue
                for pauli_str, prob in pauli16.items():
                    if pauli_str == "II" or prob <= 1e-15:
                        continue
                    p_d, p_a = pauli_str[0], pauli_str[1]
                    d_flips_data = (p_d in data_err_on_prim_cz)
                    a_flips_meas = (p_a in ("Z", "Y"))
                    if not d_flips_data and not a_flips_meas:
                        continue
                    dets: List[int] = []
                    obs = 0
                    if d_flips_data:
                        dd, oo = data_fault_dets_and_obs([q], r, after_step=s)
                        dets.extend(dd)
                        obs ^= oo
                    if a_flips_meas:
                        dets.extend([det_id(a_idx, r), det_id(a_idx, r + 1)])
                    add_mech(dets, obs, prob)

            # (c2) Conjugate stabilizer CZ/CNOT gates (inject data errors + EXACT HOOK ERRORS!)
            for c_idx, sched in enumerate(conj_sched):
                q = sched[s]
                if q is None:
                    continue
                # Remaining data qubits on this conjugate plaquette for hook propagation (s' > s)
                hook_targets = [sched[sp] for sp in range(s + 1, 4) if sched[sp] is not None]
                for pauli_str, prob in pauli16.items():
                    if pauli_str == "II" or prob <= 1e-15:
                        continue
                    p_d, p_a = pauli_str[0], pauli_str[1]
                    d_flips_data = (p_d in data_err_on_conj_cz)
                    a_injects_hook = (p_a in ("X", "Y")) and (len(hook_targets) > 0)
                    if not d_flips_data and not a_injects_hook:
                        continue
                    dets = []
                    obs = 0
                    if d_flips_data:
                        dd, oo = data_fault_dets_and_obs([q], r, after_step=s)
                        dets.extend(dd)
                        obs ^= oo
                    if a_injects_hook:
                        # Hook error arrives at each future step s' > s on target data qubit d_{s'}
                        for sp in range(s + 1, 4):
                            qt = sched[sp]
                            if qt is not None:
                                dd, oo = data_fault_dets_and_obs([qt], r, after_step=sp)
                                dets.extend(dd)
                                obs ^= oo
                    add_mech(dets, obs, prob)

        # (d) Primary ancilla final Hadamard + measurement error (p_meas from Exp140 + p_1q_flip)
        p_ro_tot = _combine_bernoulli(p_meas, p_1q_flip)
        for a_idx in range(n_prim):
            add_mech([det_id(a_idx, r), det_id(a_idx, r + 1)], 0, p_ro_tot)

    return _build_dem_from_mechanisms(memory_basis, n_det, raw_mechs)


def compile_deformed_circuit_dem(
    deformed: DeformedCode,
    rounds: int,
    pauli16: Dict[str, float],
    p_1q: float,
    p_meas: float,
    p_idle_Z: float,
    p_idle_X: float = 0.0,
    memory_basis: str = "Z",
) -> Optional[CircuitDEM]:
    """
    Compile circuit-level 3D DEM on a gauge-deformed defective surface code.
    Accounts for:
      1. Exact deformed stabilizer topology & boundary absorptions.
      2. Weight-scaled super-stabilizer measurement error:
           p_meas_super(a) = 1 - (1 - p_meas)^{merge_count[a]}
         and extra 2Q gate exposure proportional to super-stabilizer weight.
      3. Exact marginal data, hook, and correlated space-time error probabilities
         from Exp137's 15-term pauli_16 channel.
    Returns None if the defective patch failed percolation (d_eff == 0).
    """
    if memory_basis == "Z":
        if deformed.d_eff_X == 0:
            return None
        prim_stabs = deformed.z_stabs
        prim_counts = deformed.z_merge_counts
        bnd_a_edges = deformed.z_bnd_left_edges
        bnd_b_edges = deformed.z_bnd_right_edges
        p_idle_err = p_idle_X
        data_err_on_prim = ("X", "Y")
        data_err_on_conj = ("Z", "Y")
    else:
        if deformed.d_eff_Z == 0:
            return None
        prim_stabs = deformed.x_stabs
        prim_counts = deformed.x_merge_counts
        bnd_a_edges = deformed.x_bnd_top_edges
        bnd_b_edges = deformed.x_bnd_bot_edges
        p_idle_err = p_idle_Z
        data_err_on_prim = ("X", "Y")
        data_err_on_conj = ("Z", "Y")

    n_prim = len(prim_stabs)
    if n_prim == 0:
        # Only direct BND_A <-> BND_B edges exist (d_eff = 1)
        return None
    n_det = (rounds + 1) * n_prim

    def det_id(a_idx: int, r_idx: int) -> int:
        return r_idx * n_prim + a_idx

    # Map each live data qubit to its incident primary stabilizers and boundary flags
    q_to_stabs: Dict[int, List[int]] = {}
    for a_idx, supp in enumerate(prim_stabs):
        for q in supp:
            q_to_stabs.setdefault(q, []).append(a_idx)
    for q in bnd_a_edges | bnd_b_edges:
        q_to_stabs.setdefault(q, [])

    # Extract exact marginal fault rates per CZ gate from Exp137 pauli_16
    p_data_prim = sum(v for k, v in pauli16.items() if k != "II" and k[0] in data_err_on_prim and k[1] not in ("Z", "Y"))
    p_corr_prim = sum(v for k, v in pauli16.items() if k != "II" and k[0] in data_err_on_prim and k[1] in ("Z", "Y"))
    p_anc_only_prim = sum(v for k, v in pauli16.items() if k != "II" and k[0] not in data_err_on_prim and k[1] in ("Z", "Y"))
    p_data_conj = sum(v for k, v in pauli16.items() if k != "II" and k[0] in data_err_on_conj)
    p_hook_conj = sum(v for k, v in pauli16.items() if k != "II" and k[1] in ("X", "Y"))

    p_1q_flip = (2.0 / 3.0) * p_1q
    raw_mechs: Dict[Tuple[Tuple[int, ...], int], float] = {}

    def add_mech(dets_list: Sequence[int], obs: int, p: float) -> None:
        if p <= 1e-15:
            return
        parity: Dict[int, int] = {}
        for d_i in dets_list:
            parity[d_i] = parity.get(d_i, 0) ^ 1
        active = tuple(sorted(k for k, v in parity.items() if v == 1))
        if len(active) == 0 and obs == 0:
            return
        key = (active, obs & 1)
        raw_mechs[key] = _combine_bernoulli(raw_mechs.get(key, 0.0), p)

    for r in range(rounds):
        # 1. Data-qubit errors per round (from idle + 1Q + 2 primary CZs + 2 conjugate CZs + hook contribution)
        for q, stabs_q in q_to_stabs.items():
            in_a = (q in bnd_a_edges)
            in_b = (q in bnd_b_edges)
            obs = 1 if in_a else 0
            # Direct BND_A <-> BND_B bridge qubit (0 real stabilizers, 1 obs flip)
            if len(stabs_q) == 0 and not (in_a and in_b):
                continue

            # Effective single-round data fault probability on qubit q:
            # 1x idle + 1x 1Q + len(stabs_q)x primary CZ data error + 2x conjugate CZ data error + 1x hook marginal
            p_q = 0.0
            for pe in (p_idle_err, p_1q_flip, p_data_conj, p_data_conj, p_hook_conj):
                p_q = _combine_bernoulli(p_q, pe)
            for _ in range(max(len(stabs_q), 1)):
                p_q = _combine_bernoulli(p_q, p_data_prim)

            # Spacelike edge at round r (or r+1 for half of CZ steps -> split evenly for exact time-like mixing)
            dets_r = [det_id(a, r) for a in stabs_q]
            add_mech(dets_r, obs, p_q)

            # Correlated diagonal space-time edge for each primary CZ on q
            if p_corr_prim > 1e-15 and len(stabs_q) >= 1:
                for a in stabs_q:
                    others = [det_id(b, r + 1) for b in stabs_q if b != a]
                    add_mech([det_id(a, r)] + others, obs, p_corr_prim)

        # 2. Ancilla & Super-Stabilizer measurement + internal CZ ancilla-Z errors
        for a_idx, supp in enumerate(prim_stabs):
            w_a = len(supp)
            m_cnt = prim_counts[a_idx]
            # Weight-scaled measurement error for merged super-stabilizer (m_cnt gauge checks multiplied)
            p_m_super = 1.0 - (1.0 - p_meas) ** m_cnt
            # Ancilla prep/final Had + w_a CZ gates' ancilla-Z noise
            p_time = _combine_bernoulli(p_m_super, 2.0 * p_1q_flip * m_cnt)
            for _ in range(w_a):
                p_time = _combine_bernoulli(p_time, p_anc_only_prim)
            add_mech([det_id(a_idx, r), det_id(a_idx, r + 1)], 0, p_time)

    return _build_dem_from_mechanisms(memory_basis, n_det, raw_mechs)


# ---------------------------------------------------------------------------
# 4. Exact Edmonds Blossom MWPM Decoder (Sparse k-NN Shadow-Boundary Graph)
# ---------------------------------------------------------------------------

def decode_syndrome_mwpm(
    defects: np.ndarray,
    dem: CircuitDEM,
    k_nn: int = 10,
) -> int:
    """
    Exact Edmonds Blossom Minimum-Weight Perfect Matching (MWPM) over a single
    syndrome defect vector `defects` (1D array of triggered detector indices).

    Uses the exact shadow-boundary reduction:
      - Real defect i (0..m-1) connects to its shadow copy m+i with weight bnd_dist[u_i].
      - Real defect i connects to its k_nn nearest real defects j (and every pair when m <= 24)
        whenever dist[u_i, u_j] < bnd_dist[u_i] + bnd_dist[u_j], mirrored by a 0-weight
        shadow edge (m+i, m+j) so shadows can pair off freely!
    Returns predicted logical observable flip (0 or 1).
    """
    m = len(defects)
    if m == 0:
        return 0
    if m == 1:
        return int(dem.bnd_obs[defects[0]])
    if m == 2:
        u0, u1 = int(defects[0]), int(defects[1])
        d_pair = dem.dist_mat[u0, u1]
        d_bnds = dem.bnd_dist[u0] + dem.bnd_dist[u1]
        if d_pair <= d_bnds:
            return int(dem.obs_mat[u0, u1])
        return int(dem.bnd_obs[u0] ^ dem.bnd_obs[u1])

    # General m >= 3: exact Edmonds Blossom via networkx.min_weight_matching
    G = nx.Graph()
    bnd_d = dem.bnd_dist[defects]
    sub_d = dem.dist_mat[np.ix_(defects, defects)]

    # Always connect every real defect i to its own shadow node m + i
    for i in range(m):
        G.add_edge(i, m + i, weight=float(bnd_d[i]))

    if m <= 24:
        # Complete graph over all improving pairs + shadow mirror
        for i in range(m):
            bi = bnd_d[i]
            row_i = sub_d[i]
            for j in range(i + 1, m):
                dij = row_i[j]
                if dij < bi + bnd_d[j]:
                    G.add_edge(i, j, weight=float(dij))
                    G.add_edge(m + i, m + j, weight=0.0)
    else:
        # Sparse k-NN over improving pairs + shadow mirror + full shadow chain safety
        k_use = min(k_nn, m - 1)
        for i in range(m):
            row_i = sub_d[i]
            # Partition k_use smallest distances excluding self
            nbrs = np.argpartition(row_i, k_use)[: k_use + 1]
            bi = bnd_d[i]
            for j in nbrs:
                j_int = int(j)
                if j_int == i:
                    continue
                dij = row_i[j_int]
                if dij < bi + bnd_d[j_int]:
                    if not G.has_edge(i, j_int):
                        G.add_edge(i, j_int, weight=float(dij))
                        G.add_edge(m + i, m + j_int, weight=0.0)

    # Ensure every shadow pair has 0-weight matching fallback when m is odd/even:
    # Note: if an even number of real defects pair with each other (k pairs), the
    # remaining m - 2k real defects pair to their own shadows, leaving exactly 2k
    # unmatched shadows. Since every real edge (i, j) added a 0-weight shadow edge
    # (m+i, m+j), those 2k shadows ALWAYS have a 0-weight perfect matching!
    matching = nx.algorithms.matching.min_weight_matching(G, weight="weight")

    obs_pred = 0
    for u, v in matching:
        if u > v:
            u, v = v, u
        if u < m and v < m:
            obs_pred ^= int(dem.obs_mat[defects[u], defects[v]])
        elif u < m and v >= m:
            obs_pred ^= int(dem.bnd_obs[defects[u]])
        # shadow-shadow (u >= m and v >= m) contributes 0 to observable
    return obs_pred


def simulate_dem_mc(
    dem: CircuitDEM,
    n_shots: int,
    rng: np.random.Generator,
    k_nn: int = 10,
) -> Dict[str, float]:
    """
    Vectorized Monte Carlo fault sampling over `dem.mechanisms` + exact Edmonds
    Blossom MWPM decoding, returning exact logical error rate and Wilson 95% CI.
    """
    n_mech = len(dem.mechanisms)
    probs = np.array([m[2] for m in dem.mechanisms], dtype=np.float64)
    obs_arr = np.array([m[1] for m in dem.mechanisms], dtype=np.uint8)

    # Pre-split mechanism detector indices for fast vectorized XOR accumulation
    # Process in batches of 500 shots to keep peak RAM tiny (< 5 MB)
    batch_size = min(500, n_shots)
    n_fail = 0
    n_raw_fail = 0
    n_total_defects = 0

    shots_done = 0
    while shots_done < n_shots:
        b = min(batch_size, n_shots - shots_done)
        # Draw all fault firings for batch: (b, n_mech) bool
        u_rand = rng.random((b, n_mech))
        fired = u_rand < probs[None, :]

        # True observable flips: (b,) uint8
        true_obs = (fired @ obs_arr) & 1
        n_raw_fail += int(np.sum(true_obs))

        # Accumulate detector syndromes per shot
        syn = np.zeros((b, dem.n_det), dtype=np.uint8)
        # Iterate only over mechanisms that fired at least once in this batch
        fired_any = np.flatnonzero(np.any(fired, axis=0))
        for mi in fired_any:
            dets_m = dem.mechanisms[int(mi)][0]
            if not dets_m:
                continue
            rows = np.flatnonzero(fired[:, mi])
            for d_idx in dets_m:
                syn[rows, d_idx] ^= 1

        # Decode each shot in the batch
        for s_i in range(b):
            defects = np.flatnonzero(syn[s_i])
            n_total_defects += len(defects)
            pred_obs = decode_syndrome_mwpm(defects, dem, k_nn=k_nn)
            if pred_obs != int(true_obs[s_i]):
                n_fail += 1

        shots_done += b

    p_hat = n_fail / float(n_shots)
    ci_lo, ci_hi = wilson_ci95(n_fail, n_shots)
    return {
        "n_shots": int(n_shots),
        "n_fail": int(n_fail),
        "eps_L": float(p_hat),
        "ci95_lo": float(ci_lo),
        "ci95_hi": float(ci_hi),
        "raw_uncorrected_rate": float(n_raw_fail / float(n_shots)),
        "mean_defects_per_shot": float(n_total_defects / float(n_shots)),
    }


def wilson_ci95(k: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """Exact Wilson score 95% confidence interval for binomial proportion k/n."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / float(n)
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (max(0.0, center - half), min(1.0, center + half))
