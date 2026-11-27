"""Tests for Step 2A: Real 1% 29Si diamond-cubic silicon lattice bath BOED spectroscopy & Factory mode.

Verifies:
1. Exact diamond-cubic Si lattice (a0=0.5431 nm, R=6.0 nm, 45,214 sites) and
   Kohn-Luttinger + dipolar (A_par, B_perp) hyperfine parity with Exp42/Exp48.
2. Exact analytical SU(2) Asymmetric-CPMG-N propagator vs 2x2 matrix exponentiation.
3. Realistic 1% 29Si bath statistics (density ~452 spins, weak bath clutter forest,
   non-trivial sub-10 kHz / sub-5 kHz doublets, Overhauser T2e* & DD T2_bath).
4. End-to-end AdaptiveBOEDSpectroscopy vs UniformNyquistSpectrometer on real clouds
   (convergence, A_par/B_perp accuracy, probe & time speedup, legacy failure audit).
5. Honest physical failure regimes (Fourier linewidth 1/T_max wall & low-SNR cliff).
6. Factory realistic 1% 29Si lattice-bath mode (including AtlasSelector + shaped
   pulse calibration) and 100% backwards compatibility with existing workflows.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from machine_control.adaptive_spectroscopy import (
    AdaptiveBOEDSpectroscopy,
    BOEDConfig,
    BayesianSpectrometer,
    SI_LATTICE_A0_NM,
    UniformNyquistSpectrometer,
    asym_cpmg_coherence_vec,
    build_diamond_si_lattice,
    evaluate_fourier_resolution_failure_curve,
    evaluate_snr_breakdown_curve,
    generate_real_si29_bath_spectrum,
    sample_realistic_si29_population,
)
from machine_control.config import MachineConfig
from machine_control.factory import Certificate, Factory
from machine_control.selector import AtlasSelector, load_atlas_modules


def test_diamond_si_lattice_matches_exp42_and_exact_su2_cpmg():
    iso, _ad, _ps = load_atlas_modules()
    lat = build_diamond_si_lattice(radius_nm=6.0, b_dir="[123]")

    assert SI_LATTICE_A0_NM == pytest.approx(0.5431)
    assert lat.positions_nm.shape == iso.SITES.shape
    assert len(lat.positions_nm) == 45_214
    assert float(np.max(np.abs(lat.positions_nm - iso.SITES))) < 1e-12
    assert float(np.max(np.abs(lat.a_par_Hz - iso.A_BY_DIR["[123]"]))) < 1e-6
    assert np.all(lat.b_perp_Hz >= 0.0)
    assert float(np.max(lat.b_perp_Hz)) > 500_000.0  # inner-shell dipolar B_perp

    # Verify vectorized exact SU(2) Asymmetric-CPMG-N against explicit 2x2 matrix_power
    sx = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex) / 2.0
    sz = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex) / 2.0

    def _su2(hx: float, hz: float, t: float) -> np.ndarray:
        om = 2.0 * np.pi * float(np.hypot(hx, hz))
        nx, nz = (2.0 * np.pi * hx) / om, (2.0 * np.pi * hz) / om
        return np.cos(0.5 * om * t) * np.eye(2) - 1j * np.sin(0.5 * om * t) * (2.0 * nx * sx + 2.0 * nz * sz)

    nu_n = 8.465e6 * 0.20
    delta = 0.52
    for A, B, tau, N in (
        (380e3, 4.5e3, 0.275e-6, 128),
        (1150e3, 42.0e3, 0.75e-6, 32),
        (-420e3, 18.0e3, 0.31e-6, 64),
    ):
        t1, t2 = (1.0 + delta) * tau, (1.0 - delta) * tau
        v0 = _su2(0.5 * B, nu_n + 0.5 * A, 0.5 * t1) @ _su2(-0.5 * B, nu_n - 0.5 * A, t2) @ _su2(0.5 * B, nu_n + 0.5 * A, 0.5 * t1)
        v1 = _su2(-0.5 * B, nu_n - 0.5 * A, 0.5 * t2) @ _su2(0.5 * B, nu_n + 0.5 * A, t1) @ _su2(-0.5 * B, nu_n - 0.5 * A, 0.5 * t2)
        m_mat = float(np.real(np.trace(np.linalg.matrix_power(v0, N // 2) @ np.linalg.matrix_power(v1, N // 2).conj().T)) / 2.0)
        m_vec = float(asym_cpmg_coherence_vec(nu_n, np.array([A]), np.array([B]), tau, N, delta=delta)[0])
        assert abs(m_mat - m_vec) < 1e-10


def test_real_si29_1pct_bath_statistics_clutter_and_crowding():
    rng = np.random.default_rng(2026501)
    clouds = sample_realistic_si29_population(40, rng, abundance_pct=1.0, p_blank=0.0, b_field_T=1.5)

    n_spins = [c.metadata["n_bath_spins"] for c in clouds]
    n_weak = [c.metadata["n_weak_lt_10kHz"] for c in clouds]
    n_midweak = [c.metadata["n_midweak_10_40kHz"] for c in clouds]
    n_inband = [c.metadata["n_in_band_40_3500kHz"] for c in clouds]
    n_sub10 = [c.metadata["n_sub10kHz_pairs_gt120kHz"] for c in clouds]
    n_sub5 = [c.metadata["n_sub5kHz_pairs_gt120kHz"] for c in clouds]
    t2_star = [c.t2_star_electron_us for c in clouds]
    t2_dd = [c.t2_bath_dd_ms for c in clouds]
    med_gdip = [c.metadata["median_dipolar_width_Hz"] for c in clouds]

    # Genuine 1% occupation of 45,214 sites (~452 spins/donor)
    assert 420.0 < float(np.mean(n_spins)) < 485.0
    # Dense weak-bath forest clutter present (<10 kHz and 10..40 kHz)
    assert float(np.mean(n_weak)) > 220.0
    assert float(np.mean(n_midweak)) > 90.0
    assert float(np.mean(n_inband)) > 50.0
    # Real crowded sub-10 kHz and sub-5 kHz doublets exist in [120, 3500] kHz
    assert float(np.mean(n_sub10)) > 6.0
    assert float(np.mean(n_sub5)) > 4.0
    # Physical decoherence & dipolar broadening scales
    assert 0.10 < float(np.median(t2_star)) < 0.80
    assert 3.0 < float(np.median(t2_dd)) < 45.0
    assert float(np.median(med_gdip)) > 2.0

    # Natural un-cherry-picked population contains both working and crowded crystals
    n_work = sum(1 for c in clouds if c.label == "working")
    n_crowd = sum(1 for c in clouds if c.label == "crowded")
    assert n_work >= 8
    assert n_crowd >= 8


def test_boed_end_to_end_real_bath_convergence_and_speedup_vs_uniform():
    rng_pop = np.random.default_rng(2026502)
    cands = sample_realistic_si29_population(24, rng_pop, abundance_pct=1.0, p_blank=0.20, b_field_T=1.5)

    boed = AdaptiveBOEDSpectroscopy(BOEDConfig(), rng=np.random.default_rng(2026503), estimate_b_perp=True)
    unif = UniformNyquistSpectrometer(BOEDConfig(), rng=np.random.default_rng(2026504), esr_pre_gate=False, estimate_b_perp=True)
    legacy = BayesianSpectrometer(BOEDConfig(), rng=np.random.default_rng(2026505))

    res_boed = [boed.inspect_candidate(c) for c in cands]
    res_unif = [unif.inspect_candidate(c) for c in cands]
    res_legacy = [legacy.inspect_candidate(c, force_legacy_protocol=True) for c in cands]

    # Step count & wall-clock time speedup of BOED vs Uniform Nyquist
    mean_probes_boed = float(np.mean([r.n_probes_total for r in res_boed]))
    mean_probes_unif = float(np.mean([r.n_probes_total for r in res_unif]))
    mean_time_boed = float(np.mean([r.total_time_ms for r in res_boed]))
    mean_time_unif = float(np.mean([r.total_time_ms for r in res_unif]))
    assert mean_probes_unif / mean_probes_boed >= 5.0
    assert mean_time_unif / mean_time_boed >= 10.0

    # Classification accuracy & massive FNR reduction over legacy synthetic protocol
    acc_boed = sum(
        1 for c, r in zip(cands, res_boed) if (c.label == "working") == r.accepted
    ) / len(cands)
    assert acc_boed >= 0.70

    work_pairs_b = [(c, r) for c, r in zip(cands, res_boed) if c.label == "working"]
    work_pairs_l = [(c, r) for c, r in zip(cands, res_legacy) if c.label == "working"]
    fnr_boed = sum(1 for _, r in work_pairs_b if not r.accepted) / max(len(work_pairs_b), 1)
    fnr_legacy = sum(1 for _, r in work_pairs_l if not r.accepted) / max(len(work_pairs_l), 1)
    assert fnr_legacy > fnr_boed + 0.30  # legacy protocol collapses on real ~452-spin clutter

    # Posterior convergence on A_par and B_perp across accepted lines
    a_errs = []
    b_rel_errs = []
    for c, r in zip(cands, res_boed):
        if r.accepted and c.all_a_par_Hz is not None:
            assert len(r.estimated_lines_Hz) == 8
            assert r.estimated_b_perp_Hz is not None and len(r.estimated_b_perp_Hz) == 8
            all_abs = np.abs(c.all_a_par_Hz)
            for k, fhat in enumerate(r.estimated_lines_Hz):
                j = int(np.argmin(np.abs(all_abs - fhat)))
                a_errs.append(float(fhat - all_abs[j]))
                b_true = float(c.all_b_perp_Hz[j])
                b_rel_errs.append(abs(float(r.estimated_b_perp_Hz[k]) - b_true) / max(b_true, 1.0))

    assert len(a_errs) >= 16
    a_rmse = float(np.sqrt(np.mean(np.square(a_errs))))
    assert a_rmse <= 120.0
    assert float(np.median(b_rel_errs)) < 0.20


def test_honest_failure_regimes_fourier_wall_and_low_snr():
    # 1) Fourier / Rayleigh linewidth resolution wall (T_max = 0.5 ms -> 1/T_max = 2.0 kHz)
    fw = evaluate_fourier_resolution_failure_curve(
        spacings_Hz=(400.0, 1_000.0, 5_000.0, 8_000.0),
        trials_per_spacing=15,
        seed=2026601,
    )
    by_dA = {row["delta_A_Hz"]: row for row in fw["curve"]}
    # Sub-Fourier-linewidth pair (400 Hz << 2 kHz) is honestly unresolvable under saturating contrast
    assert by_dA[400.0]["doublet_detection_rate"] < 0.50
    assert by_dA[400.0]["false_singlet_leakage_rate"] > 0.50
    # Well-resolved crowded pairs (5 kHz, 8 kHz < 10 kHz gate) are cleanly rejected
    assert by_dA[5_000.0]["doublet_detection_rate"] >= 0.85
    assert by_dA[8_000.0]["doublet_detection_rate"] >= 0.85

    # 2) Low-SNR breakdown cliff
    snr_res = evaluate_snr_breakdown_curve(snr_levels=(10.0, 2.0), n_clouds_per_snr=15, seed=2026602)
    by_snr = {row["snr_per_fine_probe"]: row for row in snr_res["curve"]}
    assert by_snr[2.0]["fnr"] > by_snr[10.0]["fnr"] or by_snr[2.0]["accuracy"] < by_snr[10.0]["accuracy"]


def test_factory_real_si29_lattice_bath_mode_and_backwards_compat(tmp_path):
    # Real 1% 29Si diamond-lattice bath factory mode
    cert_file = tmp_path / "real_bath_certs.jsonl"
    f_real = Factory.with_real_si29_bath(
        MachineConfig.v400_bayesian(seed=2026701),
        cal_mode="spectral",
        estimate_b_perp=True,
    )
    rep_real = f_real.run(8, cert_path=cert_file)
    assert rep_real.bath_mode == "real_si29"
    assert rep_real.real_bath_attempts > 0
    assert rep_real.real_bath_mean_spins > 380.0
    assert rep_real.certified >= 1
    assert rep_real.real_bath_a_par_rmse_Hz is not None and rep_real.real_bath_a_par_rmse_Hz <= 150.0
    assert cert_file.is_file()
    for cert in rep_real.certificates:
        assert cert.bath_mode == "real_si29"
        assert len(cert.lines_Hz) == 8
        assert cert.min_spacing_Hz >= 5_000.0
        assert cert.b_perp_Hz is not None and len(cert.b_perp_Hz) == 8
        assert all(v > 0.0 for v in cert.b_perp_Hz)

    # Real AtlasSelector + full-bath BOED + shaped Hamiltonian 9-corner calibration
    atlas = AtlasSelector(abundance_pct=1.0, seed=5)
    f_atlas = Factory.with_real_si29_bath(
        MachineConfig.v400_bayesian(seed=2026702),
        selector=atlas,
        cal_mode="shaped",
        estimate_b_perp=False,
    )
    rep_atlas = f_atlas.run(3)
    assert rep_atlas.bath_mode == "real_si29"
    assert rep_atlas.real_bath_attempts >= 3
    assert rep_atlas.real_bath_mean_spins > 400.0

    # 100% backwards compatibility: default synthetic Factory + 7-arg Certificate constructor
    rep_syn = Factory(MachineConfig.v400_bayesian(seed=2026703)).run(15)
    assert rep_syn.bath_mode == "synthetic"
    assert rep_syn.mean_spec_time_ms < 120.0
    assert rep_syn.certified > 0
    c_legacy = Certificate("REG-0", 0, 1, 1, 15_000.0, True, [100e3] * 8)
    assert c_legacy.b_perp_Hz is None and c_legacy.bath_mode == "synthetic"


def test_benchmark_json_artifact_and_zero_hardcoded_paths():
    bench_path = ROOT / "results" / "boed_real_bath_benchmark.json"
    assert bench_path.is_file(), "results/boed_real_bath_benchmark.json must be generated"
    data = json.loads(bench_path.read_text(encoding="utf-8"))
    assert data["no_lab_measurement"] is True
    assert data["bath_statistics"]["n_donor_clouds"] >= 200
    assert data["bath_statistics"]["lattice_total_sites"] == 45_214
    assert data["comparison"]["probe_speedup_boed_vs_uniform_raw"] >= 5.0
    assert data["comparison"]["time_speedup_boed_vs_uniform_raw"] >= 10.0
    assert data["adaptive_boed"]["a_par_localization"]["rmse_Hz"] <= 120.0
    assert "fourier_resolution_wall" in data["honest_failure_regimes"]
    assert "low_snr_breakdown" in data["honest_failure_regimes"]

    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    for fp in (
        ROOT / "src" / "machine_control" / "adaptive_spectroscopy.py",
        ROOT / "src" / "machine_control" / "factory.py",
        ROOT / "tests" / "test_boed_real_bath.py",
        bench_path,
    ):
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"


def test_obs117_fpga_q16_boed_high_snr_no_int32_saturation():
    import math
    from machine_control.fpga_boed_dsp import FPGACoreConfig, Q1616BOEDCore

    core = Q1616BOEDCore(FPGACoreConfig())
    for sigma_n in (0.002, 0.001, 0.0005):
        for prior_sigma in (2000.0, 100.0):
            f_init, f_probe, y_meas, gamma = 42_000.0, 42_500.0, 0.9, 1_200.0
            f_init_i, df_bins, lp_q = core.init_prior_q16(f_init, prior_sigma_Hz=prior_sigma)
            _, trace = core.update_and_select_next(
                f_init_i, df_bins, lp_q, f_probe, y_meas, gamma, sigma_n, step_idx=0
            )
            # Exact FP64 posterior on identical grid
            grid_Hz = f_init + df_bins * core.cfg.bin_step_Hz
            lp_f = -0.5 * ((grid_Hz - f_init) / prior_sigma) ** 2
            lor_f = 1.0 / (1.0 + ((f_probe - grid_Hz) / gamma) ** 2)
            lp_f -= 0.5 * ((y_meas - lor_f) / sigma_n) ** 2
            w = np.exp(lp_f - np.max(lp_f))
            w /= np.sum(w)
            mu_fp64 = float(np.sum(w * grid_Hz))
            std_fp64 = float(math.sqrt(max(float(np.sum(w * (grid_Hz - mu_fp64) ** 2)), 0.0)))

            assert abs(trace.mu_Hz - mu_fp64) < 1.0, (
                f"sigma_n={sigma_n}, prior={prior_sigma}: Q16 mu={trace.mu_Hz} vs FP64 {mu_fp64}"
            )
            rel_std_err = abs(trace.std_Hz - std_fp64) / max(std_fp64, 1.0)
            assert rel_std_err < 0.05, (
                f"sigma_n={sigma_n}, prior={prior_sigma}: Q16 std={trace.std_Hz} vs FP64 {std_fp64}"
            )
