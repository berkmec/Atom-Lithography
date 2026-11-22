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
    # Break CH0.CSA_SUM by duplicating a pin into another net
    design.nets["CH0.CSA_OUT"].append(("U0A", "2"))
    errs = validate_netlist(design, CHANNELS)
    assert any("Pin conflict" in e for e in errs)


def test_spice_deck_structure_and_8_channels():
    cir = render_spice_deck(CHANNELS)
    assert "Profile=COLD_100K" in cir
    assert "R_F=1G" in cir
    assert "C_S=600p" in cir
    assert "C_P=600p" in cir
    assert "Q_ION=0.055f" in cir
    assert "V_THR=0.00423" in cir
    assert ".subckt IBIC_CHANNEL" in cir
    assert ".subckt OPAMP_LTC6268" in cir
    assert ".subckt OPAMP_ADA4817" in cir
    assert ".subckt CMP_TLV3501" in cir
    assert ".ac " in cir and ".tran " in cir and ".noise " in cir
    for ch in range(CHANNELS):
        assert f"Xch{ch} " in cir

    cir_rt = render_spice_deck(CHANNELS, profile="rt300k")
    assert "Profile=RT_300K" in cir_rt and "R_F=100Meg" in cir_rt and "C_S=100p" in cir_rt


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
