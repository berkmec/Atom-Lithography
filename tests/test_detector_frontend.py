"""Tests for src/board/detector_frontend.py and Exp127 IBIC frontend physics simulation."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp127_detector_frontend_sim"))

from board.detector_frontend import (
    CHANNELS,
    DEFAULT_PROFILE,
    build_board_design,
    render_kicad_netlist,
    render_spice_deck,
    validate_netlist,
)
import sim127


def test_board_netlist_erc_zero_errors_and_locked_cold100k_default():
    assert DEFAULT_PROFILE == "cold100k"
    design = build_board_design(CHANNELS)
    errors = validate_netlist(design, CHANNELS)
    assert errors == [], f"ERC failures: {errors}"
    assert len(design.components) == 204
    assert len(design.nets) == 107

    # Verify KiCad S-expression is syntactically balanced and locked to COLD_100K defaults
    net_text = render_kicad_netlist(design)
    assert net_text.count("(") == net_text.count(")")
    assert "(export (version D)" in net_text
    assert "COLD_100K" in net_text
    assert "1G_THICKFILM" in net_text
    assert "600pF_C0G_1pct" in net_text
    assert "LTC6268_CSA_FET" in net_text
    assert "ADA4817-1_SHAPER" in net_text
    assert "TLV3501_CMP_4p5NS" in net_text
    assert "DAC8568_16B_8CH_SPI" in net_text
    for ch in range(CHANNELS):
        assert f'(name "CH{ch}.THRESH")' in net_text
        assert f'(name "CH{ch}.COUNT_HIT")' in net_text

    # Optional --profile rt300k must also pass ERC cleanly
    design_rt = build_board_design(CHANNELS, profile="rt300k")
    assert validate_netlist(design_rt, CHANNELS) == []
    net_rt = render_kicad_netlist(design_rt)
    assert "100M_THICKFILM" in net_rt
    assert "100pF_C0G_1pct" in net_rt


def test_board_erc_catches_injected_floating_pin_and_conflict():
    design = build_board_design(CHANNELS)
    # Break CH0.CSA_SUM by duplicating LTC6268 pin 6 (-IN) into another net
    design.nets["CH0.CSA_OUT"].append(("U0A", "6"))
    errs = validate_netlist(design, CHANNELS)
    assert any("Pin conflict" in e for e in errs)


def test_exact_datasheet_pinouts_in_v21_netlist():
    design = build_board_design(CHANNELS)
    pin_owner = {node: net for net, nodes in design.nets.items() for node in nodes}
    for ch in range(CHANNELS):
        # LTC6268IS8 S8: 1:~SHDN, 2:V+, 3:OUT, 4:V-, 6:-IN, 7:+IN
        assert pin_owner[(f"U{ch}A", "1")] == "VCCA"
        assert pin_owner[(f"U{ch}A", "2")] == "VCCA"
        assert pin_owner[(f"U{ch}A", "3")] == f"CH{ch}.CSA_OUT"
        assert pin_owner[(f"U{ch}A", "4")] == "VSSA"
        assert pin_owner[(f"U{ch}A", "6")] == f"CH{ch}.CSA_SUM"
        assert pin_owner[(f"U{ch}A", "7")] == "AGND"
        # ADA4817-1ARDZ SOIC-8-EP: 1:FB, 2:-IN, 3:+IN, 4:-VS, 6:OUT, 7:+VS, 8:PD, EP:-VS
        assert pin_owner[(f"U{ch}B", "1")] == f"CH{ch}.SHP_GAIN"
        assert pin_owner[(f"U{ch}B", "8")] == "VCCA"
        assert pin_owner[(f"U{ch}B", "EP")] == "VSSA"
        # TI SBOS321 TLV3501AIDBVR SOT-23-6 DBV: 1:-IN, 2:V-, 3:+IN, 4:V+, 5:OUT, 6:SHDN
        assert pin_owner[(f"U{ch}C", "1")] == f"CH{ch}.THRESH"
        assert pin_owner[(f"U{ch}C", "2")] == "DGND"
        assert pin_owner[(f"U{ch}C", "3")] == f"CH{ch}.CMP_INP"
        assert pin_owner[(f"U{ch}C", "4")] == "VCCD"
        assert pin_owner[(f"U{ch}C", "5")] == f"CH{ch}.CMP_OUT"
        assert pin_owner[(f"U{ch}C", "6")] == "DGND"


def test_spice_deck_structure_and_live_ngspice_8_channels(tmp_path: Path):
    from hardware.pcb.kicad_eda_verify import run_ngspice

    cir = render_spice_deck(CHANNELS)
    assert "Profile=COLD_100K" in cir
    assert "R_F=1G" in cir
    assert "C_S=600p" in cir
    assert "C_P=600p" in cir
    assert "Q_ION=0.055f" in cir
    assert "V_THR=0.00423" in cir
    assert "LIMIT(" not in cir
    assert ".subckt IBIC_CHANNEL" in cir
    assert ".subckt OPAMP_LTC6268" in cir
    assert ".subckt OPAMP_ADA4817" in cir
    assert ".subckt CMP_TLV3501" in cir
    assert "ac dec " in cir and "tran " in cir and "noise v(Xch0.shp_out) Iion0" in cir
    for ch in range(CHANNELS):
        assert f"Xch{ch} " in cir

    # Live ngspice -b execution on disk deck (cold100k)
    disk_cir = ROOT / "src" / "board" / "detector_frontend.cir"
    res = run_ngspice(disk_cir, workdir=tmp_path)
    assert res.ok and res.returncode == 0, f"ngspice failed: {res.errors}\n{res.stderr}"
    m = res.metrics
    assert m["csa_peak_v"] > 0.1e-3, f"Expected positive CSA pulse, got {m['csa_peak_v']}"
    assert 9.0e-3 <= m["shp_peak_v"] <= 14.0e-3, f"Expected positive 9-14 mV shaper peak, got {m['shp_peak_v']}"
    assert m["hit0_init_v"] < 0.05, f"CH0 latched HIGH at t=0: {m['hit0_init_v']}"
    assert m["hit0_max_v"] >= 3.0, f"CH0 comparator failed to trigger: {m['hit0_max_v']}"
    assert m["hit0_end_v"] < 0.05, f"CH0 comparator stayed latched at end: {m['hit0_end_v']}"
    assert m["hit1_max_v"] < 0.05 and m["hit7_max_v"] < 0.05, "Dark channels false-triggered/latched!"
    assert 1e-6 < m["shp_onoise_rms_v"] < 5e-3, f"Invalid .noise RMS: {m['shp_onoise_rms_v']}"

    # Also verify optional rt300k profile executes cleanly in ngspice -b without latch-up
    cir_rt = render_spice_deck(CHANNELS, profile="rt300k")
    assert "Profile=RT_300K" in cir_rt and "R_F=100Meg" in cir_rt and "C_S=100p" in cir_rt
    rt_path = tmp_path / "detector_frontend_rt300k.cir"
    rt_path.write_text(cir_rt, encoding="utf-8")
    res_rt = run_ngspice(rt_path, workdir=tmp_path)
    assert res_rt.ok and res_rt.returncode == 0
    assert res_rt.metrics["shp_peak_v"] > 8.0e-3
    assert res_rt.metrics["hit1_max_v"] < 0.05


def test_lindhard_31p_in_si_is_monotonic_and_physical():
    l5 = sim127.lindhard_31p_in_si(5.0, 300.0)
    l10 = sim127.lindhard_31p_in_si(10.0, 300.0)
    l20 = sim127.lindhard_31p_in_si(20.0, 300.0)
    assert 0.20 < l5["Y_e_lindhard"] < l10["Y_e_lindhard"] < l20["Y_e_lindhard"] < 0.45
    assert 300.0 < l5["mean_e_pairs"] < 420.0
    assert 700.0 < l10["mean_e_pairs"] < 900.0


def test_laplace_transient_matches_ode_impulse_and_comparator_fires():
    op = sim127.FrontendOperatingPoint(name="rt200", temp_K=300.0, tau_s_s=200e-9, rf_Ohm=100e6)
    q_10 = 1111.111 * sim127.Q_E
    t, v_t, v_pk, t_pk = sim127.transient_pulse(op, 0.5e-12, q_10)
    v_ode = sim127.cross_check_analytical_lsim(op, 0.5e-12, q_10)
    assert abs(v_pk - v_ode) / v_ode < 0.02
    assert 175.0 <= t_pk * 1e9 <= 240.0
    assert 31.0 <= v_pk * 1e3 <= 38.0

    # Comparator hysteresis fires cleanly on pulse and returns to 0 after tail
    cmp_out = sim127.simulate_comparator_trace(t, v_t, v_thr=12e-3, v_hys=3.3e-3)
    assert cmp_out[0] == 0.0
    assert np.max(cmp_out) == pytest.approx(3.3)
    assert cmp_out[-1] == 0.0


def test_enc_scales_with_capacitance_and_cold_100k_closes_5kev_window():
    op_rt = sim127.FrontendOperatingPoint(name="rt200", temp_K=300.0, tau_s_s=200e-9, rf_Ohm=100e6)
    op_cold = sim127.FrontendOperatingPoint(
        name="cold1200",
        temp_K=100.0,
        tau_s_s=1200e-9,
        rf_Ohm=1e9,
        en_csa_VrtHz=2.0e-9,
        in_csa_ArtHz=0.5e-15,
        fc_1f_Hz=2e3,
        i_leak_A=0.05e-12,
    )
    e02 = sim127.compute_enc_and_rice(op_cold, 0.2e-12)
    e05 = sim127.compute_enc_and_rice(op_cold, 0.5e-12)
    e20 = sim127.compute_enc_and_rice(op_cold, 2.0e-12)
    assert e02["enc_total_e"] < e05["enc_total_e"] < e20["enc_total_e"]
    assert e05["enc_total_e"] < 30.0
    assert e05["p_false_thr_1ms"] < 1e-3

    # Monte Carlo: Cold 100 K / 1.2 us achieves eta >= 0.99 at 5 keV C_det=0.5 pF
    l5_cold = sim127.lindhard_31p_in_si(5.0, 100.0)
    mc_cold_5 = sim127.monte_carlo_eta(l5_cold, e05, n_ions=20_000, seed=127)
    assert mc_cold_5["eta"] >= 0.99

    # Contrast: uncooled 300 K / 200 ns cannot reach 0.99 at 5 keV under Lindhard
    e_rt_05 = sim127.compute_enc_and_rice(op_rt, 0.5e-12)
    l5_rt = sim127.lindhard_31p_in_si(5.0, 300.0)
    mc_rt_5 = sim127.monte_carlo_eta(l5_rt, e_rt_05, n_ions=20_000, seed=127)
    assert mc_rt_5["eta"] < 0.99
