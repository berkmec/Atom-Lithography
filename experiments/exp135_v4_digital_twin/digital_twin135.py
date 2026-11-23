"""Exp135 (H153): End-to-End v4.0 Full-Machine Digital Twin (Exp124-Exp134 + Live Control Stack).

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp135_v4_digital_twin/digital_twin135.py

Reads pre-registered ``results/exp135_v4_digital_twin/predictions_exp135.json``
and all 11 primary experiment ledgers ``results/exp124..134/exp*.json``, executes
coupled 8-layer v3.0-vs-v4.0 physics + live ``src/machine_control/`` 4x4 wafer
integration, and writes:
  - ``results/exp135_v4_digital_twin/exp135.json``
  - ``results/exp135_v4_digital_twin/exp135_plot_data.json``
  - ``results/exp135_v4_digital_twin/v4_digital_twin_cert.json``

Epistemic status: {Model} / {Sayisal-Simulasyon}, no_lab_measurement=true.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from machine_control.adaptive_spectroscopy import (  # noqa: E402
    BOEDConfig,
    BayesianSpectrometer,
    CandidateSpectrum,
    compute_min_transition_spacing_Hz,
)
from machine_control.config import MachineConfig  # noqa: E402
from machine_control.factory import Certificate, Factory  # noqa: E402
from machine_control.programmer import (  # noqa: E402
    AtomCellProgrammer,
    MultiCellProgrammer,
    WaferSite,
    program_bell,
    program_ghz,
)
from machine_control.writer import CountedWriter  # noqa: E402


RESULTS_DIR = ROOT / "results"
OUT_DIR = RESULTS_DIR / "exp135_v4_digital_twin"
PRED_PATH = OUT_DIR / "predictions_exp135.json"

PRIMARY_LEDGERS = {
    "exp124": "exp124_ion_column_optics/exp124.json",
    "exp125": "exp125_cryo_magnet_readout/exp125.json",
    "exp126": "exp126_atom_cell_programming/exp126.json",
    "exp127": "exp127_detector_frontend_sim/exp127.json",
    "exp128": "exp128_bom_sensitivity/exp128.json",
    "exp129": "exp129_valley_orbital_hyperfine/exp129.json",
    "exp130": "exp130_flash_anneal_diffusion/exp130.json",
    "exp131": "exp131_scalable_m4_architecture/exp131.json",
    "exp132": "exp132_bayesian_spectroscopy_cellisa3/exp132.json",
    "exp133": "exp133_coupled_vibration_thermal/exp133.json",
    "exp134": "exp134_fab_economics_tco/exp134.json",
}


def load_primary_ledgers(root: Path = ROOT) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Load all 11 primary Exp124-Exp134 JSON files and record their SHA-256 digests."""
    ledgers: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for key, rel in PRIMARY_LEDGERS.items():
        fp = root / "results" / rel
        if not fp.is_file():
            raise FileNotFoundError(f"Missing primary ledger: {rel}")
        raw = fp.read_bytes()
        hashes[key] = hashlib.sha256(raw).hexdigest()
        ledgers[key] = json.loads(raw.decode("utf-8"))
    return ledgers, hashes


def exact_binomial_ft_yield(n_nodes: int, max_dead: int, p_node: float) -> float:
    """Exact probability that at most ``max_dead`` of ``n_nodes`` independent sites fail."""
    p = min(max(float(p_node), 0.0), 1.0)
    q = 1.0 - p
    total = 0.0
    for k in range(0, min(max_dead, n_nodes) + 1):
        total += math.comb(n_nodes, k) * (q ** k) * (p ** (n_nodes - k))
    return float(min(max(total, 0.0), 1.0))


def mc_2d_square_percolation(
    L: int,
    p_node: float,
    n_mc: int = 2_000,
    seed: int = 2026135,
) -> dict[str, float]:
    """2D LxL square-lattice site percolation & 5%-defect FT wafer yield Monte Carlo."""
    rng = np.random.default_rng(seed)
    n_nodes = L * L
    max_dead = int(math.floor(0.05 * n_nodes))
    grids = rng.random((n_mc, L, L)) < p_node

    n_perc = 0
    gc_fracs = np.empty(n_mc, dtype=float)
    dead_counts = n_nodes - grids.sum(axis=(1, 2))
    y_ft_mc = float(np.mean(dead_counts <= max_dead))

    for idx in range(n_mc):
        g = grids[idx]
        visited = np.zeros((L, L), dtype=bool)
        max_comp = 0
        percolates = False
        for r in range(L):
            for c in range(L):
                if not g[r, c] or visited[r, c]:
                    continue
                stack = [(r, c)]
                visited[r, c] = True
                size = 0
                touches_top = False
                touches_bot = False
                while stack:
                    cr, cc = stack.pop()
                    size += 1
                    if cr == 0:
                        touches_top = True
                    if cr == L - 1:
                        touches_bot = True
                    for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
                        if 0 <= nr < L and 0 <= nc < L and g[nr, nc] and not visited[nr, nc]:
                            visited[nr, nc] = True
                            stack.append((nr, nc))
                if size > max_comp:
                    max_comp = size
                if touches_top and touches_bot:
                    percolates = True
        if percolates:
            n_perc += 1
        gc_fracs[idx] = max_comp / float(n_nodes)

    return {
        "L": L,
        "n_nodes": n_nodes,
        "max_dead_FT": max_dead,
        "p_node": round(float(p_node), 6),
        "P_perc_mc": round(float(n_perc / n_mc), 5),
        "mean_f_GC_mc": round(float(np.mean(gc_fracs)), 5),
        "Y_FT_5pct_mc": round(y_ft_mc, 5),
        "Y_FT_5pct_exact": round(exact_binomial_ft_yield(n_nodes, max_dead, p_node), 6),
    }


def min_ncand_for_target_ft_yield(
    p_single: float,
    L: int = 11,
    target_yield: float = 0.99,
    max_search: int = 200,
) -> int:
    """Smallest integer N_cand such that Y_FT_5pct(L x L, 1 - (1 - p_single)^N_cand) >= target_yield."""
    n_nodes = L * L
    max_dead = int(math.floor(0.05 * n_nodes))
    for n_cand in range(1, max_search + 1):
        p_node = 1.0 - ((1.0 - p_single) ** n_cand)
        if exact_binomial_ft_yield(n_nodes, max_dead, p_node) >= target_yield:
            return n_cand
    return max_search


