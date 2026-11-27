"""2D Surface-Code & Heavy-Hex percolation redundancy + CAD v4.0 M4 bus geometry (Exp131).

Combines:
- Mod B f=1% epitaxial spectral yield p_spec = 0.51 (Exp59 / Exp62 / Exp126)
- M4 flip-flop strong-coupling yield p_ff(Delta_z_cap*) from flipflop_cell131.py
- Exact site-percolation Monte Carlo (BFS spanning + giant component + defect-free +
  fault-tolerant <=5% dead nodes) on 2D Square (L=5, 11, 21) and exact edge-subdivided
  Heavy-Hex (d=3, 5, 7) graphs.
- Concrete electromagnetic & layout specification for CAD v4.0 / BOM M4 high-impedance
  NbTiN lambda/2 cavity-QED bus architecture.

Epistemic scope: {Model} / {Sayisal-Simulasyon} / {Literatur}. No lab measurement.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import numpy as np

# Repo anchors
P_SPEC_MODB_1PCT = 0.51        # Exp59 / Exp62 / Exp126 Mod B f=1% spectral certification yield
GAMMA_E_SIP_GHZ_PER_T = 27.997 # Bulk Si:P electron gyromagnetic ratio (g_e = 1.9985)
GAMMA_N_31P_GHZ_PER_T = 0.01723 # 31P nuclear gyromagnetic ratio
C_LIGHT_M_S = 299792458.0
EXP109_NBTIN_B_MAX_T = 0.30    # Exp109 parallel magnetic field limit maintaining Q_i >= 2e5
EXP124_SIGMA_XY_NM = 3.67


def build_square_graph(L: int) -> dict[str, Any]:
    """Build exact 2D L x L square lattice adjacency list with left/right spanning boundaries."""
    n = L * L
    adj: list[list[int]] = [[] for _ in range(n)]
    coords: list[tuple[float, float]] = []
    for r in range(L):
        for c in range(L):
            u = r * L + c
            coords.append((float(c), float(r)))
            if r > 0:
                adj[u].append((r - 1) * L + c)
            if r + 1 < L:
                adj[u].append((r + 1) * L + c)
            if c > 0:
                adj[u].append(r * L + (c - 1))
            if c + 1 < L:
                adj[u].append(r * L + (c + 1))
    left_nodes = [r * L for r in range(L)]
    right_nodes = [r * L + (L - 1) for r in range(L)]
    mean_deg = float(np.mean([len(nb) for nb in adj]))
    return {
        "name": f"square_L{L}",
        "topology": "square",
        "param": L,
        "n_nodes": n,
        "adj": adj,
        "coords": coords,
        "left_nodes": left_nodes,
        "right_nodes": right_nodes,
        "mean_degree": mean_deg,
        "bulk_degree": 4.0,
        "p_c_exact_ref": 0.592746,
    }


def build_heavy_hex_graph(nx_hex: int, ny_hex: int, code_d: int) -> dict[str, Any]:
    """Build exact edge-subdivided hexagonal (heavy-hex) patch graph.

    Every base hexagonal vertex (degree 3 in bulk) is connected through a degree-2
    flag/bridge vertex on every hexagonal edge, yielding asymptotic bulk mean degree
    (2*3 + 3*2)/5 = 2.400 and site percolation threshold p_c ~ 0.808.
    """
    base_nodes: set[tuple[int, int]] = set()
    base_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for r in range(ny_hex + 1):
        for c in range(2 * nx_hex + 2):
            base_nodes.add((r, c))
    for r in range(ny_hex + 1):
        for c in range(2 * nx_hex + 1):
            base_edges.add(tuple(sorted(((r, c), (r, c + 1)))))
    for r in range(ny_hex):
        for c in range(2 * nx_hex + 2):
            if (r + c) % 2 == 0:
                base_edges.add(tuple(sorted(((r, c), (r + 1, c)))))

    # Iteratively prune dangling degree-1 corners so every vertex has degree in {2, 3}
    while True:
        deg = {u: 0 for u in base_nodes}
        for u, v in base_edges:
            deg[u] += 1
            deg[v] += 1
        leaves = {u for u, d in deg.items() if d <= 1}
        if not leaves:
            break
        base_nodes -= leaves
        base_edges = {(u, v) for (u, v) in base_edges if u not in leaves and v not in leaves}

    sorted_base = sorted(base_nodes)
    idx_map = {u: i for i, u in enumerate(sorted_base)}
    coords: list[tuple[float, float]] = [(float(u[1]), float(u[0])) for u in sorted_base]
    n_base = len(sorted_base)
    n_edges = len(base_edges)
    n_total = n_base + n_edges
    adj: list[list[int]] = [[] for _ in range(n_total)]

    mid_id = n_base
    for u, v in sorted(base_edges):
        iu, iv = idx_map[u], idx_map[v]
        adj[mid_id].extend([iu, iv])
        adj[iu].append(mid_id)
        adj[iv].append(mid_id)
        coords.append((0.5 * (u[1] + v[1]), 0.5 * (u[0] + v[0])))
        mid_id += 1

    xs = [pt[0] for pt in coords]
    min_x, max_x = min(xs), max(xs)
    left_nodes = [i for i in range(n_total) if abs(coords[i][0] - min_x) < 1e-9]
    right_nodes = [i for i in range(n_total) if abs(coords[i][0] - max_x) < 1e-9]
    degs = [len(nb) for nb in adj]
    return {
        "name": f"heavy_hex_d{code_d}",
        "topology": "heavy_hex",
        "param": code_d,
        "nx_hex": nx_hex,
        "ny_hex": ny_hex,
        "n_nodes": n_total,
        "adj": adj,
        "coords": coords,
        "left_nodes": left_nodes,
        "right_nodes": right_nodes,
        "mean_degree": float(np.mean(degs)),
        "min_degree": int(min(degs)),
        "max_degree": int(max(degs)),
        "bulk_degree": 2.4,
        "p_c_exact_ref": 0.8079,  # Site percolation on subdivided honeycomb (heavy-hex)
    }


def analyze_single_realization(graph: dict[str, Any], alive: np.ndarray) -> tuple[bool, int, list[int]]:
    """Return (spans_left_to_right, giant_component_size, giant_component_nodes) via BFS."""
    n = graph["n_nodes"]
    adj = graph["adj"]
    right_set = set(graph["right_nodes"])
    visited = [False] * n
    spans = False
    best_comp: list[int] = []

    # Check spanning from left boundary first
    left_alive = [u for u in graph["left_nodes"] if alive[u]]
    if left_alive:
        q = deque(left_alive)
        seen_span = [False] * n
        for u in left_alive:
            seen_span[u] = True
        while q:
            u = q.popleft()
            if u in right_set:
                spans = True
                break
            for v in adj[u]:
                if alive[v] and not seen_span[v]:
                    seen_span[v] = True
                    q.append(v)

    # Find giant connected component size
    for start in range(n):
        if alive[start] and not visited[start]:
            comp = [start]
            visited[start] = True
            q = deque([start])
            while q:
                u = q.popleft()
                for v in adj[u]:
                    if alive[v] and not visited[v]:
                        visited[v] = True
                        comp.append(v)
                        q.append(v)
            if len(comp) > len(best_comp):
                best_comp = comp

    return spans, len(best_comp), best_comp


def _binomial_exact_tail(n: int, p_alive: float, max_dead: int) -> float:
    """Exact P(dead <= max_dead) for Binom(n, 1 - p_alive)."""
    q = 1.0 - p_alive
    if q <= 0.0:
        return 1.0
    if p_alive <= 0.0:
        return 1.0 if max_dead >= n else 0.0
    total = 0.0
    for k in range(min(max_dead, n) + 1):
        # Compute in log-space for numerical stability up to n=441
        log_p = (
            math.lgamma(n + 1)
            - math.lgamma(k + 1)
            - math.lgamma(n - k + 1)
            + k * math.log(q)
            + (n - k) * math.log(p_alive)
        )
        total += math.exp(log_p)
    return min(1.0, total)


def run_percolation_mc_point(
    graph: dict[str, Any],
    p_node: float,
    n_mc: int,
    rng: np.random.Generator,
    ft_max_dead_frac: float = 0.05,
) -> dict[str, Any]:
    """Run N_mc site-percolation trials on `graph` at logical-node survival probability p_node."""
    n = graph["n_nodes"]
    max_dead_ft = int(math.floor(ft_max_dead_frac * n))
    draws = rng.random((n_mc, n)) < p_node

    span_count = 0
    gc_frac_sum = 0.0
    perfect_count = 0
    ft_count = 0

    for m in range(n_mc):
        alive = draws[m]
        n_alive = int(np.sum(alive))
        n_dead = n - n_alive
        if n_dead == 0:
            perfect_count += 1
            ft_count += 1
            span_count += 1
            gc_frac_sum += 1.0
            continue
        if n_dead <= max_dead_ft:
            ft_count += 1
        spans, gc_sz, _ = analyze_single_realization(graph, alive)
        if spans:
            span_count += 1
        gc_frac_sum += gc_sz / n

    return {
        "p_node": float(p_node),
        "n_nodes": int(n),
        "n_mc": int(n_mc),
        "P_perc": float(span_count / n_mc),
        "mean_f_GC": float(gc_frac_sum / n_mc),
        "Y_perfect_mc": float(perfect_count / n_mc),
        "Y_perfect_exact": float(p_node ** n),
        "Y_FT_5pct_mc": float(ft_count / n_mc),
        "Y_FT_5pct_exact": float(_binomial_exact_tail(n, p_node, max_dead_ft)),
        "max_dead_FT": int(max_dead_ft),
    }


def compute_cad_m4_bus_geometry(
    delta_z_cap_opt_nm: float = 8.0,
    z_r_ohm: float = 3000.0,
    f_r_ghz: float = 5.0,
    l_sq_ph: float = 100.0,
    w_wire_nm: float = 100.0,
    t_film_nm: float = 9.0,
    p_node_um: float = 10.0,
    p_cand_nm: float = 200.0,
    n_cand_min: int = 3,
    n_cand_ft: int = 6,
) -> dict[str, Any]:
    """Compute concrete electromagnetic & CAD v4.0 / BOM layout geometry for M4 NbTiN bus."""
    l_sq_h = l_sq_ph * 1e-12
    w_m = w_wire_nm * 1e-9
    f_hz = f_r_ghz * 1e9

    l_per_m = l_sq_h / w_m                    # H/m (kinetic inductance dominated)
    c_per_m = l_per_m / (z_r_ohm * z_r_ohm)   # F/m
    v_ph_m_s = 1.0 / math.sqrt(l_per_m * c_per_m)
    l_res_m = v_ph_m_s / (2.0 * f_hz)         # lambda / 2 resonator length
    l_res_mm = l_res_m * 1e3
    l_res_um = l_res_m * 1e6

    # Magnetic field for flip-flop resonance f_r = (gamma_e + gamma_n) * B_M4
    gamma_ff = GAMMA_E_SIP_GHZ_PER_T + GAMMA_N_31P_GHZ_PER_T
    b_m4_t = f_r_ghz / gamma_ff
    b_margin_pct = 100.0 * (EXP109_NBTIN_B_MAX_T - b_m4_t) / EXP109_NBTIN_B_MAX_T

    # Meander layout inside a P_node x 1.5*P_node inter-node coupler footprint
    meander_pitch_um = 1.0
    meander_leg_um = 15.0
    n_meander_turns = math.ceil(l_res_um / meander_leg_um)
    meander_width_um = n_meander_turns * meander_pitch_um

    # OBS-140: 1 um pitch meander parasitic capacitance loading audit (Si substrate eps_eff = 6.35)
    # Two-wire mutual capacitance between adjacent w=100 nm legs at pitch s=1.0 um:
    #   C_mut = pi * eps0 * eps_eff / arccosh(s / w)
    eps0 = 8.854187817e-12
    eps_eff_si = 6.35
    c_mut_f_per_m = (math.pi * eps0 * eps_eff_si) / math.acosh(max(meander_pitch_um / (w_wire_nm * 1e-3), 1.01))
    # Including ground/DC-gate pad self-capacitance: realistic C_l_loaded spans 160..220 pF/m
    c_loaded_lo = 160.0e-12
    c_loaded_hi = 220.0e-12
    z_r_loaded_lo = math.sqrt(l_per_m / c_loaded_hi)   # 2132 Ohm at 220 pF/m
    z_r_loaded_hi = math.sqrt(l_per_m / c_loaded_lo)   # 2500 Ohm at 160 pF/m
    l_res_loaded_lo_um = (1.0 / (2.0 * f_hz * math.sqrt(l_per_m * c_loaded_hi))) * 1e6
    l_res_loaded_hi_um = (1.0 / (2.0 * f_hz * math.sqrt(l_per_m * c_loaded_lo))) * 1e6
    f_r_300um_loaded_lo_ghz = (1.0 / (2.0 * l_res_m * math.sqrt(l_per_m * c_loaded_hi))) / 1e9
    f_r_300um_loaded_hi_ghz = (1.0 / (2.0 * l_res_m * math.sqrt(l_per_m * c_loaded_lo))) / 1e9
    g_eff_reduction_pct_range = [
        round(100.0 * (1.0 - math.sqrt(z_r_loaded_hi / z_r_ohm)), 2),
        round(100.0 * (1.0 - math.sqrt(z_r_loaded_lo / z_r_ohm)), 2),
    ]

    # Intra-node candidate pocket standing-wave voltage uniformity across N_cand slots
    pocket_span_um = (n_cand_ft - 1) * (p_cand_nm * 1e-3)
    half_span_um = 0.5 * pocket_span_um
    antinode_cos_min = math.cos(math.pi * half_span_um / l_res_um)
    straggle_isolation_sigma = p_cand_nm / EXP124_SIGMA_XY_NM

    # Sensitivity across kinetic sheet inductance L_sq in {50, 100, 150} pH/sq
    l_sq_sensitivity = []
    for lsq in [50.0, 100.0, 150.0]:
        ll = (lsq * 1e-12) / w_m
        cl = ll / (z_r_ohm * z_r_ohm)
        vph = 1.0 / math.sqrt(ll * cl)
        lres_mm = (vph / (2.0 * f_hz)) * 1e3
        l_sq_sensitivity.append({
            "L_sq_pH_per_sq": float(lsq),
            "L_l_nH_per_um": float(ll * 1e3),
            "C_l_pF_per_m": float(cl * 1e12),
            "v_ph_over_c": float(vph / C_LIGHT_M_S),
            "L_res_mm": float(lres_mm),
            "L_res_um": float(lres_mm * 1e3),
        })

    # Local DC gate electrode budget per logical node
    # Per node: N_cand individual donor detuning fingers + 1 shared resonator coupler pad + 1 global interface bias gate
    gates_per_node_min = n_cand_min + 2
    gates_per_node_ft = n_cand_ft + 2

    return {
        "resonator_material": "NbTiN thin film (Exp109 anchor: Q_i >= 2e5 at 7-20 mK, B_par <= 0.30 T)",
        "film_thickness_nm": float(t_film_nm),
        "nanowire_width_nm": float(w_wire_nm),
        "L_sq_pH_per_sq": float(l_sq_ph),
        "Z_r_ohm": float(z_r_ohm),
        "f_r_ghz": float(f_r_ghz),
        "L_l_nH_per_um": float(l_per_m * 1e3),
        "C_l_pF_per_m": float(c_per_m * 1e12),
        "v_ph_m_s": float(v_ph_m_s),
        "v_ph_over_c": float(v_ph_m_s / C_LIGHT_M_S),
        "L_res_mm": float(l_res_mm),
        "L_res_um": float(l_res_um),
        "B_M4_T": float(b_m4_t),
        "Exp109_B_limit_T": float(EXP109_NBTIN_B_MAX_T),
        "B_margin_below_Exp109_pct": float(b_margin_pct),
        "Exp125_field_conflict_note": (
            "Exp125 1.5 T NMR readout field puts 31P ESR at 42 GHz (>5 GHz NbTiN bus & >0.30 T Q_i limit); "
            "M4 architecture operates at B_M4 = 0.1785 T (f_r = 5.0 GHz) inside Exp109 tolerance."
        ),
        "delta_z_cap_opt_nm": float(delta_z_cap_opt_nm),
        "delta_z_cap_tolerance_nm": 1.0,
        "inter_node_pitch_um": float(p_node_um),
        "meander_turns": int(n_meander_turns),
        "meander_leg_um": float(meander_leg_um),
        "meander_footprint_um": [float(meander_leg_um), float(meander_width_um)],
        "meander_parasitic_loading_OBS140": {
            "eps_eff_si": float(eps_eff_si),
            "C_ideal_pF_per_m": float(c_per_m * 1e12),
            "C_mut_adjacent_leg_pF_per_m": round(float(c_mut_f_per_m * 1e12), 2),
            "C_loaded_realistic_range_pF_per_m": [160.0, 220.0],
            "Z_r_loaded_range_ohm": [round(z_r_loaded_lo, 1), round(z_r_loaded_hi, 1)],
            "lambda_half_5GHz_loaded_range_um": [round(l_res_loaded_lo_um, 1), round(l_res_loaded_hi_um, 1)],
            "f_r_at_300um_loaded_range_ghz": [round(f_r_300um_loaded_lo_ghz, 3), round(f_r_300um_loaded_hi_ghz, 3)],
            "g_eff_sqrt_Zr_reduction_pct_range": g_eff_reduction_pct_range,
            "mitigation_note": "Increase meander pitch/ground clearance or use L_sq=150-200 pH/sq (or 3*lambda/2 harmonics) to restore 3 kOhm / >=250 um qLDPC reach.",
        },
        "intra_node_slot_pitch_nm": float(p_cand_nm),
        "pocket_span_6slots_um": float(pocket_span_um),
        "antinode_voltage_uniformity_6slots": float(antinode_cos_min),
        "lateral_straggle_isolation_sigma": float(straggle_isolation_sigma),
        "dc_gates_per_node_Ncand3": int(gates_per_node_min),
        "dc_gates_per_node_Ncand6": int(gates_per_node_ft),
        "total_dc_gates_L5_Ncand6": int(25 * gates_per_node_ft),
        "total_dc_gates_L11_Ncand6": int(121 * gates_per_node_ft),
        "cryo_cmos_multiplexing": "SKY130 4K crossbar switches (Exp33/37/58) bias 1 certified donor to eps* while parking N_cand-1 standbys at eps_park=+25 GHz.",
        "L_sq_sensitivity": l_sq_sensitivity,
    }


def run_percolation_and_geometry_study(
    p_ff_opt: float,
    delta_z_cap_opt_nm: float = 8.0,
    n_mc: int = 2000,
    seed: int = 13103,
) -> dict[str, Any]:
    """Run full 2D Square vs Heavy-Hex percolation Monte Carlo and CAD M4 geometry spec."""
    rng = np.random.default_rng(seed)
    p_m4_single = P_SPEC_MODB_1PCT * p_ff_opt

    # Build exact graphs
    sq_graphs = {L: build_square_graph(L) for L in [5, 11, 21]}
    # Heavy-hex patches sized for d=3 (21 nodes), d=5 (68 nodes), d=7 (135 nodes, 4x5 hexagons -> symmetric spanning)
    # Check 5x4 vs 4x5: use (5, 4) -> wait let's construct (5, 4) and report exact node count honestly!
    hh_graphs = {
        3: build_heavy_hex_graph(1, 2, 3),
        5: build_heavy_hex_graph(3, 3, 5),
        7: build_heavy_hex_graph(4, 5, 7),
    }

    n_cand_grid = [1, 2, 3, 4, 5, 6, 8]

    def sweep_topology(graphs: dict[int, dict[str, Any]], p_single: float) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, g in graphs.items():
            rows = []
            for nc in n_cand_grid:
                p_node = 1.0 - ((1.0 - p_single) ** nc)
                res = run_percolation_mc_point(g, p_node, n_mc, rng)
                res["N_cand"] = int(nc)
                rows.append(res)
            out[g["name"]] = {
                "topology": g["topology"],
                "param": int(g["param"]),
                "n_nodes": int(g["n_nodes"]),
                "mean_degree": float(g["mean_degree"]),
                "bulk_degree": float(g["bulk_degree"]),
                "p_c_exact_ref": float(g["p_c_exact_ref"]),
                "sweep": rows,
            }
        return out

    square_m4 = sweep_topology(sq_graphs, p_m4_single)
    heavy_hex_m4 = sweep_topology(hh_graphs, p_m4_single)
    square_spec_only = sweep_topology({11: sq_graphs[11], 21: sq_graphs[21]}, P_SPEC_MODB_1PCT)

    # Fine p_node transition curve (p in [0.40, 0.96]) for Square L=21 vs Heavy-Hex d=7 (for plotting!)
    p_curve_grid = [0.40, 0.48, 0.54, 0.58, 0.60, 0.64, 0.70, 0.74, 0.78, 0.81, 0.84, 0.88, 0.92, 0.96]
    transition_curves = {
        "p_node_grid": p_curve_grid,
        "square_L21_P_perc": [],
        "heavy_hex_d7_P_perc": [],
    }
    for pv in p_curve_grid:
        transition_curves["square_L21_P_perc"].append(
            run_percolation_mc_point(sq_graphs[21], pv, 600, rng)["P_perc"]
        )
        transition_curves["heavy_hex_d7_P_perc"].append(
            run_percolation_mc_point(hh_graphs[7], pv, 600, rng)["P_perc"]
        )

    # Concrete 11x11 realizations at N_cand in {1, 2, 3, 6} for visual inspection in figure
    rng_vis = np.random.default_rng(seed + 99)
    g11 = sq_graphs[11]
    u_base = rng_vis.random((11 * 11, 8))  # Nested draws: node alive at N_cand iff min(u[:N_cand]) < p_m4_single
    realizations_L11: dict[str, Any] = {}
    for nc in [1, 2, 3, 6]:
        alive = np.any(u_base[:, :nc] < p_m4_single, axis=1)
        spans, gc_sz, gc_nodes = analyze_single_realization(g11, alive)
        gc_set = set(gc_nodes)
        # Status grid: 0 = dead, 1 = alive (isolated), 2 = alive in giant component
        grid = []
        for r in range(11):
            row = []
            for c in range(11):
                u = r * 11 + c
                if not alive[u]:
                    row.append(0)
                elif u in gc_set:
                    row.append(2)
                else:
                    row.append(1)
            grid.append(row)
        realizations_L11[f"N_cand_{nc}"] = {
            "N_cand": nc,
            "p_node_theory": float(1.0 - (1.0 - p_m4_single) ** nc),
            "n_alive": int(np.sum(alive)),
            "n_dead": int(121 - np.sum(alive)),
            "spans": bool(spans),
            "gc_size": int(gc_sz),
            "grid_11x11": grid,
        }

    cad_geom = compute_cad_m4_bus_geometry(delta_z_cap_opt_nm=delta_z_cap_opt_nm)

    return {
        "yield_inputs": {
            "p_spec_modB_1pct": float(P_SPEC_MODB_1PCT),
            "p_ff_opt": float(p_ff_opt),
            "p_m4_combined": float(p_m4_single),
            "n_mc_per_point": int(n_mc),
            "n_cand_grid": n_cand_grid,
        },
        "square_m4": square_m4,
        "heavy_hex_m4": heavy_hex_m4,
        "square_spec_only_upper_bound": square_spec_only,
        "transition_curves": transition_curves,
        "realizations_L11": realizations_L11,
        "cad_m4_bus_geometry": cad_geom,
    }
