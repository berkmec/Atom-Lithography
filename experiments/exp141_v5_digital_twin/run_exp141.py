"""CLI runner for Exp141 (H159) — Master v5.0 End-to-End Fault-Tolerant Digital Twin.

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp141_v5_digital_twin/run_exp141.py
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from digital_twin141 import run_v5_digital_twin  # noqa: E402


def main() -> None:
    res = run_v5_digital_twin(write_outputs=True)
    print("=== EXP141 (H159) MASTER v5.0 DIGITAL TWIN VERDICTS ===")
    for k, v in res["verdicts"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"success_rule_met = {res['success_rule_met']} ({res['n_passed']}/{res['n_total']}, {res['runtime_s']}s)")

    l1 = res["layer1_integrity"]
    l2 = res["layer2_v5_placement"]
    l3 = res["layer3_quantum_chain"]
    l4 = res["layer4_live_control_stack"]
    l5 = res["layer5_surface_code_ft"]
    cx4 = res["layer6_wafer_cx4_economics"]["cx4_closure"]
    le = res["layer7_logical_qubit_economics"]

    print(
        f"L1 Integrity: {l1['n_experiment_ledgers']} exps + CAD v5 ({l1['cad_v5']['part_count']} parts, "
        f"{l1['cad_v5']['total_mass_kg']} kg, {l1['cad_v5']['solid_clashes']}/{l1['cad_v5']['pairs_checked']} clashes, "
        f"{l1['cad_v5']['clearances_passed']}/{l1['cad_v5']['clearances_total']} clearances) + "
        f"BOM v5 ({l1['bom_v5']['csv_row_count']} parts, M3=${l1['bom_v5']['m3_v5_nom_usd']:,.0f})"
    )
    print(
        f"L2 Placement: v3={l2['v300_orig_15ms_nm']} -> v4_hiddenTED={l2['v400_hidden_TED_routeC_15ms_nm']} (Exp139:{l2['exp139_reported_v4_hidden_TED_nm']} FAIL) -> "
        f"v5_1530K={l2['v500_coupled_15ms_nm']}/{l2['v500_coupled_10ms_nm']} nm (Exp139:{l2['exp139_reported_v5_1530K_nm']} PASS)"
    )
    print(
        f"L3 Quantum Chain: f*1.5%+2MV/m={l3['exp136_tb_sp3d5s']['f1p5_Ez2_yield_pct']}% (d_eff/d={l3['exp136_tb_sp3d5s']['defective_d7_N6_deff_over_d']}) | "
        f"RouteC p_ff={l3['exp139_epi_cap_routeC']['p_flipflop_C_ge_100']}, S_eps={l3['exp139_epi_cap_routeC']['S_eps_nominal_ueV_rtHz']} | "
        f"P4 F_Bell(0.25)={l3['exp137_echoed_m4_bus']['P4_S0p25_F_Bell']} | N_mux*={l3['exp140_mux_fpga']['n_mux_star']} F_RO={l3['exp140_mux_fpga']['F_ro_32_2us']}"
    )
    print(
        f"L4 Live Stack: Q16 |dRMS|={l4['q16_fpga_live']['abs_delta_rms_Hz']} Hz ({l4['q16_fpga_live']['step_latency_us']} us) | "
        f"CellISA v3.5 ({l4['cellisa_v35_live']['total_opcodes']} ops): Bare={l4['cellisa_v35_live']['mean_bare_cz_fidelity']} -> "
        f"ECHO_CZ={l4['cellisa_v35_live']['mean_echo_cz_fidelity']} (T_cyc={l4['cellisa_v35_live']['cycle_duration_us']} us)"
    )
    print(
        f"L5 Surface Code FT: P1 Lambda={l5['scenarios']['A_v4_Bare_P1_S1p0']['Lambda']} | "
        f"D2 Lambda={l5['scenarios']['D2_v5_RotaC_Q5e5_S0p25']['Lambda']:.3f} | "
        f"D3 Lambda={l5['scenarios']['D3_Target_FT_p0p005']['Lambda']:.3f} | "
        f"100L(1e-9) fleet ratio D2/D3={l5['fleet_100L_1e9_cryostat_reduction_D2_to_D3']}x"
    )
    print(
        f"L6 Wafer CX4: W1=${cx4['W1_v5_15ms_chip_10k_usd']:.3f} (CX4={cx4['W1_cx4_pass']}) | "
        f"W2=${cx4['W2_v5_15ms_chip_10k_usd']:.3f} (-{cx4['W2_reduction_vs_v3_W1_frac']*100:.1f}%, CX4={cx4['W2_cx4_pass_vs_v3_W1']}) | "
        f"W3=${cx4['W3_v5_15ms_chip_10k_usd']:.3f} (-{cx4['W3_reduction_vs_v3_W1_frac']*100:.1f}%, CX4={cx4['W3_cx4_pass_vs_v3_W1']})"
    )
    print(
        f"L7 Logical Qubit 1e-9: "
        f"D2 (d*={le['D2_primary_Lambda1p40']['1e-9']['d_star']}, {le['D2_primary_Lambda1p40']['1e-9']['cryostats_100L']} cryo): "
        f"fab(W3)=${le['D2_primary_Lambda1p40']['1e-9']['fab_usd_per_L_W3']:.2f}/L, sys(100L)=${le['D2_primary_Lambda1p40']['1e-9']['sys_100L_usd_per_L_amort_wright_p50']:,.0f}/L | "
        f"D3 (d*={le['D3_target_Lambda2p52']['1e-9']['d_star']}, {le['D3_target_Lambda2p52']['1e-9']['cryostats_100L']} cryo): "
        f"fab(W3)=${le['D3_target_Lambda2p52']['1e-9']['fab_usd_per_L_W3']:.2f}/L, sys(100L)=${le['D3_target_Lambda2p52']['1e-9']['sys_100L_usd_per_L_amort_wright_p50']:,.0f}/L "
        f"(D2/D3={le['D2_to_D3_deployed_cost_ratio_1e9']}x)"
    )
    # Full 64-hex SHA-256 (NEVER truncated!)
    print(f"V5_MASTER_CERT_SHA256 = {res['v5_master_certificate']['sha256']}")


if __name__ == "__main__":
    main()