def compute_layer1_placement(ledgers: dict[str, Any]) -> dict[str, Any]:
    """Layer 1: Exp124 + Exp130 + Exp133 compound placement RSS budget (v3.0 vs v4.0 vs rigid CFG1)."""
    d124 = ledgers["exp124"]
    d130 = ledgers["exp130"]
    d133 = ledgers["exp133"]

    op15 = d124["operating_points_5keV"]["ArchB_HiRes_Ti0p5_15ms"]
    op10 = d124["operating_points_5keV"]["ArchB_HiRes_Ti0p25_10ms"]

    # Extract 808 nm / 1 ms flash-anneal point from Exp130
    wl_rows = d130["wavelength_and_pulse_benchmarks"]
    rows_iter = wl_rows.values() if isinstance(wl_rows, dict) else wl_rows
    flash_808 = next(
        r for r in rows_iter
        if abs(float(r["wavelength_nm"]) - 808.0) < 1.0 and abs(float(r["t_pulse_ms"]) - 1.0) < 0.05
    )
    sigma_anneal_v4 = float(flash_808["sigma_anneal_nm"])

    c4_15 = d133["exp124_budget_closure"]["CFG4_V4_FULL_CTRL_VCE"]["ArchB_HiRes_Ti0p5_15ms"]
    c4_10 = d133["exp124_budget_closure"]["CFG4_V4_FULL_CTRL_VCE"]["ArchB_HiRes_Ti0p25_10ms"]
    c1_15 = d133["exp124_budget_closure"]["CFG1_RIGID_OPEN_VCE"]["ArchB_HiRes_Ti0p5_15ms"]

    def _rss(vals: list[float]) -> float:
        return math.sqrt(sum(v * v for v in vals))

    sigma_bca = float(op15["sigma_straggle_nm"])
    s_stage_v4 = float(c4_15["sigma_stage_nm"])
    s_point_v4 = float(c4_15["sigma_pointing_nm"])
    s_therm_v4 = float(c4_15["sigma_thermal_nm"])

    v4_15 = _rss([sigma_bca, float(op15["sigma_spot_nm"]), s_stage_v4, s_point_v4, s_therm_v4, sigma_anneal_v4])
    v4_10 = _rss([sigma_bca, float(op10["sigma_spot_nm"]), s_stage_v4, s_point_v4, s_therm_v4, sigma_anneal_v4])
    rigid_15 = _rss([
        sigma_bca,
        float(op15["sigma_spot_nm"]),
        float(c1_15["sigma_stage_nm"]),
        float(c1_15["sigma_pointing_nm"]),
        float(c1_15["sigma_thermal_nm"]),
        sigma_anneal_v4,
    ])

    ceiling_nm = float(d130["exp124_placement_budget_impact"]["exp124_ceiling_nm"])
    return {
        "ceiling_nm": ceiling_nm,
        "components_v4_nm": {
            "sigma_bca_5keV": round(sigma_bca, 4),
            "sigma_spot_15ms": round(float(op15["sigma_spot_nm"]), 4),
            "sigma_spot_10ms": round(float(op10["sigma_spot_nm"]), 4),
            "sigma_stage_CFG4_VCE": round(s_stage_v4, 4),
            "sigma_pointing_CFG4_VCE": round(s_point_v4, 4),
            "sigma_thermal_Zerodur_Invar": round(s_therm_v4, 4),
            "sigma_anneal_808nm_1ms": round(sigma_anneal_v4, 4),
        },
        "v300_orig_15ms_nm": round(float(op15["sigma_total_nm"]), 4),
        "v300_orig_10ms_nm": round(float(op10["sigma_total_nm"]), 4),
        "v400_coupled_15ms_nm": round(v4_15, 4),
        "v400_coupled_10ms_nm": round(v4_10, 4),
        "rigid_CFG1_15ms_nm": round(rigid_15, 2),
        "margin_v4_15ms_nm": round(ceiling_nm - v4_15, 4),
        "margin_v4_10ms_nm": round(ceiling_nm - v4_10, 4),
        "improvement_15ms_nm": round(float(op15["sigma_total_nm"]) - v4_15, 4),
        "improvement_10ms_nm": round(float(op10["sigma_total_nm"]) - v4_10, 4),
        "flash_808nm_1ms_T_peak_K": float(flash_808["T_peak_K"]),
    }


def compute_layer2_write_activation(ledgers: dict[str, Any]) -> dict[str, Any]:
    """Layer 2: Exp127 Cold-100K IBIC efficiency x Exp130 808 nm/1 ms flash activation."""
    d127 = ledgers["exp127"]
    d130 = ledgers["exp130"]

    cold_list = d127["monte_carlo_eta"]["COLD_100K_1200ns_Rf1G"]["5keV"]
    pt05 = next(r for r in cold_list if abs(float(r["c_det_pF"]) - 0.5) < 0.01)
    eta_ibic = float(pt05["eta"])

    wl_rows = d130["wavelength_and_pulse_benchmarks"]
    rows_iter = wl_rows.values() if isinstance(wl_rows, dict) else wl_rows
    flash_808 = next(
        r for r in rows_iter
        if abs(float(r["wavelength_nm"]) - 808.0) < 1.0 and abs(float(r["t_pulse_ms"]) - 1.0) < 0.05
    )
    f_act = float(flash_808["f_act_bulk"])
    surf_loss = float(flash_808["f_total_surface_loss"])
    combined = eta_ibic * f_act
    return {
        "ibic_regime": "COLD_100K_1200ns_Rf1G_C0p5pF",
        "eta_ibic": eta_ibic,
        "ibic_snr": round(float(pt05["snr"]), 2),
        "ibic_enc_e": round(float(pt05["enc_e"]), 2),
        "flash_anneal_regime": "808nm_1ms_1440K",
        "f_act_bulk": f_act,
        "surface_loss_frac": surf_loss,
        "combined_implant_activation_survival": round(combined, 6),
        "total_non_bath_loss_pct": round((1.0 - combined) * 100.0, 4),
    }


