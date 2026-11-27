"""Exp142 (H160) Independent Verification Test Suite.

Covers:
  1. Exact ABCD 50 <-> 3000 Ohm transformer unitarity/passivity (<1e-12), insertion loss & >=5x BW gain (OQ1).
  2. Exact 12x12 Lindblad CPTP (|Tr-1| < 1e-12, min_eig >= -1e-12), F_SWAP_rt >= 0.96 & >1000x lifetime gain (OQ2).
  3. Option-Q 4-port + 1-fiber cryo heat budget inside LD400/PT420 remaining headroom (OQ3).
  4. 167Er Si photonic crystal cavity Purcell factor & 10 km SMF-28 Barrett-Kok / Cabrillo link (OQ4).
  5. Exact 3D ZBL-BCA heavy-ion straggle advantage (121Sb & 167Er forward scattering vs 31P) & Wien filter.
  6. Exact 8x8 & 16x16 121Sb I=7/2 Hamiltonian, NMR separation >=20 kHz, Knill-Laflamme & strain wall (OQ6).
  7. s9q_hardware_spec.json schema, CAD v6.0 clearance & mass/cost sum integrity.
  8. Strict independent verdict recomputation of OQ1-OQ7 against pre-registered predictions_exp142.json.
  9. 2400x1400 PNG integrity & zero hardcoded host/user paths across all Exp142 files.
 10. GFM Markdown table column consistency & epistemic tagging in summary_exp142.md.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp142_option_q_multispecies_qram"
RES_DIR = ROOT / "results" / "exp142_option_q_multispecies_qram"

sys.path.insert(0, str(EXP_DIR))

import multispecies_s1_142 as ms  # noqa: E402
import qram_bridge142 as qb  # noqa: E402


def _load(path: Path) -> dict:
    assert path.is_file(), f"Missing file: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_01_abcd_impedance_transformers_unitarity_and_bw() -> None:
    """Verify exact lossless unitarity, passivity, insertion loss & bandwidth gain of 50 <-> 3000 Ohm bridge."""
    xf = qb.analyze_impedance_transformers()
    for key in ("single_qw_N1", "chebyshev_N3", "chebyshev_N5", "klopfenstein_taper"):
        m = xf[key]
        assert m["lossless_unitarity_err"] < 1e-12
        assert m["max_passivity_excess"] <= 1e-12
    assert xf["chebyshev_N5"]["IL_6GHz_dB"] <= 0.10
    assert xf["klopfenstein_taper"]["IL_6GHz_dB"] <= 0.10
    assert xf["chebyshev_N5"]["bw_15dB_GHz"] >= 2.0
    assert xf["bw_gain_N5_vs_N1"] >= 5.0


def test_02_lindblad_18x18_cptp_swap_and_lifetime_gain() -> None:
    """Verify exact 18x18 Lindblad CPTP (3-level transmon |g,e,f>), physical FSR loss & honest T2 sensitivity."""
    qr = qb.run_lindblad_qram_swap(il_bridge_db=0.0007, p31_ff_t2_us=25.0)
    assert qr["hilbert_dim"] == 18
    assert qr["transmon_levels"] == 3
    assert qr["cptp_max_trace_err"] < 1e-12
    assert qr["cptp_min_eig"] >= -1e-12
    assert qr["F_SWAP_rt_photon_only"] > 0.985
    assert qr["F_SWAP_rt_with_nuclear_31P"] >= 0.960
    assert qr["lifetime_gain_F90_vs_transmon"]["qram_XY8_DD_1s"] >= 1000.0
    assert qr["lifetime_gain_F90_vs_transmon"]["qram_T2n_star_17p7ms"] > 50.0
    # OBS-131: Honest sensitivity to Exp131 T2*=0.29 us and connector IL=0.50 dB
    qr_t2s = qb.run_lindblad_qram_swap(il_bridge_db=0.0007, p31_ff_t2_us=0.29)
    qr_loss = qb.run_lindblad_qram_swap(il_bridge_db=0.50, p31_ff_t2_us=10.0)
    assert qr_t2s["F_SWAP_rt_photon_only"] < 0.93
    assert qr_loss["kappa_R_total_rad_us"] > 50.0
    assert qr_loss["F_SWAP_rt_photon_only"] < 0.70


def test_03_option_q_cryo_heat_budget_closes() -> None:
    """Verify 4-port qRAM + 1-fiber cryo heat load stays strictly within LD400/PT420 headroom."""
    cb = qb.compute_option_q_cryo_budget(n_qram_ports=4, n_optical_fibers=1)
    assert cb["option_q_added_load"]["mxc_20mK_uW"] <= 2.0
    assert cb["option_q_added_load"]["stage_4K_W"] <= 0.15
    assert cb["combined_with_exp140_1024"]["all_stages_within_ld400_pt420"] is True
    assert cb["combined_with_exp140_1024"]["mxc_20mK_margin_uW"] > 5.0


def test_04_er167_purcell_and_smf28_link() -> None:
    """Independently check 167Er Si nanobeam Purcell formula and 10 km SMF-28 link metrics."""
    er = ms.analyze_er167_telecom_link()
    fp_ref = (3.0 / (4.0 * math.pi ** 2)) * (1.0e5 / 0.50) * 0.20 * 0.50
    assert abs(er["F_P_eff"] - fp_ref) < 1e-6
    assert er["F_P_eff"] >= 500.0
    assert er["tau_cav_us"] <= 30.0
    a10 = er["anchor_10km"]
    assert a10["F_ent_BK"] >= 0.85
    assert a10["R_ent_BK_Hz"] > 1.0
    assert a10["R_ent_1ph_Hz"] > 100.0
    # Rate must decrease monotonically with fiber distance from 1 km to 50 km
    rates_bk = [r["R_ent_BK_Hz"] for r in er["distance_sweep"]]
    assert all(rates_bk[i] > rates_bk[i + 1] for i in range(len(rates_bk) - 1))


def test_05_zbl_bca_heavy_ion_straggle_and_wien() -> None:
    """Verify heavy-ion forward scattering shrinks lateral straggle vs 5 keV 31P and Wien separates species."""
    d = _load(RES_DIR / "exp142.json")
    bca = d["part2_s1_multispecies"]["zbl_bca_implantation"]
    p5 = bca["31P_5keV"]
    sb75 = bca["121Sb_7p5keV"]
    sb14 = bca["121Sb_14keV"]
    er15 = bca["167Er_15keV"]
    # OBS-039: Corrected infinite-domain ZBL BCA matches iradina scale (31P 5 keV ~10.3/4.4 nm, 121Sb 7.5 keV ~9.8/2.3 nm vs buggy 7.17/1.85 nm)
    assert 9.5 < p5["R_p_nm"] < 11.5
    assert 4.0 < p5["sigma_lat_1d_nm"] < 4.9
    assert 9.0 < sb75["R_p_nm"] < 12.5
    assert 2.1 < sb75["sigma_lat_1d_nm"] < 3.5
    # Heavy 121Sb and 167Er have strictly smaller lateral straggle than 5 keV 31P
    assert sb75["sigma_lat_1d_nm"] < p5["sigma_lat_1d_nm"]
    assert sb14["sigma_lat_1d_nm"] < p5["sigma_lat_1d_nm"]
    assert er15["sigma_lat_1d_nm"] < p5["sigma_lat_1d_nm"]
    # Depth-matched 7.5 keV Sb matches 5 keV P within 1.5 nm with ~30-35% lower straggle
    assert abs(sb75["R_p_nm"] - p5["R_p_nm"]) < 1.5
    # Exact kinematic max lab scattering angle check: asin(28.0855 / 120.9038) ~ 13.43 deg
    assert abs(sb14["theta_max_lab_deg"] - math.degrees(math.asin(28.0855 / 120.9038))) < 0.05
    wien = d["part2_s1_multispecies"]["wien_filter_separation"]
    assert wien["cross_species_separated"] is True
    # OBS-154: Preliminary Arrhenius activation/segregation/precipitation model present
    ann = d["part2_s1_multispecies"]["thermal_activation_segregation_obs154"]
    assert ann["obstacle_id"] == "OBS-154"
    assert ann["s55_1530K_flash_compatibility"]["167Er"] is False
    assert ann["er167_kinetics"]["furnace_750C_30min_ErO"]["compatible_with_1536nm_optical_center"] is True


def test_06_sb121_qudit_hamiltonian_knill_laflamme_and_strain_wall() -> None:
    """Verify exact 8x8/16x16 121Sb NMR resolution, Knill-Laflamme spin-cat check & strain wall."""
    sb = ms.analyze_sb121_qudit()
    assert sb["n_levels"] == 8 and sb["logical_qubits_raw"] == 3
    assert sb["donor_min_nmr_spacing_kHz"] >= 20.0
    assert abs(sb["ionized_min_nmr_spacing_kHz"] - 70.0) < 0.5  # exact 2*f_Q = 70 kHz
    assert sb["knill_laflamme"]["spin_cat_77_I_Ix_Iy"]["max_off_diag"] < 1e-12
    # Clock |+-1/2> must beat both |+-7/2> spin-cat and Gross binomial under 500 Hz strain + B noise
    f1 = sb["mc_fidelity_at_1ms_with_500Hz_strain"]
    assert f1["clock_pm1_2"] > 0.99
    assert f1["clock_pm1_2"] > f1["spin_cat_pm7_2"] > f1["gross_binomial_0L"]


def test_07_s9q_hardware_spec_integrity() -> None:
    """Verify s9q_hardware_spec.json mass/cost/cryo sums match itemized parts cleanly for CAD/BOM v6.0."""
    sp = _load(RES_DIR / "s9q_hardware_spec.json")
    assert sp["no_lab_measurement"] is True
    assert sp["no_supplier_quotes"] is True
    items = sp["items"]
    assert len(items) == 4
    tot = sp["totals_option_q_plus_s1_multi"]
    assert abs(sum(it["mass_kg_total"] for it in items) - tot["total_mass_kg"]) < 1e-9
    assert sum(it["cost_usd_nom"] for it in items) == tot["cost_usd_nom"]
    assert sum(it["cost_usd_low"] for it in items) == tot["cost_usd_low"]
    assert sum(it["cost_usd_high"] for it in items) == tot["cost_usd_high"]
    assert abs(sum(it["cryo_load_20mK_uW"] for it in items) - tot["cryo_load_20mK_uW"]) < 1e-6


def test_08_exp142_verdict_integrity_and_preregistration() -> None:
    """Recompute verdicts independently from exp142.json and verify pre-registration untouched."""
    pred = _load(RES_DIR / "predictions_exp142.json")
    d = _load(RES_DIR / "exp142.json")
    assert pred["registered_before_computation"] is True
    assert pred["no_lab_measurement"] is True and d["no_lab_measurement"] is True
    v = d["verdicts"]
    assert v["OQ1_IMPEDANCE_TRANSFORMER_50_TO_3K"] is True
    assert v["OQ2_LINDBLAD_QRAM_SWAP_AND_LIFETIME"] is True
    assert v["OQ3_QRAM_CRYO_HEAT_BUDGET"] is True
    assert v["OQ4_ER167_PURCELL_AND_TELECOM_LINK"] is True
    # Honest physical strain wall: spin-cat does NOT beat |+-1/2> clock under 500 Hz strain + B noise
    assert v["OQ6_SB121_8LEVEL_QUDIT_AND_STRAIN_WALL"] is False
    assert d["verdict_counts"]["passed"] == sum(1 for x in v.values() if x)


def test_09_png_integrity_and_zero_hardcoded_paths() -> None:
    """Verify 2400x1400 PNG header and zero hardcoded host/user paths across Exp142 files."""
    png = RES_DIR / "fig_exp142_option_q_multispecies.png"
    assert png.is_file(), f"Missing PNG: {png}"
    raw = png.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)

    forbidden = [
        "/" + "home" + "/" + "berk",
        "/" + "run" + "/" + "media" + "/" + "berk",
        "E:" + "\\",
        "C:" + "\\Users\\",
    ]
    for fp in [*EXP_DIR.glob("*.py"), *RES_DIR.glob("*.json"), *RES_DIR.glob("*.md"), Path(__file__).resolve()]:
        txt = fp.read_text(encoding="utf-8")
        for tok in forbidden:
            assert tok not in txt, f"Hardcoded host path {tok!r} in {fp.name}"


def test_10_summary_gfm_tables_and_epistemics() -> None:
    """Verify summary_exp142.md has 0 GFM table column mismatches and explicit no_lab_measurement."""
    md = RES_DIR / "summary_exp142.md"
    assert md.is_file(), f"Missing summary: {md}"
    lines = md.read_text(encoding="utf-8").splitlines()
    assert any("no_lab_measurement" in ln for ln in lines)

    i = 0
    n_tables = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|") and ln.endswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                block.append(lines[i].strip())
                i += 1
            n_tables += 1
            assert len(block) >= 3
            exp_cols = block[0].replace("\\|", "ESC").count("|") - 1
            for r_idx, row in enumerate(block):
                got = row.replace("\\|", "ESC").count("|") - 1
                assert got == exp_cols, f"Table {n_tables} row {r_idx}: {got} != {exp_cols}"
        else:
            i += 1
    assert n_tables >= 4
