"""Main execution script for Exp150 (H168): Industrial Safety, HAZOP, 25-Row FMEA & Lab Safety Kit.

Generates:
  - results/exp150_industrial_safety_fmea_hazop/exp150.json
  - results/exp150_industrial_safety_fmea_hazop/s_safety_spec.json
  - results/exp150_industrial_safety_fmea_hazop/summary_exp150.md
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.exp150_industrial_safety_fmea_hazop.fmea_hazop150 import (
    build_fmea_25_rows,
    build_hazop_10_nodes,
    build_safety_hardware_spec,
)
from experiments.exp150_industrial_safety_fmea_hazop.safety_physics150 import (
    analyze_cryo_odh_and_quench,
    analyze_epo_ups_shutdown,
    analyze_hv_and_xray_safety,
    analyze_laser_safety,
    analyze_ph3_and_gas_safety,
    load_upstream_anchors,
)

RES_DIR = ROOT / "results/exp150_industrial_safety_fmea_hazop"


def evaluate_preregistered_criteria(
    laser: dict[str, Any],
    gas: dict[str, Any],
    hvx: dict[str, Any],
    cryo: dict[str, Any],
    epo: dict[str, Any],
    fmea_stats: dict[str, Any],
    hazop_nodes: list[dict[str, Any]],
    safety_spec: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    sf1_pass = (
        laser["nohd_collimated_20mrad_m"] > 100.0
        and laser["nhz_diffuse_m"] > 10.0
        and 6.3 <= laser["od_required_4pulse_wafer"] <= 6.8
        and laser["od_sweep"]["OD8"]["ratio_to_4pulse_MPE_at_wafer"] < 0.05
        and laser["interlock_sil3"]["shutter_close_ms"] <= 5.0
        and laser["interlock_sil3"]["pfd_avg_1oo2d"] < 1e-3
    )
    sf2_pass = (
        gas["unmitigated_hp_cylinder"]["room_60m3_peak_ppm"] > 50.0
        and gas["mitigated_sds_system"]["operator_conservative_ppm"] < 0.01
        and gas["mitigated_sds_system"]["margin_below_tlv_twa"] >= 5.0
        and gas["mitigated_sds_system"]["margin_below_idlh"] >= 5000.0
        and gas["forming_gas_s56"]["intrinsically_nonflammable_in_air"] is True
    )
    e22 = hvx["energy_sweep"]["22keV"]
    crow = hvx["hv_crowbar"]
    sf3_pass = (
        e22["wall_6mm_316L_uSv_h"] < 1e-6
        and e22["s55_sapphire_plus_3mm_steel_shroud_uSv_h"] < 0.01
        and crow["stored_energy_10kV_J"] < 0.5
        and crow["stored_energy_22kV_J"] < 0.5
        and crow["discharge_to_50V_22kV_ms"] < 50.0
    )
    sf4_pass = (
        cryo["helium_odh"]["room_sweep"]["60m3"]["dry_ld400_pt420_O2_pct"] > 20.5
        and cryo["asme_ovc_relief"]["relief_safety_margin"] >= 10.0
        and cryo["magnet_quench_exp125"]["dump_resistor_peak_1p5T_C"] < 55.0
        and cryo["magnet_quench_exp125"]["T_hotspot_K"] < 150.0
    )
    sf5_pass = (
        epo["ups_spec"]["transfer_time_ms"] == 0.0
        and epo["uhv_isolation"]["gate_valve_close_ms"] <= 100.0
        and epo["uhv_isolation"]["wafer_oxidation_ML"] < 0.01
        and epo["ups_spec"]["runtime_at_rated_13p5kW_min"] >= 30.0
        and epo["ups_spec"]["runtime_tier1_min"] >= 180.0
    )
    sf6_pass = (
        fmea_stats["n_rows"] == 25
        and len(hazop_nodes) >= 10
        and fmea_stats["max_rpn_pre"] >= 240
        and fmea_stats["max_rpn_post"] <= 60
        and fmea_stats["mean_rpn_reduction_pct"] >= 75.0
    )
    tot = safety_spec["totals"]
    sf7_pass = (
        tot["n_items"] == 6
        and tot["total_mass_kg"] > 0.0
        and tot["cryo_load_W"] == 0.0
        and tot["pct_of_m3_v6_full_bom"] <= 5.0
        and safety_spec["no_supplier_quotes"] is True
    )

    return {
        "SF1_class4_808nm_laser_enclosure_and_sil3_shutter": {
            "pass": bool(sf1_pass),
            "observed": {
                "NOHD_collimated_m": laser["nohd_collimated_20mrad_m"],
                "NHZ_diffuse_m": laser["nhz_diffuse_m"],
                "OD_required_4pulse": laser["od_required_4pulse_wafer"],
                "residual_ratio_OD8": laser["od_sweep"]["OD8"]["ratio_to_4pulse_MPE_at_wafer"],
                "shutter_close_ms": laser["interlock_sil3"]["shutter_close_ms"],
                "sil3_pfd_avg": laser["interlock_sil3"]["pfd_avg_1oo2d"],
            },
        },
        "SF2_ph3_sds_subatmospheric_and_forming_gas_safety": {
            "pass": bool(sf2_pass),
            "observed": {
                "unmitigated_peak_ppm": gas["unmitigated_hp_cylinder"]["room_60m3_peak_ppm"],
                "mitigated_operator_ppm": gas["mitigated_sds_system"]["operator_conservative_ppm"],
                "tlv_margin": gas["mitigated_sds_system"]["margin_below_tlv_twa"],
                "idlh_margin": gas["mitigated_sds_system"]["margin_below_idlh"],
                "forming_gas_nonflammable": gas["forming_gas_s56"]["intrinsically_nonflammable_in_air"],
            },
        },
        "SF3_hv_bremsstrahlung_xray_and_crowbar": {
            "pass": bool(sf3_pass),
            "observed": {
                "dose_6mm_316L_22keV_uSv_h": e22["wall_6mm_316L_uSv_h"],
                "dose_s55_shrouded_22keV_uSv_h": e22["s55_sapphire_plus_3mm_steel_shroud_uSv_h"],
                "hv_stored_energy_10kV_J": crow["stored_energy_10kV_J"],
                "hv_stored_energy_22kV_J": crow["stored_energy_22kV_J"],
                "hv_crowbar_50V_ms": crow["discharge_to_50V_22kV_ms"],
            },
        },
        "SF4_cryo_he_odh_rupture_disk_and_quench": {
            "pass": bool(sf4_pass),
            "observed": {
                "cleanroom_60m3_O2_pct": cryo["helium_odh"]["room_sweep"]["60m3"]["dry_ld400_pt420_O2_pct"],
                "dn50_relief_margin": cryo["asme_ovc_relief"]["relief_safety_margin"],
                "dump_resistor_peak_C": cryo["magnet_quench_exp125"]["dump_resistor_peak_1p5T_C"],
                "exp125_hotspot_K": cryo["magnet_quench_exp125"]["T_hotspot_K"],
            },
        },
        "SF5_epo_ups_15kva_safe_shutdown": {
            "pass": bool(sf5_pass),
            "observed": {
                "ups_transfer_ms": epo["ups_spec"]["transfer_time_ms"],
                "uhv_gate_valve_close_ms": epo["uhv_isolation"]["gate_valve_close_ms"],
                "wafer_oxidation_ML": epo["uhv_isolation"]["wafer_oxidation_ML"],
                "full_load_runtime_min": epo["ups_spec"]["runtime_at_rated_13p5kW_min"],
                "tier1_runtime_min": epo["ups_spec"]["runtime_tier1_min"],
            },
        },
        "SF6_25row_fmea_and_hazop_closure": {
            "pass": bool(sf6_pass),
            "observed": {
                "n_fmea_rows": fmea_stats["n_rows"],
                "n_hazop_nodes": len(hazop_nodes),
                "max_rpn_pre": fmea_stats["max_rpn_pre"],
                "max_rpn_post": fmea_stats["max_rpn_post"],
                "mean_rpn_reduction_pct": fmea_stats["mean_rpn_reduction_pct"],
            },
        },
        "SF7_safety_kit_spec_ready_for_bom_v7": {
            "pass": bool(sf7_pass),
            "observed": {
                "n_items": tot["n_items"],
                "total_mass_kg": tot["total_mass_kg"],
                "cryo_load_W": tot["cryo_load_W"],
                "pct_of_m3_v6_full": tot["pct_of_m3_v6_full_bom"],
                "no_supplier_quotes": safety_spec["no_supplier_quotes"],
            },
        },
    }


def _safe_cell(text: str) -> str:
    """Guarantee zero unescaped ASCII pipe chars inside GFM table cells."""
    return str(text).replace("|", "‖")


def render_summary_md(payload: dict[str, Any]) -> str:
    las = payload["hazard_1_laser_s55"]
    gas = payload["hazard_2_ph3_and_forming_gas"]
    hvx = payload["hazard_3_hv_and_xray"]
    cryo = payload["hazard_4_cryo_odh_and_quench"]
    epo = payload["hazard_5_epo_ups_shutdown"]
    fmea = payload["fmea_25_rows"]
    fstat = payload["fmea_summary"]
    hazop = payload["hazop_10_nodes"]
    spec = payload["s_safety_spec"]
    verdicts = payload["preregistered_verdicts"]
    il = las["interlock_sil3"]
    pfd_sw = il["pfd_sensitivity_sweep"]
    n_pass = sum(1 for v in verdicts.values() if v["pass"])

    lines: list[str] = [
        "# Exp150 (`H168`): Ön Emniyet Tasarım Hedefi, HAZOP, 25-Satırlı FMEA & `S7.SAFETY` Kiti Taslağı (Sertifikasız `M0`)",
        "",
        f"- **Tarih:** {payload['date']}  ",
        f"- **Hipotez:** `H168` (`Exp150_industrial_safety_fmea_hazop`, `v7.0` / `v7.2`)  ",
        f"- **Ön-Kayıtlı Model Kriter Kararı:** **{n_pass}/{len(verdicts)} PASS** (`{payload['overall_verdict']}`, yazılım/analitik model kontrolü)  ",
        f"- **Sertifikasyon Durumu:** `{payload['certification_status']}` — `iec61508_certified = {str(payload['iec61508_certified']).lower()}`, `semi_s2_certified = {str(payload['semi_s2_certified']).lower()}`, `sil3_pfd_band_met_at_nominal_assumed_lambda_du = {str(payload['sil3_pfd_band_met_at_nominal_assumed_lambda_du']).lower()}`, `requires_third_party_assessment = {str(payload['requires_third_party_assessment']).lower()}`  ",
        "- **Epistemik Durum:** `{Model}`, `{Analitik}`, `{Literatür}`, `{Varsayım}` — `TRL 1–2 (M0)`, `no_lab_measurement = true`, `no_supplier_quotes = true`.",
        "",
        "> [!NOTE]",
        "> **Epistemik ve Sertifikasyon Sınırı (Zorunlu Beyan):** Bu belge Python tabanlı bir **`M0` ön FMEA/HAZOP tasarım taramasıdır**; herhangi bir sertifikasyon veya uygunluk beyanı değildir (`iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`). **SEMI, kendi `SEMI S2` kılavuzu için sertifikasyon vermez** (üçüncü-taraf saha değerlendirmesi gerekir). Benzer biçimde **`IEC 61508 SIL-3`**, FMEA/RPN puanı düşürülerek veya varsayılan bir `λ_DU` ile tek-nokta PFD hesaplanarak kazanılan bir etiket olmayıp tam emniyet yaşam döngüsü, donanım mimari kısıtları (`HFT`, `SFF`), tedarikçi FMEDA verisi, sistematik yetkinlik ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. Aşağıdaki tablolarda yer alan `SIL-3`, `SIL-2` ve `SIL-1` sınıfları yalnızca **hedeflenen emniyet düzeyini (`tasarım hedefi`)** belirtir; sertifikasyon iddiası değildir.",
        "",
        "## 1. Yönetici Özeti ve Ön-Kayıtlı Model Kriterleri (`SF1–SF7`)",
        "",
        "Atom Litografi Makinesi kavramsal tasarımı (`CAD v6.0`, `M3 v6.0 Full BOM = $5,547,800`), temizoda senaryosunda beş kritik mühendislik tehlikesi için ön koruma hedefleri tanımlar: (1) `S5.5` Sınıf-4 `808 nm` `43,49 J/cm²` qCW flaş lazer, (2) `S1.1` zehirli/piroforik `PH₃` fosfin ve `S5.6` `%5 H₂/N₂` pasivasyon gazı, (3) `10–22 keV` yüksek gerilim ve Bremsstrahlung X-ışını, (4) `20 mK / 4 K` kriyojenik Helyum ODH (statik + oda kutu-ODE geçişi) + `ASME 0,5 barg` OVC tahliye + `Exp125` `18,94 kJ` mıknatıs quench, (5) plansız elektrik kesintisi (`EPO` / `15 kVA` çevrimiçi UPS). Parametrik `S7.SAFETY-01..06` ön tasarım kiti (`355,0 kg`, `1.090 W`, `0,0 W` kriyo yükü, `$145.000` nominal = `M3 v6.0` BOM'un `%2,61`'i, `no_supplier_quotes = true`) modellendiğinde `25` satırlı ön FMEA taramasındaki maksimum risk puanı `RPN_pre = 280` değerinden **`RPN_post = 42 ≤ 60`** tasarım hedefine (ortalama `%" + f"{fstat['mean_rpn_reduction_pct']:.1f}" + "` azalma, `0` artık risk `> 60`) inmektedir.",
        "",
        "| Kriter | Kapsam | Gözlenen Değerler | Karar |",
        "|---|---|---|---|",
    ]
    for cid, cval in verdicts.items():
        obs_str = ", ".join(f"`{k}={v}`" for k, v in cval["observed"].items())
        badge = "**PASS**" if cval["pass"] else "**FAIL**"
        lines.append(f"| `{cid}` | Ön-kayıtlı emniyet eşiği | {_safe_cell(obs_str)} | {badge} |")

    lines += [
        "",
        "## 2. Beş Kritik Tehlike Alanının İndirgenmiş-Mertebe Analitik Taraması",
        "",
        "### 2.1. Tehlike-1: `S5.5` Sınıf-4 `808 nm` Flaş Lazer (`ANSI Z136.1-2022` / `IEC 60825-1` Referansı)",
        "",
        f"- **Çapalı Kaynak (`Exp130`/`Exp139`/`CAD v6.0`):** `λ = {las['wavelength_nm']} nm`, `t = {las['pulse_duration_ms']} ms`, yonga fluansı `{las['wafer_fluence_J_cm2']} J/cm²` (`16×16 mm` = `{las['wafer_pulse_energy_J']} J`, kaynak `{las['source_pulse_energy_J']} J`, tepe güç `{las['source_peak_power_kW']} kW`), AR safir pencere fluansı `{las['window_fluence_AR_J_cm2']} J/cm²` (`8,96×` LIDT marjı).",
        f"- **MPE ve Tehlike Mesafeleri (`C_A = {las['ansi_C_A_808nm']}`):** Tek-darbe göz MPE = **`{las['mpe_eye_1pulse_uJ_cm2']} µJ/cm²`**, 4-darbe MPE (`C_P = 4^-0.25`) = **`{las['mpe_eye_4pulse_uJ_cm2']} µJ/cm²`**, deri MPE = `{las['mpe_skin_1pulse_J_cm2']} J/cm²`. Kolime (`20 mrad`) `NOHD =` **`{las['nohd_collimated_20mrad_m']} m`**, fiber demeti (`150 mrad`) `NOHD =` **`{las['nohd_fiber_150mrad_m']} m`**, Lambertian yaygın yansıma (`ρ=1`) `NHZ_diff =` **`{las['nhz_diffuse_m']} m`**.",
        f"- **Gerekli Optik Yoğunluk ve `1oo2D` Parametrik `PFD_avg` (Sertifikasız `M0`):** Gerekli `OD` tek-darbe `{las['od_required_1pulse_wafer']}`, 4-darbe **`{las['od_required_4pulse_wafer']}`** → `OD ≥ 7+` gerekir, tasarım hedefi **`OD = 8`** olarak belirlenmiştir (`OD8` artık fluans oranı `{las['od_sweep']['OD8']['ratio_to_4pulse_MPE_at_wafer']}× MPE << 1`). `IEC 61508-6` referans `1oo2D` çift-kanallı perde (`{il['shutter_close_ms']} ms` yay-dönüşlü mekanik bıçak + `<0,1 ms` diyot sürücü kesici) için varsayılan nominal `λ_DU = {il['nominal_assumptions']['lambda_du_per_h']:.2e} /h`, `T_i = {il['nominal_assumptions']['proof_test_interval_h']:.0f} h`, `β = {il['nominal_assumptions']['beta_ccf']*100:.0f}%` altında analitik `PFD_avg =` **`{il['pfd_avg_1oo2d']:.4e}`** `< 1e-3` (`sil3_pfd_band_met_at_nominal_assumed_lambda_du = true`, `iec61508_certified = false`; sertifikasyon değildir).",
        "",
        "| Optik Yoğunluk | Yonga Artık Fluans (J/cm²) | Pencere Artık Fluans (J/cm²) | 4-Darbe MPE Oranı | Pencere Güvenlik Marjı | Gömülü Class-1 Hedefi |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for odk, odv in las["od_sweep"].items():
        lines.append(
            f"| `{odk}` | `{odv['residual_wafer_J_cm2']:.3e}` | `{odv['residual_window_J_cm2']:.3e}` | `{odv['ratio_to_4pulse_MPE_at_wafer']:.5f}` | `{odv['margin_factor_at_window']}×` | `{'PASS' if odv['pass_class1_embedded'] else 'FAIL'}` |"
        )

    lines += [
        "",
        "#### 2.1.1. `1oo2D` Parametrik `PFD_avg` Belirsizlik ve Ortak-Neden (`λ_DU` × `β`) Duyarlılık Taraması",
        "",
        f"Nominal `λ_DU = {pfd_sw['lambda_du_nominal_per_h']:.2e} /h` varsayımı tedarikçi FMEDA ölçümü olmadığından, `λ_DU` çarpanı (`0,5× .. 25×`) ve ortak-neden arıza katsayısı (`β = 2%, 5%, 10%`) boyunca tam parametrik tarama yapılmıştır. Toplam `{pfd_sw['summary']['n_cases_total']}` durumun **`{pfd_sw['summary']['n_cases_in_sil3_pfd_band']}`** tanesi `SIL-3` PFD bandında (`< 1e-3`) kalırken, **`{pfd_sw['summary']['n_cases_degraded_to_sil2']}`** tanesi **`SIL-2` bandına (`1e-3 ≤ PFD < 1e-2`)** düşer — özellikle **`10× λ_DU` + `β = 10%`** kombinasyonunda (`PFD_avg = 1.2245e-03`) ve **`25× λ_DU`** düzeyinde tüm `β` değerlerinde `SIL-3` bandı kaybedilir.",
        "",
        "| `λ_DU` Çarpanı | `λ_DU` (/saat) | Tek-Kanal `PFD` | `β = 2%` `1oo2D PFD` (Bant) | `β = 5%` `1oo2D PFD` (Bant) | `β = 10%` `1oo2D PFD` (Bant) |",
        "|---:|---:|---:|---|---|---|",
    ]
    by_b = pfd_sw["by_beta"]
    for idx_m, mult in enumerate(pfd_sw["lambda_du_multipliers"]):
        r2 = by_b["beta_2pct"][idx_m]
        r5 = by_b["beta_5pct"][idx_m]
        r10 = by_b["beta_10pct"][idx_m]
        lines.append(
            f"| `{mult:g}×` | `{r2['lambda_du_per_h']:.2e}` | `{r2['pfd_single_channel']:.3e}` "
            f"| `{r2['pfd_avg_1oo2d']:.3e}` (`{r2['parametric_pfd_band']}`) "
            f"| `{r5['pfd_avg_1oo2d']:.3e}` (`{r5['parametric_pfd_band']}`) "
            f"| `{r10['pfd_avg_1oo2d']:.3e}` (`{r10['parametric_pfd_band']}`) |"
        )

    lines += [
        "",
        "| Ortak-Neden `β` | `SIL-3` PFD Bandı (`<1e-3`) Üst `λ_DU` Sınırı (/saat) | Nominal `λ_DU` Üzerinde İzin Verilen Maks. Çarpan |",
        "|---:|---:|---:|",
    ]
    for b_info in pfd_sw["sil3_band_boundaries_by_beta"].values():
        lines.append(
            f"| `{b_info['beta_ccf_pct']}%` | `{b_info['max_lambda_du_for_sil3_band_per_h']:.3e}` | `{b_info['max_multiplier_vs_nominal']:.2f}×` |"
        )

    hp = gas["unmitigated_hp_cylinder"]
    sds = gas["mitigated_sds_system"]
    fg = gas["forming_gas_s56"]
    lines += [
        "",
        "### 2.2. Tehlike-2: Zehirli/Piroforik `PH₃` Fosfin (`S1.1`) & `%5 H₂/N₂` Pasivasyon Gazı (`S5.6`)",
        "",
        f"- **Limitler:** `ACGIH TLV-TWA = 0,05 ppm`, `OSHA PEL = 0,30 ppm`, `NIOSH IDLH = 50,0 ppm` (ölümcül). L1 alarm = `0,02 ppm`, L2 SIL-3 hedef kapatma = `0,05 ppm`.",
        f"- **Kötü Senaryo (Önlemsiz `40 bar / 100 g` Basınçlı Silindir):** `Ø2 mm` boru kopmasında kritik boğulmalı akış `{hp['choked_flow_g_s']} g/s`, silindir `{hp['empty_time_s']} s` içinde boşalır ve `60 m³` (`20 ACH`) temizodada tepe derişim **`{hp['room_60m3_peak_ppm']} ppm`** (`IDLH`'nin **`{hp['idlh_exceedance_factor']}×`** katı — kesin ölümcül).",
        f"- **Önlemli Tasarım (`SDS <650 Torr / 10 g` + Vakum Ceket + `250 CFM` Scrubber + `0,02 ppm` SIL-3 hedefi):** Atmosfer-altı basınç nedeniyle kopmada dışarı advektif akış **0**'dır (hava içeri çekilir); yalnızca saf Fick moleküler difüzyonu (`{sds['sds_fickian_diff_mg_min']} mg/dk = {sds['sds_fickian_diff_sccm']} sccm`) oluşur. `250 CFM` gaz dolabı + `%99,9` kuru kimyasal scrubber + `12 s` SIL-3 hedef vana kesmesi altında `%2` kaçak fraksiyonlu dolap tepe oda derişimi `{sds['operator_peak_cabinet_fugitive_ppm']} ppm`, dolap bypass edilse bile doğrudan SDS difüzyon kararlı-hal oda derişimi **`{sds['operator_conservative_ppm']} ppm`** `< 0,01 ppm` kalır (`TLV-TWA` altında **`{sds['margin_below_tlv_twa']}×`**, `IDLH` altında **`{int(sds['margin_below_idlh'])}×`** güvenlik marjı).",
        f"- **`S5.6` `%5,0 H₂ / %95,0 N₂` Pasivasyon Gazı (`ISO 10156`):** `H₂` hacim oranı `{fg['h2_vol_pct']}% < {fg['iso10156_nonflammable_limit_pct']}%` (`ISO 10156 T_ci` sınırı) olduğundan havayla her seyreltmede **doğal olarak alevlenmez** (`intrinsically_nonflammable_in_air=true`).",
        "",
        "### 2.3. Tehlike-3: `10–22 keV` Yüksek Gerilim & Bremsstrahlung X-Işını (`Kramers` + `NIST XCOM`)",
        "",
        f"- **Muhafazakâr Varsayım:** `I_e = {hvx['assumptions']['leakage_electron_current_uA']} µA` geri-saçılan elektron akımı (nominal iyon demetinin `100×` katı), `Z = 42` (`Mo` elektrot), `r = 30 cm`, halk dozu limiti `1,0 µSv/h` (`ICRP 103`).",
        "- **Kritik Mühendislik Bulgusu (`S5.5` Safir Pencere):** `6 mm` muhafazakâr (`10 mm` gerçek `CAD v6.0`) `316L` paslanmaz çelik duvar `22 keV` Bremsstrahlung'u `1,06e-43 µSv/h` (`10 mm`'de `2,21e-73 µSv/h`) düzeyine bastırırken, **çıplak `8 mm` `Al₂O₃` safir pencere** düşük atom numarası nedeniyle `22 keV`'de **`10,11 µSv/h`** (`1,0 µSv/h` halk limitinin `10×` üstü!) sızdırır. Bu nedenle `S5.5` dışına eklenen **`3 mm` çelik `OD8` muhafaza kılıfı** çift-amaçlı (**Sınıf-4 Lazer + X-Işını**) zorunlu bariyerdir (`1,19e-23 µSv/h << 0,01 µSv/h`).",
        f"- **HV Aktif Crowbar (`IEC 61010-1` Referansı, `iec61010_certified=false`):** Toplam kaçak kapasitans `{hvx['hv_crowbar']['total_capacitance_nF']} nF`, depolanan enerji `10 kV`'da `{hvx['hv_crowbar']['stored_energy_10kV_J']} J`, `22 kV`'da **`{hvx['hv_crowbar']['stored_energy_22kV_J']} J < 0,50 J`**. `2 MΩ` aktif crowbar ile `22 kV → < 50 V` boşalım süresi **`{hvx['hv_crowbar']['discharge_to_50V_22kV_ms']} ms < 50 ms`** (analitik eşik `PASS`).",
        "",
        "| Enerji | Kalkan Yok (30 cm, µSv/h) | `6 mm` `316L` (µSv/h) | `10 mm` CAD `316L` (µSv/h) | Çıplak `8 mm` Safir (µSv/h) | `S5.5` Safir + `3 mm` Çelik Kılıf (µSv/h) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for ek, ev in hvx["energy_sweep"].items():
        lines.append(
            f"| `{ek}` | `{ev['unshielded_30cm_uSv_h']:.2f}` | `{ev['wall_6mm_316L_uSv_h']:.3e}` | `{ev['wall_10mm_cad_316L_uSv_h']:.3e}` | `{ev['s55_bare_sapphire_8mm_uSv_h']:.3e}` | `{ev['s55_sapphire_plus_3mm_steel_shroud_uSv_h']:.3e}` |"
        )

    odh = cryo["helium_odh"]
    rel = cryo["asme_ovc_relief"]
    qch = cryo["magnet_quench_exp125"]
    lines += [
        "",
        "### 2.4. Tehlike-4: `20 mK / 4 K` Kriyojenik Helyum ODH (Statik & Kutu-ODE), `ASME 0,5 barg` Tahliye & `Exp125` Quench",
        "",
        f"- **Kuru Kapalı-Çevrim Helyum ODH (`OSHA ≥ %19,5`):** `LD400` karışımı (`{odh['dr_mixture_stp_m3']} m³` STP) + `PT420` kompresör/hatları (`{odh['pt420_inventory_stp_m3']} m³` STP) + `%20` marj = **`{odh['total_with_20pct_margin_stp_m3']} m³` STP**. Tüm envanterin anlık salınımında `60 m³` temizodada oksijen oranı **`{odh['room_sweep']['60m3']['dry_ld400_pt420_O2_pct']}% >> %19,5`** kalır (aynı odada `100 L` ıslak sıvı Helyum kriyostatı `O₂ = {odh['room_sweep']['60m3']['wet_100L_LHe_comparison_O2_pct']}%` ile ölümcül boğulma yaratırdı). Yine de `15 m³` küçük servis odaları için duvara monteli `O₂` monitörü (`%19,5` alarm) zorunludur.",
        f"- **`ASME BPVC Sec VIII` / `CGA S-1.3` OVC Tahliye (Tam Saint-Venant İzentropik Subsonik Akış):** `0,50 barg` ayarlı (`+10%` UG-125 birikimle `0,55 barg`) tek **`DN50` patlama diski** (`250 K`) He kapasitesi `{rel['dn50_relief_capacity_he_kg_s']} kg/s` (paralel yaylı tahliye vanası ek `2×` yedeklik sağlar); analitik/fiziksel taşıma modeli en kötü He girişi (`PT420` `20 bar` `Ø2 mm` `50 K` kırığı + `LD400` `5 s` tam boşalım = `{rel['worst_case_he_inflow_kg_s']} kg/s`) karşısında **`{rel['relief_safety_margin_he']}×`**, `N₂` cryo-yoğuşma geri-buharlaşması (`{rel['worst_case_n2_inflow_kg_s']} kg/s` vs `{rel['dn50_relief_capacity_n2_kg_s']} kg/s`) karşısında **`{rel['relief_safety_margin_n2']}×`** (`≥ 10×`) güvenlik marjı sağlar.",
        f"- **`Exp125` 8-Bobin Mıknatıs Quench:** `1,50 T` tam alanda `{qch['E_mag_1p5T_kJ']} kJ` (`M4` `0,1785 T` modunda `{qch['E_mag_M4_0p1785T_kJ']} kJ`), `R_dump = {qch['R_dump_ohm']} Ω`, `τ = {qch['tau_decay_s']} s`, `V_max = {qch['V_max_V']} V`, bobin sıcak noktası `T_hotspot = {qch['T_hotspot_K']} K < 150 K`. Harici `{qch['dump_resistor_mass_kg']} kg` hava-soğutmalı boşaltma direnci yalnızca `ΔT = {qch['dump_resistor_dT_1p5T_K']} K` ısınarak **`{qch['dump_resistor_peak_1p5T_C']} °C < 55 °C`** güvenli dokunma eşiğinin altında kalır (`5 Gauss` sınırı `r < {qch['pacemaker_5gauss_radius_m']} m`).",
        "",
        "| Oda Hacmi | Kuru `LD400+PT420` `O₂` (%) | OSHA (`≥%19,5`) | Karşılaştırma: `100 L` Islak LHe `O₂` (%) |",
        "|---|---:|---|---:|",
    ]
    for rk, rv in odh["room_sweep"].items():
        lines.append(
            f"| `{rk}` | `{rv['dry_ld400_pt420_O2_pct']:.3f}%` | `{'PASS' if rv['dry_passes_osha_19p5pct'] else 'FAIL'}` | `{rv['wet_100L_LHe_comparison_O2_pct']:.2f}%` |"
        )

    lines += [
        "",
        "#### 2.4.1. Oda ODH Kutu-ODE Geçiş Analizi (RK4, `0–600 s`)",
        "",
        "| Senaryo | Oda (`m³`) | `ACH` | Salınım (`m³` STP / `s`) | Minimum `O₂` (%) | `t_min` (`s`) | `600 s` Sonu `O₂` (%) | `<%19,5` Süre (`s`) | OSHA |",
        "|---|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for sk, sv in odh["box_ode_transient"].items():
        lines.append(
            f"| `{sk}` | `{sv['room_volume_m3']:.0f}` | `{sv['ventilation_ach']:.0f}` "
            f"| `{sv['he_released_stp_m3']} / {sv['release_duration_s']:.0f}` "
            f"| `{sv['o2_min_pct']:.4f}%` | `{sv['t_at_o2_min_s']:.1f}` | `{sv['o2_final_600s_pct']:.4f}%` "
            f"| `{sv['time_below_osha_19p5pct_s']:.1f}` | `{'PASS' if sv['passes_osha_19p5pct'] else 'FAIL'}` |"
        )

    ups = epo["ups_spec"]
    uhv = epo["uhv_isolation"]
    lines += [
        "",
        "### 2.5. Tehlike-5: Plansız Güç Kesintisi (`EPO` / `15 kVA` Çevrimiçi UPS & Güvenli Kapanma)",
        "",
        f"- **`15 kVA / 10 kWh` LFP Online Double-Conversion UPS:** Geçiş süresi **`{ups['transfer_time_ms']} ms`**, nominal tam güçte (`{ups['rated_real_power_kW']} kW`) **`{ups['runtime_at_rated_13p5kW_min']} dk`** (`≥ 30 dk`), kritik Tier-1 güvenlik + UHV + kontrol yükünde (`{ups['tier1_safety_vacuum_kW']} kW`) **`{ups['runtime_tier1_min']} dk`** (`≥ 180 dk`).",
        f"- **Hızlı UHV İzolasyon & Yonga Koruma:** Yay-dönüşlü all-metal UHV sürgülü vanalar **`{uhv['gate_valve_close_ms']} ms`** (`≤ 100 ms`) içinde kapanır; `{uhv['surge_pressure_torr']:.1e} Torr` basınç dalgasında temiz `Si(100)` yonga oksitlenmesi yalnızca **`{uhv['wafer_oxidation_ML']:.3e} ML`** (`<< 0,01 ML`).",
        "",
        "| Zaman (`t`) | Alt-Sistem | Deterministik Güvenli Kapanma Eylemi |",
        "|---:|---|---|",
    ]
    for st in epo["shutdown_sequence"]:
        t_lbl = f"{st['t_ms']:.1f} ms" if st["t_ms"] < 1000.0 else f"{st['t_ms']/1000.0:.0f} s"
        lines.append(f"| `{t_lbl}` | `{st['subsystem']}` | {_safe_cell(st['action'])} |")

    lines += [
        "",
        "## 3. Tam 25-Satırlı Ön FMEA (`S × O × D = RPN`, Önlem Öncesi vs Sonrası — Sertifikasız `M0`)",
        "",
        f"- **Özet İstatistikler:** `25` satır, `RPN_pre`: ort. `{fstat['mean_rpn_pre']}`, maks. **`{fstat['max_rpn_pre']}`** (`FM-01`, `FM-10`); `RPN_post`: ort. `{fstat['mean_rpn_post']}`, maks. **`{fstat['max_rpn_post']} ≤ 60`** (`0` kabul edilemez artık risk), ortalama risk azalması **`%{fstat['mean_rpn_reduction_pct']}`**.",
        "",
        "| ID | Alt-Sistem | Hata Modu | Etki | `S/O/D` (Önce) | `RPN_pre` | Mühendislik Önlemi (`S7.SAFETY` Tasarım Hedefi) | `S/O/D` (Sonra) | `RPN_post` | Azalma | Hedef SIL (Sertifikasız) |",
        "|---|---|---|---|---|---:|---|---|---:|---:|---|",
    ]
    for r in fmea:
        lines.append(
            f"| `{r['id']}` | `{r['subsystem']}` | {_safe_cell(r['failure_mode'])} | {_safe_cell(r['effect'])} "
            f"| `{r['S_pre']}/{r['O_pre']}/{r['D_pre']}` | **{r['RPN_pre']}** | {_safe_cell(r['mitigation'])} "
            f"| `{r['S_post']}/{r['O_post']}/{r['D_post']}` | **{r['RPN_post']}** | `-{r['rpn_reduction_pct']}%` | `{r['target_sil']}` |"
        )

    lines += [
        "",
        "## 4. 10-Düğümlü Ön HAZOP Taraması (`IEC 61882` / `SEMI S2` Referansı — Sertifikasız `M0`)",
        "",
        "| Düğüm | Sistem | Kılavuz Sözcük | Sapma | Birincil Koruma Bariyeri (Tasarım Hedefi) | Hedef SIL (Sertifikasız) |",
        "|---|---|---|---|---|---|",
    ]
    for h in hazop:
        lines.append(
            f"| `{h['node']}` | {_safe_cell(h['system'])} | `{h['guideword']}` | {_safe_cell(h['deviation'])} | {_safe_cell(h['safeguard'])} | `{h['sil']}` |"
        )

    tot = spec["totals"]
    lines += [
        "",
        "## 5. Ön Emniyet Kiti Tasarım Taslağı (`s_safety_spec.json` — `BOM v7.0` Parametrik Paketi, Sertifikasız `M0`)",
        "",
        f"- **Toplam Kit Özeti (`S7.SAFETY-01..06`):** `{tot['n_items']}` kalem, toplam kütle **`{tot['total_mass_kg']} kg`**, elektrik gücü **`{tot['steady_electrical_power_W']} W`**, kriyojenik ısıl yük **`{tot['cryo_load_W']} W`**, parametrik bütçe aralığı **`${tot['cost_usd_low']:,} – ${tot['cost_usd_nom']:,} – ${tot['cost_usd_high']:,}`** (`M3 v6.0` Full BOM `$5,547,800`'ün **`%{tot['pct_of_m3_v6_full_bom']}`**'i). `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false` (`{{Varsayım}}` / `{{Liste-Capasi}}`).",
        "",
        "| Parça ID | Donanım Tanımı | Konum | Kütle (kg) | Güç (W) | Kriyo (W) | Maliyet Low / Nom / High (USD) | Hedef SIL | Epistemik |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for it in spec["items"]:
        lines.append(
            f"| `{it['part_id']}` | {_safe_cell(it['name'])} | {_safe_cell(it['location'])} "
            f"| `{it['mass_kg_total']:.1f}` | `{it['power_W_total']:.0f}` | `{it['cryo_load_W']:.1f}` "
            f"| `${it['cost_usd_low']:,} / ${it['cost_usd_nom']:,} / ${it['cost_usd_high']:,}` | `{it['sil_level']}` | `{{{it['epistemic_tag']}}}` |"
        )

    lines += [
        "",
        "## 6. Epistemik Sınırlar ve Kapsam Dışı Maddeler",
        "",
        "- Bu rapor indirgenmiş-mertebe analitik fizik modelleri (`{Model}` / `{Analitik}`), uluslararası emniyet standart/kılavuz referansları (`{Literatür}`) ve parametrik bütçe tahminlerine (`{Varsayım}`) dayanır (`TRL 1–2 / M0`).",
        "- **Sertifikasyon Yoktur (`PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED`):** `iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`. SEMI kendi `SEMI S2` kılavuzu için sertifika vermez; `IEC 61508 SIL-3` ise tam emniyet yaşam döngüsü, donanım mimari kısıtları (`HFT`, `SFF`), tedarikçi FMEDA verisi, sistematik yetkinlik ve bağımsız fonksiyonel emniyet değerlendirmesi gerektirir. Gerçek saha `X-ışını` dozimetri ölçümü, `PH₃` sızıntı kalibrasyonu, üçüncü-taraf `SEMI S2` / `IEC 61508` saha değerlendirmesi ve gerçek tedarikçi fiyat teklifleri (`no_lab_measurement=true`, `no_supplier_quotes=true`) laboratuvar kurulum fazında yapılmalıdır.",
        "- **Global Carbon & Hydrogen Kuralı:** Bu belge `Hydrogen` (yazar) çıktısıdır; kapanış onayı (`KABUL`) sıfır-bağlamlı **Carbon** denetimine tabidir.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    RES_DIR.mkdir(parents=True, exist_ok=True)
    prereg_path = RES_DIR / "predictions_exp150.json"
    if not prereg_path.exists():
        raise FileNotFoundError(f"Pre-registered predictions missing: {prereg_path}")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))

    anchors = load_upstream_anchors(ROOT)
    laser = analyze_laser_safety(anchors)
    gas = analyze_ph3_and_gas_safety()
    hvx = analyze_hv_and_xray_safety(anchors)
    cryo = analyze_cryo_odh_and_quench(anchors)
    epo = analyze_epo_ups_shutdown(anchors)

    fmea_rows = build_fmea_25_rows()
    hazop_nodes = build_hazop_10_nodes()
    safety_spec = build_safety_hardware_spec(anchors["m3_v6_full_bom_usd"])

    rpn_pre = [r["RPN_pre"] for r in fmea_rows]
    rpn_post = [r["RPN_post"] for r in fmea_rows]
    fmea_stats = {
        "n_rows": len(fmea_rows),
        "max_rpn_pre": max(rpn_pre),
        "min_rpn_pre": min(rpn_pre),
        "mean_rpn_pre": round(sum(rpn_pre) / len(rpn_pre), 1),
        "max_rpn_post": max(rpn_post),
        "min_rpn_post": min(rpn_post),
        "mean_rpn_post": round(sum(rpn_post) / len(rpn_post), 1),
        "mean_rpn_reduction_pct": round((1.0 - sum(rpn_post) / sum(rpn_pre)) * 100.0, 1),
        "n_unacceptable_pre_gt100": sum(1 for x in rpn_pre if x > 100),
        "n_unacceptable_post_gt60": sum(1 for x in rpn_post if x > 60),
        "sil_counts": {
            s: sum(1 for r in fmea_rows if r["target_sil"] == s)
            for s in ("SIL-3", "SIL-2", "SIL-1")
        },
    }

    verdicts = evaluate_preregistered_criteria(
        laser, gas, hvx, cryo, epo, fmea_stats, hazop_nodes, safety_spec
    )
    n_pass = sum(1 for v in verdicts.values() if v["pass"])
    must_pass = all(
        verdicts[k]["pass"]
        for k in (
            "SF1_class4_808nm_laser_enclosure_and_sil3_shutter",
            "SF2_ph3_sds_subatmospheric_and_forming_gas_safety",
            "SF3_hv_bremsstrahlung_xray_and_crowbar",
            "SF4_cryo_he_odh_rupture_disk_and_quench",
            "SF6_25row_fmea_and_hazop_closure",
        )
    )
    overall = "PASS" if (n_pass >= 6 and must_pass) else "FAIL"

    payload: dict[str, Any] = {
        "experiment": "exp150_industrial_safety_fmea_hazop",
        "hypothesis_id": "H168",
        "date": str(date.today()),
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "iec61508_certified": False,
        "semi_s2_certified": False,
        "certification_status": "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED",
        "sil3_pfd_band_met_at_nominal_assumed_lambda_du": bool(
            laser["interlock_sil3"]["sil3_pfd_band_met_at_nominal_assumed_lambda_du"]
        ),
        "requires_third_party_assessment": True,
        "overall_verdict": overall,
        "criteria_passed": f"{n_pass}/{len(verdicts)}",
        "preregistered_file": prereg["experiment"],
        "upstream_anchors": anchors,
        "preregistered_verdicts": verdicts,
        "hazard_1_laser_s55": laser,
        "hazard_2_ph3_and_forming_gas": gas,
        "hazard_3_hv_and_xray": hvx,
        "hazard_4_cryo_odh_and_quench": cryo,
        "hazard_5_epo_ups_shutdown": epo,
        "fmea_summary": fmea_stats,
        "fmea_25_rows": fmea_rows,
        "hazop_10_nodes": hazop_nodes,
        "s_safety_spec": safety_spec,
    }

    (RES_DIR / "exp150.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (RES_DIR / "s_safety_spec.json").write_text(json.dumps(safety_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (RES_DIR / "summary_exp150.md").write_text(render_summary_md(payload), encoding="utf-8")

    print(f"[Exp150 / H168] Overall: {overall} ({n_pass}/{len(verdicts)} PASS)")
    for k, v in verdicts.items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'}  {k}: {v['observed']}")
    print(f"  FMEA 25-row RPN: pre max={fmea_stats['max_rpn_pre']} (mean={fmea_stats['mean_rpn_pre']}) -> post max={fmea_stats['max_rpn_post']} (mean={fmea_stats['mean_rpn_post']}, -{fmea_stats['mean_rpn_reduction_pct']}%)")
    print(f"  S7.SAFETY Kit: {safety_spec['totals']['total_mass_kg']} kg, {safety_spec['totals']['steady_electrical_power_W']} W, ${safety_spec['totals']['cost_usd_nom']:,} ({safety_spec['totals']['pct_of_m3_v6_full_bom']}% of M3 v6.0)")


if __name__ == "__main__":
    main()