def compute_layer3_risk_r1_regimes(ledgers: dict[str, Any]) -> dict[str, Any]:
    """Layer 3: Exp129 Risk R1 bath-yield envelope (KL vs VOKL-6 HM5962 vs VOKL-6 norm)."""
    d129 = ledgers["exp129"]
    mb = d129["mode_b_yield_n400"]

    kl_f1 = float(d129["exp59_62_portable_audit"]["cells"]["F1"]["yield_frac"])
    kl_n400 = mb["KL_legacy"]["F1"]
    hm_f1 = mb["VOKL6_HM5962_ext"]["F1"]
    hm_f2 = mb["VOKL6_HM5962_ext"]["F2"]
    nm_f1 = mb["VOKL6_norm_ext"]["F1"]

    def _sub6p89_frac(entry: dict[str, Any]) -> float:
        y = float(entry["yield_frac"])
        y_gt = float(entry["gap_stats"]["yield_and_gap_ge_6893Hz"])
        return round(1.0 - (y_gt / max(y, 1e-12)), 4)

    return {
        "KL_canonical_f1": {
            "label": "Canonical KL (f=1.0%)",
            "abundance_pct": 1.0,
            "p_bath": kl_f1,
            "p_bath_n400_audit": float(kl_n400["yield_frac"]),
            "frac_certified_below_6p89kHz": _sub6p89_frac(kl_n400),
        },
        "VOKL6_HM5962_f1": {
            "label": "VOKL-6 HM5962 (f=1.0%, Risk R1)",
            "abundance_pct": 1.0,
            "p_bath": float(hm_f1["yield_frac"]),
            "shift_vs_KL": round(float(hm_f1["yield_frac"]) - kl_f1, 4),
            "frac_certified_below_6p89kHz": _sub6p89_frac(hm_f1),
        },
        "VOKL6_HM5962_f2_lever": {
            "label": "VOKL-6 HM5962 (f=2.0% Isotope Lever)",
            "abundance_pct": 2.0,
            "p_bath": float(hm_f2["yield_frac"]),
            "shift_vs_KL": round(float(hm_f2["yield_frac"]) - kl_f1, 4),
            "frac_certified_below_6p89kHz": _sub6p89_frac(hm_f2),
        },
        "VOKL6_norm_f1_worst": {
            "label": "VOKL-6 norm (f=1.0%, Worst-Case Floor)",
            "abundance_pct": 1.0,
            "p_bath": float(nm_f1["yield_frac"]),
            "shift_vs_KL": round(float(nm_f1["yield_frac"]) - kl_f1, 4),
            "frac_certified_below_6p89kHz": _sub6p89_frac(nm_f1),
        },
    }


def compute_layer4_boed_throughput(
    ledgers: dict[str, Any],
    layer2: dict[str, Any],
    layer3: dict[str, Any],
) -> dict[str, Any]:
    """Layer 4: Exp132 + Exp125 coupled adaptive BOED throughput across all Risk R1 regimes."""
    d132 = ledgers["exp132"]
    d125 = ledgers["exp125"]
    bm = d132["boed_20mK_LNA1p4K_N2000"]

    t_work_ms = float(bm["by_class"]["working"]["mean_time_ms"])
    t_crowd_ms = float(bm["by_class"]["crowded"]["mean_time_ms"])
    t_blank_ms = float(bm["by_class"]["blank"]["mean_time_ms"])
    eta_ibic = float(layer2["eta_ibic"])
    f_act = float(layer2["f_act_bulk"])
    tau_snr10_ms = float(d125["verdicts"]["CV5_measure"]["tau_SNR10_20mK_1p4K_ms"])

    cfg_ref = MachineConfig.v400_bayesian(detector_eta=eta_ibic)
    sec_day = 86_400.0 * cfg_ref.duty_cycle
    writer = CountedWriter(eta_ibic, np.random.default_rng(2026135))
    shots_per_attempt = 1.0 / eta_ibic
    write_shots_15ms = (cfg_ref.beamlets / 0.015) * sec_day
    write_shots_10ms = (cfg_ref.beamlets / 0.010) * sec_day

    regimes_out: dict[str, Any] = {}
    for key in ("KL_canonical_f1", "VOKL6_HM5962_f1", "VOKL6_norm_f1_worst"):
        p_b = float(layer3[key]["p_bath"])
        # Effective per-attempt certification probability including IBIC stray factor and 808 nm activation
        p_eff = writer.effective_yield(p_b, cfg_ref.stray_survival) * f_act
        attempts_per_reg = 1.0 / p_eff
        shots_per_reg = shots_per_attempt * attempts_per_reg

        # BOED adaptive mean spectroscopy time:
        #   (a) Factory mixture (blank_prob = 0.50 of failures are blank, 0.50 crowded)
        t_boed_factory_ms = p_eff * t_work_ms + (1.0 - p_eff) * (0.5 * t_blank_ms + 0.5 * t_crowd_ms)
        #   (b) Conservative zero-blank bound (100% of failures are crowded -> 14.58 ms)
        t_boed_all_crowded_ms = p_eff * t_work_ms + (1.0 - p_eff) * t_crowd_ms

        v3_readout_per_day = (cfg_ref.readout_channels / (attempts_per_reg * 1.0)) * sec_day
        v4_ro_cap_factory = (cfg_ref.readout_channels / (attempts_per_reg * (t_boed_factory_ms / 1e3))) * sec_day
        v4_ro_cap_crowded = (cfg_ref.readout_channels / (attempts_per_reg * (t_boed_all_crowded_ms / 1e3))) * sec_day

        w_ceil_15 = write_shots_15ms / shots_per_reg
        w_ceil_10 = write_shots_10ms / shots_per_reg

        v3_net_15 = min(v3_readout_per_day, w_ceil_15)
        v4_net_15 = min(v4_ro_cap_factory, w_ceil_15)
        v4_net_10 = min(v4_ro_cap_factory, w_ceil_10)
        # Check conservative all-crowded too
        v4_net_15_cons = min(v4_ro_cap_crowded, w_ceil_15)
        v4_net_10_cons = min(v4_ro_cap_crowded, w_ceil_10)

        cross_15_ms = 1000.0 * (v3_readout_per_day / w_ceil_15)
        cross_10_ms = 1000.0 * (v3_readout_per_day / w_ceil_10)

        regimes_out[key] = {
            "p_bath": p_b,
            "p_eff_coupled": round(p_eff, 6),
            "attempts_per_register": round(attempts_per_reg, 4),
            "shots_per_register": round(shots_per_reg, 4),
            "boed_t_spec_factory_ms": round(t_boed_factory_ms, 2),
            "boed_t_spec_all_crowded_ms": round(t_boed_all_crowded_ms, 2),
            "raw_readout_speedup_factory": round(1000.0 / t_boed_factory_ms, 2),
            "raw_readout_speedup_all_crowded": round(1000.0 / t_boed_all_crowded_ms, 2),
            "crossover_15ms_t_spec_ms": round(cross_15_ms, 2),
            "crossover_10ms_t_spec_ms": round(cross_10_ms, 2),
            "v300_net_15ms_per_day": v3_net_15,
            "v400_readout_cap_factory_per_day": v4_ro_cap_factory,
            "v400_readout_cap_crowded_per_day": v4_ro_cap_crowded,
            "write_ceiling_15ms_per_day": w_ceil_15,
            "write_ceiling_10ms_per_day": w_ceil_10,
            "v400_net_15ms_per_day": v4_net_15,
            "v400_net_10ms_per_day": v4_net_10,
            "write_limited_15ms": bool(v4_ro_cap_factory >= w_ceil_15 and v4_ro_cap_crowded >= w_ceil_15),
            "write_limited_10ms": bool(v4_ro_cap_factory >= w_ceil_10 and v4_ro_cap_crowded >= w_ceil_10),
            "realized_speedup_15ms_vs_same_v3": round(v4_net_15 / v3_net_15, 3),
            "realized_speedup_10ms_vs_same_v3": round(v4_net_10 / v3_net_15, 3),
            "conservative_matches_write_ceiling": bool(
                abs(v4_net_15_cons - w_ceil_15) < 1.0 and abs(v4_net_10_cons - w_ceil_10) < 1.0
            ),
        }

    # Add speedup relative to v3.0 canonical KL baseline for cross-regime clarity
    v3_kl_base = regimes_out["KL_canonical_f1"]["v300_net_15ms_per_day"]
    for r in regimes_out.values():
        r["ratio_15ms_vs_v3_KL_baseline"] = round(r["v400_net_15ms_per_day"] / v3_kl_base, 3)
        r["ratio_10ms_vs_v3_KL_baseline"] = round(r["v400_net_10ms_per_day"] / v3_kl_base, 3)

    return {
        "exp125_tau_SNR10_20mK_ms": round(tau_snr10_ms, 6),
        "exp132_class_times_ms": {
            "working": t_work_ms,
            "crowded": t_crowd_ms,
            "blank": t_blank_ms,
            "exp132_N2000_mean": float(bm["mean_time_all_ms"]),
            "rms_freq_error_Hz": float(bm["rms_freq_error_Hz"]),
            "fnr": float(bm["fnr"]),
            "fpr": float(bm["fpr"]),
        },
        "regimes": regimes_out,
    }


