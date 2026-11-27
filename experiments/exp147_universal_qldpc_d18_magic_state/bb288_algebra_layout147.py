"""Exp147 Module 1: Exact Bravyi [[288, 12, 18]] Bivariate Bicycle Code Algebra,
Verified Depth-7 Zero-Kickback CNOT Schedule, Z_12 Automorphism Thickness-2 M4
Physical Layout (24x24 Folded Torus), and 576-Cell Defect-Free Block Yield.

Reuses verified GF(2) CSS & schedule machinery from Exp144 cleanly via repo-relative imports.
Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
Epistemic scope: {Model} / {Literatur}. no_lab_measurement=True.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp144_qldpc_bivariate_bicycle_m4.bb_codes_and_layout144 import (  # noqa: E402
    BB_CODE_SPECS,
    BBCodeSpec,
    _fold_1d,
    build_bb_code,
    find_verified_commuting_schedule,
)

# Exact Bravyi et al. (Nature 2024, Table 1) [[288, 12, 18]] Bivariate Bicycle Code:
# l = 12, m = 12 -> nh = 144, n = 288 data qubits, 2n = 576 active cells (48 cells/logical)
# A = x^3 + y^2 + y^7,  B = y^3 + x + x^2
# Note: {x, x^2} -> step 1 in x; {y^2, y^7} -> difference y^5 where gcd(5, 12) = 1 ->
# exact Z_12 automorphism b' = 5*b (mod 12) turns {y^2, y^7} into step 1 in y'!
BB_288_SPEC = BBCodeSpec(
    name="[[288,12,18]]",
    l=12,
    m=12,
    A_terms=((3, 0), (0, 2), (0, 7)),
    B_terms=((0, 3), (1, 0), (2, 0)),
    d_lit=18,
)

ALL_BB_SPECS_V7: Dict[str, BBCodeSpec] = {
    **BB_CODE_SPECS,
    "BB_288_12_18": BB_288_SPEC,
}


def verify_bb288_algebra_and_schedule() -> Dict[str, Any]:
    """Build and exhaustively verify [[288,12,18]] GF(2) CSS algebra, symplectic logical basis,
    and Bravyi Lemma-5 depth-7 zero-collision, zero-kickback CNOT schedule.
    """
    code = build_bb_code(BB_288_SPEC)
    sched = find_verified_commuting_schedule(code)
    L_X, L_Z = code["L_X"], code["L_Z"]
    H_X, H_Z = code["H_X"], code["H_Z"]

    symp_ok = bool(
        np.array_equal((L_X @ L_Z.T) & 1, np.eye(code["k"], dtype=np.uint8))
        and np.all(((H_Z @ L_X.T) & 1) == 0)
        and np.all(((H_X @ L_Z.T) & 1) == 0)
    )
    return {
        "code": code,
        "schedule": sched,
        "summary": {
            "name": BB_288_SPEC.name,
            "l": 12,
            "m": 12,
            "n_data": code["n_data"],
            "n_ancilla": code["n_ancilla"],
            "n_total_cells": code["n_total_cells"],
            "k": code["k"],
            "d_lit": BB_288_SPEC.d_lit,
            "encoding_rate_k_over_n": round(code["k"] / code["n_data"], 5),
            "active_cells_per_logical": round(code["n_total_cells"] / code["k"], 2),
            "rank_X": code["rank_X"],
            "rank_Z": code["rank_Z"],
            "commutativity_H_X_H_ZT_zero": code["commutativity_H_X_H_ZT_zero"],
            "all_row_col_weight_6": code["all_row_col_weight_6"],
            "symplectic_logical_valid": symp_ok,
            "min_basis_logical_weight_X": int(np.min(np.sum(L_X, axis=1))),
            "min_basis_logical_weight_Z": int(np.min(np.sum(L_Z, axis=1))),
            "schedule_depth": sched["depth_cnot_layers"],
            "schedule_total_cnots": sched["total_cnots_per_round"],
            "schedule_zero_collisions": sched["zero_collision_verified"],
            "schedule_zero_kickback": sched["zero_kickback_verified"],
        },
    }


def build_bb288_thickness2_m4_layout(
    code: Dict[str, Any],
    pitches_um: Tuple[float, ...] = (15.0, 18.0, 20.0, 25.0, 30.0),
    l_res_nominal_um: float = 300.0,
    f_r_nominal_ghz: float = 5.0,
) -> Dict[str, Any]:
    """Embed [[288,12,18]] (l=12, m=12, 576 qubits) onto a 24 x 24 folded-torus 2D silicon grid
    using the exact Z_12 group automorphism b' = (5 * b) mod 12 (since 5^2 = 1 mod 12).

    Under b' = 5*b mod 12:
      - A_1 = y^2 -> (y')^10 = (y')^{-2}, A_2 = y^7 -> (y')^35 = (y')^{-1} (difference step +1!)
      - B_1 = x,   B_2 = x^2 (difference step +1!)
      - A_0 = x^3, B_0 = y^3 -> (y')^15 = (y')^3 (long-range shift 3!)

    Exact Bravyi Lemma-3 torus bijection on the 24 x 24 grid:
      X(a, b') -> (2a,     2b'    ) mod (24, 24)  [even, even]
      L(a, b') -> (2a,     2b' + 3) mod (24, 24)  [even, odd ]
      R(a, b') -> (2a - 3, 2b'    ) mod (24, 24)  [odd,  even]
      Z(a, b') -> (2a - 3, 2b' + 3) mod (24, 24)  [odd,  odd ]

    Checks analytically that ALL 1,152 Layer-1 edges have EXACT torus distance 1.0 (0 torus crossings)
    and computes exact flat 2:1 folded chip resonator lengths L_max across P_cell in [15, 30] um!
    """
    l, m = code["l"], code["m"]
    assert l == 12 and m == 12, "24x24 automorphism layout specialized for [[288,12,18]]"
    nh = l * m  # 144
    W_grid, H_grid = 2 * l, 2 * m  # 24, 24

    coords_torus: Dict[int, Tuple[int, int]] = {}
    coords_folded: Dict[int, Tuple[int, int]] = {}
    qubit_types: Dict[int, str] = {}

    for a in range(l):
        for b in range(m):
            idx = a * m + b
            bp = (5 * b) % m  # Exact Z_12 automorphism mapping {y^2, y^7} -> {(y')^-2, (y')^-1}
            positions = [
                (2 * nh + idx, "X", (2 * a) % W_grid, (2 * bp) % H_grid),
                (idx, "L", (2 * a) % W_grid, (2 * bp + 3) % H_grid),
                (nh + idx, "R", (2 * a - 3) % W_grid, (2 * bp) % H_grid),
                (3 * nh + idx, "Z", (2 * a - 3) % W_grid, (2 * bp + 3) % H_grid),
            ]
            for qid, qtype, gx, gy in positions:
                coords_torus[qid] = (gx, gy)
                coords_folded[qid] = (_fold_1d(gx, W_grid), _fold_1d(gy, H_grid))
                qubit_types[qid] = qtype

    assert len(set(coords_torus.values())) == 576, "Torus coordinates must be an exact bijection on 24x24"
    assert len(set(coords_folded.values())) == 576, "Folded flat-chip coordinates must be a bijection"

    # Extract all 1,728 Tanner edges split into Layer 1 (local: A1,A2,B1,B2) & Layer 2 (long: A0,B0)
    layer1_edges: List[Tuple[int, int]] = []
    layer2_edges: List[Tuple[int, int]] = []
    for term_idx, M in enumerate(code["A_mats"]):
        rs, cs = np.nonzero(M)
        tgt = layer2_edges if term_idx == 0 else layer1_edges
        for r, c in zip(rs, cs):
            tgt.append((2 * nh + int(r), int(c)))          # X - L
            tgt.append((3 * nh + int(c), nh + int(r)))     # Z - R (A^T)

    for term_idx, M in enumerate(code["B_mats"]):
        rs, cs = np.nonzero(M)
        tgt = layer2_edges if term_idx == 0 else layer1_edges
        for r, c in zip(rs, cs):
            tgt.append((2 * nh + int(r), nh + int(c)))     # X - R
            tgt.append((3 * nh + int(c), int(r)))          # Z - L (B^T)

    # Verify EXACT torus Manhattan/Euclidean distance of ALL Layer-1 and Layer-2 edges!
    def _torus_dist(u: int, v: int) -> float:
        x1, y1 = coords_torus[u]
        x2, y2 = coords_torus[v]
        dx = min(abs(x1 - x2), W_grid - abs(x1 - x2))
        dy = min(abs(y1 - y2), H_grid - abs(y1 - y2))
        return math.hypot(dx, dy)

    l1_torus_dists = np.array([_torus_dist(u, v) for u, v in layer1_edges], dtype=np.float64)
    l2_torus_dists = np.array([_torus_dist(u, v) for u, v in layer2_edges], dtype=np.float64)
    l1_all_unit_torus = bool(np.allclose(l1_torus_dists, 1.0, atol=1e-12))
    l2_torus_unique = sorted({round(float(d), 4) for d in l2_torus_dists})

    # Compute folded flat-chip Euclidean AND exact orthogonal Manhattan distances (OBS-045)
    e1_grid = np.array(
        [math.hypot(coords_folded[u][0] - coords_folded[v][0], coords_folded[u][1] - coords_folded[v][1]) for u, v in layer1_edges],
        dtype=np.float64,
    )
    e2_grid = np.array(
        [math.hypot(coords_folded[u][0] - coords_folded[v][0], coords_folded[u][1] - coords_folded[v][1]) for u, v in layer2_edges],
        dtype=np.float64,
    )
    m1_grid = np.array(
        [abs(coords_folded[u][0] - coords_folded[v][0]) + abs(coords_folded[u][1] - coords_folded[v][1]) for u, v in layer1_edges],
        dtype=np.float64,
    )
    m2_grid = np.array(
        [abs(coords_folded[u][0] - coords_folded[v][0]) + abs(coords_folded[u][1] - coords_folded[v][1]) for u, v in layer2_edges],
        dtype=np.float64,
    )
    all_e_grid = np.concatenate([e1_grid, e2_grid])

    # OBS-045: Exact flat-chip airbridge crossing counts for BB_288 (484 L1 + 23,772 L2 = 24,256!)
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
                d1 = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
                d2 = (x4 - x3) * (y2 - y3) - (y4 - y3) * (x2 - x3)
                d3 = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
                d4 = (x2 - x1) * (y4 - y1) - (y2 - y1) * (x4 - x1)
                if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
                    cnt += 1
        return cnt

    xings_l1_flat = _count_proper_crossings(layer1_edges)
    xings_l2_flat = _count_proper_crossings(layer2_edges)
    l_res_loaded_um = 250.0  # OBS-140 loaded meander ceiling at 160 pF/m

    pitch_sweep: List[Dict[str, Any]] = []
    for pitch in pitches_um:
        L_l1_max = float(np.max(e1_grid) * pitch)
        L_l2_med = float(np.median(e2_grid) * pitch)
        L_l2_max = float(np.max(e2_grid) * pitch)
        L_max = float(np.max(all_e_grid) * pitch)
        L_l1_manh_max = float(np.max(m1_grid) * pitch)
        L_l2_manh_med = float(np.median(m2_grid) * pitch)
        L_l2_manh_max = float(np.max(m2_grid) * pitch)
        L_l2_manh_frac_gt_300 = float(np.mean(m2_grid * pitch > l_res_nominal_um))
        f_r_fixed = f_r_nominal_ghz if L_max <= l_res_nominal_um else f_r_nominal_ghz * (l_res_nominal_um / L_max)
        L_sq_5G = 100.0 if L_max <= l_res_nominal_um else 100.0 * ((l_res_nominal_um / L_max) ** 2)
        pitch_sweep.append({
            "pitch_um": pitch,
            "block_size_um": [round(W_grid * pitch, 1), round(H_grid * pitch, 1)],
            "block_area_mm2": round((W_grid * pitch * H_grid * pitch) / 1e6, 4),
            "layer1_max_eucl_um": round(L_l1_max, 1),
            "layer2_median_eucl_um": round(L_l2_med, 1),
            "layer2_max_eucl_um": round(L_l2_max, 1),
            "L_max_um": round(L_max, 1),
            "layer1_max_manh_um": round(L_l1_manh_max, 1),
            "layer2_median_manh_um": round(L_l2_manh_med, 1),
            "layer2_max_manh_um": round(L_l2_manh_max, 1),
            "layer2_frac_gt_300um_manh": round(L_l2_manh_frac_gt_300, 4),
            "fits_300um_m4_resonator": bool(L_max <= l_res_nominal_um),
            "fits_300um_m4_manhattan": bool(max(L_l1_manh_max, L_l2_manh_max) <= l_res_nominal_um),
            "fits_250um_loaded_meander_eucl": bool(L_max <= l_res_loaded_um),
            "fits_500um_extended_m4": bool(L_max <= 500.0),
            "f_r_fixed_100pH_ghz": round(f_r_fixed, 3),
            "L_sq_pH_for_5GHz": round(L_sq_5G, 1),
        })

    return {
        "code_name": code["name"],
        "automorphism": "b' = 5*b mod 12 (Z_12 generator)",
        "grid_shape": [W_grid, H_grid],
        "n_qubits": 576,
        "n_edges_total": len(layer1_edges) + len(layer2_edges),
        "n_edges_layer1_local": len(layer1_edges),
        "n_edges_layer2_long_range": len(layer2_edges),
        "torus_thickness": 2,
        "layer1_all_unit_torus_distance": l1_all_unit_torus,
        "layer1_torus_crossings": 0 if l1_all_unit_torus else -1,
        "flat_folded_layer1_airbridges": int(xings_l1_flat),
        "flat_folded_layer2_airbridges": int(xings_l2_flat),
        "total_flat_airbridge_crossings": int(xings_l1_flat + xings_l2_flat),
        "layer2_torus_lengths_pitch": l2_torus_unique,
        "pitch_sweep": pitch_sweep,
        "coords_folded": coords_folded,
        "qubit_types": qubit_types,
        "layer1_edges": layer1_edges,
        "layer2_edges": layer2_edges,
    }


def compute_bb288_defect_yields(
    n_cells_block: int = 576,
    n_blocks_cryo: int = 5,
    n_blocks_femoco_mem: int = 16,
) -> Dict[str, Any]:
    """Compute exact defect-free 576-cell [[288,12,18]] block yield, 5-block (60L) single-cryostat
    yield, and 16-block (192L FeMoco memory) yield across legacy unfiltered AND honest DDRF
    (OBS-029) + iradina/valley (OBS-047) fabrication regimes.
    """
    fnr = 0.002008
    regimes = {
        "f1p0_Ez0_no_stark": 0.5275 * 0.9770 * (1.0 - fnr),
        "f1p5_Ez2MVm_v5_star": 0.7750 * 0.9770 * (1.0 - fnr),
        "f1p0_Ez0_ddrf6893": 0.2950 * 0.9770 * (1.0 - fnr),
        "f1p5_Ez2MVm_ddrf6893": 0.5400 * 0.9770 * (1.0 - fnr),
        "f1p5_Ez2MVm_iradina_valley_pff0p5375": 0.7750 * 0.5375 * (1.0 - fnr),
        "f1p5_Ez2MVm_ddrf6893_and_iradina_valley": 0.5400 * 0.5375 * (1.0 - fnr),
    }
    out: Dict[str, Any] = {}
    for rname, p_slot in regimes.items():
        by_n: Dict[str, Any] = {}
        for n_cand in (6, 7, 8, 9, 10, 11, 14, 18, 24, 30):
            p_drop = (1.0 - p_slot) ** n_cand
            y_blk = (1.0 - p_drop) ** n_cells_block
            y_5blk = y_blk ** n_blocks_cryo
            y_4of5 = (y_blk ** 5) + 5.0 * (y_blk ** 4) * (1.0 - y_blk)
            y_16blk = y_blk ** n_blocks_femoco_mem
            y_16of18 = (
                (y_blk ** 18)
                + 18.0 * (y_blk ** 17) * (1.0 - y_blk)
                + 153.0 * (y_blk ** 16) * ((1.0 - y_blk) ** 2)
            )
            by_n[f"N{n_cand}"] = {
                "N_cand": n_cand,
                "p_drop": float(p_drop),
                "p_drop_pct": round(p_drop * 100.0, 6),
                "block_576_yield": round(y_blk, 6),
                "block_576_yield_pct": round(y_blk * 100.0, 4),
                "cryo_5block_60L_yield_pct": round(y_5blk * 100.0, 4),
                "cryo_4of5_spared_yield_pct": round(y_4of5 * 100.0, 4),
                "femoco_16block_192L_yield_pct": round(y_16blk * 100.0, 4),
                "femoco_16of18_spared_yield_pct": round(y_16of18 * 100.0, 4),
                "phys_candidates_per_block": n_cells_block * n_cand,
                "phys_candidates_per_logical": round((n_cells_block * n_cand) / 12.0, 2),
            }
        n_req_99 = 1
        while ((1.0 - (1.0 - p_slot) ** n_req_99) ** n_cells_block) < 0.99 and n_req_99 < 100:
            n_req_99 += 1
        out[rname] = {"p_slot": round(p_slot, 5), "N_cand_req_99pct_block": int(n_req_99), "by_N_cand": by_n}
    return out


if __name__ == "__main__":
    v = verify_bb288_algebra_and_schedule()
    s = v["summary"]
    print(f"=== [[288,12,18]] Verification ===")
    print(
        f"  n={s['n_data']}, 2n={s['n_total_cells']}, k={s['k']}, rankX={s['rank_X']}, rankZ={s['rank_Z']}, "
        f"comm={s['commutativity_H_X_H_ZT_zero']}, wt6={s['all_row_col_weight_6']}, symp={s['symplectic_logical_valid']}, "
        f"minW={s['min_basis_logical_weight_X']}/{s['min_basis_logical_weight_Z']}, "
        f"sched_depth={s['schedule_depth']} (zero_kickback={s['schedule_zero_kickback']}, CNOTs={s['schedule_total_cnots']})"
    )
    lay = build_bb288_thickness2_m4_layout(v["code"])
    print(
        f"  Layout 24x24: L1={lay['n_edges_layer1_local']} (all_unit_torus={lay['layer1_all_unit_torus_distance']}), "
        f"L2={lay['n_edges_layer2_long_range']} (torus_lens={lay['layer2_torus_lengths_pitch']})"
    )
    for ps in lay["pitch_sweep"]:
        print(
            f"    pitch={ps['pitch_um']:4.0f}um: die={ps['block_size_um']}um ({ps['block_area_mm2']} mm2), "
            f"L_max={ps['L_max_um']:5.1f}um, fits_300um={ps['fits_300um_m4_resonator']}, L_sq={ps['L_sq_pH_for_5GHz']} pH/sq"
        )
    dy = compute_bb288_defect_yields()
    for rk, rv in dy.items():
        print(f"  Yield [{rk}] (p_slot={rv['p_slot']}):")
        for nk in ("N6", "N8", "N9", "N10"):
            r = rv["by_N_cand"][nk]
            print(
                f"    {nk}: blk576={r['block_576_yield_pct']:.3f}%, 5-blk(60L)={r['cryo_5block_60L_yield_pct']:.3f}%, "
                f"FeMoco 16-blk={r['femoco_16block_192L_yield_pct']:.3f}% (16/18 spared={r['femoco_16of18_spared_yield_pct']:.3f}%)"
            )
