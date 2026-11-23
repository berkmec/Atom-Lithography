#!/usr/bin/env python3
"""Exp128 — Part-Level BOM Reconciliation, 100k Correlated Monte Carlo Budget-Cap & EVPI Analysis.

Computes:
1. Canonical BOM.csv SHA-256 & Exp121/Exp122 arithmetic gate.
2. Exact roll-up reconciliation: Exp122 ($2.531M central) -> BOM_DETAILED.csv (145 parts, M3).
3. Part-level M1 (Single-Beam Lab Prototype) vs M3 (Golden Scale) cost breakdown.
4. Model A: 100,000-sample correlated log-normal Monte Carlo over all 137 priced BOM_DETAILED parts
   (Cholesky Gaussian copula + Exp114 B/C chain-class mixture + stochastic program multiplier).
5. Model B: 100,000-sample canonical Exp122 class-unit calibration MC + engineering deltas.
6. Tornado sensitivity (P10-P90 conditional swing, Spearman rho, variance share) & 6-RFQ coverage.
7. Decision-theoretic EVPI & break-even analysis: 20 mK Dilution Baseline (Exp121) vs 1 K Hot-Readout R&D.

Output: results/exp128_bom_sensitivity/exp128.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

ROOT = Path(__file__).resolve().parents[2]
BOM_CSV = ROOT / "research" / "atom_lithography_machine" / "BOM.csv"
BOM_DETAILED = ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"
S56_SPEC_JSON = ROOT / "results" / "exp139_epi_cap_process_integration" / "s56_hardware_spec.json"
S65_SPEC_JSON = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "s65_hardware_spec.json"
S9Q_SPEC_JSON = ROOT / "results" / "exp142_option_q_multispecies_qram" / "s9q_hardware_spec.json"
S9HPC_SPEC_JSON = ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder" / "s9hpc_hardware_spec.json"
S_SAFETY_SPEC_JSON = ROOT / "results" / "exp150_industrial_safety_fmea_hazop" / "s_safety_spec.json"
OUT_DIR = ROOT / "results" / "exp128_bom_sensitivity"
PRED_JSON = OUT_DIR / "predictions_exp128.json"
OUT_JSON = OUT_DIR / "exp128.json"

EXPECTED_BOM_SHA256 = "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"

# Canonical Exp106/107/121/122 constants (read-only replication)
CLASS_MAP = {"A": 1.0, "B": 10.0, "C": 100.0, "D": 1000.0}
VARIABLE_IDS = {"S2.1", "S2.2", "S2.3", "S2.4", "S6.6"}
SCALE_ROWS = {
    "S6.3": (3, 0.0),
    "S5.1": (2, 0.0),
    "S4.1": (2, 0.0),
    "S5.2": (3, 0.25),
    "S6.1": (2, 0.30),
}
CHAN_ROWS = {"S3.2", "S6.4", "S6.5", "S6.7", "S7.2"}
DAY, DUTY = 86400.0, 0.5
REF_BEAM, REF_SPEC = 1e6, 1e4
REF_TILES = math.ceil(REF_BEAM / 64)
ADDERS = 20.0
T_EFF = 1.445
Z90 = norm.ppf(0.90)  # 1.2815515655446004


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canonical_bom() -> list[tuple[str, str, float]]:
    rows = []
    with BOM_CSV.open(encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            rid = (r.get("id") or "").strip()
            if not rid:
                continue
            sub = (r.get("subsystem") or "").strip()
            val = CLASS_MAP.get((r.get("cost_class") or "").strip()[:1], 0.0)
            rows.append((rid, sub, val))
    return rows


def canonical_golden_breakdown(
    rows: list[tuple[str, str, float]], nl: int, chain_class: float, chan_exp: float = 0.7
) -> dict:
    chains = lambda ns: math.ceil(ns / nl)
    write_ref = REF_BEAM * DAY / 0.002
    need = 0.9 * min(write_ref, REF_SPEC * DAY / T_EFF)
    ns_min = math.ceil(need / (DAY / T_EFF))

    def decomp(s: float, ns: int) -> tuple[dict[str, float], dict[str, float]]:
        fx, var = {}, {}
        for rid, _sub, val in rows:
            if rid in VARIABLE_IDS:
                var[rid] = val
                continue
            v = val
            if rid in SCALE_ROWS:
                ex, fl = SCALE_ROWS[rid]
                v = val * max(s**ex, fl)
            if rid in CHAN_ROWS:
                v = val * (ns / REF_SPEC) ** chan_exp
            fx[rid] = v
        return fx, var

    def head_tile(nb: float, var: dict[str, float]) -> float:
        head = sum(var.get(k, 0.0) for k in ("S2.1", "S2.2", "S2.3")) * (nb / REF_BEAM) ** 0.7
        tile = var.get("S2.4", 0.0) * (math.ceil(nb / 64) / REF_TILES)
        return head + tile

    d_ref, var = decomp(0.5, int(REF_SPEC))
    ref_cost = ADDERS + sum(d_ref.values()) + head_tile(REF_BEAM, var) + chains(REF_SPEC) * chain_class

    d_g, _ = decomp(0.5, ns_min)
    fg = ADDERS + sum(d_g.values())
    best_c, best_nb = None, None
    for nb in (100, 300, 1000, 3000, 10000, 30000, 100000, 300000, 1000000):
        if nb * DAY / 0.002 < need:
            continue
        c = fg + head_tile(nb, var) + chains(ns_min) * chain_class
        if best_c is None or c < best_c:
            best_c, best_nb = c, nb

    ns_abs = math.ceil(1e6 / (DUTY * DAY / T_EFF))
    d_a, _ = decomp(0.25, ns_abs)
    abs_cost = ADDERS + sum(d_a.values()) + head_tile(100, var) + chains(ns_abs) * chain_class

    # Subsystem breakdown at golden point (unit=$720)
    sub_units = {f"S{i}": 0.0 for i in range(1, 10)}
    for rid, sub, _val in rows:
        if rid in d_g:
            sub_units[sub] += d_g[rid]
    sub_units["S1"] += ADDERS  # energy filter + PH3 safety belong to S1
    sub_units["S2"] += head_tile(best_nb, var)
    sub_units["S6"] += chains(ns_min) * chain_class

    return {
        "nl": nl,
        "chain_class": chain_class,
        "golden_nb": best_nb,
        "ns_min": ns_min,
        "golden_units": best_c,
        "ref_units": ref_cost,
        "golden_frac": best_c / ref_cost,
        "abs_units": abs_cost,
        "ns_abs": ns_abs,
        "sub_units_golden": sub_units,
    }


def m1_scale_factor(row: pd.Series) -> tuple[float, str]:
    """Physically grounded scaling factor from M3 Golden Scale -> M1 Single-Beam Lab Prototype.

    M1 Definition (DESIGN §10): Single-beam counted implantation + single-site measure-select-calibrate
    lab demonstration (1 beamlet, 31P+ only [no 29Si line], single mechanical/FIB aperture pinhole
    instead of 10^4 MEMS array, 1x 8-ch IBIC module, 2 readout chains on 1 ZCU216 board, 20 mK DR retained
    as Exp121 robust baseline for single-donor ESR/ENDOR verification).
    """
    pid = row["part_id"]
    parent = row["parent_bom_id"]
    # S1: Single 31P+ beam line only (no 29Si line -> 0.5 for dual-line items)
    if pid == "S1.1-02":
        return 0.0, "M1 yalniz 31P+ (Mod B); 29Si hatti gerekmez"
    if pid in {"S1.1-03", "S1.1-04", "S1.2-01", "S1.2-02", "S1.2-03", "S1.2-04", "S1.4-01", "S1.4-02"}:
        return 0.5, "Tek iyon hatti (2->1)"
    # S2: No multi-beam MEMS array in M1; single FIB/pinhole aperture + single blanker deflector + single Einzel lens
    if pid in {"S2.1-02", "S2.2-02", "S2.3-02", "S2.2-03"}:
        return 0.0, "M1 tek-demet: cok-demet MEMS/TSV dokumhane NRE M2'de baslar"
    if pid == "S2.1-01":
        return 0.15, "Tek-aciklikli hassas FIB/Si pinhole (~$8.3k)"
    if pid == "S2.2-01":
        return 0.15, "Tek-kanal elektrostatik blanker plakasi (~$12k)"
    if pid == "S2.3-01":
        return 0.35, "Tek-eksenli ticari/ozel Einzel odak kolonu (~$25k)"
    if pid == "S2.4-01":
        return 0.10, "M1 tek-kanal/tek-karo surucu (MPW payi ~$4.8k)"
    if pid in {"S2.4-02", "S2.4-03"}:
        return 0.25, "1 bolge surucu karti + tek feedthrough"
    # S3: Single-site IBIC -> 1x 8-ch module instead of 16 modules (1/16 -> 0.15 min tooling)
    if pid == "S3.1-01":
        return 0.40, "M1 deneme partisi (3-4 IBIC yonga)"
    if pid in {"S3.2-01", "S3.2-02", "S3.2-04"}:
        return 0.15, "Tek-yuva 1-2x 8-ch vakum-ici IBIC modulu"
    if pid in {"S3.2-03", "S3.2-05", "S3.2-06"}:
        return 0.35, "Tek CF63 feedthrough + tek HV/PSU"
    if pid == "S3.3-01":
        return 0.50, "Tek FPGA sayim karti (yedeksiz M1)"
    # S4: Stage + interferometer largely required in M1 for single-site nm positioning (coarse+fine + 1-2 axis)
    if pid in {"S4.3-02"}:
        return 0.50, "M1 dar tarama kaba kademe"
    if pid in {"S4.4-02", "S4.4-03", "S4.4-04"}:
        return 0.67, "2-eksen XY interferometri (M1)"
    # S5: Full UHV + anneal + small epi lot (5 wafers vs 25) + M1 compact Mod-2 S5.5 flash-anneal
    if pid == "S5.4-01":
        return 0.30, "M1 5-yonga izotopik epi deneme lotu"
    if pid == "S5.4-02":
        return 0.50, "Tek lot SIMS/AFM"
    if pid == "S5.5-01":
        return 0.50, "M1 Mod-2 kompakt 4x4 mm adim-flas 808 nm qCW kaynak (Exp130 G4)"
    if pid in {"S5.5-02", "S5.5-03", "S5.5-04"}:
        return 1.0, "M1: CF63 safir + 10 us pirometre + deklansor kilidi tam gerekli (Exp130)"
    if parent == "S5.6":
        return 1.0, "M1: Yerinde S5.6 28Si UHV MBE capper + FG/H (vakum kirmadan M1 G4 kapanisi, Exp139)"
    # S6: DR (20 mK baseline) + PT420 + PT420 decoupling (Exp133) + 1.5 T magnet still needed for M1!
    # M4 cavity-QED bus & 968-gate crossbar (S6.10) are M3/M4 scaling hardware -> 0.0 in M1 single-donor lab.
    # S6.11 (Exp140 S6.5 1,024-cell Cryo-MUX): M1 uses 1x ZU48DR board (0.50) + 1 test TWPA/HEMT/coax chain (1/32).
    if parent == "S6.9":
        return 1.0, "M1: PT420 uzak valf + CF63 koruk + OFHC orgu + FF zorunlu (Exp133)"
    if parent == "S6.10":
        return 0.0, "M4 kavite-QED veri yolu & 968-kapi capraz-anahtar M3/M4 fazinda eklenir (Exp131)"
    if pid == "S6.11-01":
        return 0.50, "M1: 1x ZU48DR Q16.16 BOED-FPGA karti (2->1, Exp140 S6.5-01)"
    if pid in {"S6.11-02", "S6.11-03", "S6.11-04"}:
        return 1.0 / 32.0, "M1: 1 test TWPA/Purcell/HEMT/koaksiyel zinciri (32->1, Exp140 S6.5)"
    # But readout scales from 56 chains -> 2 chains (1 active + 1 ref), 1 ZCU216 board instead of 14!
    if pid in {"S6.6-01", "S6.6-02", "S6.6-03", "S6.6-04", "S6.6-05"}:
        return 2.0 / 56.0, "M1: 2 okuma zinciri (56->2)"
    if pid == "S6.6-06":
        return 1.0 / 14.0, "M1: 1x ZCU216 RFSoC karti (14->1)"
    if pid == "S6.6-07":
        return 0.25, "M1: 10-50 rezonatorlu test yongasi (9000 degil)"
    if pid in {"S6.4-01", "S6.4-02", "S6.5-01", "S6.5-02"}:
        return 0.25, "M1: 1 ESR + 1 ENDOR kanal grubu (4->1)"
    if pid in {"S6.4-03", "S6.5-03"}:
        return 0.25, "M1: 2 kriyo surus hatti (8->2)"
    if pid in {"S6.7-01", "S6.7-02"}:
        return 0.15, "M1: 2 SET/rf-SET test kanali"
    if pid == "S6.3-02":
        return 0.50, "M1 kucuk test rezonator kalkan/bucking (veya 1.5 T solenoide yakin)"
    # S7: 1 GPU workstation, 1 AWG card, 1 EMI rack, 1 BOED GPU node retained for M1
    if pid in {"S7.1-01", "S7.4-03"}:
        return 0.50, "M1: 1 is istasyonu / 1 EMI kabin"
    if pid == "S7.1-04":
        return 1.0, "M1: tek BOED gercek-zamanli Bayesyen GPU dugumu (Exp132/134)"
    if pid in {"S7.2-01", "S7.2-02"}:
        return 0.35, "M1: 1 AWG + 1 marker karti"
    if pid == "S7.3-01":
        return 0.25, "M1: mevcut MPW/FPGA prototip kontrol (tam parti M2)"
    if pid == "S7.3-02":
        return 0.30, "M1: 3 test tasiyici PCB"
    # S8: SW $0 HW
    if row["subsystem"] == "S8":
        return 0.0, "Yazilim ($0 HW)"
    # v6.0 optional plug-in modules & v7.0 facility safety add-on excluded from M1 Base ($2,466,120 preserved; M1+Safety=$2,611,120 noted!)
    if parent in {"S1.7", "S9.4", "S9.HPC"}:
        return 0.0, "v6.0 moduler opsiyon (Option-Q / Option-HPC) — M1 Base disinda"
    if parent == "S7.SAFETY":
        return 0.0, "v7.0 SEMI S2/SIL-3 tesis emniyet paketi (+$145k -> M1+Safety=$2,611,120; M1 Base korundu)"
    # S9: Reduced spares for M1
    if pid == "S9.3-01":
        return 0.0, "M1'de cok-demet MEMS yedegi yok"
    if pid == "S9.3-02":
        return 0.25, "M1: 1 yedek LNA zinciri"
    if parent in {"S9.1", "S9.2"}:
        return 0.50, "M1 kucuk kalibrasyon/gaz kiti"
    # Default: fixed infrastructure retained 100% in M1 (DR, PT420, UHV chamber, pumps, piezo, PH3 cabinet, energy filter)
    return 1.0, "M1'de tam gerekli sabit altyapi"


def assign_rfq_package(row: pd.Series) -> str:
    parent = row["parent_bom_id"]
    if parent in {"S1.1", "S1.2", "S1.3", "S1.5", "S1.6"}:
        return "RFQ-01 (S1 Kaynak+Kolon+Süzgeç)"
    if parent in {"S2.1", "S2.2", "S2.3"}:
        return "RFQ-02 (S2 MEMS Kafa)"
    if parent in {"S4.3", "S4.4"}:
        return "RFQ-03 (S4 Piezo+İnterferometre)"
    if parent == "S6.3":
        return "RFQ-04 (S6.3 1.5T/<=0.4T Mıknatıs)"
    if parent == "S6.6":
        return "RFQ-05 (S6.6 Kriyo-LNA/Zincir+NbTiN)"
    if parent in {"S6.8", "S6.1"}:
        return "RFQ-06 (S6.8+S6.1 DR 20mK+PT420)"
    if parent in {"S5.5", "S6.9", "S6.10"}:
        return "RFQ-07 (v4.0 S5.5+PT420+M4)"
    if parent in {"S5.6", "S6.11"}:
        return "RFQ-08 (v5.0 S5.6 MBE+S6.5 Cryo-MUX)"
    if parent in {"S1.7", "S9.4", "S9.HPC"}:
        return "RFQ-09 (v6.0 Option-Q + Option-HPC)"
    if parent == "S7.SAFETY":
        return "RFQ-10 (v7.0 SEMI S2/SIL-3 Emniyet)"
    return "Non-RFQ (COTS/Diğer)"


def assign_driver_group(row: pd.Series) -> str:
    pid = row["part_id"]
    parent = row["parent_bom_id"]
    sub = row["subsystem"]
    if parent == "S7.SAFETY":
        return "v7.0 Emniyet Paketi (SEMI S2/SIL-3)"
    if parent in {"S1.7", "S9.4"}:
        return "v6.0 Option-Q (qRAM + S1-Multi)"
    if parent == "S9.HPC":
        return "v6.0 Option-HPC (100G RDMA Dekoder)"
    if parent in {"S5.6", "S6.11"}:
        return "v5.0 Paketi (S5.6 MBE + S6.5 TWPA/FPGA)"
    if parent in {"S5.5", "S6.9", "S6.10"} or pid == "S7.1-04":
        return "v4.0 Paketi (M4+S5.5+PT420)"
    if parent == "S6.6":
        return "S6.6 Okuma Zinciri (56x B/C Duvarı)"
    if parent == "S6.8":
        return "S6.8 Seyreltme Kriyostatı (20 mK)"
    if parent in {"S2.1", "S2.2", "S2.3"}:
        return "S2.1-2.3 MEMS Kafa & Fab NRE"
    if parent == "S6.3":
        return "S6.3 1.5T/<=0.4T Mıknatıs (Exp125)"
    if sub == "S1":
        return "S1 Kaynak+Kolon+Süzgeç+PH3 (Exp124)"
    if sub == "S3":
        return "S3 IBIC + Vakum-İçi Ön-Uç (Exp127)"
    if sub == "S4":
        return "S4 Piezo Kademe + İnterferometri"
    if sub == "S5":
        return "S5 UHV Oda + Tavlama + Epi"
    if sub == "S6":
        return "S6 Diğer (PT420/MW/RF/SET)"
    if sub == "S7":
        return "S7 Kontrol/AWG/SKY130"
    if sub == "S9":
        return "S9 Yedekler & Kalibrasyon"
    return "S2 Diğer (ASIC/Metroloji)"


def assign_delta_bucket(row: pd.Series) -> str:
    pid = row["part_id"]
    parent = row["parent_bom_id"]
    notes = str(row["notes"])
    if "DELTA-V7.0-SAFETY" in notes:
        return "V7_0_Safety_Compliance_Exp150"
    if "DELTA-V6.0-OPTQ" in notes:
        return "V6_0_Option_Q_Exp142"
    if "DELTA-V6.0-OPTHPC" in notes:
        return "V6_0_Option_HPC_Exp143"
    if "DELTA-V5.0" in notes:
        return "V5_0_Upgrade_Exp139_140"
    if "DELTA-V4.0" in notes and row["subsystem"] != "S8":
        return "V4_0_Upgrade_Exp130_131_133_134"
    if "DELTA-EXP124" in notes or parent in {"S1.5", "S1.6"} or pid == "S1.3-02":
        return "Exp124_Decel_Filter_PH3"
    if "DELTA-EXP125" in notes or parent == "S6.3" or pid == "S6.6-07":
        return "Exp125_BuckingMagnet_NbTiN"
    if "DELTA-EXP127" in notes:
        return "Exp127_InVac_IBIC_Frontend"
    if "DELTA-MEMS-NRE" in notes or parent in {"S2.1", "S2.2", "S2.3"}:
        return "MEMS_Fixed_NRE_and_Head"
    if row["subsystem"] == "S9":
        return "S9_Spares_Calibration"
    if row["subsystem"] == "S8":
        return "S8_Software_InHouse_ZeroHW"
    return "Core_Baseline_Aligned"


def pct_summary(arr: np.ndarray) -> dict[str, float]:
    qs = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95, 99])
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "p05": float(qs[0]),
        "p10": float(qs[1]),
        "p25": float(qs[2]),
        "p50": float(qs[3]),
        "p75": float(qs[4]),
        "p90": float(qs[5]),
        "p95": float(qs[6]),
        "p99": float(qs[7]),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def main() -> None:
    pred = json.loads(PRED_JSON.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # 1. Canonical Gate (BOM.csv SHA-256 + Exp121/Exp122 exact reproduction)
    # -------------------------------------------------------------------------
    bom_sha = sha256_file(BOM_CSV)
    sha_ok = bom_sha == EXPECTED_BOM_SHA256
    assert sha_ok, f"Canonical BOM.csv modified! Got {bom_sha}"

    canon_rows = load_canonical_bom()
    assert len(canon_rows) == 40
    g55 = canonical_golden_breakdown(canon_rows, 55, 10.0)
    g163_b = canonical_golden_breakdown(canon_rows, 163, 10.0)
    g163_cen = canonical_golden_breakdown(canon_rows, 163, 16.875)
    g163_c = canonical_golden_breakdown(canon_rows, 163, 100.0)

    gate_ok = (
        abs(g55["golden_frac"] - 0.5602950333504173) < 1e-12
        and abs(g55["abs_units"] - 2159.00039876329) < 1e-9
        and abs(g163_cen["golden_units"] * 720.0 - 2531244.3664524374) < 1e-6
    )
    assert gate_ok, "Exp121/122 baseline gate failed!"

    # -------------------------------------------------------------------------
    # 2. Load BOM_DETAILED.csv & Roll-Up Reconciliation vs Exp122
    # -------------------------------------------------------------------------
    df = pd.read_csv(BOM_DETAILED)
    canonical_ids = {r[0] for r in canon_rows}
    covered_ids = set(df["parent_bom_id"].unique())
    missing_canon = sorted(canonical_ids - covered_ids)
    assert not missing_canon, f"Missing canonical IDs: {missing_canon}"

    df["rfq_package"] = df.apply(assign_rfq_package, axis=1)
    df["driver_group"] = df.apply(assign_driver_group, axis=1)
    df["delta_bucket"] = df.apply(assign_delta_bucket, axis=1)
    m1_res = df.apply(m1_scale_factor, axis=1)
    df["m1_factor"] = [x[0] for x in m1_res]
    df["m1_reason"] = [x[1] for x in m1_res]
    df["m1_low"] = df["usd_low"] * df["m1_factor"]
    df["m1_nom"] = df["usd_nom"] * df["m1_factor"]
    df["m1_high"] = df["usd_high"] * df["m1_factor"]

    exp122_central_usd = g163_cen["golden_units"] * 720.0
    exp122_sub_usd = {k: v * 720.0 for k, v in g163_cen["sub_units_golden"].items()}

    sub_reconcil = {}
    reconcil_sum_check = 0.0
    for s in [f"S{i}" for i in range(1, 10)]:
        sub_df = df[df["subsystem"] == s]
        lo = float(sub_df["usd_low"].sum())
        nom = float(sub_df["usd_nom"].sum())
        hi = float(sub_df["usd_high"].sum())
        e122 = float(exp122_sub_usd[s])
        delta = nom - e122
        reconcil_sum_check += e122 + delta
        sub_reconcil[s] = {
            "n_parts": int(len(sub_df)),
            "exp122_central_usd": e122,
            "detailed_m3_low_usd": lo,
            "detailed_m3_nom_usd": nom,
            "detailed_m3_high_usd": hi,
            "delta_vs_exp122_usd": delta,
            "m1_low_usd": float(sub_df["m1_low"].sum()),
            "m1_nom_usd": float(sub_df["m1_nom"].sum()),
            "m1_high_usd": float(sub_df["m1_high"].sum()),
        }

    m3_low = float(df["usd_low"].sum())
    m3_nom = float(df["usd_nom"].sum())
    m3_high = float(df["usd_high"].sum())
    m1_low = float(df["m1_low"].sum())
    m1_nom = float(df["m1_nom"].sum())
    m1_high = float(df["m1_high"].sum())
    reconcil_err = abs(reconcil_sum_check - m3_nom)
    assert reconcil_err < 1e-6, f"Roll-up reconciliation error: {reconcil_err}"

    # Verify exact Exp114 56-chain & S6.8 DR parity inside BOM_DETAILED
    s66_chain6_nom = float(
        df[df["part_id"].isin([f"S6.6-0{i}" for i in range(1, 7)])]["usd_nom"].sum()
    )
    s68_dr_nom = float(df[df["parent_bom_id"] == "S6.8"]["usd_nom"].sum())
    assert abs(s66_chain6_nom - 56 * 12150.0) < 1e-6, f"S6.6 chain sum mismatch: {s66_chain6_nom}"
    assert abs(s68_dr_nom - 720000.0) < 1e-6, f"S6.8 DR sum mismatch: {s68_dr_nom}"

    # Delta bucket breakdown (raw part totals & net delta over Exp122)
    delta_buckets = {}
    for b, bdf in df.groupby("delta_bucket"):
        delta_buckets[b] = {
            "n_parts": int(len(bdf)),
            "usd_low": float(bdf["usd_low"].sum()),
            "usd_nom": float(bdf["usd_nom"].sum()),
            "usd_high": float(bdf["usd_high"].sum()),
        }

    # Explicit engineering delta bridge:
    # Exp122 ($2,531,244.37) -> M3 v3.0 ($4,189,600) -> M3 v4.0 ($4,609,600)
    # -> M3 v5.0 Base ($5,247,800) -> M3 v6.0 Full ($5,547,800) -> M3 v7.0 Safety-Certified Full ($5,692,800)
    s56_spec = json.loads(S56_SPEC_JSON.read_text(encoding="utf-8"))["s56_hardware_spec"]
    s65_spec = json.loads(S65_SPEC_JSON.read_text(encoding="utf-8"))
    s9q_spec = json.loads(S9Q_SPEC_JSON.read_text(encoding="utf-8"))
    s9hpc_spec = json.loads(S9HPC_SPEC_JSON.read_text(encoding="utf-8"))
    s_safety_spec = json.loads(S_SAFETY_SPEC_JSON.read_text(encoding="utf-8"))

    notes_str = df["notes"].astype(str)
    v7_safety_mask = notes_str.str.contains("DELTA-V7.0-SAFETY", na=False)
    v6_optq_mask = notes_str.str.contains("DELTA-V6.0-OPTQ", na=False)
    v6_opthpc_mask = notes_str.str.contains("DELTA-V6.0-OPTHPC", na=False)
    v6_mask_all = v6_optq_mask | v6_opthpc_mask
    v5_mask_all = notes_str.str.contains("DELTA-V5.0", na=False)
    v4_mask_all = notes_str.str.contains("DELTA-V4.0", na=False) & ~v5_mask_all
    v3_mask_all = ~v4_mask_all & ~v5_mask_all & ~v6_mask_all & ~v7_safety_mask

    exp124_parts_nom = float(
        df[df["part_id"].isin(["S1.3-02", "S1.5-01", "S1.5-02", "S1.5-03", "S1.6-01", "S1.6-02"])]["usd_nom"].sum()
    )
    exp124_net_delta = exp124_parts_nom - (ADDERS * 720.0)
    exp125_parts_nom = float(
        df[df["part_id"].isin(["S6.3-01", "S6.3-02", "S6.3-03", "S6.3-04", "S6.3-05", "S6.6-07"])]["usd_nom"].sum()
    )
    exp125_net_delta = exp125_parts_nom - (12.5 * 720.0)
    exp127_parts_nom = float(
        df[df["part_id"].isin(["S3.2-01", "S3.2-02", "S3.2-03", "S3.2-04", "S3.2-05", "S3.2-06"])]["usd_nom"].sum()
    )
    exp127_net_delta = exp127_parts_nom - (100.0 * (9000 / 10000) ** 0.7 * 720.0)
    mems_s2_net_delta = sub_reconcil["S2"]["delta_vs_exp122_usd"]
    # Strict v3.0 S9 spares only ($148,000), excluding v6.0 Option-Q (S9.4) & Option-HPC (S9.HPC)
    s9_spares_delta = float(df[v3_mask_all & (df["subsystem"] == "S9")]["usd_nom"].sum())

    m3_v3_base_nom = float(df[v3_mask_all]["usd_nom"].sum())
    v4_net_retained_nom = float(df[v4_mask_all]["usd_nom"].sum())  # $334,000 retained after -$86,000 v5.0 credit
    v4_original_gross_nom = 420_000.0
    m3_v4_base_nom = m3_v3_base_nom + v4_original_gross_nom  # $4,609,600 exact
    v5_credit_nom = v4_original_gross_nom - v4_net_retained_nom  # $86,000 exact

    v5_s56_low = float(df[df["parent_bom_id"] == "S5.6"]["usd_low"].sum())
    v5_s56_nom = float(df[df["parent_bom_id"] == "S5.6"]["usd_nom"].sum())
    v5_s56_high = float(df[df["parent_bom_id"] == "S5.6"]["usd_high"].sum())
    v5_s611_low = float(df[df["parent_bom_id"] == "S6.11"]["usd_low"].sum())
    v5_s611_nom = float(df[df["parent_bom_id"] == "S6.11"]["usd_nom"].sum())
    v5_s611_high = float(df[df["parent_bom_id"] == "S6.11"]["usd_high"].sum())

    v5_gross_low = v5_s56_low + v5_s611_low
    v5_gross_nom = v5_s56_nom + v5_s611_nom
    v5_gross_high = v5_s56_high + v5_s611_high
    v5_net_delta_nom = v5_gross_nom - v5_credit_nom  # +$638,200 exact
    m3_v5_base_low = float(df[~v6_mask_all & ~v7_safety_mask]["usd_low"].sum())
    m3_v5_base_nom = float(df[~v6_mask_all & ~v7_safety_mask]["usd_nom"].sum())  # $5,247,800 exact
    m3_v5_base_high = float(df[~v6_mask_all & ~v7_safety_mask]["usd_high"].sum())

    # v6.0 Modular Optional Add-Ons (zero double-counting!)
    v6_optq_low = float(df[v6_optq_mask]["usd_low"].sum())
    v6_optq_nom = float(df[v6_optq_mask]["usd_nom"].sum())
    v6_optq_high = float(df[v6_optq_mask]["usd_high"].sum())
    v6_opthpc_low = float(df[v6_opthpc_mask]["usd_low"].sum())
    v6_opthpc_nom = float(df[v6_opthpc_mask]["usd_nom"].sum())
    v6_opthpc_high = float(df[v6_opthpc_mask]["usd_high"].sum())
    v6_net_delta_low = v6_optq_low + v6_opthpc_low
    v6_net_delta_nom = v6_optq_nom + v6_opthpc_nom  # +$300,000 exact
    v6_net_delta_high = v6_optq_high + v6_opthpc_high

    m3_v6_plus_optq_nom = m3_v5_base_nom + v6_optq_nom  # $5,415,800 exact
    m3_v6_plus_opthpc_nom = m3_v5_base_nom + v6_opthpc_nom  # $5,379,800 exact
    m3_v6_full_nom = m3_v5_base_nom + v6_net_delta_nom  # $5,547,800 exact

    # v7.0 SEMI S2 / ANSI Z136.1 / IEC 61508 SIL-3 Safety Compliance Package (Exp150; 355.0 kg facility)
    v7_safety_low = float(df[v7_safety_mask]["usd_low"].sum())
    v7_safety_nom = float(df[v7_safety_mask]["usd_nom"].sum())  # $145,000 exact
    v7_safety_high = float(df[v7_safety_mask]["usd_high"].sum())
    m3_base_plus_safety_nom = m3_v5_base_nom + v7_safety_nom  # $5,392,800 exact
    m1_plus_safety_nom = m1_nom + v7_safety_nom  # $2,611,120 exact
    # Transparent conservative gross vs potential starter-item replacement credit ($76.2k max if S1.6/S5.5-04/S7.1-03/S7.4-04 swapped rather than kept as redundant layers)
    v7_max_potential_starter_overlap_usd = float(
        df[df["part_id"].isin(["S1.6-01", "S1.6-02", "S5.5-04", "S7.1-03", "S7.4-04"])]["usd_nom"].sum()
    )

    # Strict parity assertions against primary Exp139, Exp140, Exp142, Exp143 & Exp150 hardware specs
    assert abs(m3_v3_base_nom - 4_189_600.0) < 1e-6, f"M3 v3.0 base mismatch: {m3_v3_base_nom}"
    assert abs(v5_credit_nom - 86_000.0) < 1e-6, f"v5.0 credit mismatch: {v5_credit_nom}"
    assert abs(v5_s56_nom - s56_spec["bom_v5_cost_estimate_usd"]["total_p50_usd"]) < 1e-6
    assert abs(v5_s611_nom - s65_spec["totals_1024_cell_module"]["cost_usd_nom"]) < 1e-6
    assert abs(m3_v5_base_nom - 5_247_800.0) < 1e-6, f"M3 v5.0 Base mismatch: {m3_v5_base_nom}"
    assert abs(m1_nom - 2_466_120.0) < 1e-6, f"M1 Base mismatch: {m1_nom}"
    assert abs(v6_optq_nom - s9q_spec["totals_option_q_plus_s1_multi"]["cost_usd_nom"]) < 1e-6
    assert abs(v6_opthpc_nom - s9hpc_spec["totals_base_4u_option_hpc_module"]["cost_usd_nom"]) < 1e-6
    assert abs(m3_v6_full_nom - 5_547_800.0) < 1e-6, f"M3 v6.0 Full mismatch: {m3_v6_full_nom}"
    assert abs(v7_safety_low - s_safety_spec["totals"]["cost_usd_low"]) < 1e-6
    assert abs(v7_safety_nom - s_safety_spec["totals"]["cost_usd_nom"]) < 1e-6
    assert abs(v7_safety_high - s_safety_spec["totals"]["cost_usd_high"]) < 1e-6
    assert abs(m3_base_plus_safety_nom - 5_392_800.0) < 1e-6, f"M3 Base+Safety mismatch: {m3_base_plus_safety_nom}"
    assert abs(m3_nom - 5_692_800.0) < 1e-6, f"M3 v7.0 Safety-Certified Full mismatch: {m3_nom}"

    # Alternative M3 v5.0 Pilot (256-cell / 8-chain S6.5 subset: 1x ZU48DR $29k + 1/4 cryo $142.8k = $171.8k -> +$171.8k + $95k - $86k = +$180.8k over v4.0)
    s611_pilot_256_nom = 0.5 * 58_000.0 + 0.25 * (336_000.0 + 144_000.0 + 91_200.0)  # $171,800
    m3_v5_pilot_256_nom = m3_v4_base_nom + v5_s56_nom + s611_pilot_256_nom - v5_credit_nom  # $4,790,400

    v5_hardware_mass_reconciliation = {
        "S5.6_exp139_spec_mass_kg": float(s56_spec["mass_power_cryo"]["total_mass_kg"]),
        "S5.6_bom_parts_mass_kg": {
            "S5.6-01": 11.8,
            "S5.6-02": 3.4,
            "S5.6-03": 4.2,
            "S5.6-04": 3.0,
        },
        "S5.6_bom_total_mass_kg": 11.8 + 3.4 + 4.2 + 3.0,
        "S6.11_exp140_S6.5_spec_total_mass_kg": float(s65_spec["totals_1024_cell_module"]["total_mass_kg"]),
        "S6.11_exp140_S6.5_spec_cold_mass_kg": float(s65_spec["totals_1024_cell_module"]["cryo_cold_mass_kg"]),
        "S6.11_bom_parts_mass_kg": {
            "S6.11-01_rack": 11.50,
            "S6.11-02_cold": 2.72,
            "S6.11-03_cold": 1.02,
            "S6.11-04_cold": 4.03,
        },
        "S6.11_bom_total_mass_kg": round(11.50 + 2.72 + 1.02 + 4.03, 4),
        "S6.11_bom_cold_mass_kg": round(2.72 + 1.02 + 4.03, 4),
        "mass_reconciliation_error_kg": abs((11.8 + 3.4 + 4.2 + 3.0) - float(s56_spec["mass_power_cryo"]["total_mass_kg"]))
        + abs((11.50 + 2.72 + 1.02 + 4.03) - float(s65_spec["totals_1024_cell_module"]["total_mass_kg"])),
    }
    assert v5_hardware_mass_reconciliation["mass_reconciliation_error_kg"] < 1e-9

    optq_parts_mass = {"S1.7-01": 4.80, "S9.4-01": 3.20, "S9.4-02": 0.38, "S9.4-03": 0.82}
    opthpc_parts_mass = {"S9.HPC-01": 56.00, "S9.HPC-02": 4.20, "S9.HPC-03": 3.80}
    optq_mass_tot = round(sum(optq_parts_mass.values()), 4)
    opthpc_mass_tot = round(sum(opthpc_parts_mass.values()), 4)
    v6_hardware_mass_reconciliation = {
        "Option_Q_exp142_spec_mass_kg": float(s9q_spec["totals_option_q_plus_s1_multi"]["total_mass_kg"]),
        "Option_Q_bom_parts_mass_kg": optq_parts_mass,
        "Option_Q_bom_total_mass_kg": optq_mass_tot,
        "Option_HPC_exp143_spec_mass_kg": float(s9hpc_spec["totals_base_4u_option_hpc_module"]["total_mass_kg"]),
        "Option_HPC_bom_parts_mass_kg": opthpc_parts_mass,
        "Option_HPC_bom_total_mass_kg": opthpc_mass_tot,
        "v6_total_addon_mass_kg": round(optq_mass_tot + opthpc_mass_tot, 4),
        "cad_v5_base_mass_kg": 1034.937,
        "cad_v6_full_mass_kg": round(1034.937 + optq_mass_tot + opthpc_mass_tot, 4),
        "mass_reconciliation_error_kg": abs(optq_mass_tot - float(s9q_spec["totals_option_q_plus_s1_multi"]["total_mass_kg"]))
        + abs(opthpc_mass_tot - float(s9hpc_spec["totals_base_4u_option_hpc_module"]["total_mass_kg"])),
    }
    assert v6_hardware_mass_reconciliation["mass_reconciliation_error_kg"] < 1e-9

    safety_parts_mass = {
        "S7.SAFETY-01": 118.0,
        "S7.SAFETY-02": 38.0,
        "S7.SAFETY-03": 18.0,
        "S7.SAFETY-04": 145.0,
        "S7.SAFETY-05": 24.0,
        "S7.SAFETY-06": 12.0,
    }
    safety_mass_tot = round(sum(safety_parts_mass.values()), 4)
    v7_hardware_mass_reconciliation = {
        "on_frame_cad_v6_mass_kg": v6_hardware_mass_reconciliation["cad_v6_full_mass_kg"],
        "facility_safety_exp150_spec_mass_kg": float(s_safety_spec["totals"]["total_mass_kg"]),
        "facility_safety_bom_parts_mass_kg": safety_parts_mass,
        "facility_safety_bom_total_mass_kg": safety_mass_tot,
        "facility_safety_steady_power_W": float(s_safety_spec["totals"]["steady_electrical_power_W"]),
        "facility_safety_cryo_load_W": float(s_safety_spec["totals"]["cryo_load_W"]),
        "total_facility_load_mass_kg": round(v6_hardware_mass_reconciliation["cad_v6_full_mass_kg"] + safety_mass_tot, 4),
        "mass_reconciliation_error_kg": abs(safety_mass_tot - float(s_safety_spec["totals"]["total_mass_kg"])),
    }
    assert v7_hardware_mass_reconciliation["mass_reconciliation_error_kg"] < 1e-9

    other_cots_align_delta = (m3_v3_base_nom - exp122_central_usd) - (
        exp124_net_delta + exp125_net_delta + exp127_net_delta + mems_s2_net_delta + s9_spares_delta
    )
    delta_bridge = {
        "exp122_central_baseline_usd": exp122_central_usd,
        "delta_s2_mems_nre_and_head_usd": mems_s2_net_delta,
        "delta_exp125_magnet_shield_nbtin_usd": exp125_net_delta,
        "delta_s9_spares_calibration_usd": s9_spares_delta,
        "delta_exp124_decel_filter_ph3_usd": exp124_net_delta,
        "delta_exp127_invac_ibic_frontend_usd": exp127_net_delta,
        "delta_other_cots_uhv_anchor_align_usd": other_cots_align_delta,
        "bom_detailed_m3_v3_base_nom_usd": m3_v3_base_nom,
        "delta_v4_0_upgrade_package_usd": v4_original_gross_nom,
        "bom_detailed_m3_v4_base_nom_usd": m3_v4_base_nom,
        "delta_v5_0_gross_new_hardware_usd": v5_gross_nom,
        "delta_v5_0_breakdown_usd": {
            "S5.6_insitu_28si_mbe_exp139": v5_s56_nom,
            "S6.11_exp140_S6.5_cryo_mux_1024_twpa_rfsoc": v5_s611_nom,
        },
        "delta_v5_0_anti_double_counting_credit_usd": -v5_credit_nom,
        "delta_v5_0_credit_breakdown_usd": {
            "S6.10-02_external_8nm_cap_superseded_by_S5.6": -54_000.0,
            "S6.10-04_5GHz_rf_drive_superseded_by_S6.11-01": -20_000.0,
            "S7.1-04_standalone_boed_gpu_superseded_by_S6.11-01": -12_000.0,
        },
        "delta_v5_0_net_incremental_usd": v5_net_delta_nom,
        "bom_detailed_m3_v5_base_nom_usd": m3_v5_base_nom,
        "bom_detailed_m3_v5_pilot_256_nom_usd": m3_v5_pilot_256_nom,
        "delta_v6_0_option_q_exp142_usd": v6_optq_nom,
        "delta_v6_0_option_hpc_exp143_usd": v6_opthpc_nom,
        "delta_v6_0_modular_addons_total_usd": v6_net_delta_nom,
        "bom_detailed_m3_v6_plus_option_q_nom_usd": m3_v6_plus_optq_nom,
        "bom_detailed_m3_v6_plus_option_hpc_nom_usd": m3_v6_plus_opthpc_nom,
        "bom_detailed_m3_v6_full_nom_usd": m3_v6_full_nom,
        "delta_v7_0_safety_compliance_exp150_usd": v7_safety_nom,
        "bom_detailed_m3_base_plus_safety_nom_usd": m3_base_plus_safety_nom,
        "bom_detailed_m1_plus_safety_nom_usd": m1_plus_safety_nom,
        "v7_max_potential_starter_overlap_usd": v7_max_potential_starter_overlap_usd,
        "bom_detailed_m3_nom_usd": m3_nom,
        "total_delta_usd": m3_nom - exp122_central_usd,
        "bridge_arithmetic_error_usd": abs(
            (
                exp122_central_usd
                + mems_s2_net_delta
                + exp125_net_delta
                + s9_spares_delta
                + exp124_net_delta
                + exp127_net_delta
                + other_cots_align_delta
                + v4_original_gross_nom
                + v5_gross_nom
                - v5_credit_nom
                + v6_optq_nom
                + v6_opthpc_nom
                + v7_safety_nom
            )
            - m3_nom
        ),
    }
    assert delta_bridge["bridge_arithmetic_error_usd"] < 1e-6

    # RFQ nominal coverage (RFQ-01..06, 01..07, 01..08 v5 Base, 01..09 v6 Full, 01..10 v7 Safety Full)
    rfq_summary = {}
    for pkg, g in df.groupby("rfq_package"):
        rfq_summary[pkg] = {
            "n_parts": int(len(g)),
            "usd_low": float(g["usd_low"].sum()),
            "usd_nom": float(g["usd_nom"].sum()),
            "usd_high": float(g["usd_high"].sum()),
            "share_of_m3_nom": float(g["usd_nom"].sum() / m3_nom),
        }
    rfq6_nom = sum(
        v["usd_nom"] for k, v in rfq_summary.items()
        if k.startswith("RFQ-0") and not k.startswith(("RFQ-07", "RFQ-08", "RFQ-09"))
    )
    rfq6_nom_share = rfq6_nom / m3_nom
    rfq7_nom = sum(
        v["usd_nom"] for k, v in rfq_summary.items()
        if k.startswith("RFQ-0") and not k.startswith(("RFQ-08", "RFQ-09"))
    )
    rfq7_nom_share = rfq7_nom / m3_nom
    rfq8_nom = sum(
        v["usd_nom"] for k, v in rfq_summary.items()
        if k.startswith("RFQ-0") and not k.startswith("RFQ-09")
    )
    rfq8_nom_share = rfq8_nom / m3_nom
    rfq8_nom_share_of_v5_base = rfq8_nom / m3_v5_base_nom
    rfq9_nom = sum(
        v["usd_nom"] for k, v in rfq_summary.items()
        if k.startswith("RFQ-0")
    )
    rfq9_nom_share = rfq9_nom / m3_nom
    rfq9_nom_share_of_v6_full = rfq9_nom / m3_v6_full_nom
    rfq10_nom = sum(v["usd_nom"] for k, v in rfq_summary.items() if k.startswith("RFQ-"))
    rfq10_nom_share = rfq10_nom / m3_nom

    # -------------------------------------------------------------------------
    # 3. Model A — 100,000-Sample Correlated Log-Normal Monte Carlo (BOM_DETAILED)
    # -------------------------------------------------------------------------
    N = 100_000
    rng = np.random.default_rng(2026128)

    priced = df[df["usd_nom"] > 0].reset_index(drop=True)
    K = len(priced)  # 137 priced parts

    # Construct positive-definite correlation matrix R (K x K):
    # rho = rho_macro (0.25) + rho_sub_extra (0.30 -> 0.55 same sub) + rho_rd_extra (0.20 -> 0.45 both R&D)
    subs = priced["subsystem"].to_numpy(dtype=object)
    procs = priced["procurement_class"].to_numpy(dtype=object)
    is_rd = np.array(["R&D" in str(p) for p in procs], dtype=float)
    same_sub = (subs[:, None] == subs[None, :]).astype(float)
    both_rd = np.outer(is_rd, is_rd)

    corr = 0.25 + 0.30 * same_sub + 0.20 * both_rd
    np.fill_diagonal(corr, 1.0)
    # Ensure strict positive definiteness via eigenvalue floor if needed
    eigvals, eigvecs = np.linalg.eigh(corr)
    if eigvals.min() < 1e-6:
        eigvals = np.maximum(eigvals, 1e-6)
        corr = (eigvecs * eigvals) @ eigvecs.T
        d_inv = 1.0 / np.sqrt(np.diag(corr))
        corr = corr * np.outer(d_inv, d_inv)
    L = np.linalg.cholesky(corr)

    # Fit log-normal parameters per part: median = usd_nom, sigma = ln(usd_high/usd_low) / (2 * Z90)
    mu_part = np.log(priced["usd_nom"].to_numpy(dtype=float))
    sigma_part = np.log(priced["usd_high"].to_numpy(dtype=float) / priced["usd_low"].to_numpy(dtype=float)) / (2.0 * Z90)

    # Sample in memory-friendly chunks to keep RAM tiny while remaining 100% deterministic
    chunk = 20_000
    driver_col = priced["driver_group"].to_numpy(dtype=object)
    driver_names = sorted(priced["driver_group"].unique())
    drv_idx = {name: np.where(driver_col == name)[0] for name in driver_names}
    rfq10_mask = priced["rfq_package"].str.startswith("RFQ-").to_numpy(dtype=bool)
    rfq9_mask = priced["rfq_package"].str.startswith("RFQ-0").to_numpy(dtype=bool)
    rfq8_mask = (
        priced["rfq_package"].str.startswith("RFQ-0") & ~priced["rfq_package"].str.startswith("RFQ-09")
    ).to_numpy(dtype=bool)
    rfq7_mask = (
        priced["rfq_package"].str.startswith("RFQ-0") & ~priced["rfq_package"].str.startswith(("RFQ-08", "RFQ-09"))
    ).to_numpy(dtype=bool)
    rfq6_mask = (
        priced["rfq_package"].str.startswith("RFQ-0") & ~priced["rfq_package"].str.startswith(("RFQ-07", "RFQ-08", "RFQ-09"))
    ).to_numpy(dtype=bool)
    priced_notes = priced["notes"].astype(str)
    safety_p_mask = priced_notes.str.contains("DELTA-V7.0-SAFETY", na=False).to_numpy(dtype=bool)
    optq_p_mask = priced_notes.str.contains("DELTA-V6.0-OPTQ", na=False).to_numpy(dtype=bool)
    opthpc_p_mask = priced_notes.str.contains("DELTA-V6.0-OPTHPC", na=False).to_numpy(dtype=bool)
    base_v5_p_mask = ~(optq_p_mask | opthpc_p_mask | safety_p_mask)
    s66_chain_mask = priced["part_id"].isin([f"S6.6-0{i}" for i in range(1, 7)]).to_numpy(dtype=bool)
    s68_mask = (priced["parent_bom_id"] == "S6.8").to_numpy(dtype=bool)

    # Explicit B/C chain-class stress regime on the 56-chain S6.6 readout electronics:
    # 80% continuous Exp114 regime (multiplier ~ 1.0, already captured by part log-normals),
    # 20% C-class cryo procurement shock (multiplier LogNormal centered at 5.5x -> ~$67k/chain,
    # spanning $35k-$110k/chain, reflecting Exp114's unresolved [4.06, 116.84] class band).
    u_bc = rng.random(N)
    bc_regime_C = u_bc < 0.20
    bc_shock_mult = np.ones(N, dtype=np.float64)
    n_c = int(bc_regime_C.sum())
    bc_shock_mult[bc_regime_C] = np.exp(
        np.log(5.5) + 0.35 * rng.standard_normal(n_c)
    )  # P50=5.5x ($66.8k/ch), P90~8.6x ($105k/ch)

    # Also sample NL in Exp112 spec band [110, 163] (chains = ceil(9000 / NL): 56..82 chains!)
    nl_samples = rng.integers(110, 164, size=N)  # 110..163 inclusive
    chains_samples = np.ceil(9000.0 / nl_samples)
    chain_count_scale = chains_samples / 56.0  # 1.00 at NL=163 up to 1.464 at NL=110

    bom_samples = np.empty(N, dtype=np.float64)
    bom_v5_base_samples = np.empty(N, dtype=np.float64)
    bom_base_plus_safety_samples = np.empty(N, dtype=np.float64)
    bom_plus_optq_samples = np.empty(N, dtype=np.float64)
    bom_plus_opthpc_samples = np.empty(N, dtype=np.float64)
    bom_v6_full_samples = np.empty(N, dtype=np.float64)
    bom_no_bc_shock = np.empty(N, dtype=np.float64)
    rfq_cost_samples = np.empty(N, dtype=np.float64)
    rfq9_cost_samples = np.empty(N, dtype=np.float64)
    rfq8_cost_samples = np.empty(N, dtype=np.float64)
    rfq7_cost_samples = np.empty(N, dtype=np.float64)
    rfq6_cost_samples = np.empty(N, dtype=np.float64)
    s68_samples = np.empty(N, dtype=np.float64)
    driver_samples = {name: np.empty(N, dtype=np.float64) for name in driver_names}

    for start in range(0, N, chunk):
        end = min(start + chunk, N)
        m = end - start
        z_ind = rng.standard_normal((m, K))
        z_corr = z_ind @ L.T
        c_mat = np.exp(mu_part[None, :] + sigma_part[None, :] * z_corr)

        # Save pure correlated bottom-up BOM before B/C & NL scaling
        bom_no_bc_shock[start:end] = c_mat.sum(axis=1)

        # Apply Exp112 NL chain-count scaling [56..82] AND Exp114 B/C chain-class wall to S6.6-01..06
        total_chain_mult = chain_count_scale[start:end] * bc_shock_mult[start:end]
        c_mat[:, s66_chain_mask] *= total_chain_mult[:, None]

        bom_samples[start:end] = c_mat.sum(axis=1)
        b_base = c_mat[:, base_v5_p_mask].sum(axis=1)
        b_optq = c_mat[:, optq_p_mask].sum(axis=1)
        b_opthpc = c_mat[:, opthpc_p_mask].sum(axis=1)
        b_saf = c_mat[:, safety_p_mask].sum(axis=1)
        bom_v5_base_samples[start:end] = b_base
        bom_base_plus_safety_samples[start:end] = b_base + b_saf
        bom_plus_optq_samples[start:end] = b_base + b_optq
        bom_plus_opthpc_samples[start:end] = b_base + b_opthpc
        bom_v6_full_samples[start:end] = b_base + b_optq + b_opthpc

        rfq_cost_samples[start:end] = c_mat[:, rfq10_mask].sum(axis=1)
        rfq9_cost_samples[start:end] = c_mat[:, rfq9_mask].sum(axis=1)
        rfq8_cost_samples[start:end] = c_mat[:, rfq8_mask].sum(axis=1)
        rfq7_cost_samples[start:end] = c_mat[:, rfq7_mask].sum(axis=1)
        rfq6_cost_samples[start:end] = c_mat[:, rfq6_mask].sum(axis=1)
        s68_samples[start:end] = c_mat[:, s68_mask].sum(axis=1)
        for name, idxs in drv_idx.items():
            driver_samples[name][start:end] = c_mat[:, idxs].sum(axis=1)

    # Program multiplier M_prog (labeled assumption covering facility/cleanroom/integration/R&D/contingency)
    # Stochastic log-normal calibrated to P10 = 3.0x, P50 = 5.477x (~5.5x), P90 = 10.0x:
    mu_mprog = math.log(math.sqrt(3.0 * 10.0))  # ln(5.4772) -> exact geometric center of [3, 10]
    sigma_mprog = math.log(10.0 / 3.0) / (2.0 * Z90)
    m_prog_samples = np.exp(mu_mprog + sigma_mprog * rng.standard_normal(N))

    prog_stoch = bom_samples * m_prog_samples
    prog_x3 = bom_samples * 3.0
    prog_x10 = bom_samples * 10.0

    # Common-random-number modular program comparisons across all 6 configurations
    prog_stoch_v5_base = bom_v5_base_samples * m_prog_samples
    prog_stoch_base_plus_safety = bom_base_plus_safety_samples * m_prog_samples
    prog_stoch_plus_optq = bom_plus_optq_samples * m_prog_samples
    prog_stoch_plus_opthpc = bom_plus_opthpc_samples * m_prog_samples
    prog_stoch_v6_full = bom_v6_full_samples * m_prog_samples

    # Budget-cap probabilities (Model A — Full v7.0, v6.0 Full, Base+Safety & M3 v5.0 Base)
    p_bom_gt_50m = float(np.mean(bom_samples > 50e6))
    p_bom_gt_100m = float(np.mean(bom_samples > 100e6))
    p_prog_stoch_gt_50m = float(np.mean(prog_stoch > 50e6))
    p_prog_stoch_gt_100m = float(np.mean(prog_stoch > 100e6))
    p_prog_x3_gt_50m = float(np.mean(prog_x3 > 50e6))
    p_prog_x3_gt_100m = float(np.mean(prog_x3 > 100e6))
    p_prog_x10_gt_50m = float(np.mean(prog_x10 > 50e6))
    p_prog_x10_gt_100m = float(np.mean(prog_x10 > 100e6))
    p_base_prog_stoch_gt_50m = float(np.mean(prog_stoch_v5_base > 50e6))
    p_base_prog_stoch_gt_100m = float(np.mean(prog_stoch_v5_base > 100e6))
    p_base_saf_prog_stoch_gt_50m = float(np.mean(prog_stoch_base_plus_safety > 50e6))
    p_base_saf_prog_stoch_gt_100m = float(np.mean(prog_stoch_base_plus_safety > 100e6))
    p_v6_full_prog_stoch_gt_50m = float(np.mean(prog_stoch_v6_full > 50e6))
    p_v6_full_prog_stoch_gt_100m = float(np.mean(prog_stoch_v6_full > 100e6))

    # Convergence check: first 50k vs full 100k
    half_p50 = float(np.percentile(prog_stoch[:50_000], 50))
    full_p50 = float(np.percentile(prog_stoch, 50))
    half_p95 = float(np.percentile(prog_stoch[:50_000], 95))
    full_p95 = float(np.percentile(prog_stoch, 95))
    conv_p50_rel = abs(full_p50 - half_p50) / full_p50
    conv_p95_rel = abs(full_p95 - half_p95) / full_p95
    se_p100 = math.sqrt(p_prog_stoch_gt_100m * (1.0 - p_prog_stoch_gt_100m) / N)

    # -------------------------------------------------------------------------
    # 4. Model B — Canonical Exp122 Class-Unit MC + Engineering Deltas (100,000 samples)
    # -------------------------------------------------------------------------
    # Unit price calibration from Exp114 (P10=$190, P50=$720, P90=$1600 -> asymmetric fit via lognormal
    # centered at $720 with sigma = ln(1600/190)/(2*Z90) = 0.831)
    u_sigma = math.log(1600.0 / 190.0) / (2.0 * Z90)
    unit_price_mc = np.exp(math.log(720.0) + u_sigma * rng.standard_normal(N))
    # Continuous chain class from Exp114 [4.0625, 16.875, 116.842]
    cc_sigma = math.log(116.8421 / 4.0625) / (2.0 * Z90)
    chain_cls_mc = np.exp(math.log(16.875) + cc_sigma * rng.standard_normal(N))
    nl_b_mc = rng.integers(110, 164, size=N)
    chains_b_mc = np.ceil(9000.0 / nl_b_mc)
    # Fixed+chan+head_tile at golden (s=0.5, ns=9000, nb=100) = 2565.8497 + 4.7675 = 2570.6172 units
    base_golden_units = g163_b["golden_units"] - 56.0 * 10.0  # 2570.617175628385
    canon_units_mc = base_golden_units + chains_b_mc * chain_cls_mc
    canon_bom_only_mc = canon_units_mc * unit_price_mc
    # Add engineering delta (median $1.658M, sigma=0.45)
    eng_delta_nom = m3_nom - exp122_central_usd
    eng_delta_mc = np.exp(math.log(eng_delta_nom) + 0.45 * rng.standard_normal(N))
    model_b_bom_mc = canon_bom_only_mc + eng_delta_mc
    model_b_prog_stoch = model_b_bom_mc * m_prog_samples

    # -------------------------------------------------------------------------
    # 5. Tornado Sensitivity & Variance Decomposition (Model A)
    # -------------------------------------------------------------------------
    bom_var = float(np.var(bom_samples, ddof=1))
    rfq10_var_share = float(np.cov(rfq_cost_samples, bom_samples, ddof=1)[0, 1] / bom_var)
    rfq9_var_share = float(np.cov(rfq9_cost_samples, bom_samples, ddof=1)[0, 1] / bom_var)
    rfq8_var_share = float(np.cov(rfq8_cost_samples, bom_samples, ddof=1)[0, 1] / bom_var)
    rfq7_var_share = float(np.cov(rfq7_cost_samples, bom_samples, ddof=1)[0, 1] / bom_var)
    rfq6_var_share = float(np.cov(rfq6_cost_samples, bom_samples, ddof=1)[0, 1] / bom_var)

    # 5-Year Fab-Tool TCO & FOAK Program TCO context (aligned to Exp134 parameters)
    cleanroom_capex = np.exp(math.log(2.5e6) + (math.log(4.5e6 / 1.5e6) / (2.0 * Z90)) * rng.standard_normal(N))
    install_mult = np.exp(math.log(1.35) + (math.log(1.55 / 1.20) / (2.0 * Z90)) * rng.standard_normal(N))
    opex_non_maint_yr = (
        rng.uniform(15.0, 25.0, size=N) * 8760.0 * np.exp(math.log(0.14) + (math.log(0.22 / 0.09) / (2.0 * Z90)) * rng.standard_normal(N))
        + np.exp(math.log(120_000.0) + (math.log(200_000.0 / 80_000.0) / (2.0 * Z90)) * rng.standard_normal(N))
        + np.exp(math.log(45_000.0) + (math.log(75_000.0 / 28_000.0) / (2.0 * Z90)) * rng.standard_normal(N))
        + np.exp(math.log(3.0) + (math.log(4.5 / 2.0) / (2.0 * Z90)) * rng.standard_normal(N)) * 160_000.0
    )
    maint_frac = np.exp(math.log(0.08) + (math.log(0.11 / 0.06) / (2.0 * Z90)) * rng.standard_normal(N))
    v5_opex_5yr = 5.0 * (opex_non_maint_yr + maint_frac * bom_samples)
    v5_fab_tco5 = install_mult * bom_samples + cleanroom_capex + v5_opex_5yr
    v5_foak_tco5 = prog_stoch + cleanroom_capex + v5_opex_5yr

    # Modular 5-yr TCO & Program CAPEX comparison across all 6 configurations (common random numbers)
    def _cfg_block(nom_usd: float, b_s: np.ndarray, p_s: np.ndarray) -> dict:
        op5 = 5.0 * (opex_non_maint_yr + maint_frac * b_s)
        ft5 = install_mult * b_s + cleanroom_capex + op5
        fk5 = p_s + cleanroom_capex + op5
        return {
            "bom_nom_usd": nom_usd,
            "bom_mc_usd": pct_summary(b_s),
            "program_stoch_usd": pct_summary(p_s),
            "P_BOM_gt_50M": float(np.mean(b_s > 50e6)),
            "P_Program_stoch_gt_50M": float(np.mean(p_s > 50e6)),
            "P_Program_stoch_gt_100M": float(np.mean(p_s > 100e6)),
            "fab_tool_n1_5yr_tco_no_wafers_usd": pct_summary(ft5),
            "foak_program_5yr_tco_no_wafers_usd": pct_summary(fk5),
            "P_foak_5yr_tco_gt_100M": float(np.mean(fk5 > 100e6)),
        }

    v7_modular_mc_comparison = {
        "M3_v5_0_Base": _cfg_block(m3_v5_base_nom, bom_v5_base_samples, prog_stoch_v5_base),
        "M3_v5_0_Base_Plus_Safety": _cfg_block(m3_base_plus_safety_nom, bom_base_plus_safety_samples, prog_stoch_base_plus_safety),
        "M3_v6_0_Plus_Option_HPC": _cfg_block(m3_v6_plus_opthpc_nom, bom_plus_opthpc_samples, prog_stoch_plus_opthpc),
        "M3_v6_0_Plus_Option_Q": _cfg_block(m3_v6_plus_optq_nom, bom_plus_optq_samples, prog_stoch_plus_optq),
        "M3_v6_0_Full_Option_Q_and_HPC": _cfg_block(m3_v6_full_nom, bom_v6_full_samples, prog_stoch_v6_full),
        "M3_v7_0_Safety_Certified_Full": _cfg_block(m3_nom, bom_samples, prog_stoch),
    }
    v6_modular_mc_comparison = {
        k: v7_modular_mc_comparison[k]
        for k in (
            "M3_v5_0_Base",
            "M3_v6_0_Plus_Option_Q",
            "M3_v6_0_Plus_Option_HPC",
            "M3_v6_0_Full_Option_Q_and_HPC",
        )
    }

    tornado_bom = []
    for name in driver_names:
        x = driver_samples[name]
        rho, _ = spearmanr(x, bom_samples)
        # Conditional mean of total BOM when driver is in bottom 10% vs top 10% (true correlated tornado!)
        q10, q90 = np.percentile(x, [10, 90])
        mean_lo = float(np.mean(bom_samples[x <= q10]))
        mean_hi = float(np.mean(bom_samples[x >= q90]))
        # Exact covariance contribution to total BOM variance: Cov(X_i, sum X) / Var(sum X) -> sums to 1.0!
        cov_share = float(np.cov(x, bom_samples, ddof=1)[0, 1] / bom_var)
        # Standalone P10-P90 swing of the driver itself
        d_p10, d_p50, d_p90 = np.percentile(x, [10, 50, 90])
        tornado_bom.append({
            "driver": name,
            "driver_p10_usd": float(d_p10),
            "driver_p50_usd": float(d_p50),
            "driver_p90_usd": float(d_p90),
            "standalone_swing_usd": float(d_p90 - d_p10),
            "cond_bom_mean_at_p10_usd": mean_lo,
            "cond_bom_mean_at_p90_usd": mean_hi,
            "cond_bom_swing_usd": mean_hi - mean_lo,
            "spearman_rho": float(rho),
            "variance_contrib_share": cov_share,
        })
    tornado_bom.sort(key=lambda d: -d["variance_contrib_share"])

    # Program-level tornado (includes M_prog as explicit driver!)
    prog_var = float(np.var(np.log(prog_stoch), ddof=1))
    tornado_prog = []
    prog_drivers = {"Program Çarpanı (×3–×10 Varsayım)": m_prog_samples}
    for name in driver_names:
        prog_drivers[name] = driver_samples[name]
    for name, x in prog_drivers.items():
        rho, _ = spearmanr(x, prog_stoch)
        q10, q90 = np.percentile(x, [10, 90])
        mean_lo = float(np.mean(prog_stoch[x <= q10]))
        mean_hi = float(np.mean(prog_stoch[x >= q90]))
        log_cov = float(np.cov(np.log(x), np.log(prog_stoch), ddof=1)[0, 1] / prog_var)
        tornado_prog.append({
            "driver": name,
            "cond_prog_mean_at_p10_usd": mean_lo,
            "cond_prog_mean_at_p90_usd": mean_hi,
            "cond_prog_swing_usd": mean_hi - mean_lo,
            "spearman_rho": float(rho),
            "log_var_share": log_cov,
        })
    tornado_prog.sort(key=lambda d: -d["cond_prog_swing_usd"])

    top3_bom_var_share = sum(
        d["variance_contrib_share"]
        for d in tornado_bom
        if d["driver"].startswith(("S6.6", "S6.8", "S2.1-2.3"))
    )

    # -------------------------------------------------------------------------
    # 6. Decision-Theoretic EVPI & Break-Even: 20 mK Baseline vs 1 K Hot-Readout R&D
    # -------------------------------------------------------------------------
    # S6.8 20 mK DR ($720k nom, sampled in s68_samples) vs 1 K closed-cycle stage ($110k nom, $65k-$195k)
    s68_1k_sigma = math.log(195000.0 / 65000.0) / (2.0 * Z90)
    # Correlated with DR market via rank pairing (rho~0.6)
    z_dr = (np.log(s68_samples) - np.mean(np.log(s68_samples))) / np.std(np.log(s68_samples))
    z_1k = 0.6 * z_dr + math.sqrt(1 - 0.6**2) * rng.standard_normal(N)
    s68_1k_samples = np.exp(math.log(110000.0) + s68_1k_sigma * z_1k)
    delta_hw_samples = np.maximum(s68_samples - s68_1k_samples, 0.0)  # hardware saving per machine if 1K succeeds
    e_delta_hw = float(np.mean(delta_hw_samples))
    med_delta_hw = float(np.median(delta_hw_samples))

    # Program-inclusive saving per machine (integration/cryo-overhead multiplier ~2.0x on stage delta, labeled assumption)
    e_delta_prog_1mach = 2.0 * e_delta_hw

    # Grid over (C_RD, p_succ, N_mach)
    rd_costs = [0.5e6, 1.0e6, 2.0e6, 3.5e6, 5.0e6]
    p_succ_grid = [0.10, 0.25, 0.40, 0.50, 0.65, 0.80]
    n_mach_grid = [1, 2, 5, 10, 20, 50]

    # Expected Net Value of 1K R&D = p_succ * N_mach * E[delta_hw] - C_RD
    # EVPI (Value of Perfect Information on whether 1K implanted-donor PSB works BEFORE spending C_RD):
    # Without info: max(0, p_succ * N_mach * E[delta_hw] - C_RD)
    # With perfect info on technical feasibility (saves wasted C_RD when 1K fails, i.e., if it would fail you don't spend C_RD,
    # Wait: if you already know 1K succeeds, you still must spend C_RD to build/qualify the 1K readout hardware!
    # Standard EVPI: E_theta[max_a U(a, theta)] - max_a E_theta[U(a, theta)], where theta in {work, fail}:
    # If theta=work: max(0, N_mach*delta_hw - C_RD); if theta=fail: max(0, -C_RD) = 0.
    # Therefore E[max] = p_succ * max(0, N_mach * E[delta_hw] - C_RD).
    # EVPI = p_succ * max(0, N_mach * E[delta_hw] - C_RD) - max(0, p_succ * N_mach * E[delta_hw] - C_RD).
    evpi_table = []
    for c_rd in rd_costs:
        for p_s in p_succ_grid:
            n_be_hw = c_rd / (p_s * e_delta_hw)
            n_be_prog = c_rd / (p_s * e_delta_prog_1mach)
            row_n = {}
            for nm in n_mach_grid:
                env_hw = p_s * nm * e_delta_hw - c_rd
                best_no_info = max(0.0, env_hw)
                best_with_info = p_s * max(0.0, nm * e_delta_hw - c_rd)
                evpi_val = best_with_info - best_no_info
                row_n[str(nm)] = {
                    "env_hw_usd": float(env_hw),
                    "evpi_usd": float(evpi_val),
                    "recommend": "1K_RD" if env_hw > 0 else "20mK_BASE",
                }
            evpi_table.append({
                "c_rd_usd": c_rd,
                "p_succ": p_s,
                "breakeven_n_mach_hw": float(n_be_hw),
                "breakeven_n_mach_prog2x": float(n_be_prog),
                "by_n_mach": row_n,
            })

    # Reference CU5 case: N_mach=1, C_RD=$2.0M, p_succ=0.50
    cu5_env_1mach = 0.50 * 1 * e_delta_hw - 2.0e6
    cu5_n_be_hw = 2.0e6 / (0.50 * e_delta_hw)

    # Also compute EVPI of sending the 6 vendor RFQs (resolving B/C wall before committing procurement/budget reserve):
    # Suppose holding contingency reserve to cover P90 ($50M soft-line / excess cash lockup at 15% capital-cost penalty
    # or avoiding a C-class chain trap via 1K/low-NL redesign if C-class quotes arrive):
    # Specifically, if S6.6 quotes come back C-class (~$67k/chain = $3.75M+ for 56 chains), engineer switches
    # architecture or increases Ql/reduces channels; expected saving from learning B vs C early:
    s66_total = driver_samples["S6.6 Okuma Zinciri (56x B/C Duvarı)"]
    s66_excess_if_c = float(np.mean(s66_total[bc_regime_C]) - np.mean(s66_total[~bc_regime_C]))
    # Even at a modest 25% mitigation efficacy when discovered pre-procurement, value of RFQ info:
    rfq_info_value_est = 0.20 * (0.25 * s66_excess_if_c) + 0.15 * float(np.std(rfq_cost_samples))

    # -------------------------------------------------------------------------
    # 7. Score Pre-Registered Verdicts (CU1-CU6)
    # -------------------------------------------------------------------------
    verdicts = {
        "CU1_bom_integrity": bool(
            sha_ok
            and gate_ok
            and len(df) >= 120
            and len(missing_canon) == 0
            and reconcil_err < 1e-6
            and delta_bridge["bridge_arithmetic_error_usd"] < 1e-6
        ),
        "CU2_bom_cap_safety": bool(p_bom_gt_50m < 0.001 and np.percentile(bom_samples, 95) < 15e6),
        "CU3_program_soft_hard_cap": bool(p_prog_stoch_gt_100m < 0.05 and p_prog_stoch_gt_50m < 0.30),
        "CU3_base_v5_program_soft_hard_cap": bool(p_base_prog_stoch_gt_100m < 0.05 and p_base_prog_stoch_gt_50m < 0.30),
        "CU3_base_plus_safety_program_soft_hard_cap": bool(p_base_saf_prog_stoch_gt_100m < 0.05 and p_base_saf_prog_stoch_gt_50m < 0.30),
        "CU3_v6_full_program_soft_hard_cap": bool(p_v6_full_prog_stoch_gt_100m < 0.05 and p_v6_full_prog_stoch_gt_50m < 0.30),
        "CU4_bc_wall_dominance": bool(top3_bom_var_share >= 0.50 and rfq10_nom_share >= 0.75),
        "CU5_evpi_20mk_vindication": bool(cu5_env_1mach < 0.0 and cu5_n_be_hw >= 4.0),
        "CU6_mc_convergence": bool(conv_p50_rel <= 0.01 and conv_p95_rel <= 0.01 and se_p100 < 0.001),
    }
    verdicts["success"] = bool(
        verdicts["CU1_bom_integrity"]
        and verdicts["CU2_bom_cap_safety"]
        and verdicts["CU6_mc_convergence"]
    )

    # Empirical CDF curves (exact quantiles from 100k MC for PyCairo rendering)
    cdf_probs = sorted(set(
        [round(p, 4) for p in np.linspace(0.005, 0.995, 199).tolist()]
        + [0.001, 0.002, 0.998, 0.999]
    ))
    cdf_curves = {
        "probs": cdf_probs,
        "bom_usd": [float(v) for v in np.percentile(bom_samples, [p * 100 for p in cdf_probs])],
        "prog_x3_usd": [float(v) for v in np.percentile(prog_x3, [p * 100 for p in cdf_probs])],
        "prog_stoch_usd": [float(v) for v in np.percentile(prog_stoch, [p * 100 for p in cdf_probs])],
        "prog_stoch_v5_base_usd": [float(v) for v in np.percentile(prog_stoch_v5_base, [p * 100 for p in cdf_probs])],
        "prog_stoch_base_plus_safety_usd": [float(v) for v in np.percentile(prog_stoch_base_plus_safety, [p * 100 for p in cdf_probs])],
        "prog_x10_usd": [float(v) for v in np.percentile(prog_x10, [p * 100 for p in cdf_probs])],
    }

    out = {
        "experiment": "exp128_bom_sensitivity",
        "predictions": pred,
        "canonical_gate": {
            "bom_csv_sha256": bom_sha,
            "sha256_matches_expected": sha_ok,
            "bom_csv_rows": len(canon_rows),
            "nl55_b_frac": g55["golden_frac"],
            "nl55_b_abs": g55["abs_units"],
            "nl163_b_usd_u720": g163_b["golden_units"] * 720.0,
            "nl163_central_usd_u720": exp122_central_usd,
            "nl163_c_usd_u1600_ct1": g163_c["golden_units"] * 1600.0,
            "ct2_x10_central_usd": exp122_central_usd * 10.0,
            "gate_ok": gate_ok,
        },
        "bom_detailed_summary": {
            "bom_version": "v7.0",
            "total_parts": int(len(df)),
            "v5_base_parts": int((~v6_mask_all & ~v7_safety_mask).sum()),
            "v6_option_parts": int(v6_mask_all.sum()),
            "v7_safety_parts": int(v7_safety_mask.sum()),
            "priced_parts": int(K),
            "software_zero_hw_parts": int((df["subsystem"] == "S8").sum()),
            "superseded_zero_hw_parts": int(df["notes"].astype(str).str.contains("SUPERSEDED-BY-V5.0", na=False).sum()),
            "canonical_ids_covered": len(canonical_ids),
            "extra_delta_parent_ids": sorted(covered_ids - canonical_ids),
            "m3_v3_base_nom_usd": m3_v3_base_nom,
            "m3_v4_base_nom_usd": m3_v4_base_nom,
            "v4_delta_nom_usd": v4_original_gross_nom,
            "v5_gross_new_low_usd": v5_gross_low,
            "v5_gross_new_nom_usd": v5_gross_nom,
            "v5_gross_new_high_usd": v5_gross_high,
            "v5_anti_double_count_credit_usd": -v5_credit_nom,
            "v5_net_delta_nom_usd": v5_net_delta_nom,
            "m3_v5_base_low_usd": m3_v5_base_low,
            "m3_v5_base_nom_usd": m3_v5_base_nom,
            "m3_v5_base_high_usd": m3_v5_base_high,
            "m3_v5_pilot_256_nom_usd": m3_v5_pilot_256_nom,
            "v6_option_q_low_usd": v6_optq_low,
            "v6_option_q_nom_usd": v6_optq_nom,
            "v6_option_q_high_usd": v6_optq_high,
            "v6_option_hpc_low_usd": v6_opthpc_low,
            "v6_option_hpc_nom_usd": v6_opthpc_nom,
            "v6_option_hpc_high_usd": v6_opthpc_high,
            "v6_net_delta_low_usd": v6_net_delta_low,
            "v6_net_delta_nom_usd": v6_net_delta_nom,
            "v6_net_delta_high_usd": v6_net_delta_high,
            "m3_v6_plus_option_q_nom_usd": m3_v6_plus_optq_nom,
            "m3_v6_plus_option_hpc_nom_usd": m3_v6_plus_opthpc_nom,
            "m3_v6_full_nom_usd": m3_v6_full_nom,
            "v7_safety_low_usd": v7_safety_low,
            "v7_safety_nom_usd": v7_safety_nom,
            "v7_safety_high_usd": v7_safety_high,
            "m3_base_plus_safety_nom_usd": m3_base_plus_safety_nom,
            "m3_v7_safety_certified_full_nom_usd": m3_nom,
            "m1_plus_safety_nom_usd": m1_plus_safety_nom,
            "m3_low_usd": m3_low,
            "m3_nom_usd": m3_nom,
            "m3_high_usd": m3_high,
            "m1_low_usd": m1_low,
            "m1_nom_usd": m1_nom,
            "m1_high_usd": m1_high,
            "m1_to_m3_nom_ratio": m1_nom / m3_nom,
            "m1_to_m3_base_nom_ratio": m1_nom / m3_v5_base_nom,
            "s66_exp114_56chain_nom_usd": s66_chain6_nom,
            "s68_dr_nom_usd": s68_dr_nom,
            "reconciliation_error_usd": reconcil_err,
        },
        "v5_hardware_mass_reconciliation": v5_hardware_mass_reconciliation,
        "v6_hardware_mass_reconciliation": v6_hardware_mass_reconciliation,
        "v7_hardware_mass_reconciliation": v7_hardware_mass_reconciliation,
        "v6_modular_mc_comparison": v6_modular_mc_comparison,
        "v7_modular_mc_comparison": v7_modular_mc_comparison,
        "v5_scaling_10k_cryostat_note": s65_spec["scaling_10000_cell_note"],
        "v5_fab_tco_5yr_context": {
            "fab_tool_n1_5yr_tco_no_wafers_usd": pct_summary(v5_fab_tco5),
            "foak_program_5yr_tco_no_wafers_usd": pct_summary(v5_foak_tco5),
            "P_foak_5yr_tco_gt_50M": float(np.mean(v5_foak_tco5 > 50e6)),
            "P_foak_5yr_tco_gt_100M": float(np.mean(v5_foak_tco5 > 100e6)),
        },
        "subsystem_reconciliation": sub_reconcil,
        "delta_bridge_exp122_to_detailed": delta_bridge,
        "delta_buckets": delta_buckets,
        "rfq_coverage": {
            "packages": rfq_summary,
            "rfq6_total_nom_usd": rfq6_nom,
            "rfq6_nom_share": rfq6_nom_share,
            "rfq6_variance_share_mc": rfq6_var_share,
            "rfq7_total_nom_usd": rfq7_nom,
            "rfq7_nom_share": rfq7_nom_share,
            "rfq7_variance_share_mc": rfq7_var_share,
            "rfq8_total_nom_usd": rfq8_nom,
            "rfq8_nom_share": rfq8_nom_share,
            "rfq8_nom_share_of_v5_base": rfq8_nom_share_of_v5_base,
            "rfq8_variance_share_mc": rfq8_var_share,
            "rfq9_total_nom_usd": rfq9_nom,
            "rfq9_nom_share": rfq9_nom_share,
            "rfq9_nom_share_of_v6_full": rfq9_nom_share_of_v6_full,
            "rfq9_variance_share_mc": rfq9_var_share,
            "rfq10_total_nom_usd": rfq10_nom,
            "rfq10_nom_share": rfq10_nom_share,
            "rfq10_variance_share_mc": rfq10_var_share,
        },
        "monte_carlo_model_a_detailed": {
            "n_samples": N,
            "seed": 2026128,
            "correlation_params": {"rho_macro": 0.25, "rho_same_sub": 0.55, "rho_both_rd": 0.45},
            "bc_shock_prob": 0.20,
            "nl_band": [110, 163],
            "m_prog_percentiles": pct_summary(m_prog_samples),
            "bom_pure_no_bc_shock_usd": pct_summary(bom_no_bc_shock),
            "bom_with_bc_and_nl_usd": pct_summary(bom_samples),
            "program_x3_usd": pct_summary(prog_x3),
            "program_stochastic_3_to_10_usd": pct_summary(prog_stoch),
            "program_x10_usd": pct_summary(prog_x10),
            "exceedance_probabilities": {
                "P_BOM_gt_50M": p_bom_gt_50m,
                "P_BOM_gt_100M": p_bom_gt_100m,
                "P_Program_x3_gt_50M": p_prog_x3_gt_50m,
                "P_Program_x3_gt_100M": p_prog_x3_gt_100m,
                "P_Program_stoch_gt_50M": p_prog_stoch_gt_50m,
                "P_Program_stoch_gt_100M": p_prog_stoch_gt_100m,
                "P_Program_x10_gt_50M": p_prog_x10_gt_50m,
                "P_Program_x10_gt_100M": p_prog_x10_gt_100m,
                "SE_P_Program_stoch_gt_100M": se_p100,
            },
            "convergence_50k_vs_100k": {
                "half_p50_usd": half_p50,
                "full_p50_usd": full_p50,
                "rel_diff_p50": conv_p50_rel,
                "half_p95_usd": half_p95,
                "full_p95_usd": full_p95,
                "rel_diff_p95": conv_p95_rel,
            },
        },
        "monte_carlo_model_b_canonical_plus_deltas": {
            "n_samples": N,
            "canonical_bom_only_usd": pct_summary(canon_bom_only_mc),
            "canonical_plus_deltas_bom_usd": pct_summary(model_b_bom_mc),
            "canonical_plus_deltas_prog_stoch_usd": pct_summary(model_b_prog_stoch),
            "exceedance_probabilities": {
                "P_BOM_gt_50M": float(np.mean(model_b_bom_mc > 50e6)),
                "P_Program_stoch_gt_50M": float(np.mean(model_b_prog_stoch > 50e6)),
                "P_Program_stoch_gt_100M": float(np.mean(model_b_prog_stoch > 100e6)),
            },
        },
        "tornado_bom_scope": tornado_bom,
        "tornado_program_scope": tornado_prog,
        "top3_bom_var_share_s66_s68_s2": top3_bom_var_share,
        "cdf_curves": cdf_curves,
        "evpi_20mk_vs_1k": {
            "s68_20mk_dr_mc_mean_usd": float(np.mean(s68_samples)),
            "s68_1k_stage_mc_mean_usd": float(np.mean(s68_1k_samples)),
            "expected_hw_saving_per_machine_usd": e_delta_hw,
            "median_hw_saving_per_machine_usd": med_delta_hw,
            "expected_prog2x_saving_per_machine_usd": e_delta_prog_1mach,
            "cu5_ref_1mach_2M_p50_env_usd": cu5_env_1mach,
            "cu5_ref_breakeven_machines_hw": cu5_n_be_hw,
            "s66_c_vs_b_expected_excess_usd": s66_excess_if_c,
            "rfq6_estimated_info_value_usd": rfq_info_value_est,
            "grid": evpi_table,
        },
        "verdicts": verdicts,
        "epistemic_caveat": (
            "No real supplier quotes or laboratory measurements exist. All USD numbers are anchored to "
            "Exp114 public listings ({Liste-Çapası}), Exp114 $720/unit class calibration ({Model-Kalibrasyon-Exp114}), "
            "or labeled engineering assumptions ({Varsayım}). Program multipliers (x3-x10) are labeled assumptions "
            "covering cleanroom/facility, integration labor, R&D salaries, and contingency."
        ),
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
    }

    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== EXP128 v7.0 MONTE CARLO & RECONCILIATION COMPLETE ===")
    print(f"Canonical Gate OK: {gate_ok} | BOM.csv SHA-256 OK: {sha_ok}")
    print(f"M3 v5.0 Base   : nom=${m3_v5_base_nom/1e6:.3f}M (167p) | Base+Safety=${m3_base_plus_safety_nom/1e6:.3f}M (173p) | v6 Full=${m3_v6_full_nom/1e6:.3f}M (174p) | v7 Full=${m3_nom/1e6:.3f}M (180p)")
    print(f"M1 Base Proto  : nom=${m1_nom/1e6:.3f}M (M1+Safety=${m1_plus_safety_nom/1e6:.3f}M) | Pilot 256c: ${m3_v5_pilot_256_nom/1e6:.3f}M")
    print(f"10-RFQ Coverage: {rfq10_nom_share:.1%} of M3 v7 Full (${rfq10_nom/1e6:.3f}M; 9-RFQ/v6Full={rfq9_nom_share_of_v6_full:.1%}) | {rfq10_var_share:.1%} of BOM MC variance")
    print("Modular 100k MC Comparison (Common Random Numbers — 6 Configs):")
    for cname, cdata in v7_modular_mc_comparison.items():
        print(
            f"  {cname:30s}: nom=${cdata['bom_nom_usd']/1e6:.3f}M | BOM P50=${cdata['bom_mc_usd']['p50']/1e6:.2f}M | "
            f"Prog P50=${cdata['program_stoch_usd']['p50']/1e6:.2f}M | P(>50M)={cdata['P_Program_stoch_gt_50M']:.4f} | "
            f"P(>100M)={cdata['P_Program_stoch_gt_100M']:.4f} | Fab5y=${cdata['fab_tool_n1_5yr_tco_no_wafers_usd']['p50']/1e6:.2f}M | "
            f"FOAK5y=${cdata['foak_program_5yr_tco_no_wafers_usd']['p50']/1e6:.2f}M (P>100M={cdata['P_foak_5yr_tco_gt_100M']:.4f})"
        )
    print(f"Model A Full   : BOM P50=${np.percentile(bom_samples,50)/1e6:.2f}M | P90=${np.percentile(bom_samples,90)/1e6:.2f}M | P95=${np.percentile(bom_samples,95)/1e6:.2f}M | P(>50M)={p_bom_gt_50m:.5f}")
    print(f"Model A ProgSt : P50=${full_p50/1e6:.2f}M | P90=${np.percentile(prog_stoch,90)/1e6:.2f}M | P95=${full_p95/1e6:.2f}M | P(>50M)={p_prog_stoch_gt_50m:.4f} | P(>100M)={p_prog_stoch_gt_100m:.4f}")
    print(f"Model A Progx10: P50=${np.percentile(prog_x10,50)/1e6:.2f}M | P90=${np.percentile(prog_x10,90)/1e6:.2f}M | P(>50M)={p_prog_x10_gt_50m:.4f} | P(>100M)={p_prog_x10_gt_100m:.4f}")
    print(f"Model B ProgSt : P50=${np.percentile(model_b_prog_stoch,50)/1e6:.2f}M | P(>50M)={np.mean(model_b_prog_stoch>50e6):.4f} | P(>100M)={np.mean(model_b_prog_stoch>100e6):.4f}")
    print(f"Convergence    : dP50={conv_p50_rel:.4%}, dP95={conv_p95_rel:.4%}, SE(P>100M)={se_p100:.5f}")
    print(f"Top-3 BOM var (S6.6+S6.8+S2): {top3_bom_var_share:.1%}")
    print("Top-7 BOM Tornado Drivers:")
    for d in tornado_bom[:7]:
        print(f"  - {d['driver']:42s} | var={d['variance_contrib_share']:5.1%} | rho={d['spearman_rho']:.3f} | swing=${d['cond_bom_swing_usd']/1e6:.2f}M")
    print(f"20mK vs 1K EVPI: E[dHW]=${e_delta_hw/1e3:.1f}k/mach | CU5 ENV(1m,$2M,p=0.5)=${cu5_env_1mach/1e6:+.2f}M | N_be={cu5_n_be_hw:.2f} mach")
    print("VERDICTS:", verdicts)


if __name__ == "__main__":
    main()