def compute_layer5_quantum_and_bus(ledgers: dict[str, Any]) -> dict[str, Any]:
    """Layer 5: Exp126 32D 448-spectator programming + Exp131 high-Z NbTiN Lindblad cavity bus."""
    d126 = ledgers["exp126"]
    d131 = ledgers["exp131"]

    p4 = d126["verdicts"]["P126_4_risk_r3_interleaved_dd_f1"]["measured"]
    p7 = d126["verdicts"]["P126_7_multicell_program_fidelities"]["measured"]
    p8 = d126["verdicts"]["P126_8_d0_storage_and_parallel_array"]["measured"]

    # Extract N_total = 32 sweet spot from Exp126 f1_ghz4_ndd_sweep
    n32 = next(r for r in d126["part2_risk_r3_interleaved_dd"]["f1_ghz4_ndd_sweep"] if r["N_total"] == 32)
    imp = d131["part2_lindblad_bus"]["impedance_wall_comparison"]
    opt_cap = d131["part1_flipflop_straggle"]["optimal_capping"]

    return {
        "exp126_32d_448spec": {
            "N32_sweetspot_Q32D_alpha1": round(float(n32["results"]["a1_e0.001"]["Q_32d"]), 6),
            "N32_sweetspot_Q32D_alpha2": round(float(n32["results"]["a2_e0.001"]["Q_32d"]), 6),
            "N32_spectator_overlap_448": round(float(n32["spectator_overlap_all448"]), 6),
            "N64_Q32D_alpha1": round(float(p4["Q_32d_f1_N64_alpha1_e1e3"]), 6),
            "N64_Q32D_alpha2": round(float(p4["Q_32d_f1_N64_alpha2_e1e3"]), 6),
            "16cell_bell_mean_a2": round(float(p7["mean_bell_a2"]), 6),
            "16cell_ghz4_mean_a2": round(float(p7["mean_ghz4_a2"]), 6),
            "16cell_bitflip3_mean_a2": round(float(p7["mean_bitflip3_a2"]), 6),
            "16cell_qft3_mean_a2": round(float(p7["mean_qft3_a2"]), 6),
            "max_d0_leakage_17p5s": float(p8["max_d0_leakage_17p5s_across_16cells"]),
        },
        "exp131_m4_cavity_bus": {
            "optimal_capping_nm": float(opt_cap["delta_z_cap_nm"]),
            "p_flipflop_C_ge_100": float(opt_cap["yield_C_ge_100_tuned"]),
            "median_cooperativity_tuned": round(float(opt_cap["median_C_tuned"]), 1),
            "cpw_50ohm_mean_F_bell": round(float(imp["cpw_50ohm"]["mean_F_bell"]), 6),
            "nbtin_3kohm_mean_F_bell": round(float(imp["nbtin_3kohm"]["mean_F_bell"]), 6),
            "nbtin_3kohm_median_F_bell": round(float(imp["nbtin_3kohm"]["median_F_bell"]), 6),
            "nbtin_3kohm_mean_t_bell_us": round(float(imp["nbtin_3kohm"]["mean_t_bell_us"]), 4),
            "impedance_fidelity_gain": round(
                float(imp["nbtin_3kohm"]["mean_F_bell"]) - float(imp["cpw_50ohm"]["mean_F_bell"]), 6
            ),
        },
    }


def compute_layer6_m4_percolation_collision(
    ledgers: dict[str, Any],
    layer3: dict[str, Any],
) -> dict[str, Any]:
    """Layer 6: Exp131 + Exp129 collision — M4 2D surface-code percolation & N_cand* under Risk R1."""
    d131 = ledgers["exp131"]
    p_ff = float(d131["part1_flipflop_straggle"]["optimal_capping"]["yield_C_ge_100_tuned"])

    # Cross-check exact Exp131 L=11 N_cand=6 value
    exp131_l11_n6 = next(
        x for x in d131["part3_percolation_and_cad"]["square_m4"]["square_L11"]["sweep"]
        if x["N_cand"] == 6
    )

    out: dict[str, Any] = {
        "p_flipflop_opt_8nm": p_ff,
        "exp131_reference_KL_L11_Ncand6_Y_FT": round(float(exp131_l11_n6["Y_FT_5pct_exact"]), 6),
        "regimes": {},
    }

    sweep_ncands = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14]
    for r_idx, key in enumerate(
        ("KL_canonical_f1", "VOKL6_HM5962_f1", "VOKL6_HM5962_f2_lever", "VOKL6_norm_f1_worst")
    ):
        p_b = float(layer3[key]["p_bath"])
        p_m4 = p_b * p_ff
        nc_l5 = min_ncand_for_target_ft_yield(p_m4, L=5, target_yield=0.99)
        nc_l11 = min_ncand_for_target_ft_yield(p_m4, L=11, target_yield=0.99)
        nc_l21 = min_ncand_for_target_ft_yield(p_m4, L=21, target_yield=0.99)

        # Full L=11 exact + 2D lattice percolation MC sweep
        l11_sweep = []
        for nc in sweep_ncands:
            p_node = 1.0 - ((1.0 - p_m4) ** nc)
            # Run 2D percolation MC on key operating points (N=1,4,6,8,9,10,11,12) for fast exactness
            if nc in (1, 4, 6, 8, 9, 10, 11, 12):
                mc = mc_2d_square_percolation(L=11, p_node=p_node, n_mc=2_000, seed=2026135 + r_idx * 100 + nc)
                l11_sweep.append({"N_cand": nc, **mc})
            else:
                l11_sweep.append({
                    "N_cand": nc,
                    "L": 11,
                    "n_nodes": 121,
                    "max_dead_FT": 6,
                    "p_node": round(p_node, 6),
                    "Y_FT_5pct_exact": round(exact_binomial_ft_yield(121, 6, p_node), 6),
                })

        y_at_6 = next(x["Y_FT_5pct_exact"] for x in l11_sweep if x["N_cand"] == 6)
        y_at_9 = next(x["Y_FT_5pct_exact"] for x in l11_sweep if x["N_cand"] == 9)
        y_at_10 = next(x["Y_FT_5pct_exact"] for x in l11_sweep if x["N_cand"] == 10)
        y_at_11 = next(x["Y_FT_5pct_exact"] for x in l11_sweep if x["N_cand"] == 11)

        out["regimes"][key] = {
            "label": layer3[key]["label"],
            "p_bath": p_b,
            "p_m4_combined": round(p_m4, 6),
            "N_cand_star_L5_99pct": nc_l5,
            "N_cand_star_L11_99pct": nc_l11,
            "N_cand_star_L21_99pct": nc_l21,
            "L11_Y_FT_at_Ncand6": y_at_6,
            "L11_Y_FT_at_Ncand9": y_at_9,
            "L11_Y_FT_at_Ncand10": y_at_10,
            "L11_Y_FT_at_Ncand11": y_at_11,
            "L11_sweep": l11_sweep,
        }

    return out


