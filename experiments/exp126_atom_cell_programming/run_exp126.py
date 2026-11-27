"""Exp126 master runner: Full 32D GRAPE + Interleaved XY8/CPMG Risk R3 Closure + 16-Cell Atom Programmability.

Reads pre-registered predictions from results/exp126_atom_cell_programming/predictions_exp126.json
and writes complete verified numerical outputs + waveforms to results/exp126_atom_cell_programming/exp126.json.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

import grape_dd126 as g126
import hamiltonian126 as h126
import programs126 as p126

OUT_DIR = h126.repo_root() / "results" / "exp126_atom_cell_programming"
PRED_PATH = OUT_DIR / "predictions_exp126.json"
OUT_JSON = OUT_DIR / "exp126.json"


def _exp63_analytical_table() -> Dict[str, Dict[str, float]]:
    """Load exact Exp63 analytical Q63 benchmarks directly from results/exp63/exp63.json."""
    e63 = json.loads((h126.repo_root() / "results" / "exp63" / "exp63.json").read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, float]] = {}
    for key, c in e63["cells"].items():
        out[key] = {
            "abundance_pct": float(c["abundance_pct"]),
            "yield_frac": float(c["yield_frac"]),
            "T2e_ms": float(c["T2e_s"] * 1e3),
            "Q_exp62_interp": float(c["Q_exp62"]),
            "Q63": {k: float(v) for k, v in c["Q63"].items()},
        }
    return out


def _evaluate_xy8_vs_cpmg_systematic(
    lib_xy8: g126.CellPulseLibrary,
    dev: torch.device,
    n_traj: int = 256,
) -> Dict[str, object]:
    """Compare XY8 vs CPMG under systematic electron pi-pulse over-rotation on X-axis and Y-axis GHZ states."""
    cell = lib_xy8.cell
    # Build matching CPMG waveforms (same RF controls, CPMG X-only electron pi axis sequence!)
    cx_cpmg: Dict[int, g126.PulseWaveform] = {}
    for k in range(4):
        wf = lib_xy8.cx_e_to_n[k]
        cx_cpmg[k] = g126.PulseWaveform(
            gate_name=wf.gate_name, target_qubit=wf.target_qubit, duration_us=wf.duration_us,
            n_slices=wf.n_slices, n_dd=wf.n_dd, dd_sequence="CPMG", carrier_offset_hz=wf.carrier_offset_hz,
            controls_khz=wf.controls_khz.copy(), bound_khz=wf.bound_khz,
            apply_virtual_rze_neg_pi2=wf.apply_virtual_rze_neg_pi2,
            virtual_z_nuc_rad=wf.virtual_z_nuc_rad.copy(),
        )

    # GHZ_X: H_e |0_e> = (|0_e> + |1_e>)/sqrt(2) -> (|0_e 1111> + |1_e 0000>)/sqrt(2)
    # GHZ_Y: Rx_e(-pi/2) |0_e> = (|0_e> + i|1_e>)/sqrt(2) -> (|0_e 1111> + i|1_e 0000>)/sqrt(2)
    # Note: CPMG (all X pulses) commutes with X-axis states but FAILS catastrophically on Y-axis states!
    prog_x_xy8 = p126.compile_program("GHZ-4", lib_xy8)
    prog_x_cpmg = p126.compile_program("GHZ-4", lib_xy8, cx_override=cx_cpmg)

    ideal_y = np.zeros(32, dtype=np.complex128)
    ideal_y[15] = 1.0 / math.sqrt(2.0)
    ideal_y[16] = 1.0j / math.sqrt(2.0)

    def make_ghz_y(cx_map):
        ops_y = [p126._e_rot("X", -0.5 * math.pi)] + [p126._rf(cx_map[k]) for k in range(4)]
        tot_us, esup_us, n_rf, n_dd, n_2q = p126._schedule_stats(ops_y)
        return p126.CompiledProgram(
            name="GHZ-4-Y", cell_id=cell.cell_id, ops=ops_y, ideal_state_32d=ideal_y,
            total_duration_us=tot_us, electron_superposition_us=esup_us,
            n_rf_pulses=n_rf, n_dd_electron_pi_pulses=n_dd, n_two_qubit_blocks=n_2q,
        )

    prog_y_xy8 = make_ghz_y(lib_xy8.cx_e_to_n)
    prog_y_cpmg = make_ghz_y(cx_cpmg)

    delta_thetas = [0.0, 2.0 * math.sqrt(2.5e-4), 2.0 * math.sqrt(1e-3), 0.10]
    rows = []
    for dt_sys in delta_thetas:
        rx_xy8 = p126.execute_program_32d(prog_x_xy8, lib_xy8, noise_alpha=2.0, eps_stoch=0.0,
                                          delta_theta_sys=dt_sys, n_traj=n_traj, seed=12671, device=dev)
        rx_cpmg = p126.execute_program_32d(prog_x_cpmg, lib_xy8, noise_alpha=2.0, eps_stoch=0.0,
                                           delta_theta_sys=dt_sys, n_traj=n_traj, seed=12671, device=dev)
        # For GHZ-4-Y, execute and multiply coherence by same spectator overlap
        spec_ovl = rx_xy8["spectator_overlap_all"]
        ry_xy8_raw = p126.execute_program_32d(prog_y_xy8, lib_xy8, noise_alpha=2.0, eps_stoch=0.0,
                                              delta_theta_sys=dt_sys, n_traj=n_traj, seed=12672,
                                              include_spectator_overlap=False, device=dev)
        ry_cpmg_raw = p126.execute_program_32d(prog_y_cpmg, lib_xy8, noise_alpha=2.0, eps_stoch=0.0,
                                               delta_theta_sys=dt_sys, n_traj=n_traj, seed=12672,
                                               include_spectator_overlap=False, device=dev)
        # Apply spectator overlap factor conservatively to coherence component
        fy_xy8 = float(0.5 + (ry_xy8_raw["fidelity"] - 0.5) * spec_ovl) if ry_xy8_raw["fidelity"] > 0.5 else float(ry_xy8_raw["fidelity"])
        fy_cpmg = float(0.5 + (ry_cpmg_raw["fidelity"] - 0.5) * spec_ovl) if ry_cpmg_raw["fidelity"] > 0.5 else float(ry_cpmg_raw["fidelity"])
        rows.append({
            "delta_theta_rad": float(dt_sys),
            "equiv_single_pulse_eps": float(math.sin(dt_sys / 2.0) ** 2),
            "ghz_x_xy8": float(rx_xy8["fidelity"]),
            "ghz_x_cpmg": float(rx_cpmg["fidelity"]),
            "ghz_y_xy8": float(fy_xy8),
            "ghz_y_cpmg": float(fy_cpmg),
            "min_axis_xy8": float(min(rx_xy8["fidelity"], fy_xy8)),
            "min_axis_cpmg": float(min(rx_cpmg["fidelity"], fy_cpmg)),
            "xy8_advantage_y": float(fy_xy8 - fy_cpmg),
        })
    return {"n_total_pulses": 64, "n_traj": n_traj, "sweep": rows}


def _evaluate_native_ccz_f1(lib: g126.CellPulseLibrary, dev: torch.device) -> Dict[str, float]:
    """Verify native 3-body electron-hub CCZ(0,1,2) in full 32D noiseless subspace."""
    ops_ccz = p126.emit_ccz_012(lib)
    basis = torch.zeros((16, 32), dtype=torch.complex128, device=dev)
    for idx in range(16):
        basis[idx, idx] = 1.0
    out = p126._apply_ops_32d(basis, ops_ccz, lib.cell, device=dev).cpu().numpy()
    U_sub = out[:, :16].T
    U_id = np.eye(16, dtype=np.complex128)
    for idx in range(16):
        if ((idx >> 3) & 1) == 1 and ((idx >> 2) & 1) == 1 and ((idx >> 1) & 1) == 1:
            U_id[idx, idx] = -1.0
    f_proc = float((abs(np.sum(U_id.conj() * U_sub)) / 16.0) ** 2)
    leak = float(np.max(np.sum(np.abs(out[:, 16:]) ** 2, axis=1)))
    tot_us, esup_us, n_rf, n_dd, _ = p126._schedule_stats(ops_ccz)
    return {
        "subspace_process_fidelity": f_proc,
        "max_electron_leakage": leak,
        "total_duration_us": float(tot_us),
        "electron_superposition_us": float(esup_us),
        "n_rf_pulses": int(n_rf),
        "n_dd_pulses": int(n_dd),
    }


def _ddrf_headroom_diagnostic(f1: h126.CellSpec, dev: torch.device) -> Dict[str, object]:
    """Quantify bare GAUSS500 DDRF spectator crosstalk collapse vs GRAPE RF Rabi headroom on F1 k=3."""
    M, T = 64, 500e-6
    dt = T / M
    x = (np.arange(M) + 0.5) / M
    raw = np.exp(-0.5 * ((x - 0.5) / (1.0 / 6.0)) ** 2)
    ux = raw * (0.5 / (dt * float(np.sum(raw)))) / 1e3
    ctrl_gauss = np.stack([ux, np.zeros(M)], axis=1)

    gauss_rows = []
    for n_dd in (0, 2, 4, 8, 16, 32):
        ev = g126.evaluate_gate_32d(f1, ctrl_gauss, "cX", 3, 500.0, n_dd, "XY8",
                                    offsets_hz=(0.0,), scales=(1.0,), device=dev)
        gauss_rows.append({
            "n_dd_per_gate": int(n_dd),
            "f_mod_kHz": float(n_dd / (2.0 * 0.5)),
            "nominal_fidelity_32d": float(ev["nominal_fidelity_32d"]),
            "min_spectator_retention_nom": float(ev["min_spectator_retention_nom"]),
            "spectator_overlap_all448": float(ev["spectator_overlap_all_nom"]),
        })

    grape_rows = []
    for bnd in (5.0, 10.0, 15.0):
        wf = g126.synthesize_gate_grape(
            f1, "cX", target_qubit=3, duration_us=500.0, n_slices=64, n_dd=16, dd_sequence="XY8",
            bound_khz=bnd, stage1_iters=200, stage2_iters=55, device=dev,
        )
        grape_rows.append({
            "bound_kHz": float(bnd),
            "nominal_fidelity_32d": float(wf.nominal_fidelity_32d),
            "worst_corner_fidelity_32d": float(wf.worst_corner_fidelity_32d),
            "min_spectator_retention_nom": float(wf.min_spectator_retention_nom),
            "min_spectator_retention_all": float(wf.min_spectator_retention_all),
            "spectator_overlap_all448": float(wf.spectator_overlap_all_nom),
            "max_amp_kHz": float(wf.max_amp_khz),
        })
    return {"target": "F1_q3_min_gap_6.89kHz", "gauss500_vs_ndd": gauss_rows, "grape_ndd16_vs_bound": grape_rows}


def main() -> None:
    t_start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dev = g126.get_device()
    print(f"=== EXP126 START on device={dev} ===", flush=True)

    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    exp63_ref = _exp63_analytical_table()

    # -----------------------------------------------------------------------
    # PART 1: Universal Gate Set + All 6 CZ/CNOT Pairs + DDRF Headroom on F1
    # -----------------------------------------------------------------------
    print("\n--- PART 1: F1 Universal Gate Set & Two-Qubit Entanglers ---", flush=True)
    finalists = h126.load_exp62_finalists(verify_lie=True)
    f1 = finalists["F1"]

    lib_f1 = g126.synthesize_cell_library(
        f1, cx_n_dd=16, cx_sequence="XY8", duration_us=500.0, n_slices=64,
        bound_khz=15.0, native_ry_and_x=True, stage1_iters=240, stage2_iters=70, device=dev,
    )
    f1_gates_summary: Dict[str, List[Dict[str, object]]] = {}
    f1_waveforms_serialized: Dict[str, Dict[str, object]] = {}
    for gname, gmap in [("Rx_pi2", lib_f1.rx_pi2), ("Ry_pi2", lib_f1.ry_pi2),
                        ("X", lib_f1.x_gate), ("cX_XY8_16", lib_f1.cx_e_to_n)]:
        rows = []
        for k in range(4):
            w = gmap[k]
            rows.append(w.to_summary_dict())
            # Save full waveforms for F1 so fig_exp126 and tests can independently verify propagation!
            f1_waveforms_serialized[f"{gname}_q{k}"] = {
                "gate_name": w.gate_name,
                "target_qubit": int(w.target_qubit),
                "duration_us": float(w.duration_us),
                "n_slices": int(w.n_slices),
                "n_dd": int(w.n_dd),
                "dd_sequence": w.dd_sequence,
                "controls_khz": [[float(a), float(b)] for a, b in w.controls_khz],
                "corner_fidelities": [float(x) for x in w.corner_fidelities],
                "nominal_fidelity_32d": float(w.nominal_fidelity_32d),
                "worst_corner_fidelity_32d": float(w.worst_corner_fidelity_32d),
                "max_unitarity_err_fro": float(w.max_unitarity_err_fro),
            }
            print(f"  F1 {gname:10s} q{k}: nom={w.nominal_fidelity_32d:.5f}, worst={w.worst_corner_fidelity_32d:.5f}, "
                  f"u_err={w.max_unitarity_err_fro:.1e}, sp_nom={w.min_spectator_retention_nom:.5f}, sp_ovl={w.spectator_overlap_all_nom:.5f}", flush=True)
        f1_gates_summary[gname] = rows

    # DDRF headroom diagnostic on hardest F1 target k=3
    ddrf_diag = _ddrf_headroom_diagnostic(f1, dev)
    print("  DDRF headroom diag done.", flush=True)

    # All 6 nuclear pairs CZ and CNOT on F1 (noiseless + noisy alpha=2, eps=1e-3)
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    cz_ideal_list, cnot_ideal_list, cz_noisy_list = [], [], []
    for idx_p, (i, j) in enumerate(pairs):
        cz_i = p126.evaluate_two_qubit_gate_32d(lib_f1, i, j, "CZ", device=dev)
        cn_i = p126.evaluate_two_qubit_gate_32d(lib_f1, i, j, "CNOT", device=dev)
        cz_n = p126.evaluate_two_qubit_gate_32d(lib_f1, i, j, "CZ", noise_alpha=2.0, eps_stoch=1e-3,
                                                n_traj=48, seed=12650 + idx_p, device=dev)
        cz_ideal_list.append(cz_i)
        cnot_ideal_list.append(cn_i)
        cz_noisy_list.append(cz_n)
        print(f"  Pair ({i},{j}): CZ_id={cz_i['subspace_process_fidelity']:.5f} (leak={cz_i['max_electron_leakage']:.1e}), "
              f"CNOT_id={cn_i['subspace_process_fidelity']:.5f}, CZ_noisy_a2={cz_n['noisy_process_fidelity_mean']:.5f}", flush=True)

    ccz_f1 = _evaluate_native_ccz_f1(lib_f1, dev)
    print(f"  Native 3-body CCZ(0,1,2) F1 ideal: F_proc={ccz_f1['subspace_process_fidelity']:.5f}, leak={ccz_f1['max_electron_leakage']:.1e}", flush=True)

    # -----------------------------------------------------------------------
    # PART 2: Risk R3 Hamiltonian Closure (Hahn Echo + Interleaved XY8 vs Exp63 + XY8 vs CPMG)
    # -----------------------------------------------------------------------
    print("\n--- PART 2: Risk R3 Interleaved XY8 vs Exp63 & XY8 vs CPMG ---", flush=True)
    hahn_cal: Dict[str, Dict[str, Dict[str, float]]] = {}
    d0_finalists: Dict[str, Dict[str, Dict[str, float]]] = {}
    for key in ("F0.5", "F1", "F2", "F4.7"):
        cell = finalists[key]
        d0_finalists[key] = h126.exact_d0_storage_leakage(cell.A_hz, cell.J_hz, (17.5, 175.0))
        hahn_cal[key] = {}
        for alpha in (1.0, 2.0):
            he = g126.run_hahn_echo_32d(cell, alpha=alpha, n_traj=512, seed=12610 + int(alpha * 10), device=dev)
            hahn_cal[key][f"alpha_{alpha:g}"] = he
            print(f"  Hahn echo {key:4s} a={alpha:g}: W={he['coherence_W']:.4f} vs 1/e={he['target_inv_e']:.4f} (err={he['abs_err']:.4f})", flush=True)

    # Full N_total sweep on F1: N_dd_gate in {0, 2, 4, 8, 16, 32} => N_total in {0, 8, 16, 32, 64, 128}
    f1_cx_by_ndd: Dict[int, Dict[int, g126.PulseWaveform]] = {16: lib_f1.cx_e_to_n}
    for n_dd_g in (0, 2, 4, 8, 32):
        seq = "NONE" if n_dd_g == 0 else "XY8"
        f1_cx_by_ndd[n_dd_g] = {}
        for k in range(4):
            f1_cx_by_ndd[n_dd_g][k] = g126.synthesize_gate_grape(
                f1, "cX", k, duration_us=500.0, n_slices=64, n_dd=n_dd_g, dd_sequence=seq,
                bound_khz=15.0, stage1_iters=160, stage2_iters=35, device=dev,
            )
        print(f"  F1 cX synthesized for n_dd_gate={n_dd_g} (N_total={4*n_dd_g})", flush=True)

    f1_dd_sweep = []
    for n_dd_g in (0, 2, 4, 8, 16, 32):
        n_tot = 4 * n_dd_g
        prog = p126.compile_program("GHZ-4", lib_f1, cx_override=f1_cx_by_ndd[n_dd_g])
        res_id = p126.execute_program_32d(prog, lib_f1, device=dev)
        entry: Dict[str, object] = {
            "n_dd_per_gate": int(n_dd_g),
            "N_total": int(n_tot),
            "ideal_fidelity_with_spec": float(res_id["fidelity"]),
            "spectator_overlap_all448": float(res_id["spectator_overlap_all"]),
            "results": {},
        }
        for alpha in (1.0, 2.0):
            for eps in (0.0, 1e-3, 1e-2):
                r = p126.execute_program_32d(
                    prog, lib_f1, noise_alpha=alpha, eps_stoch=eps, n_traj=256,
                    seed=126200 + n_tot * 10 + int(alpha), device=dev,
                )
                kstr = f"a{alpha:g}_e{eps:g}"
                exp63_key = f"a{alpha:g}_N{n_tot}_e{eps:g}"
                q63_val = exp63_ref["F1"]["Q63"].get(exp63_key)
                entry["results"][kstr] = {
                    "Q_32d": float(r["fidelity"]),
                    "Q_32d_active_only": float(r["fidelity_32d_active_only"]),
                    "Q_exp63_beta1": float(q63_val) if q63_val is not None else None,
                }
        f1_dd_sweep.append(entry)
        r_a1 = entry["results"]["a1_e0.001"]["Q_32d"]
        r_a2 = entry["results"]["a2_e0.001"]["Q_32d"]
        r_e2 = entry["results"]["a2_e0.01"]["Q_32d"]
        print(f"  F1 GHZ-4 N={n_tot:3d}: ideal={res_id['fidelity']:.4f} (sp={res_id['spectator_overlap_all']:.4f}), "
              f"a1/e-3={r_a1:.4f}, a2/e-3={r_a2:.4f}, a2/e-2={r_e2:.4f}", flush=True)

    # Multi-abundance comparison across ALL 4 Exp62 finalists (F0.5, F1, F2, F4.7) at N_total in {0, 64, 128}
    abundance_dd_table: Dict[str, Dict[str, object]] = {}
    for key in ("F0.5", "F1", "F2", "F4.7"):
        cell = finalists[key]
        if key == "F1":
            cx_sets = {0: f1_cx_by_ndd[0], 16: f1_cx_by_ndd[16], 32: f1_cx_by_ndd[32]}
            dummy_lib = lib_f1
        else:
            cx_sets = {}
            for n_dd_g in (0, 16, 32):
                seq = "NONE" if n_dd_g == 0 else "XY8"
                cx_sets[n_dd_g] = {
                    k: g126.synthesize_gate_grape(
                        cell, "cX", k, duration_us=500.0, n_slices=64, n_dd=n_dd_g, dd_sequence=seq,
                        bound_khz=15.0, stage1_iters=160, stage2_iters=30, device=dev,
                    )
                    for k in range(4)
                }
            dummy_lib = g126.CellPulseLibrary(cell=cell, rx_pi2={}, ry_pi2={}, x_gate={}, cx_e_to_n=cx_sets[16])

        cell_rec: Dict[str, object] = {
            "abundance_pct": float(cell.abundance_pct),
            "T2e_ms": float(cell.t2e_s * 1e3),
            "yield_frac_exp59_62": float(exp63_ref[key]["yield_frac"]),
            "N_runs": {},
        }
        for n_dd_g in (0, 16, 32):
            n_tot = 4 * n_dd_g
            prog = p126.compile_program("GHZ-4", dummy_lib, cx_override=cx_sets[n_dd_g])
            r_id = p126.execute_program_32d(prog, dummy_lib, device=dev)
            r_a1 = p126.execute_program_32d(prog, dummy_lib, noise_alpha=1.0, eps_stoch=1e-3,
                                            n_traj=256, seed=126300 + n_tot, device=dev)
            r_a2 = p126.execute_program_32d(prog, dummy_lib, noise_alpha=2.0, eps_stoch=1e-3,
                                            n_traj=256, seed=126350 + n_tot, device=dev)
            r_a2_ideal_pi = p126.execute_program_32d(prog, dummy_lib, noise_alpha=2.0, eps_stoch=0.0,
                                                     n_traj=256, seed=126390 + n_tot, device=dev)
            cell_rec["N_runs"][f"N{n_tot}"] = {
                "ideal_with_spec": float(r_id["fidelity"]),
                "spectator_overlap_all": float(r_id["spectator_overlap_all"]),
                "Q_32d_a1_e1e3": float(r_a1["fidelity"]),
                "Q_32d_a2_e1e3": float(r_a2["fidelity"]),
                "Q_32d_a2_e0": float(r_a2_ideal_pi["fidelity"]),
                "Q_exp63_a1_e1e3": float(exp63_ref[key]["Q63"][f"a1_N{n_tot}_e0.001"]),
                "Q_exp63_a2_e1e3": float(exp63_ref[key]["Q63"][f"a2_N{n_tot}_e0.001"]),
            }
        abundance_dd_table[key] = cell_rec
        n64 = cell_rec["N_runs"]["N64"]
        print(f"  Abundance {key:4s} N=64: 32D a1={n64['Q_32d_a1_e1e3']:.4f} (Exp63={n64['Q_exp63_a1_e1e3']:.4f}), "
              f"32D a2={n64['Q_32d_a2_e1e3']:.4f} (Exp63={n64['Q_exp63_a2_e1e3']:.4f}), sp_ovl={n64['spectator_overlap_all']:.4f}", flush=True)

    # XY8 vs CPMG systematic pulse over-rotation test
    xy8_vs_cpmg = _evaluate_xy8_vs_cpmg_systematic(lib_f1, dev, n_traj=256)
    for row in xy8_vs_cpmg["sweep"]:
        print(f"  XY8 vs CPMG (dtheta={row['delta_theta_rad']:.4f}): "
              f"GHZ_X XY8={row['ghz_x_xy8']:.4f}/CPMG={row['ghz_x_cpmg']:.4f}, "
              f"GHZ_Y XY8={row['ghz_y_xy8']:.4f}/CPMG={row['ghz_y_cpmg']:.4f} (adv={row['xy8_advantage_y']:+.4f})", flush=True)

    # -----------------------------------------------------------------------
    # PART 3: 16-Cell Heterogeneous Multi-Cell Atom Programmability Proof
    # -----------------------------------------------------------------------
    print("\n--- PART 3: 16 Heterogeneous Certified f=1% Cells x 5 Quantum Programs ---", flush=True)
    cells16 = h126.sample_certified_f1_cells(16, abundance_pct=1.0, include_exp62_f1_first=True)
    all_A_flat = np.concatenate([c.A_hz for c in cells16])
    a_cv = float(np.std(all_A_flat) / abs(float(np.mean(all_A_flat))))
    unique_spectra = len({tuple(np.round(np.sort(c.A_hz), 1)) for c in cells16})
    print(f"  Certified 16 cells ready: unique={unique_spectra}/16, A_k CV={a_cv:.3f}, "
          f"min_gap range=[{min(c.min_gap_hz for c in cells16)/1e3:.2f}, {max(c.min_gap_hz for c in cells16)/1e3:.2f}] kHz", flush=True)

    program_names = ("Bell", "GHZ-4", "QFT-3", "BitFlip-3", "Grover-2")
    multicell_records: List[Dict[str, object]] = []

    for c_idx, cell in enumerate(cells16):
        tc0 = time.time()
        if c_idx == 0:
            lib = lib_f1
            lib.cell.cell_id = cell.cell_id
        else:
            lib = g126.synthesize_cell_library(
                cell, cx_n_dd=16, cx_sequence="XY8", duration_us=500.0, n_slices=64,
                bound_khz=15.0, native_ry_and_x=False, stage1_iters=150, stage2_iters=20, device=dev,
            )

        d0_c = h126.exact_d0_storage_leakage(cell.A_hz, cell.J_hz, (17.5, 175.0))
        gate_stats = {
            "min_nom_fid_32d": float(min(
                min(w.nominal_fidelity_32d for w in lib.rx_pi2.values()),
                min(w.nominal_fidelity_32d for w in lib.x_gate.values()),
                min(w.nominal_fidelity_32d for w in lib.cx_e_to_n.values()),
            )),
            "min_worst_corner_fid_32d": float(min(
                min(w.worst_corner_fidelity_32d for w in lib.rx_pi2.values()),
                min(w.worst_corner_fidelity_32d for w in lib.x_gate.values()),
                min(w.worst_corner_fidelity_32d for w in lib.cx_e_to_n.values()),
            )),
            "max_unitarity_err_fro": float(max(
                max(w.max_unitarity_err_fro for w in lib.rx_pi2.values()),
                max(w.max_unitarity_err_fro for w in lib.x_gate.values()),
                max(w.max_unitarity_err_fro for w in lib.cx_e_to_n.values()),
            )),
        }

        prog_results: Dict[str, Dict[str, object]] = {}
        for pname in program_names:
            prog = p126.compile_program(pname, lib)
            r_id = p126.execute_program_32d(prog, lib, device=dev)
            r_cp = p126.execute_program_32d(prog, lib, offset_hz=+400.0, amp_scale=1.02, device=dev)
            r_cm = p126.execute_program_32d(prog, lib, offset_hz=-400.0, amp_scale=0.98, device=dev)
            r_n2 = p126.execute_program_32d(prog, lib, noise_alpha=2.0, eps_stoch=1e-3,
                                            n_traj=128, seed=126500 + c_idx * 10, device=dev)
            p_rec: Dict[str, object] = {
                "meta": prog.to_metadata_dict(),
                "ideal_fidelity": float(r_id["fidelity"]),
                "corner_plus_fidelity": float(r_cp["fidelity"]),
                "corner_minus_fidelity": float(r_cm["fidelity"]),
                "worst_static_corner_fidelity": float(min(r_cp["fidelity"], r_cm["fidelity"])),
                "noisy_a2_e1e3_fidelity": float(r_n2["fidelity"]),
                "max_state_norm_err": float(max(r_id["max_state_norm_err"], r_n2["max_state_norm_err"])),
            }
            if pname in ("Bell", "GHZ-4"):
                r_n1 = p126.execute_program_32d(prog, lib, noise_alpha=1.0, eps_stoch=1e-3,
                                                n_traj=128, seed=126600 + c_idx * 10, device=dev)
                p_rec["noisy_a1_e1e3_fidelity"] = float(r_n1["fidelity"])
            if pname == "Grover-2":
                p_rec["marked_11_prob_noisy_a2"] = float(r_n2["marked_11_prob"])
            if pname == "BitFlip-3":
                p_rec["syndrome_11_prob_noisy_a2"] = float(r_n2["syndrome_11_prob"])
                p_rec["unencoded_error_fidelity"] = 0.0
            if pname == "GHZ-4":
                p_rec["spectator_overlap_all"] = float(r_id["spectator_overlap_all"])
            prog_results[pname] = p_rec

        rec = {
            "cell_meta": cell.to_metadata_dict(),
            "d0_storage": d0_c,
            "gate_library_summary": gate_stats,
            "programs": prog_results,
            "cell_elapsed_s": float(time.time() - tc0),
        }
        multicell_records.append(rec)
        print(f"  [{c_idx+1:2d}/16] {cell.cell_id:18s} (gap={cell.min_gap_hz/1e3:5.2f} kHz, D0={d0_c['17.5s']['max_leak']:.1e}): "
              f"Bell={prog_results['Bell']['noisy_a2_e1e3_fidelity']:.4f}, "
              f"GHZ4={prog_results['GHZ-4']['noisy_a2_e1e3_fidelity']:.4f}, "
              f"QFT3={prog_results['QFT-3']['noisy_a2_e1e3_fidelity']:.4f}, "
              f"BF3={prog_results['BitFlip-3']['noisy_a2_e1e3_fidelity']:.4f}, "
              f"Grov2={prog_results['Grover-2']['noisy_a2_e1e3_fidelity']:.4f} ({rec['cell_elapsed_s']:.1f}s)", flush=True)

    # Aggregate 16-cell statistics & M4 parallel array scheduling analysis
    multicell_summary: Dict[str, Dict[str, float]] = {}
    for pname in program_names:
        vals_id = [r["programs"][pname]["ideal_fidelity"] for r in multicell_records]
        vals_wc = [r["programs"][pname]["worst_static_corner_fidelity"] for r in multicell_records]
        vals_n2 = [r["programs"][pname]["noisy_a2_e1e3_fidelity"] for r in multicell_records]
        s: Dict[str, float] = {
            "ideal_mean": float(np.mean(vals_id)),
            "ideal_min": float(np.min(vals_id)),
            "worst_corner_mean": float(np.mean(vals_wc)),
            "worst_corner_min": float(np.min(vals_wc)),
            "noisy_a2_mean": float(np.mean(vals_n2)),
            "noisy_a2_median": float(np.median(vals_n2)),
            "noisy_a2_min": float(np.min(vals_n2)),
            "noisy_a2_max": float(np.max(vals_n2)),
            "noisy_a2_std": float(np.std(vals_n2)),
            "wall_clock_duration_ms": float(multicell_records[0]["programs"][pname]["meta"]["total_duration_us"] / 1e3),
            "parallel_16cell_speedup": 16.0,
        }
        if pname in ("Bell", "GHZ-4"):
            vals_n1 = [r["programs"][pname]["noisy_a1_e1e3_fidelity"] for r in multicell_records]
            s["noisy_a1_mean"] = float(np.mean(vals_n1))
            s["noisy_a1_min"] = float(np.min(vals_n1))
        if pname == "Grover-2":
            probs = [r["programs"][pname]["marked_11_prob_noisy_a2"] for r in multicell_records]
            s["marked_11_prob_mean"] = float(np.mean(probs))
            s["marked_11_prob_min"] = float(np.min(probs))
        multicell_summary[pname] = s

    # Inter-cell micron-pitch dipolar isolation (M4 preview)
    # Max dipolar J between 29Si nuclei in neighboring cells at distance r_um (1 - 3 cos^2 = -2 max):
    # |J_max| = 2 * 4.748 Hz*nm^3 / (r_um * 1000)^3
    parallel_array = {
        "n_cells": 16,
        "synchronization": "Synchronized 500 us RF slot / XY8 frame with independent per-cell local RF carrier frequencies {f_k^(c)} (FDMA/local-AWG)",
        "pitch_isolation_Hz": {
            "1_um": float(2.0 * h126.D_NN_HZ_NM3 / (1000.0 ** 3)),
            "2_um": float(2.0 * h126.D_NN_HZ_NM3 / (2000.0 ** 3)),
            "5_um": float(2.0 * h126.D_NN_HZ_NM3 / (5000.0 ** 3)),
        },
        "parallel_speedup": 16.0,
        "parallel_vs_sequential_ms": {
            pname: {
                "parallel_16cells_ms": float(multicell_summary[pname]["wall_clock_duration_ms"]),
                "sequential_16cells_ms": float(16.0 * multicell_summary[pname]["wall_clock_duration_ms"]),
            }
            for pname in program_names
        },
    }

    # -----------------------------------------------------------------------
    # EVALUATE PRE-REGISTERED PREDICTIONS P126_1 .. P126_8 (honest, unedited)
    # -----------------------------------------------------------------------
    p_th = preds["predictions"]

    # P126_1
    all_f1_gates = [w for gmap in (lib_f1.rx_pi2, lib_f1.ry_pi2, lib_f1.x_gate, lib_f1.cx_e_to_n) for w in gmap.values()]
    p1_u_err = max(w.max_unitarity_err_fro for w in all_f1_gates)
    p1_min_nom = min(w.nominal_fidelity_32d for w in all_f1_gates)
    p1_min_wc = min(w.worst_corner_fidelity_32d for w in all_f1_gates)
    p1_min_sp = min(w.min_spectator_retention_nom for w in all_f1_gates)
    t1 = p_th["P126_1_unitarity_and_grape_corners"]["thresholds"]
    v1 = bool(
        p1_u_err < t1["max_unitarity_err"]
        and p1_min_nom >= t1["min_nominal_fidelity"]
        and p1_min_wc >= t1["min_worst_corner_fidelity"]
        and p1_min_sp >= t1["min_spectator_retention"]
    )

    # P126_2
    p2_min_cz = min(r["subspace_process_fidelity"] for r in cz_ideal_list)
    p2_min_cn = min(r["subspace_process_fidelity"] for r in cnot_ideal_list)
    p2_max_lk = max(max(r["max_electron_leakage"] for r in cz_ideal_list),
                    max(r["max_electron_leakage"] for r in cnot_ideal_list))
    p2_mean_cz_n = float(np.mean([r["noisy_process_fidelity_mean"] for r in cz_noisy_list]))
    t2 = p_th["P126_2_two_qubit_cz_cnot"]["thresholds"]
    v2 = bool(
        min(p2_min_cz, p2_min_cn) >= t2["min_noiseless_cz_fidelity"]
        and p2_max_lk < t2["max_electron_leakage"]
        and p2_mean_cz_n >= t2["min_noisy_cz_mean_fidelity"]
    )

    # P126_3
    p3_max_err = max(he["abs_err"] for cdict in hahn_cal.values() for he in cdict.values())
    t3 = p_th["P126_3_hahn_echo_calibration"]["thresholds"]
    v3 = bool(p3_max_err <= t3["max_abs_error"])

    # P126_4
    f1_n64 = abundance_dd_table["F1"]["N_runs"]["N64"]
    t4 = p_th["P126_4_risk_r3_interleaved_dd_f1"]["thresholds"]
    v4 = bool(
        f1_n64["Q_32d_a1_e1e3"] >= t4["min_Q_ghz_alpha1"]
        and f1_n64["Q_32d_a2_e1e3"] >= t4["min_Q_ghz_alpha2"]
    )

    # P126_5
    f1_n64_sweep = next(r for r in f1_dd_sweep if r["N_total"] == 64)
    p5_eps1e2 = f1_n64_sweep["results"]["a2_e0.01"]["Q_32d"]
    row_2sq = next(r for r in xy8_vs_cpmg["sweep"] if abs(r["delta_theta_rad"] - 2.0 * math.sqrt(1e-3)) < 1e-6)
    p5_adv = row_2sq["xy8_advantage_y"]
    t5 = p_th["P126_5_pulse_ceiling_and_xy8_vs_cpmg"]["thresholds"]
    v5 = bool(p5_eps1e2 < t5["max_Q_at_eps_1e_2"] and p5_adv >= t5["min_xy8_minus_cpmg_advantage"])

    # P126_6
    t6 = p_th["P126_6_heterogeneous_16cell_certification"]["thresholds"]
    v6 = bool(
        len(cells16) == t6["n_cells"]
        and unique_spectra == t6["n_cells"]
        and all(c.lie_rank_k4 == t6["lie_rank_required"] for c in cells16)
        and all(c.vandermonde_rank_k8 == 8 and c.vandermonde_rank_k4 == 4 for c in cells16)
        and all(c.min_gap_hz >= t6["min_gap_Hz"] for c in cells16)
        and all(c.max_abs_J_hz <= t6["max_abs_J_Hz"] for c in cells16)
        and a_cv > t6["min_A_cv"]
    )

    # P126_7
    t7 = p_th["P126_7_multicell_program_fidelities"]["thresholds"]
    v7 = bool(
        multicell_summary["Bell"]["noisy_a2_mean"] >= t7["mean_bell"]
        and multicell_summary["GHZ-4"]["noisy_a2_mean"] >= t7["mean_ghz4"]
        and multicell_summary["Grover-2"]["marked_11_prob_mean"] >= t7["mean_grover2"]
        and multicell_summary["QFT-3"]["noisy_a2_mean"] >= t7["mean_qft3"]
        and multicell_summary["BitFlip-3"]["noisy_a2_mean"] >= t7["mean_bitflip3"]
        and multicell_summary["Bell"]["noisy_a2_min"] >= t7["worst_bell"]
        and multicell_summary["GHZ-4"]["noisy_a2_min"] >= t7["worst_ghz4"]
    )

    # P126_8
    t8 = p_th["P126_8_d0_storage_and_parallel_array"]["thresholds"]
    p8_max_d0 = max(r["d0_storage"]["17.5s"]["max_leak"] for r in multicell_records)
    p8_j_1um = parallel_array["pitch_isolation_Hz"]["1_um"]
    v8 = bool(p8_max_d0 <= t8["max_d0_leakage_17p5s"] and p8_j_1um < t8["max_intercell_J_Hz"])

    verdicts = {
        "P126_1_unitarity_and_grape_corners": {
            "passed": v1,
            "measured": {
                "max_unitarity_err_fro": float(p1_u_err),
                "min_nominal_fidelity_32d": float(p1_min_nom),
                "min_worst_corner_fidelity_32d": float(p1_min_wc),
                "min_spectator_retention_nom": float(p1_min_sp),
            },
        },
        "P126_2_two_qubit_cz_cnot": {
            "passed": v2,
            "measured": {
                "min_noiseless_cz_fidelity": float(p2_min_cz),
                "min_noiseless_cnot_fidelity": float(p2_min_cn),
                "max_electron_leakage": float(p2_max_lk),
                "mean_noisy_cz_process_fidelity": float(p2_mean_cz_n),
            },
        },
        "P126_3_hahn_echo_calibration": {
            "passed": v3,
            "measured": {"max_abs_err_vs_inv_e": float(p3_max_err)},
        },
        "P126_4_risk_r3_interleaved_dd_f1": {
            "passed": v4,
            "measured": {
                "Q_32d_f1_N64_alpha1_e1e3": float(f1_n64["Q_32d_a1_e1e3"]),
                "Q_32d_f1_N64_alpha2_e1e3": float(f1_n64["Q_32d_a2_e1e3"]),
                "Q_exp63_f1_N64_alpha1_e1e3": float(f1_n64["Q_exp63_a1_e1e3"]),
                "Q_exp63_f1_N64_alpha2_e1e3": float(f1_n64["Q_exp63_a2_e1e3"]),
            },
        },
        "P126_5_pulse_ceiling_and_xy8_vs_cpmg": {
            "passed": v5,
            "measured": {
                "Q_32d_f1_N64_alpha2_e1e2": float(p5_eps1e2),
                "xy8_minus_cpmg_ghz_y_at_2sqrt1e3": float(p5_adv),
                "ghz_y_xy8": float(row_2sq["ghz_y_xy8"]),
                "ghz_y_cpmg": float(row_2sq["ghz_y_cpmg"]),
            },
        },
        "P126_6_heterogeneous_16cell_certification": {
            "passed": v6,
            "measured": {
                "n_cells": len(cells16),
                "unique_spectra": unique_spectra,
                "A_k_cv": a_cv,
                "min_lie_rank": min(c.lie_rank_k4 for c in cells16),
                "min_gap_kHz": float(min(c.min_gap_hz for c in cells16) / 1e3),
                "max_abs_J_Hz": float(max(c.max_abs_J_hz for c in cells16)),
            },
        },
        "P126_7_multicell_program_fidelities": {
            "passed": v7,
            "measured": {
                "mean_bell_a2": multicell_summary["Bell"]["noisy_a2_mean"],
                "worst_bell_a2": multicell_summary["Bell"]["noisy_a2_min"],
                "mean_ghz4_a2": multicell_summary["GHZ-4"]["noisy_a2_mean"],
                "worst_ghz4_a2": multicell_summary["GHZ-4"]["noisy_a2_min"],
                "mean_grover2_prob11_a2": multicell_summary["Grover-2"]["marked_11_prob_mean"],
                "mean_qft3_a2": multicell_summary["QFT-3"]["noisy_a2_mean"],
                "mean_bitflip3_a2": multicell_summary["BitFlip-3"]["noisy_a2_mean"],
            },
        },
        "P126_8_d0_storage_and_parallel_array": {
            "passed": v8,
            "measured": {
                "max_d0_leakage_17p5s_across_16cells": float(p8_max_d0),
                "intercell_J_1um_Hz": float(p8_j_1um),
                "parallel_speedup": 16.0,
            },
        },
    }
    n_pass = sum(1 for v in verdicts.values() if v["passed"])
    success_rule_met = all(v["passed"] for v in verdicts.values())

    out_payload = {
        "experiment": "exp126_atom_cell_programming",
        "date": time.strftime("%Y-%m-%d"),
        "device": str(dev),
        "no_lab_measurement": True,
        "epistemic_tag": "Model / Full-32D-Hamiltonian-Simulation",
        "elapsed_sec": float(time.time() - t_start),
        "n_predictions_passed": int(n_pass),
        "n_predictions_total": len(verdicts),
        "success_rule_met": bool(success_rule_met),
        "verdicts": verdicts,
        "obs_029_141_honest_audit": {
            "kl_scale_audit": h126.audit_legacy_kl_vs_hm5962(),
            "ddrf_crowding_wall_Hz": float(h126.DDRF_MIN_GAP_WALL_HZ),
            "unresolved_gate_wall_status": "HONEST_FAIL_RECORDED" if not success_rule_met else "CLOSED",
            "honest_failed_verdicts": [k for k, v in verdicts.items() if not v["passed"]],
            "remediation_note": (
                "Legacy 2.981 MHz double-halved KL fixed via hyperfine_scale='hm5962' (5.962 MHz); "
                "DDRF 6.893 kHz crowding wall enforced in sample_certified_f1_cells; P126_1/2/3 "
                "failures honestly retained until longer frequency-selective GRAPE + dipolar bath calibration."
            ),
        },
        "part1_f1_universal_gates": {
            "cell_meta": f1.to_metadata_dict(),
            "gates_summary": f1_gates_summary,
            "waveforms": f1_waveforms_serialized,
            "ddrf_headroom_diagnostic": ddrf_diag,
            "two_qubit_cz_ideal": cz_ideal_list,
            "two_qubit_cnot_ideal": cnot_ideal_list,
            "two_qubit_cz_noisy_a2_e1e3": cz_noisy_list,
            "native_ccz_012_ideal": ccz_f1,
        },
        "part2_risk_r3_interleaved_dd": {
            "hahn_echo_calibration_32d": hahn_cal,
            "d0_storage_finalists": d0_finalists,
            "f1_ghz4_ndd_sweep": f1_dd_sweep,
            "abundance_dd_vs_exp63": abundance_dd_table,
            "xy8_vs_cpmg_systematic": xy8_vs_cpmg,
        },
        "part3_multicell_16_programs": {
            "n_cells": len(cells16),
            "unique_spectra": unique_spectra,
            "A_k_cv": a_cv,
            "program_summary": multicell_summary,
            "parallel_array_m4_preview": parallel_array,
            "cells": multicell_records,
        },
    }

    OUT_JSON.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print(f"\n=== EXP126 COMPLETE in {out_payload['elapsed_sec']:.1f}s ===", flush=True)
    print(f"Verdicts: {n_pass}/{len(verdicts)} PASS, success_rule_met={success_rule_met}", flush=True)
    for k, v in verdicts.items():
        print(f"  {k}: {'PASS' if v['passed'] else 'FAIL'} -> {v['measured']}", flush=True)


if __name__ == "__main__":
    main()
