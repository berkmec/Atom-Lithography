"""Exp140 (H158): Real-Time Q16.16 BOED-FPGA Accelerator + 3 kOhm NbTiN Mux Cryo Readout & CellISA v3.5.

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp140_cryo_fpga_boed_mux_readout/run_exp140.py

Reads pre-registered ``results/exp140_cryo_fpga_boed_mux_readout/predictions_exp140.json``
and writes:
  - ``results/exp140_cryo_fpga_boed_mux_readout/exp140.json``
  - ``results/exp140_cryo_fpga_boed_mux_readout/s65_hardware_spec.json``
  - ``results/exp140_cryo_fpga_boed_mux_readout/exp140_plot_data.json``
  - ``results/exp140_cryo_fpga_boed_mux_readout/syndrome_v35_demo.jsonl``

Epistemic status: {Model} / {Sayisal-Simulasyon} / {Liste-Capasi}, no_lab_measurement=true.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from machine_control.adaptive_spectroscopy import (  # noqa: E402
    BOEDConfig,
    compute_min_transition_spacing_Hz,
    sample_candidate_population,
)
from machine_control.factory import Certificate  # noqa: E402
from machine_control.fpga_boed_dsp import (  # noqa: E402
    FPGACoreConfig,
    run_paired_fp64_vs_q16_benchmark,
)
from machine_control.programmer import (  # noqa: E402
    MultiCellProgrammer,
    VALID_OPCODES,
    VALID_OPCODES_V35,
    WaferSite,
)
from mux_cryo_model140 import (  # noqa: E402
    build_s65_hardware_spec,
    evaluate_cryo_heat_budget,
    evaluate_mux_readout_sweep,
)

OUT_DIR = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout"
PRED_PATH = OUT_DIR / "predictions_exp140.json"


def run_exp140(n_candidates: int = 400, write_outputs: bool = True) -> dict:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))

    # 1. Paired FP64 vs Bit-Exact Q16.16 BOED-FPGA DSP Benchmark
    rng_pop = np.random.default_rng(2026140)
    cands = sample_candidate_population(n_candidates, rng_pop)
    fpga_bench = run_paired_fp64_vs_q16_benchmark(cands, BOEDConfig(), FPGACoreConfig(), seed=2026140)

    # 2. 3 kOhm NbTiN Frequency-Multiplexed + Purcell + 20 mK TWPA + 4 K HEMT Readout Sweep
    mux_res = evaluate_mux_readout_sweep(
        n_mux_list=(8, 16, 32, 64),
        tau_ro_us_grid=(0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0),
    )
    n_mux_star = int(mux_res["n_mux_star"])

    # 3. 4-Stage Cryostat Heat-Load Budgets: 1,024-cell vs 10,000-cell M4 arrays
    cryo_1024_7p8 = evaluate_cryo_heat_budget(1_024, n_mux=n_mux_star, xy_mux=32, use_low_power_hemt=False)
    cryo_1024_2p1 = evaluate_cryo_heat_budget(1_024, n_mux=n_mux_star, xy_mux=32, use_low_power_hemt=True)
    cryo_10000_7p8 = evaluate_cryo_heat_budget(10_000, n_mux=n_mux_star, xy_mux=32, use_low_power_hemt=False)
    cryo_10000_2p1 = evaluate_cryo_heat_budget(10_000, n_mux=n_mux_star, xy_mux=32, use_low_power_hemt=True)

    # Scaling curve across array sizes [256 .. 10000] for figure
    array_scale_curve = [
        evaluate_cryo_heat_budget(n, n_mux=n_mux_star, xy_mux=32, use_low_power_hemt=False)
        for n in (256, 512, 1_024, 2_048, 3_000, 4_096, 6_000, 8_000, 10_000)
    ]

    # 4. S6.5 Hardware Engineering Specification JSON (for CAD v5.0 & BOM v5.0)
    s65_spec = build_s65_hardware_spec(
        fpga_bench["fpga_resources"], cryo_1024_7p8, cryo_10000_7p8, n_mux_star
    )

    # 5. Live CellISA v3.5 Fault-Tolerant Syndrome Cycle on 4x4 Heterogeneous Wafer
    rng_w = np.random.default_rng(1402026)
    base_lines = np.array([62e3, 128e3, 248e3, 480e3, 835e3, 1295e3, 1960e3, 2990e3])
    dead_coords = {(0, 1), (0, 3), (1, 2), (2, 1), (2, 3), (3, 0), (3, 2)}
    wafer_sites: list[WaferSite] = []
    for r in range(4):
        for c in range(4):
            if (r, c) in dead_coords:
                wafer_sites.append(WaferSite(r, c, "blank" if (r + c) % 2 == 0 else "crowded", None, 1.0))
            else:
                lines = np.sort(base_lines * rng_w.uniform(0.93, 1.07, size=8))
                cert = Certificate(
                    register_id=f"M4V35-R{r}C{c}",
                    slot=r * 4 + c,
                    attempts=1,
                    shots=1,
                    min_spacing_Hz=compute_min_transition_spacing_Hz(lines),
                    dd_quality_gate=True,
                    lines_Hz=[float(x) for x in lines],
                )
                wafer_sites.append(WaferSite(r, c, "working", cert, 74.5))

    mprog = MultiCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    ro_star = mux_res["by_nmux"][str(n_mux_star)]
    out_jsonl = (OUT_DIR / "syndrome_v35_demo.jsonl") if write_outputs else None
    route, mcert_v35, syn_summary = mprog.execute_syndrome_cycle(
        wafer_sites,
        target_cells=4,
        logical_code="stabilizer_z4_echo_mux",
        n_mux=n_mux_star,
        tau_ro_us=2.0,
        s_eps_uev=1.0,
        echo_pulses=1,
        readout_fidelity=ro_star["F_ro_at_2us"],
        crosstalk_error=0.0,  # already included inside ro_star["F_ro_at_2us"]
        rounds=1,
        out_jsonl=out_jsonl,
    )

    # Portability self-check
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    hardcoded_hits: list[str] = []
    for fp in (
        ROOT / "src" / "machine_control" / "fpga_boed_dsp.py",
        ROOT / "src" / "machine_control" / "programmer.py",
        ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout" / "mux_cryo_model140.py",
        ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout" / "run_exp140.py",
        PRED_PATH,
    ):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            if bad_a in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_a}")
            if bad_b in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_b}")

    # Evaluate pre-registered verdicts FM1-FM7
    par = fpga_bench["parity"]
    res_fpga = fpga_bench["fpga_resources"]
    t16 = res_fpga["total_16ch"]
    ch_phys = mux_res["chain_physics"]
    nm32 = mux_res["by_nmux"]["32"]
    nm64 = mux_res["by_nmux"]["64"]

    verdicts = {
        "FM1_Q16_16_FP64_PARITY": bool(
            par["abs_delta_rms_Hz"] < 1.0
            and par["abs_delta_fnr_pct"] < 0.05
            and par["abs_delta_fpr_pct"] < 0.05
            and fpga_bench["q16_16"]["rms_freq_error_Hz"] <= 100.0
            and fpga_bench["stage0_sprt_disagreements"] == 0
        ),
        "FM2_FPGA_CYCLE_LATENCY_AND_RESOURCES": bool(
            res_fpga["latency_per_boed_step_us"] < 25.0
            and t16["dsp48e2_pct"] < 25.0
            and t16["bram36_pct"] < 25.0
            and t16["lut_pct"] < 25.0
        ),
        "FM3_PURCELL_AND_TWPA_SINGLE_SHOT_RO": bool(
            ch_phys["purcell_protection_factor"] > 100.0
            and ch_phys["t1_purcell_filtered_ms"] > 10.0
            and nm32["F_ro_at_2us"] >= 0.990
        ),
        "FM4_PHYSICAL_NMUX_CEILING": bool(
            n_mux_star in (16, 32)
            and (not nm64["passes_99pct_at_2us"])
            and nm64["F_ro_at_2us"] < nm32["F_ro_at_2us"]
        ),
        "FM5_CRYO_BUDGET_1024_CLOSES_10000_WALL": bool(
            cryo_1024_7p8["closes_single_pt420_ld400"] is True
            and cryo_10000_7p8["closes_single_pt420_ld400"] is False
            and cryo_10000_7p8["loads"]["mxc_20mK_uW"] > 14.0
            and cryo_10000_7p8["loads"]["stage_4K_W"] > 2.0
            and cryo_10000_7p8["min_modular_ld400_pt420_cryostats"] >= 4
        ),
        "FM6_CELLISA_V35_SYNDROME_AND_BACKCOMPAT": bool(
            len(VALID_OPCODES) == 17
            and VALID_OPCODES_V35 == frozenset({"ECHO_CZ", "MUX_READOUT", "SYNDROME_CYCLE"})
            and mcert_v35.isa_version == "3.5"
            and mcert_v35.certified
            and mcert_v35.verify_signature()
            and syn_summary["echo_fidelity_gain"] > 0.15
        ),
        "FM7_S65_SPEC_PORTABILITY_AND_TESTS": bool(
            len(hardcoded_hits) == 0
            and s65_spec["subsystem_id"] == "S6.5"
            and len(s65_spec["items"]) == 4
        ),
    }

    out_data = {
        "experiment": "exp140_cryo_fpga_boed_mux_readout",
        "hypothesis_id": "H158",
        "date": "2026-11-23",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "epistemic_tags": ["Model", "Sayisal-Simulasyon", "Liste-Capasi"],
        "runtime_s": round(time.perf_counter() - t0, 2),
        "predictions": preds,
        "verdicts": verdicts,
        "n_passed": sum(1 for v in verdicts.values() if v),
        "n_total": len(verdicts),
        "success_rule_met": bool(all(verdicts.values())),
        "fpga_boed_q16_benchmark": fpga_bench,
        "mux_readout_3kOhm_NbTiN": mux_res,
        "cryo_heat_budgets": {
            "m4_1024_hemt7p8mW": cryo_1024_7p8,
            "m4_1024_hemt2p1mW": cryo_1024_2p1,
            "m4_10000_hemt7p8mW": cryo_10000_7p8,
            "m4_10000_hemt2p1mW": cryo_10000_2p1,
            "array_scale_curve": array_scale_curve,
        },
        "cellisa_v35_syndrome_demo": {
            "route": {
                "working_sites": route.working_sites,
                "dead_sites": route.dead_sites,
                "assigned_cell_ids": route.assigned_cell_ids,
                "assigned_coords": [list(c) for c in route.assigned_coords],
                "bus_edges": [[a, b, h] for a, b, h in route.bus_edges],
            },
            "summary": syn_summary,
            "certificate": asdict(mcert_v35),
            "sha256_verified": mcert_v35.verify_signature(),
        },
        "s65_hardware_spec": s65_spec,
        "portability_hardcoded_hits": hardcoded_hits,
    }

    if write_outputs:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "exp140.json").write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        (OUT_DIR / "s65_hardware_spec.json").write_text(json.dumps(s65_spec, indent=2), encoding="utf-8")
        plot_payload = {
            "verdicts": verdicts,
            "fpga_bench": fpga_bench,
            "mux_res": mux_res,
            "cryo_1024": cryo_1024_7p8,
            "cryo_10000": cryo_10000_7p8,
            "array_scale_curve": array_scale_curve,
            "cellisa_v35": out_data["cellisa_v35_syndrome_demo"],
            "s65_spec": s65_spec,
        }
        (OUT_DIR / "exp140_plot_data.json").write_text(json.dumps(plot_payload, indent=2), encoding="utf-8")

    return out_data


def main() -> None:
    res = run_exp140(n_candidates=400, write_outputs=True)
    print("=== EXP140 (H158) VERDICTS ===")
    for k, v in res["verdicts"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"success_rule_met = {res['success_rule_met']} ({res['n_passed']}/{res['n_total']}, {res['runtime_s']}s)")
    fb = res["fpga_boed_q16_benchmark"]
    fr = fb["fpga_resources"]
    print(
        f"FPGA Q16.16 vs FP64 (N={fb['n_candidates']}, {fb['n_lines_paired']} lines): "
        f"RMS={fb['q16_16']['rms_freq_error_Hz']:.2f} vs {fb['fp64']['rms_freq_error_Hz']:.2f} Hz "
        f"(|dRMS|={fb['parity']['abs_delta_rms_Hz']:.4f} Hz, quant_rms={fb['parity']['rms_quantization_diff_Hz']:.4f} Hz) | "
        f"dFNR={fb['parity']['abs_delta_fnr_pct']:.4f}% | "
        f"step={fr['cycles_per_boed_step']} cyc = {fr['latency_per_boed_step_us']} us | "
        f"16ch DSP={fr['total_16ch']['dsp48e2_pct']}% BRAM={fr['total_16ch']['bram36_pct']}% LUT={fr['total_16ch']['lut_pct']}%"
    )
    mx = res["mux_readout_3kOhm_NbTiN"]
    cp = mx["chain_physics"]
    print(
        f"Mux 3kOhm NbTiN (Purcell={cp['purcell_protection_factor']}x, T1_P={cp['t1_purcell_filtered_ms']} ms, T_sys={cp['t_sys_with_twpa_K']} K): "
        f"N_mux*={mx['n_mux_star']} | F_RO(2us): "
        + ", ".join(f"N={k}:{mx['by_nmux'][k]['F_ro_at_2us']:.4f}(coll={mx['by_nmux'][k]['pair_collision_prob_pct']:.2f}%)" for k in ("8", "16", "32", "64"))
    )
    c1 = res["cryo_heat_budgets"]["m4_1024_hemt7p8mW"]
    c10 = res["cryo_heat_budgets"]["m4_10000_hemt7p8mW"]
    print(
        f"Cryo 1,024 ({c1['n_ro_chains']} RO): closes={c1['closes_single_pt420_ld400']} | "
        f"20mK={c1['loads']['mxc_20mK_uW']}/14uW, 100mK={c1['loads']['cp_100mK_uW']}/400uW, "
        f"4K={c1['loads']['stage_4K_W']}/2.0W, 50K={c1['loads']['stage_50K_W']}/40W"
    )
    print(
        f"Cryo 10,000 ({c10['n_ro_chains']} RO): closes={c10['closes_single_pt420_ld400']} (max_single={c10['single_cryostat_max_cells']}, min_fridges={c10['min_modular_ld400_pt420_cryostats']}) | "
        f"20mK={c10['loads']['mxc_20mK_uW']}uW, 100mK={c10['loads']['cp_100mK_uW']}uW, "
        f"4K={c10['loads']['stage_4K_W']}W, 50K={c10['loads']['stage_50K_W']}W"
    )
    v35 = res["cellisa_v35_syndrome_demo"]
    print(
        f"CellISA v3.5 ({v35['summary']['total_opcodes_supported']} opcodes): "
        f"Bare CZ={v35['summary']['mean_bare_cz_fidelity']:.4f} -> ECHO_CZ={v35['summary']['mean_echo_cz_fidelity']:.4f} "
        f"(+{v35['summary']['echo_fidelity_gain']:.4f}) | Syndrome F={v35['summary']['syndrome_round_fidelity']:.4f} | "
        f"T_cyc={v35['summary']['cycle_duration_us']:.3f} us | SHA256={v35['sha256_verified']}"
    )


if __name__ == "__main__":
    main()