def compute_layer7_economics(
    ledgers: dict[str, Any],
    layer4: dict[str, Any],
    layer6: dict[str, Any],
) -> dict[str, Any]:
    """Layer 7: Exp134 + Exp128 coupled unit economics & $50M/$100M budget cap margins."""
    d134 = ledgers["exp134"]
    d128 = ledgers["exp128"]

    tco_v3 = float(d134["tco_5yr_summary_no_wafers"]["v3_fab_tool_n1_5yr_tco_usd"]["p50"])
    tco_v4 = float(d134["tco_5yr_summary_no_wafers"]["v4_fab_tool_n1_5yr_tco_usd"]["p50"])
    tco_v3_foak = float(d134["tco_5yr_summary_no_wafers"]["v3_foak_program_5yr_tco_usd"]["p50"])
    tco_v4_foak = float(d134["tco_5yr_summary_no_wafers"]["v4_foak_program_5yr_tco_usd"]["p50"])

    bc = d134["budget_cap_v3_vs_v4"]
    exc = bc["exceedance_probabilities"]

    # Exp134 uses 5 yr * 365 days * 0.80 uptime = 1,460.0 active fab days
    active_days_5yr = 5.0 * 365.0 * 0.80
    n_phys_d17 = 577.0

    def _cost_row(tco_5yr: float, reg_per_day: float, p_b: float, n_cand_star: int) -> dict[str, float]:
        reg_5yr = reg_per_day * active_days_5yr
        usd_reg = tco_5yr / reg_5yr
        return {
            "reg_per_day": reg_per_day,
            "reg_5yr": reg_5yr,
            "uUSD_per_register": round(usd_reg * 1e6, 3),
            "uUSD_per_phys_qubit_K8": round((usd_reg / 8.0) * 1e6, 4),
            "usd_per_10k_chip_machine": round(usd_reg * 10_000.0, 4),
            "usd_per_d17_logical_1overpB": round(usd_reg * (n_phys_d17 / p_b), 5),
            "usd_per_d17_logical_M4_Ncand": round(usd_reg * (n_phys_d17 * n_cand_star), 5),
            "N_cand_star_used": n_cand_star,
        }

    r_kl = layer4["regimes"]["KL_canonical_f1"]
    r_hm = layer4["regimes"]["VOKL6_HM5962_f1"]
    r_nm = layer4["regimes"]["VOKL6_norm_f1_worst"]

    nc_kl = int(layer6["regimes"]["KL_canonical_f1"]["N_cand_star_L11_99pct"])
    nc_hm = int(layer6["regimes"]["VOKL6_HM5962_f1"]["N_cand_star_L11_99pct"])
    nc_nm = int(layer6["regimes"]["VOKL6_norm_f1_worst"]["N_cand_star_L11_99pct"])

    scenarios = {
        "v300_KL_15ms": _cost_row(tco_v3, r_kl["v300_net_15ms_per_day"], r_kl["p_bath"], nc_kl),
        "v400_KL_15ms": _cost_row(tco_v4, r_kl["v400_net_15ms_per_day"], r_kl["p_bath"], nc_kl),
        "v400_KL_10ms": _cost_row(tco_v4, r_kl["v400_net_10ms_per_day"], r_kl["p_bath"], nc_kl),
        "v300_VOKL6_HM5962_15ms": _cost_row(tco_v3, r_hm["v300_net_15ms_per_day"], r_hm["p_bath"], nc_hm),
        "v400_VOKL6_HM5962_15ms": _cost_row(tco_v4, r_hm["v400_net_15ms_per_day"], r_hm["p_bath"], nc_hm),
        "v400_VOKL6_HM5962_10ms": _cost_row(tco_v4, r_hm["v400_net_10ms_per_day"], r_hm["p_bath"], nc_hm),
        "v300_VOKL6_norm_15ms": _cost_row(tco_v3, r_nm["v300_net_15ms_per_day"], r_nm["p_bath"], nc_nm),
        "v400_VOKL6_norm_15ms": _cost_row(tco_v4, r_nm["v400_net_15ms_per_day"], r_nm["p_bath"], nc_nm),
    }

    cost_drop_kl_15_pct = (
        1.0 - scenarios["v400_KL_15ms"]["uUSD_per_register"] / scenarios["v300_KL_15ms"]["uUSD_per_register"]
    ) * 100.0
    cost_drop_kl_10_pct = (
        1.0 - scenarios["v400_KL_10ms"]["uUSD_per_register"] / scenarios["v300_KL_15ms"]["uUSD_per_register"]
    ) * 100.0
    cost_drop_hm_vs_v3kl_pct = (
        1.0 - scenarios["v400_VOKL6_HM5962_15ms"]["uUSD_per_register"] / scenarios["v300_KL_15ms"]["uUSD_per_register"]
    ) * 100.0

    return {
        "active_days_5yr": active_days_5yr,
        "tco_5yr_p50_usd": {
            "v3_fab_n1": round(tco_v3, 2),
            "v4_fab_n1": round(tco_v4, 2),
            "v3_foak_prog": round(tco_v3_foak, 2),
            "v4_foak_prog": round(tco_v4_foak, 2),
            "v4_hw_delta_usd": round(float(d134["v4_hardware_deltas"]["total_nom_usd"]), 2),
        },
        "bom_and_budget_caps": {
            "exp128_bom_detailed_total_usd": round(float(d128["bom_detailed_summary"]["m3_nom_usd"]), 2),
            "v3_hw_p50_usd": round(float(bc["v3_hw_mc_usd"]["p50"]), 2),
            "v4_hw_p50_usd": round(float(bc["v4_hw_mc_usd"]["p50"]), 2),
            "v4_prog_stoch_p50_usd": round(float(bc["v4_prog_stoch_usd"]["p50"]), 2),
            "v4_prog_stoch_p95_usd": round(float(bc["v4_prog_stoch_usd"]["p95"]), 2),
            "P_v4_BOM_gt_50M": float(exc["P_v4_BOM_gt_50M"]),
            "P_v4_Prog_stoch_gt_50M": float(exc["P_v4_Prog_stoch_gt_50M"]),
            "P_v4_Prog_stoch_gt_100M": float(exc["P_v4_Prog_stoch_gt_100M"]),
        },
        "unit_cost_reduction_pct": {
            "v4_KL_15ms_vs_v3_KL": round(cost_drop_kl_15_pct, 2),
            "v4_KL_10ms_vs_v3_KL": round(cost_drop_kl_10_pct, 2),
            "v4_HM5962_15ms_vs_v3_KL": round(cost_drop_hm_vs_v3kl_pct, 2),
        },
        "scenarios": scenarios,
    }


