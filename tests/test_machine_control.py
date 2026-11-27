"""Tests for the Atom Lithography Machine control stack (v2.0).

Expectations are anchored to registered experiment results (Exp48/61/65/67/68/116/117/122),
not to circular self-checks.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from machine_control.calibrator import calibrate
from machine_control.config import MachineConfig, dd_is_feasible
from machine_control.factory import Factory
from machine_control.selector import AtlasSelector
from machine_control.sim import main as sim_main
from machine_control.writer import CountedWriter


def test_writer_geometric_mean():
    rng = np.random.default_rng(7)
    w = CountedWriter(0.9, rng)
    ks = [w.fire_single().implanted for _ in range(20000)]
    assert abs(np.mean(ks) - 1 / 0.9) < 0.02


def test_writer_effective_yield_matches_exp67_closed_form():
    w = CountedWriter(0.99, np.random.default_rng(0))
    # Exp67: eta=0.99, s=0.5 degrades attempt yield by <1% relative.
    assert w.effective_yield(1.0, 0.5) > 0.99
    w2 = CountedWriter(0.5, np.random.default_rng(0))
    # Exp67: eta=0.5 degrades by >=25%.
    assert w2.effective_yield(1.0, 0.5) <= 0.75


def test_calibrator_gate():
    close = np.array([100e3, 103e3, 900e3, 2.9e6])
    wide = np.array([50e3, 400e3, 1.2e6, 2.9e6])
    assert not calibrate(close).certified
    assert calibrate(wide).certified


def test_factory_slot_success_near_exp67_prediction():
    cfg = MachineConfig(max_retries=3)
    rep = Factory(cfg).run(4000)
    p_eff = CountedWriter(cfg.detector_eta, np.random.default_rng(0)).effective_yield(
        cfg.bath_yield, cfg.stray_survival
    )
    expected = 1 - (1 - p_eff) ** 3
    assert rep.slot_success <= expected + 0.02
    assert rep.slot_success > 0.5 * expected
    assert rep.certified == len(rep.certificates)
    assert all(c.dd_quality_gate for c in rep.certificates)
    assert all(len(c.lines_Hz) == 8 for c in rep.certificates)
    assert rep.total_subsites >= rep.slots


def test_analytic_rate_is_measurement_limited_exp65():
    cfg = MachineConfig()
    rep = Factory(cfg).run(200)
    assert rep.certified_per_day_analytic >= 1e5
    day = 86400.0
    p_eff = CountedWriter(cfg.detector_eta, np.random.default_rng(0)).effective_yield(
        cfg.bath_yield, cfg.stray_survival
    )
    q = 1 - p_eff
    exp_att = sum(q ** i for i in range(cfg.max_retries)) / (1 - q ** cfg.max_retries)
    write = cfg.beamlets / (exp_att / cfg.detector_eta * cfg.shot_cycle_s) * day
    measure = cfg.readout_channels / (exp_att * cfg.spec_time_s) * day
    assert measure < write


def test_dd_gate_blocks_f2_under_alpha2_only_via_config():
    rep = Factory(MachineConfig(abundance_pct=4.7, bath_yield=0.66)).run(300)
    assert rep.certified == 0  # f=4.7% never DD-feasible -> no certificates


def test_dd_gate_enforces_both_alpha1_and_alpha2():
    # Exp68 robust spec: f=1% passes BOTH alpha=1 & alpha=2; f=2% fails alpha=1.
    assert dd_is_feasible(1.0, require_both_alpha=True)
    assert not dd_is_feasible(2.0, require_both_alpha=True)
    assert dd_is_feasible(2.0, require_both_alpha=False)
    rep_strict = Factory(MachineConfig(abundance_pct=2.0, bath_yield=0.69, require_both_alpha=True)).run(100)
    rep_alpha2 = Factory(MachineConfig(abundance_pct=2.0, bath_yield=0.69, require_both_alpha=False)).run(100)
    assert rep_strict.certified == 0
    assert rep_alpha2.certified > 50


def test_v224_presets_and_1k_upgrade():
    c_leg = MachineConfig.legacy_exp65()
    c_224 = MachineConfig.v224_baseline()
    c_300 = MachineConfig.v300_baseline()
    c_1k = MachineConfig.v224_1k_upgrade()

    # Carbon F1 locked Arch-B equal-pitch array: 32x32 = 1024 beamlets @ 0.50 mm, 15 ms/shot
    assert c_224.beamlets == 1_024
    assert c_300.beamlets == 1_024
    assert c_224.beam_pitch_mm == pytest.approx(0.50)
    assert c_224.shot_cycle_s == pytest.approx(0.015)
    assert c_300.shot_cycle_s == pytest.approx(0.015)
    assert c_224.implant_energy_keV == 5.0
    assert c_224.detector_eta == pytest.approx(0.9994)
    assert c_224.nl_per_chain == 160
    assert c_224.cryo_stage_class == "D"
    assert c_224.readout_temp_K == pytest.approx(0.020)
    assert c_1k.cryo_stage_class == "C"
    assert c_1k.readout_temp_K == pytest.approx(1.0)
    assert c_1k.beamlets == 1_024
    assert c_1k.shot_cycle_s == pytest.approx(0.015)
    assert c_leg.beamlets == 1_000_000
    assert c_leg.shot_cycle_s == pytest.approx(1e-3)

    # Raw write capacity at 1024 beamlets, 15 ms, 50% duty = 2.949e9 shots/day >> readout
    raw_write = c_224.beamlets / c_224.shot_cycle_s * 86400.0 * c_224.duty_cycle
    assert raw_write == pytest.approx(2.94912e9, rel=1e-4)

    r_224 = Factory(c_224).run(200)
    r_1k = Factory(c_1k).run(200)
    assert r_224.certified > 140
    assert raw_write > 10.0 * r_224.certified_per_day_analytic
    # 1K PSB averaging penalty = 3.165x -> throughput scales inversely
    ratio = r_224.certified_per_day_analytic / r_1k.certified_per_day_analytic
    assert ratio == pytest.approx(3.165, rel=1e-3)


def test_atlas_selector_runs_natively_on_linux_and_certifies():
    atlas = AtlasSelector(abundance_pct=1.0, seed=0)
    rep = Factory(MachineConfig.v224_baseline(), selector=atlas).run(3)
    assert rep.slots == 3
    assert rep.certified >= 1
    for cert in rep.certificates:
        assert len(cert.lines_Hz) == 8
        assert cert.min_spacing_Hz >= 5_000.0
        assert cert.dd_quality_gate


def test_atlas_selector_applies_stray_ion_contamination():
    # With eta=0.25 and stray_survival=0.0, most shots have k>1 -> contaminated
    atlas_clean = AtlasSelector(abundance_pct=1.0, seed=10)
    atlas_noisy = AtlasSelector(abundance_pct=1.0, seed=10)
    rep_clean = Factory(
        MachineConfig.v224_baseline(detector_eta=1.0, stray_survival=0.0, max_retries=1),
        selector=atlas_clean,
    ).run(6)
    rep_noisy = Factory(
        MachineConfig.v224_baseline(detector_eta=0.25, stray_survival=0.0, max_retries=1),
        selector=atlas_noisy,
    ).run(6)
    assert rep_noisy.certified <= rep_clean.certified
    assert rep_noisy.shots_total > rep_clean.shots_total


@pytest.mark.parametrize("slots", [50])
def test_certificates_written(tmp_path, slots):
    path = tmp_path / "certs.jsonl"
    rep = Factory().run(slots, cert_path=path)
    lines = path.read_text(encoding="utf-8").strip().splitlines() if rep.certified else []
    assert len(lines) == rep.certified
    rows = [json.loads(line) for line in lines]
    assert all(len(r["lines_Hz"]) == 8 for r in rows)


def test_sim_cli_presets_and_program(tmp_path):
    certs = tmp_path / "certs.jsonl"
    pcerts = tmp_path / "prog.jsonl"
    rep = sim_main([
        "--slots", "25",
        "--preset", "v224",
        "--program", "bell",
        "--program-mode", "shaped",
        "--program-cells", "2",
        "--certs", str(certs),
        "--prog-certs", str(pcerts),
    ])
    assert rep.certified > 0
    assert certs.exists() and pcerts.exists()
    prows = [json.loads(x) for x in pcerts.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(prows) == min(2, rep.certified)
    assert all(r["certified"] and len(r["sha256"]) == 64 for r in prows)


# ===========================================================================
# Regression Tests for OBS-013, OBS-056, OBS-081, OBS-083, OBS-128, OBS-153
# ===========================================================================

def test_obs153_scada_telemetry_exported_in_all():
    import machine_control
    assert "scada_telemetry" in machine_control.__all__


def test_obs013_kapitza_electron_heating_and_dynamic_elzerman_set_readout():
    from machine_control.config import (
        elzerman_thermal_error,
        elzerman_zeeman_splitting_ueV,
        kapitza_electron_temp_K,
    )
    from machine_control.sim import ElzermanSETConfig, simulate_elzerman_set_readout

    # Kapitza T^5 electron-phonon heating: 0.1 pW in 2e-19 m^3 -> 346.6 mK; 10 uW in 2e-12 m^3 -> 549.3 mK
    t_set = kapitza_electron_temp_K(0.020, 1.0e-13, 2.0e-19, 1.0e8)
    t_mw = kapitza_electron_temp_K(0.020, 10.0e-6, 2.0e-12, 1.0e8)
    assert t_set == pytest.approx(0.34657, abs=5e-4)
    assert t_mw == pytest.approx(0.54928, abs=5e-4)

    # Zeeman splitting & Fermi dark-tunneling error at B_M4 = 0.1785 T
    ez_m4 = elzerman_zeeman_splitting_ueV(0.1785)
    assert 20.0 <= ez_m4 <= 21.0
    assert elzerman_thermal_error(0.1785, 0.020) == pytest.approx(0.00248, abs=3e-4)
    assert elzerman_thermal_error(0.1785, 0.100) == pytest.approx(0.23165, abs=3e-3)
    assert elzerman_thermal_error(0.1785, 0.350) == pytest.approx(0.41518, abs=3e-3)
    assert elzerman_thermal_error(1.5, 0.350) == pytest.approx(0.05321, abs=3e-3)

    # MachineConfig tracks non-zero Kapitza thermal readout error (never silently zeroed)
    cfg = MachineConfig.v224_baseline()
    assert cfg.effective_electron_temp_K() > 0.30
    assert cfg.elzerman_thermal_error(b_field_T=cfg.b_m4_T) > 0.40

    # Dynamic Monte Carlo rf-SET simulator rejects Elzerman at B_M4=0.1785 T under Kapitza heating
    mc_m4 = simulate_elzerman_set_readout(ElzermanSETConfig(b_field_T=0.1785, set_power_W=1e-13, n_shots=1500), seed=13)
    assert mc_m4["t_e_K"] > 0.34
    assert mc_m4["thermal_fermi_error"] > 0.40
    assert mc_m4["elzerman_viable"] is False
    assert mc_m4["recommended_mechanism"] == "Dispersive_PSB_M4_TWPA"

    # M4 dispersive preset aligns B_sample with B_M4=0.1785 T and switches away from Elzerman
    cfg_m4 = MachineConfig.v400_m4_dispersive()
    assert cfg_m4.b_sample_T == pytest.approx(0.1785)
    assert "Elzerman" not in cfg_m4.readout_mechanism


def test_obs056_calibrator_removes_hardcoded_rubber_stamp_and_rejects_degenerate_lines():
    # Degenerate 1-line and empty inputs MUST be rejected in every mode
    for mode in ("spectral", "shaped", "grape"):
        r1 = calibrate(np.array([120e3]), mode=mode, b_field_T=1.5)
        assert r1.certified is False
        assert r1.min_corner_fidelity == 0.0

    # Tight 5.1 kHz register [62e3, 72.2e3, ...] MUST NOT be rubber-stamped at 0.9975
    tight = np.array([62e3, 72.2e3, 240e3, 470e3, 820e3, 1280e3, 1950e3, 2950e3])
    r_spec = calibrate(tight, mode="spectral", b_field_T=1.5)
    assert r_spec.corner_verified is True
    assert r_spec.certified is False
    assert r_spec.min_spectator_retention < 0.99

    # Well-separated register passes genuine Bloch 9-corner verification (no hardcoded 0.9975)
    wide = np.array([50e3, 400e3, 1.2e6, 2.9e6])
    r_wide = calibrate(wide, mode="spectral", b_field_T=1.5)
    assert r_wide.certified is True
    assert r_wide.corner_verified is True
    assert r_wide.min_corner_fidelity >= 0.99
    assert r_wide.min_spectator_retention >= 0.99
    assert r_wide.min_corner_fidelity != 0.9975


def test_obs081_factory_analytic_rate_respects_dd_ok_and_atlas_abundance():
    # When dd_ok is False (4.7% natural Si), BOTH certified count AND analytic rate MUST be 0.0
    rep_nat = Factory(MachineConfig(abundance_pct=4.7, bath_yield=0.66, seed=42)).run(10)
    assert rep_nat.certified == 0
    assert rep_nat.certified_per_day_analytic == 0.0

    # AtlasSelector(4.7) in real_si29 mode MUST honor selector's abundance_pct=4.7 and dd_ok=False
    atlas47 = AtlasSelector(abundance_pct=4.7, seed=42)
    rep_r47 = Factory(MachineConfig(seed=42), selector=atlas47, bath_mode="real_si29").run(4)
    assert rep_r47.certified == 0
    assert rep_r47.certified_per_day_analytic == 0.0


def test_obs083_ibic_rice_false_positive_rate_and_counted_writer_propagation():
    from machine_control.config import compute_ibic_rice_false_positive_rate

    # At locked 15 ms window: 5.5 sigma exceeds 1e-3 gate; 6.2 sigma drops < 1e-4
    p_fp_55 = compute_ibic_rice_false_positive_rate(0.015, threshold_sigma=5.5)
    p_fp_62 = compute_ibic_rice_false_positive_rate(0.015, threshold_sigma=6.2)
    assert p_fp_55 > 3.0e-3
    assert p_fp_62 < 1.0e-4

    # v224_baseline locks 6.2-sigma rate (< 1e-3) instead of silent 0.0
    c224 = MachineConfig.v224_baseline()
    assert 0.0 < c224.detector_false_positive_rate < 1.0e-3

    # CountedWriter models zero-ion false-positive triggers and yield reduction (1 - p_fp)
    w = CountedWriter(eta=0.999, rng=np.random.default_rng(7), false_positive_rate=0.10)
    shots = [w.fire_single() for _ in range(4000)]
    fp_frac = sum(1 for s in shots if s.false_positive and s.implanted == 0) / len(shots)
    assert abs(fp_frac - 0.10) < 0.015
    w_zero = CountedWriter(eta=0.999, rng=np.random.default_rng(7), false_positive_rate=0.0)
    assert w.effective_yield(0.51, 0.5) == pytest.approx(0.90 * w_zero.effective_yield(0.51, 0.5), rel=1e-9)

    # Factory propagates false_positive_shots into FactoryReport
    rep_fp = Factory(MachineConfig.v224_baseline(detector_false_positive_rate=0.15, seed=99)).run(60)
    assert rep_fp.false_positive_shots > 0


def test_obs128_v400_bayesian_uses_realistic_1pct_si29_boed_constants():
    c_v4 = MachineConfig.v400_bayesian()
    c_real = MachineConfig.v400_real_si29()
    assert c_v4.spec_time_s >= 0.12
    assert c_v4.spec_sigma_Hz >= 90.0
    assert c_real.spec_time_s == pytest.approx(0.1304, abs=1e-3)
    assert c_real.spec_sigma_Hz == pytest.approx(96.0, abs=1.0)
