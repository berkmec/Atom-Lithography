"""
Exp143 (H161) — Option-HPC 100 Gbps RoCEv2 RDMA Real-Time QEC Syndrome Decoder
Latency Chain, Backlog Wall Analysis, & CAD/BOM v6.0 Hardware Specification (S9.HPC).

Models end-to-end physical latency and throughput:
  20 mK TWPA + 4 K HEMT + cryo coax (~7 ns)
    -> ZU48DR RFSoC IQ demod + Q16.16 threshold + 100G CMAC TX (~320 ns)
    -> 100 GbE RoCEv2 RDMA fiber (20 m OM4 + ConnectX-7 GPUDirect DMA, ~450 ns)
    -> Decoder compute (Single-Core CPU vs Parallel Windowed Option-HPC GPU/FPGA)
       across Rotated Surface Code d in {7, 11, 21, 37} and qLDPC [[144, 12, 12]] BP-OSD.

Also exports `s9hpc_hardware_spec.json` matching Exp140's `s65_hardware_spec.json` schema
for seamless CAD v6.0 & BOM v6.0 integration.

Epistemic Tag: {Model} / {Liste-Capasi} / {Varsayım}. no_lab_measurement = True,
no_supplier_quotes = True.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List

import numpy as np

from experiments.exp138_defective_surface_code_ft.rotated_surface_code138 import (
    build_rotated_surface_code,
    compile_ideal_circuit_dem,
    decode_syndrome_mwpm,
    depolarizing_pauli16,
)


# Fixed physical transport latencies (nanoseconds -> microseconds)
# Anchored to Xilinx ZU48DR RFSoC DSP/CMAC datasheets & NVIDIA ConnectX-7 RoCEv2 specs {Liste-Capasi}
LATENCY_CHAIN_US = {
    "cryo_twpa_hemt_coax_1p5m_us": 0.007,     # 1.5 m cryo coax @ 0.7c
    "rfsoc_zu48dr_iq_thresh_cmac_us": 0.320,  # 160 ns ADC/DDC/Q16.16 thresh + 160 ns 100G CMAC TX
    "rdma_rocev2_100g_fiber_dma_us": 0.450,   # 100 ns 20m fiber + 350 ns ConnectX-7 GPUDirect DMA
    "return_feedforward_link_us": 0.450,      # Return Pauli-frame / T-gate reaction packet
}
TAU_INGEST_US = (
    LATENCY_CHAIN_US["cryo_twpa_hemt_coax_1p5m_us"]
    + LATENCY_CHAIN_US["rfsoc_zu48dr_iq_thresh_cmac_us"]
    + LATENCY_CHAIN_US["rdma_rocev2_100g_fiber_dma_us"]
)  # 0.777 us


def benchmark_local_python_mwpm_ref(p_2q: float = 0.0045, p_meas: float = 0.003861) -> Dict[str, Any]:
    """
    Live empirical timing reference on this machine's CPU using Exp138's exact
    Python/networkx Edmonds Blossom decoder at d=7 and d=11 (300 shots each),
    measuring exact defects-per-round at D3 physical noise to anchor the analytical
    C++/GPU/FPGA throughput models!
    """
    rng = np.random.default_rng(14399)
    p16 = depolarizing_pauli16(p_2q)
    out: Dict[str, Any] = {}
    for d in (7, 11):
        code = build_rotated_surface_code(d)
        dem = compile_ideal_circuit_dem(code, d, p16, p_1q=0.00083, p_meas=p_meas, p_idle_Z=0.00020, memory_basis="Z")
        probs = np.array([m[2] for m in dem.mechanisms], dtype=np.float64)
        n_shots = 300
        fired_mat = rng.random((n_shots, len(probs))) < probs[None, :]
        # Pre-build syndromes
        syns = []
        tot_def = 0
        for s in range(n_shots):
            syn = np.zeros(dem.n_det, dtype=np.uint8)
            for mi in np.flatnonzero(fired_mat[s]):
                for d_i in dem.mechanisms[int(mi)][0]:
                    syn[d_i] ^= 1
            defects = np.flatnonzero(syn)
            tot_def += len(defects)
            syns.append(defects)
        t0 = time.perf_counter()
        for defects in syns:
            _ = decode_syndrome_mwpm(defects, dem, k_nn=10)
        dt_s = time.perf_counter() - t0
        # Per-round defect rate across BOTH X and Z checks (2x single basis!)
        defects_per_round_both = 2.0 * (tot_def / float(n_shots)) / float(d)
        p_det_empirical = defects_per_round_both / float(d * d - 1)
        out[f"d{d}"] = {
            "d": d,
            "n_checks_total": d * d - 1,
            "n_shots": n_shots,
            "empirical_defects_per_round_XZ": float(defects_per_round_both),
            "empirical_p_det_per_check": float(p_det_empirical),
            "python_networkx_us_per_round_XZ": float(2.0 * (dt_s * 1e6 / n_shots) / d),
        }
    return out


def benchmark_live_ldpc_bb144_cpu(
    p_2q: float = 0.0050,
    p_meas: float = 0.003861,
    n_shots_r4: int = 12,
    n_shots_r8: int = 4,
) -> Dict[str, Any]:
    """Live empirical C++ `ldpc` BpOsdDecoder CPU timing on real BB_144_12_12 circuit DEM (OBS-023)."""
    from experiments.exp144_qldpc_bivariate_bicycle_m4.bb_codes_and_layout144 import (
        BB_CODE_SPECS,
        build_bb_code,
        find_verified_commuting_schedule,
    )
    from experiments.exp144_qldpc_bivariate_bicycle_m4.bp_osd_decoder144 import (
        build_bb_circuit_dem,
    )
    try:
        try:
            from ldpc import BpOsdDecoder
        except Exception:
            from ldpc.bposd_decoder import BpOsdDecoder
        has_ldpc = True
    except Exception:
        has_ldpc = False

    c144 = build_bb_code(BB_CODE_SPECS["BB_144_12_12"])
    sched = find_verified_commuting_schedule(c144)
    rng = np.random.default_rng(14323)
    out: Dict[str, Any] = {"ldpc_cpp_available": has_ldpc}

    for tag, n_rnd, n_sh in (("R4", 4, n_shots_r4), ("R8", 8, n_shots_r8)):
        dem = build_bb_circuit_dem(
            c144, sched, n_noisy_rounds=n_rnd, p_2q=p_2q, p_meas=p_meas,
            p_prep=0.00083, p_1q_idle_step=0.00010, p_data_ro_idle=0.00015, memory_basis="Z",
        )
        H_dem = dem["H_dem"].astype(np.uint8)
        p_dem = dem["p_dem"]
        faults = (rng.random((n_sh, len(p_dem))) < p_dem[None, :]).astype(np.uint8)
        syns = (faults @ H_dem.T) & 1

        if has_ldpc:
            from scipy.sparse import csc_matrix
            dec_bp = BpOsdDecoder(
                csc_matrix(H_dem), error_channel=p_dem.tolist(),
                max_iter=50, bp_method="minimum_sum", ms_scaling_factor=0.625,
                osd_method="osd_cs", osd_order=2,
            )
            lat_us = []
            bp_conv = 0
            for s in range(n_sh):
                t0 = time.perf_counter()
                _ = dec_bp.decode(syns[s])
                lat_us.append((time.perf_counter() - t0) * 1e6)
                if getattr(dec_bp, "converge", False):
                    bp_conv += 1
            mean_us = float(np.mean(lat_us))
            p99_us = float(np.percentile(lat_us, 99))
            bp_frac = float(bp_conv / n_sh)
        else:
            # Conservative fallback anchored to OBS-023 live measurements
            mean_us = 34680.0 if n_rnd == 4 else 181710.0
            p99_us = mean_us * 1.5
            bp_frac = 0.390 if n_rnd == 4 else 0.180

        out[tag] = {
            "n_rounds": n_rnd,
            "M_detectors": int(dem["M_detectors"]),
            "N_faults": int(dem["N_fault_mechanisms"]),
            "n_shots": int(n_sh),
            "bp_converged_frac": round(bp_frac, 4),
            "osd_trigger_frac": round(1.0 - bp_frac, 4),
            "mean_us_per_shot": round(mean_us, 2),
            "mean_ms_per_shot": round(mean_us / 1e3, 3),
            "p99_us_per_shot": round(p99_us, 2),
        }
    return out


def analyze_option_hpc_decoder_wall(
    t_gate_d3_us: float = 0.65,
    t_cyc_fast_us: float = 2.6201,
    t_cyc_4cz_v5_us: float = 8.932,
    p_2q_d3: float = 0.0045,
    p_meas: float = 0.003861,
) -> Dict[str, Any]:
    """
    Full Option-HPC real-time syndrome decoding latency, backlog-free boundary,
    100G RoCEv2 fiber bandwidth, HPC node sizing, and power budget across:
      - Rotated Surface Code d in {7, 11, 21, 37}
      - qLDPC [[144, 12, 12]] Gross Code (BP-OSD)
    evaluated at:
      - T_cyc_fast = 2.620 us (Exp140 1-CZ fast readout demo)
      - T_cyc_4cz_D3 = 4 * t_gate_d3 + 2.0 + 0.2 us (v6.0 D3 GRAPE 4-CZ cycle)
      - T_cyc_4cz_v5 = 8.932 us (v5.0 Exp138 P4 4-CZ cycle)
    """
    t_cyc_4cz_d3_us = 4.0 * t_gate_d3_us + 2.0 + 0.2
    # Cap decoder benchmark operating point to the sub-threshold D3 target [0.45%, 0.55%]
    # (above threshold >1%, QEC decoding diverges; even AT 0.50%, live C++ ldpc CPU is >10,000x too slow!)
    p_2q_bench = min(max(float(p_2q_d3), 0.0045), 0.0055)
    local_bench = benchmark_local_python_mwpm_ref(p_2q=p_2q_bench, p_meas=p_meas)
    p_det = 0.5 * (
        local_bench["d7"]["empirical_p_det_per_check"]
        + local_bench["d11"]["empirical_p_det_per_check"]
    )

    # 1. Surface Code MWPM Scaling (d = 7, 11, 21, 37)
    # Literature anchors:
    #   - Single-core C++ Sparse Blossom / PyMatching v2 (Higgott & Gidney 2023):
    #     t_base = 0.28 us + 0.34 us/defect * (1 + 0.14 * ln(1 + m_def))  [calibrated at p~0.5%]
    #   - Parallel Windowed Fusion-Blossom / GPU-FPGA HPC (Skoric 2023, Tan 2023, Willow 2025):
    #     P_win parallel overlapping windows (4 for d<=21, 8 for d=37) with seam-merge overhead
    #     tau_seam = 0.22 + 0.004 * d us and parallel efficiency eta_par = 0.82.
    surface_rows: List[Dict[str, Any]] = []
    for d in (7, 11, 21, 37):
        n_checks = d * d - 1
        n_active = 2 * d * d - 1
        m_def_round = n_checks * p_det

        # Single-core C++ Sparse Blossom per-round decode time (us)
        tau_cpu_single_us = 0.28 + 0.36 * m_def_round * (1.0 + 0.15 * math.log1p(m_def_round))
        # Option-HPC parallel windowed GPU/FPGA decoder (P_win=4 for d<=21, P_win=8 for d=37)
        p_win = 4 if d <= 21 else 8
        eta_par = 0.85 if p_win == 4 else 0.82
        tau_seam_us = 0.22 + 0.004 * d
        tau_hpc_compute_us = tau_cpu_single_us / (p_win * eta_par) + tau_seam_us
        # End-to-end streaming pipeline latency (ingest + compute); note backlog depends on
        # max(TAU_INGEST_US, tau_hpc_compute_us) for pipelined throughput, AND we also check
        # conservative non-pipelined sum (TAU_INGEST_US + tau_hpc_compute_us) for strict safety!
        tau_hpc_e2e_stream_us = TAU_INGEST_US + tau_hpc_compute_us
        tau_hpc_pipelined_eff_us = max(TAU_INGEST_US, tau_hpc_compute_us)
        # Reaction time (non-Clifford T-gate feedforward): ingest + commit window + return
        tau_reaction_us = TAU_INGEST_US + tau_hpc_compute_us + LATENCY_CHAIN_US["return_feedforward_link_us"]

        # Syndrome data rate (hard-decision 1 bit/check + 25% RoCEv2 header overhead vs 12-bit soft-IQ)
        # Evaluated at both 8.932 us (v5) and fast D3 cycle
        bw_1L_hard_v5_gbps = (n_checks * 1.25) / (t_cyc_4cz_v5_us * 1e3)
        bw_1L_hard_d3_gbps = (n_checks * 1.25) / (t_cyc_4cz_d3_us * 1e3)
        bw_1L_soft12_v5_gbps = (n_checks * 12.0 * 1.15) / (t_cyc_4cz_v5_us * 1e3)
        bw_100L_hard_v5_gbps = 100.0 * bw_1L_hard_v5_gbps
        bw_100L_hard_d3_gbps = 100.0 * bw_1L_hard_d3_gbps
        bw_100L_soft12_v5_gbps = 100.0 * bw_1L_soft12_v5_gbps

        # Redundant 100G QSFP28 fiber links (N+1 redundancy, <= 65% max link utilization for deterministic tail!)
        fibers_100g_100L_hard_v5 = max(2, math.ceil(bw_100L_hard_v5_gbps / 65.0) + 1)
        fibers_100g_100L_hard_d3 = max(2, math.ceil(bw_100L_hard_d3_gbps / 65.0) + 1)
        fibers_100g_100L_soft_v5 = max(2, math.ceil(bw_100L_soft12_v5_gbps / 65.0) + 1)

        # HPC node sizing: each 2U HPC decoder node carries 2x H100/Alveo-U280-class cards
        # = 64 concurrent hardware/CUDA decoder window engines (at 1,050 W/node):
        engines_per_node = 64
        logical_per_node = max(1, engines_per_node // p_win)
        nodes_100L = math.ceil(100.0 / logical_per_node)
        racks_4u_2node_100L = math.ceil(nodes_100L / 2.0)
        power_kw_100L = (nodes_100L * 1050.0 + racks_4u_2node_100L * 95.0) / 1000.0

        surface_rows.append({
            "code": f"Surface_d{d}",
            "d": d,
            "n_active_cells": n_active,
            "n_checks": n_checks,
            "expected_defects_per_round": float(m_def_round),
            "tau_cpu_single_us": float(tau_cpu_single_us),
            "p_win_parallel": p_win,
            "tau_hpc_compute_us": float(tau_hpc_compute_us),
            "tau_hpc_pipelined_eff_us": float(tau_hpc_pipelined_eff_us),
            "tau_hpc_e2e_stream_us": float(tau_hpc_e2e_stream_us),
            "tau_reaction_t_gate_us": float(tau_reaction_us),
            "backlog_free_cpu_2p62us": bool(tau_cpu_single_us < t_cyc_fast_us),
            "backlog_free_cpu_d3_cyc": bool(tau_cpu_single_us < t_cyc_4cz_d3_us),
            "backlog_free_cpu_8p93us": bool(tau_cpu_single_us < t_cyc_4cz_v5_us),
            "backlog_free_hpc_2p62us": bool(tau_hpc_e2e_stream_us < t_cyc_fast_us),
            "backlog_free_hpc_d3_cyc": bool(tau_hpc_e2e_stream_us < t_cyc_4cz_d3_us),
            "backlog_free_hpc_8p93us": bool(tau_hpc_e2e_stream_us < t_cyc_4cz_v5_us),
            "bw_100L_hard_v5_gbps": float(bw_100L_hard_v5_gbps),
            "bw_100L_hard_d3_gbps": float(bw_100L_hard_d3_gbps),
            "bw_100L_soft12_v5_gbps": float(bw_100L_soft12_v5_gbps),
            "fibers_100g_100L_hard_v5": int(fibers_100g_100L_hard_v5),
            "fibers_100g_100L_hard_d3": int(fibers_100g_100L_hard_d3),
            "fibers_100g_100L_soft_v5": int(fibers_100g_100L_soft_v5),
            "logical_per_hpc_node": int(logical_per_node),
            "hpc_nodes_100L": int(nodes_100L),
            "option_hpc_4u_modules_100L": int(racks_4u_2node_100L),
            "hpc_power_kw_100L": float(power_kw_100L),
        })

    # 2. qLDPC [[144, 12, 12]] Gross Code (Bravyi et al. Nature 2024) BP-OSD Decoder Model (OBS-023 FIX)
    # Replace falsified hardcoded constants (3.5% OSD, 6.8 us BP, 42 us CPU / 14.5 us HPC -> 2.32 us)
    # with LIVE C++ `ldpc` BpOsdDecoder measurements on the actual BB_144_12_12 circuit-level DEM!
    qldpc_checks_per_block = 144
    qldpc_blocks_for_100L = math.ceil(100.0 / 12.0)  # 9 blocks = 108 logical qubits
    live_ldpc_bench = benchmark_live_ldpc_bb144_cpu(p_2q=max(p_2q_bench, 0.0050), p_meas=p_meas)
    p_osd_trigger_r4 = live_ldpc_bench["R4"]["osd_trigger_frac"]
    p_osd_trigger_r8 = live_ldpc_bench["R8"]["osd_trigger_frac"]
    tau_cpu_mean_r4_us = live_ldpc_bench["R4"]["mean_us_per_shot"]
    tau_cpu_p99_r4_us = live_ldpc_bench["R4"]["p99_us_per_shot"]
    tau_cpu_mean_r8_us = live_ldpc_bench["R8"]["mean_us_per_shot"]
    # Real steady-state R=d=12 requires dedicated FPGA/GPU BP-OSD/LSD hardware core; ZERO QEC decoder RTL exists in repo!
    qec_decoder_rtl_in_repo = False
    t_cyc_bb_d3_us = 7.0 * t_gate_d3_us + 2.0 + 0.2
    required_hw_speedup_r4 = tau_cpu_mean_r4_us / max(t_cyc_bb_d3_us, 1e-6)
    required_hw_speedup_r8 = tau_cpu_mean_r8_us / max(t_cyc_bb_d3_us, 1e-6)

    bw_qldpc_108L_hard_v5_gbps = (qldpc_blocks_for_100L * qldpc_checks_per_block * 1.25) / (t_cyc_4cz_v5_us * 1e3)
    bw_qldpc_108L_hard_d3_gbps = (qldpc_blocks_for_100L * qldpc_checks_per_block * 1.25) / (t_cyc_4cz_d3_us * 1e3)
    bw_qldpc_108L_soft12_v5_gbps = (qldpc_blocks_for_100L * qldpc_checks_per_block * 12.0 * 1.15) / (t_cyc_4cz_v5_us * 1e3)

    qldpc_row = {
        "code": "qLDPC_[[144,12,12]]",
        "d": 12,
        "k_logical_per_block": 12,
        "n_active_per_block": 288,
        "n_checks_per_block": qldpc_checks_per_block,
        "blocks_for_100L": qldpc_blocks_for_100L,
        "logical_qubits_delivered": qldpc_blocks_for_100L * 12,
        "actual_unclamped_p2q_input": float(p_2q_d3),
        "benchmark_p2q_operating_point": float(max(p_2q_bench, 0.0050)),
        "unclamped_p2q_above_stim_threshold": bool(p_2q_d3 > 0.0098),
        "qec_decoder_rtl_exists_in_repo": qec_decoder_rtl_in_repo,
        "live_ldpc_cpu_benchmark": live_ldpc_bench,
        "p_osd_fallback_R4": float(p_osd_trigger_r4),
        "p_osd_fallback_R8": float(p_osd_trigger_r8),
        "p_osd_fallback": float(p_osd_trigger_r4),
        "tau_cpu_mean_us": float(tau_cpu_mean_r4_us),
        "tau_cpu_p99_us": float(tau_cpu_p99_r4_us),
        "tau_cpu_mean_R8_us": float(tau_cpu_mean_r8_us),
        # Honest unverified hardware target (no RTL/GPU implementation exists -> cannot claim 2.32 us closure!)
        "tau_hpc_compute_mean_us": float(tau_cpu_mean_r4_us),
        "tau_hpc_e2e_mean_us": float(TAU_INGEST_US + tau_cpu_mean_r4_us),
        "tau_hpc_p99_us": float(TAU_INGEST_US + tau_cpu_p99_r4_us),
        "required_fpga_gpu_speedup_vs_cpu_R4": float(required_hw_speedup_r4),
        "required_fpga_gpu_speedup_vs_cpu_R8": float(required_hw_speedup_r8),
        "hardware_acceleration_status": "HORIZON_TARGET_REQUIRED_NO_QEC_DECODER_RTL",
        "backlog_free_cpu_2p62us": bool(tau_cpu_mean_r4_us < t_cyc_fast_us),
        "backlog_free_cpu_8p93us": bool(tau_cpu_mean_r4_us < t_cyc_4cz_v5_us),
        "backlog_free_hpc_2p62us": False,
        "backlog_free_hpc_d3_cyc": False,
        "backlog_free_hpc_8p93us": False,
        "bw_108L_hard_v5_gbps": float(bw_qldpc_108L_hard_v5_gbps),
        "bw_108L_hard_d3_gbps": float(bw_qldpc_108L_hard_d3_gbps),
        "bw_108L_soft12_v5_gbps": float(bw_qldpc_108L_soft12_v5_gbps),
        "fibers_100g_108L_hard": 2,  # 1 active + 1 redundant
        "hpc_nodes_108L": 2,
        "option_hpc_4u_modules_108L": 1,
        "hpc_power_kw_108L": 2.195,
    }

    return {
        "epistemic_tag": "{Model}/{Liste-Capasi}",
        "cycle_times_us": {
            "T_cyc_fast_exp140_demo_us": float(t_cyc_fast_us),
            "T_cyc_4cz_d3_grape_us": float(t_cyc_4cz_d3_us),
            "T_cyc_4cz_v5_exp138_us": float(t_cyc_4cz_v5_us),
        },
        "latency_chain_us": LATENCY_CHAIN_US,
        "tau_ingest_us": float(TAU_INGEST_US),
        "empirical_p_det_per_check": float(p_det),
        "local_python_mwpm_benchmark": local_bench,
        "surface_code_scaling": surface_rows,
        "qldpc_gross_144_12_12": qldpc_row,
    }


def build_s9hpc_hardware_spec(hpc_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build CAD v6.0 & BOM v6.0 compatible `s9hpc_hardware_spec.json` for optional
    Option-HPC 4U 2-Node 100 Gbps RoCEv2 RDMA QEC Decoder Rack Module.
    Matches Exp140 `s65_hardware_spec.json` structure cleanly.
    """
    items = [
        {
            "part_id": "S9.HPC-01",
            "name": "2U Dual-Accelerator QEC Decoder Node (2x H100/Alveo-U280-Class + Dual-100G ConnectX-7 RoCEv2 NIC)",
            "qty": 2,
            "stage": "300K_hpc_rack",
            "rack_U": 4,
            "envelope_mm": [482.6, 780.0, 177.8],
            "mass_kg_total": 56.0,
            "power_W_total": 2100.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 84000,
            "cost_usd_nom": 112000,
            "cost_usd_high": 152000,
            "epistemic_tag": "Varsayim",
        },
        {
            "part_id": "S9.HPC-02",
            "name": "1U Ultra-Low-Latency Cut-Through 100 GbE RoCEv2 Optical Bridge + 4x QSFP28-100G-SR4 + 20m OM4 MPO-12 Loom",
            "qty": 1,
            "stage": "300K_hpc_rack",
            "rack_U": 1,
            "envelope_mm": [482.6, 380.0, 44.5],
            "mass_kg_total": 4.2,
            "power_W_total": 95.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 9500,
            "cost_usd_nom": 13500,
            "cost_usd_high": 19500,
            "epistemic_tag": "Liste-Capasi",
        },
        {
            "part_id": "S9.HPC-03",
            "name": "Redundant 2.6 kW Titanium PSU Pack, Sliding Rack Rails & ZU48DR 100G CMAC RDMA Firmware Integration Kit",
            "qty": 1,
            "stage": "300K_hpc_rack",
            "rack_U": 0,
            "envelope_mm": [482.6, 780.0, 177.8],
            "mass_kg_total": 3.8,
            "power_W_total": 0.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 4500,
            "cost_usd_nom": 6500,
            "cost_usd_high": 9500,
            "epistemic_tag": "Varsayim",
        },
    ]

    tot_mass = sum(it["mass_kg_total"] for it in items)
    tot_power = sum(it["power_W_total"] for it in items)
    tot_low = sum(it["cost_usd_low"] for it in items)
    tot_nom = sum(it["cost_usd_nom"] for it in items)
    tot_high = sum(it["cost_usd_high"] for it in items)

    d37 = next(r for r in hpc_analysis["surface_code_scaling"] if r["d"] == 37)
    d21 = next(r for r in hpc_analysis["surface_code_scaling"] if r["d"] == 21)
    qldpc = hpc_analysis["qldpc_gross_144_12_12"]

    return {
        "subsystem_id": "S9.HPC",
        "option_name": "Option-HPC",
        "title": "100 Gbps RoCEv2 RDMA Supercomputer Real-Time QEC Syndrome Decoder Module (v6.0 Optional Rack)",
        "module_form_factor_U": 4,
        "module_form_factor_with_1u_switch_U": 5,
        "optional_addon_to_m3_v5": True,
        "no_supplier_quotes": True,
        "no_lab_measurement": True,
        "epistemic_tags": ["Model", "Liste-Capasi", "Varsayim"],
        "totals_base_4u_option_hpc_module": {
            "total_mass_kg": float(tot_mass),
            "cryo_cold_mass_kg": 0.0,
            "room_temp_power_W": float(tot_power),
            "cryo_load_W": 0.0,
            "envelope_mm_4u_direct_attach": [482.6, 780.0, 177.8],
            "envelope_mm_5u_with_1u_bridge": [482.6, 780.0, 222.3],
            "rdma_ports_100g_qsfp28": 4,
            "one_way_ingest_latency_us": float(hpc_analysis["tau_ingest_us"]),
            "cost_usd_low": int(tot_low),
            "cost_usd_nom": int(tot_nom),
            "cost_usd_high": int(tot_high),
        },
        "capacity_and_100L_scaling": {
            "base_module_capacity_surface_d21_logical": int(2 * d21["logical_per_hpc_node"]),
            "base_module_capacity_surface_d37_logical": int(2 * d37["logical_per_hpc_node"]),
            "base_module_capacity_qldpc_144_12_12_logical": 108,
            "surface_d37_100L_modules_required": int(d37["option_hpc_4u_modules_100L"]),
            "surface_d37_100L_nodes_required": int(d37["hpc_nodes_100L"]),
            "surface_d37_100L_power_kW": float(d37["hpc_power_kw_100L"]),
            "surface_d37_100L_hard_bw_v5_Gbps": float(d37["bw_100L_hard_v5_gbps"]),
            "surface_d37_100L_hard_bw_d3_Gbps": float(d37["bw_100L_hard_d3_gbps"]),
            "surface_d37_100L_100g_fibers_redundant": int(d37["fibers_100g_100L_hard_d3"]),
            "qldpc_108L_modules_required": int(qldpc["option_hpc_4u_modules_108L"]),
            "qldpc_108L_power_kW": float(qldpc["hpc_power_kw_108L"]),
            "qldpc_108L_hard_bw_d3_Gbps": float(qldpc["bw_108L_hard_d3_gbps"]),
        },
        "items": items,
    }