def run_layer8_live_integration(
    layer1: dict[str, Any],
    layer2: dict[str, Any],
    layer4: dict[str, Any],
    layer6: dict[str, Any],
    layer7: dict[str, Any],
    ledger_hashes: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Layer 8: Live src/machine_control/ v4.0 run (Factory + BOED + AtomCellProgrammer + CellISA v3.0)."""
    # 1. Live Factory comparison (120 slots each: v3 KL, v4 KL, v4 VOKL-6 HM5962)
    eta = float(layer2["eta_ibic"])
    cfg_v3 = MachineConfig.v300_baseline(detector_eta=eta, seed=2026135)
    cfg_v4_kl = MachineConfig.v400_bayesian(detector_eta=eta, bath_yield=0.51, seed=2026135)
    cfg_v4_hm = MachineConfig.v400_bayesian(detector_eta=eta, bath_yield=0.3325, seed=2026135)

    rep_v3 = Factory(cfg_v3).run(120)
    rep_v4_kl = Factory(cfg_v4_kl).run(120)
    rep_v4_hm = Factory(cfg_v4_hm).run(120)

    # 2. Live single-cell AtomCellProgrammer Bell + GHZ4 on first certified v4 register
    prog_local = AtomCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    cert0 = rep_v4_kl.certificates[0]
    _, pcert_bell = prog_local.execute_and_certify(cert0, program_bell(), verify_corners=True, seed=2026135)
    _, pcert_ghz = prog_local.execute_and_certify(cert0, program_ghz(4), verify_corners=False, seed=2026135)

    # 3. Live 4x4 heterogeneous wafer scanned by BayesianSpectrometer -> CellISA v3.0 MultiCellProgrammer
    rng_w = np.random.default_rng(1352026)
    spec_live = BayesianSpectrometer(BOEDConfig(), rng=np.random.default_rng(1352027))
    base_lines = np.array([65e3, 132e3, 255e3, 490e3, 845e3, 1310e3, 1980e3, 3020e3])
    wafer_sites: list[WaferSite] = []
    wafer_site_records: list[dict[str, Any]] = []
    for r in range(4):
        for c in range(4):
            u = rng_w.random()
            if u < 0.54:
                lines = np.sort(base_lines * rng_w.uniform(0.90, 1.10, size=8))
                # Ensure clean >= 12 kHz spacing for working site
                for idx in range(1, len(lines)):
                    if lines[idx] - lines[idx - 1] < 16_000.0:
                        lines[idx] = lines[idx - 1] + 18_000.0
                cand = CandidateSpectrum("working", True, lines, compute_min_transition_spacing_Hz(lines))
            elif u < 0.78:
                lines = np.sort(base_lines * rng_w.uniform(0.92, 1.08, size=8))
                lines[4] = lines[3] + 2_100.0
                cand = CandidateSpectrum("crowded", True, lines, compute_min_transition_spacing_Hz(lines))
            else:
                cand = CandidateSpectrum("blank", False, np.zeros(0, dtype=float), 0.0)

            res = spec_live.inspect_candidate(cand)
            cert = None
            status = cand.label
            if res.accepted and len(res.estimated_lines_Hz) == 8:
                est = np.sort(res.estimated_lines_Hz)
                cert = Certificate(
                    register_id=f"DT4-R{r}C{c}",
                    slot=r * 4 + c,
                    attempts=1,
                    shots=1,
                    min_spacing_Hz=compute_min_transition_spacing_Hz(est),
                    dd_quality_gate=True,
                    lines_Hz=[float(x) for x in est],
                )
                status = "working"
            elif status == "working":
                status = "crowded"
            ws = WaferSite(r, c, status, cert, round(res.total_time_ms, 2))
            wafer_sites.append(ws)
            wafer_site_records.append({
                "row": r,
                "col": c,
                "status": status,
                "cell_id": ws.cell_id,
                "boed_ms": round(res.total_time_ms, 2),
                "min_gap_kHz": round(cert.min_spacing_Hz / 1e3, 1) if cert else 0.0,
            })

    mprog = MultiCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    route, mcert = mprog.execute_routed_multicell_program(
        wafer_sites, target_cells=4, logical_code="bitflip3_plus_ancilla"
    )

    live_summary = {
        "factory_120slot": {
            "v300_KL": {
                "certified": rep_v3.certified,
                "mean_spec_ms": round(rep_v3.mean_spec_time_ms, 2),
                "analytic_per_day": rep_v3.certified_per_day_analytic,
            },
            "v400_KL": {
                "certified": rep_v4_kl.certified,
                "mean_spec_ms": round(rep_v4_kl.mean_spec_time_ms, 2),
                "early_aborts": rep_v4_kl.early_aborts,
                "analytic_per_day": rep_v4_kl.certified_per_day_analytic,
            },
            "v400_VOKL6_HM5962": {
                "certified": rep_v4_hm.certified,
                "mean_spec_ms": round(rep_v4_hm.mean_spec_time_ms, 2),
                "early_aborts": rep_v4_hm.early_aborts,
                "analytic_per_day": rep_v4_hm.certified_per_day_analytic,
            },
        },
        "single_cell_local_programming": {
            "register_id": cert0.register_id,
            "bell_nominal_fidelity": pcert_bell.nominal_state_fidelity,
            "bell_corner_min_fidelity": pcert_bell.corner_min_fidelity,
            "bell_sha256": pcert_bell.sha256,
            "ghz4_nominal_fidelity": pcert_ghz.nominal_state_fidelity,
            "ghz4_sha256": pcert_ghz.sha256,
        },
        "wafer_4x4_live": {
            "working_sites": route.working_sites,
            "dead_sites": route.dead_sites,
            "mean_boed_scan_ms": round(float(np.mean([s.spec_time_ms for s in wafer_sites])), 2),
            "routed_cell_ids": route.assigned_cell_ids,
            "routed_coords": [list(rc) for rc in route.assigned_coords],
            "bus_edges": [[a, b, h] for a, b, h in route.bus_edges],
            "sites": wafer_site_records,
            "multicell_cert": asdict(mcert),
            "multicell_sha256_verified": mcert.verify_signature(),
        },
    }

    # Build SHA-256 signed v4.0 Digital Twin Master Certificate
    master_payload: dict[str, Any] = {
        "certificate_type": "ATOM_LITHOGRAPHY_MACHINE_V4_DIGITAL_TWIN",
        "experiment": "exp135_v4_digital_twin",
        "hypothesis_id": "H153",
        "no_lab_measurement": True,
        "epistemic_tag": "Model / Sayisal-Simulasyon",
        "primary_ledger_sha256": ledger_hashes,
        "placement_sigma_v4_15ms_nm": layer1["v400_coupled_15ms_nm"],
        "placement_sigma_v4_10ms_nm": layer1["v400_coupled_10ms_nm"],
        "write_activation_survival": layer2["combined_implant_activation_survival"],
        "throughput_v4_KL_15ms_per_day": layer4["regimes"]["KL_canonical_f1"]["v400_net_15ms_per_day"],
        "throughput_v4_HM5962_15ms_per_day": layer4["regimes"]["VOKL6_HM5962_f1"]["v400_net_15ms_per_day"],
        "m4_L11_Ncand_star_KL": layer6["regimes"]["KL_canonical_f1"]["N_cand_star_L11_99pct"],
        "m4_L11_Ncand_star_HM5962": layer6["regimes"]["VOKL6_HM5962_f1"]["N_cand_star_L11_99pct"],
        "uUSD_per_reg_v4_KL_15ms": layer7["scenarios"]["v400_KL_15ms"]["uUSD_per_register"],
        "uUSD_per_reg_v4_HM5962_15ms": layer7["scenarios"]["v400_VOKL6_HM5962_15ms"]["uUSD_per_register"],
        "live_multicell_sha256": mcert.sha256,
        "live_multicell_joint_fidelity": mcert.joint_state_fidelity,
        "live_multicell_min_bus_cz": mcert.min_bus_cz_fidelity,
        "live_multicell_certified": mcert.certified,
    }
    canon = json.dumps(master_payload, sort_keys=True, separators=(",", ":"))
    master_cert = dict(master_payload)
    master_cert["sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return live_summary, master_cert


def verify_master_certificate(cert: dict[str, Any]) -> bool:
    """Recompute and verify SHA-256 integrity of a v4.0 Digital Twin Master Certificate."""
    sig = str(cert.get("sha256", ""))
    if not sig:
        return False
    payload = {k: v for k, v in cert.items() if k != "sha256"}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == sig


def run_digital_twin(write_outputs: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    ledgers, hashes = load_primary_ledgers(ROOT)

    layer1 = compute_layer1_placement(ledgers)
    layer2 = compute_layer2_write_activation(ledgers)
    layer3 = compute_layer3_risk_r1_regimes(ledgers)
    layer4 = compute_layer4_boed_throughput(ledgers, layer2, layer3)
    layer5 = compute_layer5_quantum_and_bus(ledgers)
    layer6 = compute_layer6_m4_percolation_collision(ledgers, layer3)
    layer7 = compute_layer7_economics(ledgers, layer4, layer6)
    layer8, master_cert = run_layer8_live_integration(layer1, layer2, layer4, layer6, layer7, hashes)

    # Portability self-check on Exp135 files
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    hardcoded_hits: list[str] = []
    for fp in (
        ROOT / "experiments" / "exp135_v4_digital_twin" / "digital_twin135.py",
        PRED_PATH,
    ):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            if bad_a in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_a}")
            if bad_b in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_b}")

    # Evaluate pre-registered verdicts DT1-DT7
    r_kl = layer4["regimes"]["KL_canonical_f1"]
    r_hm = layer4["regimes"]["VOKL6_HM5962_f1"]
    r_nm = layer4["regimes"]["VOKL6_norm_f1_worst"]
    p6_hm = layer6["regimes"]["VOKL6_HM5962_f1"]
    p6_f2 = layer6["regimes"]["VOKL6_HM5962_f2_lever"]
    p6_nm = layer6["regimes"]["VOKL6_norm_f1_worst"]
    sc7 = layer7["scenarios"]
    bc7 = layer7["bom_and_budget_caps"]
    mc8 = layer8["wafer_4x4_live"]["multicell_cert"]

    verdicts = {
        "DT1_PLACEMENT_BUDGET_V4": bool(
            layer1["v400_coupled_15ms_nm"] < 3.65
            and layer1["v400_coupled_10ms_nm"] < 3.60
            and layer1["rigid_CFG1_15ms_nm"] > 2000.0
            and layer2["combined_implant_activation_survival"] >= 0.999
        ),
        "DT2_BOED_WRITE_CEILING_ACROSS_R1": bool(
            r_kl["boed_t_spec_factory_ms"] > r_hm["boed_t_spec_factory_ms"] > r_nm["boed_t_spec_factory_ms"]
            and r_kl["write_limited_15ms"]
            and r_hm["write_limited_15ms"]
            and r_nm["write_limited_15ms"]
            and r_kl["v400_net_15ms_per_day"] >= 1.50e9
            and r_hm["v400_net_15ms_per_day"] >= 9.5e8
        ),
        "DT3_VOKL6_M4_PERCOLATION_PENALTY": bool(
            p6_hm["L11_Y_FT_at_Ncand6"] < 0.10
            and 10 <= p6_hm["N_cand_star_L11_99pct"] <= 12
            and p6_nm["N_cand_star_L11_99pct"] > 50
            and p6_f2["N_cand_star_L11_99pct"] == 6
        ),
        "DT4_UNIT_ECONOMICS_AND_BUDGET_CAP": bool(
            layer7["unit_cost_reduction_pct"]["v4_KL_15ms_vs_v3_KL"] >= 80.0
            and sc7["v400_KL_15ms"]["uUSD_per_register"] <= 8.0
            and sc7["v400_VOKL6_HM5962_15ms"]["uUSD_per_register"] <= 12.0
            and sc7["v400_KL_15ms"]["usd_per_d17_logical_1overpB"] < 0.01
            and sc7["v400_VOKL6_HM5962_15ms"]["usd_per_d17_logical_1overpB"] < 0.025
            and bc7["P_v4_BOM_gt_50M"] == 0.0
            and bc7["P_v4_Prog_stoch_gt_100M"] < 0.05
        ),
        "DT5_EXP126_QUANTUM_AND_BUS_BRIDGE": bool(
            layer5["exp126_32d_448spec"]["N64_Q32D_alpha2"] >= 0.94
            and layer5["exp126_32d_448spec"]["16cell_bell_mean_a2"] >= 0.94
            and layer5["exp126_32d_448spec"]["16cell_ghz4_mean_a2"] >= 0.93
            and layer5["exp126_32d_448spec"]["max_d0_leakage_17p5s"] <= 1e-8
            and layer5["exp131_m4_cavity_bus"]["nbtin_3kohm_mean_F_bell"] >= 0.96
            and layer5["exp131_m4_cavity_bus"]["cpw_50ohm_mean_F_bell"] < 0.80
        ),
        "DT6_LIVE_4X4_WAFER_DIGITAL_TWIN_CERT": bool(
            mc8["certified"]
            and mc8["joint_state_fidelity"] >= 0.95
            and mc8["min_bus_cz_fidelity"] >= 0.98
            and layer8["wafer_4x4_live"]["multicell_sha256_verified"]
            and verify_master_certificate(master_cert)
        ),
        "DT7_PORTABILITY_AND_REGRESSION": bool(len(hardcoded_hits) == 0),
    }

    out_data = {
        "experiment": "exp135_v4_digital_twin",
        "hypothesis_id": "H153",
        "date": "2026-11-23",
        "no_lab_measurement": True,
        "epistemic_tags": ["Model", "Sayisal-Simulasyon"],
        "runtime_s": round(time.perf_counter() - t0, 2),
        "predictions": preds,
        "verdicts": verdicts,
        "n_passed": sum(1 for v in verdicts.values() if v),
        "n_total": len(verdicts),
        "success_rule_met": bool(all(verdicts.values())),
        "primary_ledger_sha256": hashes,
        "layer1_placement_budget": layer1,
        "layer2_write_activation": layer2,
        "layer3_risk_r1_envelope": layer3,
        "layer4_boed_throughput": layer4,
        "layer5_quantum_and_bus": layer5,
        "layer6_m4_percolation_collision": layer6,
        "layer7_unit_economics": layer7,
        "layer8_live_integration": layer8,
        "v4_master_certificate": master_cert,
        "portability_hardcoded_hits": hardcoded_hits,
    }

    if write_outputs:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "exp135.json").write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        (OUT_DIR / "v4_digital_twin_cert.json").write_text(
            json.dumps(master_cert, indent=2), encoding="utf-8"
        )
        # Compact plot payload for pure-stdlib PyCairo plotter
        plot_payload = {
            "verdicts": verdicts,
            "layer1": layer1,
            "layer2": layer2,
            "layer3": layer3,
            "layer4": layer4,
            "layer5": layer5,
            "layer6": layer6,
            "layer7": layer7,
            "wafer_live": layer8["wafer_4x4_live"],
            "master_cert": master_cert,
        }
        (OUT_DIR / "exp135_plot_data.json").write_text(
            json.dumps(plot_payload, indent=2), encoding="utf-8"
        )
    return out_data


def main() -> None:
    res = run_digital_twin(write_outputs=True)
    print("=== EXP135 (H153) v4.0 DIGITAL TWIN VERDICTS ===")
    for k, v in res["verdicts"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"success_rule_met = {res['success_rule_met']} ({res['n_passed']}/{res['n_total']}, {res['runtime_s']}s)")
    l1 = res["layer1_placement_budget"]
    l2 = res["layer2_write_activation"]
    l4 = res["layer4_boed_throughput"]["regimes"]
    l6 = res["layer6_m4_percolation_collision"]["regimes"]
    l7 = res["layer7_unit_economics"]["scenarios"]
    print(
        f"L1 Placement: v3={l1['v300_orig_15ms_nm']}/{l1['v300_orig_10ms_nm']} nm -> "
        f"v4={l1['v400_coupled_15ms_nm']}/{l1['v400_coupled_10ms_nm']} nm (CFG1 rigid={l1['rigid_CFG1_15ms_nm']} nm) | "
        f"L2 survival={l2['combined_implant_activation_survival']}"
    )
    print(
        f"L4 BOED Throughput (15ms/10ms): "
        f"KL={l4['KL_canonical_f1']['v400_net_15ms_per_day']:.3e}/{l4['KL_canonical_f1']['v400_net_10ms_per_day']:.3e} (t_BOED={l4['KL_canonical_f1']['boed_t_spec_factory_ms']}ms) | "
        f"HM5962={l4['VOKL6_HM5962_f1']['v400_net_15ms_per_day']:.3e}/{l4['VOKL6_HM5962_f1']['v400_net_10ms_per_day']:.3e} (t_BOED={l4['VOKL6_HM5962_f1']['boed_t_spec_factory_ms']}ms) | "
        f"norm={l4['VOKL6_norm_f1_worst']['v400_net_15ms_per_day']:.3e} (t_BOED={l4['VOKL6_norm_f1_worst']['boed_t_spec_factory_ms']}ms)"
    )
    print(
        f"L6 M4 L=11 Percolation: KL N_cand*={l6['KL_canonical_f1']['N_cand_star_L11_99pct']} (N=6:{l6['KL_canonical_f1']['L11_Y_FT_at_Ncand6']:.4f}) | "
        f"HM5962 N_cand*={l6['VOKL6_HM5962_f1']['N_cand_star_L11_99pct']} (N=6:{l6['VOKL6_HM5962_f1']['L11_Y_FT_at_Ncand6']:.4f}, N=9:{l6['VOKL6_HM5962_f1']['L11_Y_FT_at_Ncand9']:.4f}, N=10:{l6['VOKL6_HM5962_f1']['L11_Y_FT_at_Ncand10']:.4f}, N=11:{l6['VOKL6_HM5962_f1']['L11_Y_FT_at_Ncand11']:.4f}) | "
        f"HM5962 f=2% N_cand*={l6['VOKL6_HM5962_f2_lever']['N_cand_star_L11_99pct']} | "
        f"norm N_cand*={l6['VOKL6_norm_f1_worst']['N_cand_star_L11_99pct']}"
    )
    print(
        f"L7 Cost (uUSD/reg | d=17 $): v3_KL={l7['v300_KL_15ms']['uUSD_per_register']} | ${l7['v300_KL_15ms']['usd_per_d17_logical_1overpB']} -> "
        f"v4_KL_15ms={l7['v400_KL_15ms']['uUSD_per_register']} | ${l7['v400_KL_15ms']['usd_per_d17_logical_1overpB']} | "
        f"v4_HM5962_15ms={l7['v400_VOKL6_HM5962_15ms']['uUSD_per_register']} | ${l7['v400_VOKL6_HM5962_15ms']['usd_per_d17_logical_1overpB']}"
    )
    mc = res["layer8_live_integration"]["wafer_4x4_live"]["multicell_cert"]
    print(
        f"L8 Live 4x4: F_joint={mc['joint_state_fidelity']:.6f}, min_CZ={mc['min_bus_cz_fidelity']:.6f}, "
        f"master_sha256={res['v4_master_certificate']['sha256']}"
    )


if __name__ == "__main__":
    main()
