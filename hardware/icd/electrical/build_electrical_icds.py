"""Complete Per-Part Electrical ICD & Master Power / UPS / Timing Budget Builder.

Generates strictly BOM-reconciled electrical Interface Control Documents (ICDs) for ALL 95
non-E1 electrical parts from BOM_DETAILED.csv (Wave 2B audit partition #281):
  - 17 E2 parts: Cryo-RF, microwave, superconducting readout/bus & cryo-wiring harnesses
  - 35 E3 parts: COTS rack HV/magnet/RF/MW/AWG/compute/timing/UPS/safety instruments
  - 43 E4 parts: Electro-mechanical, HV-electrode, vacuum, piezo, heater & sensor interfaces

Also generates:
  - master_electrical_power_ups_budget.json:
      * Exact S7.SAFETY-04 15 kVA / 13.5 kW / 10 kWh Online LFP UPS Tier-1 (2.533 kW -> 213.2 min)
        and Tier-2 sheddable (12.275 kW) reconciliation matching Exp150 to 0.001 kW
      * Operational-phase power envelopes (Write, Cryo-Readout, Bakeout, Quench/EPO)
      * Grounding-domain isolation map (AGND, DGND, HV_MINUS_5KV_DECK, CRYO_OVC, FACILITY_PE)
      * Complete 10 MHz Rb atomic clock (S7.4-01) 16-port fan-out tree
      * Complete White Rabbit sub-ns trigger (S7.4-02) 16-port optical/coax fan-out tree
  - README.md summary.

Epistemic status: M0_M1_ELECTRICAL_ICD_DESIGN_ONLY; no_lab_measurement=true; iec61508_certified=false.
Zero hardcoded host paths.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUT_DIR.parents[2]
BOM_CSV = REPO_ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"

VALID_GROUNDING_DOMAINS = (
    "AGND",
    "DGND",
    "HV_MINUS_5KV_DECK",
    "CRYO_OVC",
    "FACILITY_PE",
)
VALID_UPS_TIERS = ("TIER1_CRITICAL", "TIER2_SHED", "NONE")

E2_IDS: tuple[str, ...] = (
    "S3.2-04", "S6.4-03", "S6.5-03", "S6.6-01", "S6.6-02", "S6.6-03", "S6.6-04",
    "S6.6-07", "S6.7-01", "S6.10-01", "S6.11-02", "S6.11-03", "S6.11-04",
    "S9.3-02", "S9.4-01", "S9.4-02", "S9.4-03",
)
E3_IDS: tuple[str, ...] = (
    "S1.1-05", "S1.2-03", "S1.4-02", "S1.5-03", "S3.2-06", "S3.3-04", "S4.2-03",
    "S4.3-04", "S4.4-01", "S5.2-04", "S5.3-01", "S5.3-03", "S6.2-03", "S6.3-05",
    "S6.4-01", "S6.4-02", "S6.5-01", "S6.5-02", "S6.6-05", "S6.6-06", "S6.8-02",
    "S7.1-01", "S7.1-02", "S7.1-03", "S7.2-01", "S7.2-02", "S7.2-03", "S7.4-01",
    "S7.4-02", "S7.4-03", "S7.SAFETY-04", "S7.SAFETY-05", "S9.HPC-01",
    "S9.HPC-02", "S9.HPC-03",
)
E4_IDS: tuple[str, ...] = (
    "S1.1-01", "S1.1-02", "S1.1-03", "S1.1-04", "S1.2-01", "S1.2-02", "S1.3-02",
    "S1.4-01", "S1.5-01", "S1.5-02", "S1.6-01", "S1.6-02", "S1.7-01", "S2.1-03",
    "S2.2-01", "S2.2-04", "S2.3-01", "S2.5-01", "S2.5-02", "S3.1-04", "S3.2-05",
    "S4.2-01", "S4.2-02", "S4.3-01", "S4.3-02", "S4.3-03", "S4.5-02", "S5.1-02",
    "S5.1-03", "S5.2-01", "S5.2-02", "S5.2-03", "S5.6-01", "S5.6-02", "S5.6-03",
    "S5.6-04", "S6.1-02", "S6.3-01", "S6.3-02", "S6.9-01", "S7.3-03",
    "S7.SAFETY-01", "S7.SAFETY-06",
)

ALL_95_IDS: tuple[str, ...] = E2_IDS + E3_IDS + E4_IDS


def _rail(
    name: str,
    voltage_v: float,
    ctype: str,
    max_i_a: float,
    steady_w: float,
    peak_w: float,
    source: str,
) -> dict[str, Any]:
    return {
        "rail_name": name,
        "voltage_v": voltage_v,
        "current_type": ctype,
        "max_current_a": max_i_a,
        "steady_power_w": steady_w,
        "peak_power_w": peak_w,
        "source_part_id": source,
    }


def _conn(
    ref: str,
    ctype: str,
    side: str,
    mating: str,
    pins: list[tuple[str, str, str, str]],
) -> dict[str, Any]:
    return {
        "connector_ref": ref,
        "connector_type": ctype,
        "location_side": side,
        "mating_part_id": mating,
        "pins": [
            {"pin": p[0], "signal": p[1], "direction": p[2], "nominal_level": p[3]}
            for p in pins
        ],
    }


def _hook(sig: str, target: str, action: str, resp_ms: float) -> dict[str, Any]:
    return {
        "signal_name": sig,
        "target_part_id": target,
        "action_on_trip": action,
        "response_time_ms": resp_ms,
    }


# ---------------------------------------------------------------------------
# Complete 95-Part Bespoke Electrical Specification Table
# ---------------------------------------------------------------------------

def _build_part_specs() -> dict[str, dict[str, Any]]:
    """Return bespoke electrical ICD entries for all 95 E2/E3/E4 parts."""
    specs: dict[str, dict[str, Any]] = {}

    # =========================================================================
    # E2 — 17 CRYO-RF, MICROWAVE, SUPERCONDUCTING READOUT & CRYO-WIRING PARTS
    # =========================================================================

    specs["S3.2-04"] = {
        "electrical_class": "E2",
        "grounding_domain": "AGND",
        "grounding_notes": "Coax outer shield tied single-point to 100 K cold-island AGND; C_par < 0.15 pF.",
        "supply_rails": [_rail("PASSIVE_COAX", 0.0, "PASSIVE", 0.001, 0.0, 0.0, "S3.2-01")],
        "connectors_and_pinout": [
            _conn("P1_DET", "MMCX / Micro-Coax 50R PTFE (<5 cm)", "100K_cold_island", "S3.1-01", [
                ("1", "IBIC_PIX_SIG[0:7]", "IN", "0.055 fC charge pulse"),
                ("2", "COAX_SHIELD_AGND", "PWR", "0 V AGND"),
            ]),
            _conn("P2_CSA", "SMP-M 50R Cryo", "100K_cold_island", "S3.2-01", [
                ("1", "CSA_SUM_IN[0:7]", "OUT", "Virtual ground <0.15 pF"),
                ("2", "AGND_SHIELD", "PWR", "0 V AGND"),
            ]),
        ],
        "mating_part_ids": ["S3.1-01", "S3.2-01", "S3.2-05"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Passive analog pulse cable"},
    }

    specs["S6.4-03"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Coax outer jackets thermally & galvanically anchored at 50 K, 4 K, Still, CP, MXC stages.",
        "supply_rails": [_rail("MW_DRIVE_40GHZ", 0.0, "RF", 0.01, 0.0, 0.01, "S6.4-02")],
        "connectors_and_pinout": [
            _conn("J1_300K", "2.92mm-K Hermetic 50R (8x)", "300K_OVC_top", "S6.4-02", [
                ("1", "ESR_MW_IN[0:7]", "IN", "10-45 GHz <= +10 dBm at 300 K"),
                ("2", "OVC_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J2_20MK", "SMP-M 50R Superconducting Launch (8x)", "20mK_MXC", "S6.6-07", [
                ("1", "ESR_MW_ATT[0:7]", "OUT", "-60 dB staged (-20/-10/-10/-20 dB)"),
                ("2", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.4-02", "S6.8-04", "S6.6-07"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Phase-matched MW drive coax"},
    }

    specs["S6.5-03"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Eccosorb CR-124 LPF housings bolted directly to 4 K & 20 mK OFHC gold-plated thermal clamps.",
        "supply_rails": [_rail("RF_ENDOR_200MHZ", 0.0, "RF", 0.05, 0.0, 0.05, "S6.5-02")],
        "connectors_and_pinout": [
            _conn("J1_300K", "SMA-F Hermetic 50R (8x)", "300K_OVC_top", "S6.5-02", [
                ("1", "ENDOR_RF_IN[0:7]", "IN", "1-200 MHz RF drive"),
                ("2", "OVC_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J2_20MK", "SMP-F Filtered + Bias-Tee (8x)", "20mK_MXC", "S6.7-01", [
                ("1", "ENDOR_RF_FILT[0:7]", "OUT", "DC-200 MHz (>40 dB >1 GHz)"),
                ("2", "DC_BIAS_PORT[0:7]", "IN", "±2.5 V low-noise DC bias"),
                ("3", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.5-02", "S6.7-01", "S6.8-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Passive filtered ENDOR coax"},
    }

    specs["S6.6-01"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "56x 4 K InP HEMT housings bolted to 4 K flange; DC bias filtered on cryo_rf_bias_panel.",
        "supply_rails": [
            _rail("HEMT_4K_VD_56CH", 0.60, "DC", 0.25, 0.118, 0.437, "S3.2-06"),
            _rail("HEMT_4K_VG_56CH", -0.20, "DC", 0.005, 0.001, 0.002, "S3.2-06"),
        ],
        "connectors_and_pinout": [
            _conn("J_RF_IN", "SMA-F 50R Cryo (56x)", "4K_flange", "S6.6-04", [
                ("1", "HEMT_RFIN[0:55]", "IN", "4-8 GHz <= -90 dBm"),
                ("2", "CRYO_4K_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_RF_OUT", "SMA-F 50R Cryo (56x)", "4K_flange", "S6.6-05", [
                ("1", "HEMT_RFOUT[0:55]", "OUT", "+41.6 dB gain, Tn=1.4 K"),
                ("2", "CRYO_4K_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_BIAS", "Micro-D 9-pin Cryo (per bank)", "4K_flange", "S6.11-04", [
                ("1", "VD_FORCE", "IN", "+0.60 V (2.1-7.8 mW/ch)"),
                ("2", "VD_SENSE", "OUT", "4-wire Kelvin sense"),
                ("3", "VG_BIAS", "IN", "-0.20 V gate bias"),
                ("4", "AGND_CRYO", "PWR", "0 V star ground"),
            ]),
        ],
        "mating_part_ids": ["S6.6-02", "S6.6-04", "S6.6-05", "S9.3-02"],
        "interlock_hooks": [_hook("CRYO_4K_OVERTEMP_INHIBIT", "S6.2-03", "Disable HEMT drain bias if T_4K > 8 K", 100.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Cryogenic LNA stage"},
    }

    specs["S6.6-02"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Magnetically shielded cryo ferrite housings bolted to 20 mK MXC / 4 K bracket (passive).",
        "supply_rails": [_rail("PASSIVE_ISOLATOR", 0.0, "PASSIVE", 0.0, 0.0, 0.0, "S6.6-01")],
        "connectors_and_pinout": [
            _conn("J_PORT1", "SMA-F 50R Cryo (56x)", "20mK_4K_stage", "S6.6-07", [
                ("1", "ISO_IN[0:55]", "IN", "4-8 GHz IL<=0.5 dB"),
                ("2", "CRYO_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_PORT2", "SMA-F 50R Cryo (56x)", "20mK_4K_stage", "S6.6-04", [
                ("1", "ISO_OUT[0:55]", "OUT", "Reverse isolation >=20 dB"),
                ("2", "CRYO_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.6-01", "S6.6-04", "S6.6-07", "S9.3-02"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Passive non-reciprocal isolator"},
    }

    specs["S6.6-03"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "56x SS304 0.086 in input coax looms with -20/-10/-10/-20 dB thermalized attenuators.",
        "supply_rails": [_rail("PASSIVE_ATT_COAX", 0.0, "RF", 0.001, 0.0, 0.001, "S6.6-06")],
        "connectors_and_pinout": [
            _conn("J_300K", "SMA-F Hermetic Bulkhead (56x)", "300K_OVC", "S6.6-06", [
                ("1", "RO_DRIVE_300K[0:55]", "IN", "<= -40 dBm/tone @ 300 K"),
                ("2", "OVC_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_20MK", "SMP-M 50R Cryo (56x)", "20mK_MXC", "S6.6-07", [
                ("1", "RO_DRIVE_MXC[0:55]", "OUT", "<= -100 dBm/tone @ 20 mK"),
                ("2", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.6-06", "S6.6-07", "S6.8-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Attenuated readout drive loom"},
    }

    specs["S6.6-04"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "56x superconducting NbTi/NbTi (20 mK->4 K) + SS304 (4 K->300 K) output readout coaxes.",
        "supply_rails": [_rail("PASSIVE_NBTI_COAX", 0.0, "RF", 0.001, 0.0, 0.001, "S6.6-01")],
        "connectors_and_pinout": [
            _conn("J_20MK", "SMA-M Cryo (56x)", "20mK_MXC", "S6.6-02", [
                ("1", "RO_OUT_MXC[0:55]", "IN", "Lossless NbTi <0.1 dB/m"),
                ("2", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_300K", "SMA-F Hermetic Bulkhead (56x)", "300K_OVC", "S6.6-05", [
                ("1", "RO_OUT_300K[0:55]", "OUT", "Amplified 4-8 GHz readout"),
                ("2", "OVC_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.6-01", "S6.6-02", "S6.6-05", "S6.8-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Low-loss superconducting return loom"},
    }

    specs["S6.6-07"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "NbTiN resonator chip enclosed inside S6.3-03 Nb Meissner cup (B_res=22.3 uT) at 20 mK.",
        "supply_rails": [_rail("PASSIVE_RESONATOR_ARRAY", 0.0, "RF", 0.0, 0.0, 0.0, "S6.6-03")],
        "connectors_and_pinout": [
            _conn("J_FEED_IN", "SMP-M Non-Magnetic PCB Launch (56x)", "20mK_MXC", "S6.6-03", [
                ("1", "RES_FEED_IN[0:55]", "IN", "NL=110-160 tones/line, -100 dBm/tone"),
                ("2", "NBTIN_GND", "PWR", "0 V MXC superconducting ground"),
            ]),
            _conn("J_FEED_OUT", "SMP-M Non-Magnetic PCB Launch (56x)", "20mK_MXC", "S6.6-02", [
                ("1", "RES_FEED_OUT[0:55]", "OUT", "Dispersive Ql=800-1200, Qi~2e5"),
                ("2", "NBTIN_GND", "PWR", "0 V MXC superconducting ground"),
            ]),
        ],
        "mating_part_ids": ["S6.6-02", "S6.6-03", "S6.3-03", "S6.10-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Superconducting dispersive readout bank"},
    }

    specs["S6.7-01"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "56x 20 mK rf-SET LC tanks (L=820 nH, C=0.30 pF, f0=321.5 MHz) & bias-tees (>98 dB DC iso).",
        "supply_rails": [_rail("SET_SD_DC_BIAS", 0.5, "DC", 0.001, 0.0005, 0.001, "S6.7-02")],
        "connectors_and_pinout": [
            _conn("J_RF_PORT", "SMP-M 50R Cryo (56x)", "20mK_MXC", "S6.6-02", [
                ("1", "RFSET_CARRIER[0:55]", "BIDIR", "321.5 MHz reflectometry (d|Gamma|=0.396)"),
                ("2", "MXC_RF_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_DC_BT", "Micro-D Filtered DC Bias-Tee Port", "20mK_MXC", "S6.7-02", [
                ("1", "SET_VSD_BIAS[0:55]", "IN", "0-2 mV DC (>98 dB RF isolation)"),
                ("2", "SET_AGND_CRYO", "PWR", "0 V AGND/CRYO_OVC star"),
            ]),
        ],
        "mating_part_ids": ["S6.5-03", "S6.6-02", "S6.7-02"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "High-Z charge sensor reflectometry tank"},
    }

    specs["S6.10-01"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "20 mK high-Z 3 kOhm NbTiN (L_sq=100 pH/sq) M4 cavity-QED bus chip inside Nb shield.",
        "supply_rails": [_rail("PASSIVE_3KOHM_CAVITY", 0.0, "RF", 0.0, 0.0, 0.0, "S9.4-02")],
        "connectors_and_pinout": [
            _conn("P_CAV_COUPLE", "Wirebond / Flip-Chip 3 kOhm Port", "20mK_MXC", "S9.4-02", [
                ("1", "M4_BUS_3KOHM_P", "BIDIR", "5.0 GHz, Z_r=3000 Ohm, B_M4=0.1785 T"),
                ("2", "M4_BUS_GND", "PWR", "0 V NbTiN ground plane"),
            ]),
            _conn("P_DC_GATES", "Cryo Wirebond Fan-Out (968 gates)", "20mK_MXC", "S6.10-03", [
                ("1", "M4_DIPOLE_GATE[0:967]", "IN", "±1.5 V sweet-spot DC bias"),
                ("2", "M4_SUBSTRATE_GND", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.10-03", "S6.11-02", "S9.4-02"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Superconducting 3 kOhm cavity-QED bus"},
    }

    specs["S6.11-02"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "32x 20 mK Josephson TWPA + 625x Purcell + dual-isolator packs; MXC heat load = 2.144 uW.",
        "supply_rails": [
            _rail("TWPA_FLUX_BIAS_32CH", 0.05, "DC", 0.032, 0.000002, 0.000005, "S6.11-01"),
            _rail("TWPA_PUMP_RF", 0.0, "RF", 0.001, 0.0, 0.000001, "S6.11-01"),
        ],
        "connectors_and_pinout": [
            _conn("J_SIG_IN", "SMP-F 50R Non-Mag (32x)", "20mK_MXC", "S6.10-01", [
                ("1", "TWPA_IN[0:31]", "IN", "4-8 GHz, P1dB=-98 dBm, 625x Purcell"),
                ("2", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_SIG_OUT", "SMP-F 50R Non-Mag (32x)", "20mK_MXC", "S6.11-04", [
                ("1", "TWPA_OUT[0:31]", "OUT", "G=20 dB, TN=0.30 K, dual-iso 40 dB"),
                ("2", "MXC_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_FLUX", "Micro-D NbTi Twisted-Pair", "20mK_MXC", "S6.11-04", [
                ("1", "TWPA_FLUX_P[0:31]", "IN", "±1 mA flux tuning via Eccosorb LPF"),
                ("2", "TWPA_FLUX_N[0:31]", "IN", "Return twisted pair"),
            ]),
        ],
        "mating_part_ids": ["S6.10-01", "S6.11-01", "S6.11-03", "S6.11-04"],
        "interlock_hooks": [_hook("MXC_TEMP_GT_100MK", "S6.2-03", "Mute TWPA RF pumps if MXC > 100 mK", 50.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Quantum-limited parametric preamp"},
    }

    specs["S6.11-03"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "32x 4 K InP HEMT LNA bank (LNF-LNC4_8C class, 7.8 mW/ch = 0.2496 W @ 4 K).",
        "supply_rails": [
            _rail("HEMT32_VD", 0.65, "DC", 0.384, 0.2496, 0.28, "S3.2-06"),
            _rail("HEMT32_VG", -0.15, "DC", 0.005, 0.001, 0.002, "S3.2-06"),
        ],
        "connectors_and_pinout": [
            _conn("J_RFIN", "SMA-F 50R Cryo (32x)", "4K_flange", "S6.11-04", [
                ("1", "HEMT32_IN[0:31]", "IN", "4-8 GHz from 20 mK TWPA"),
                ("2", "CRYO_4K_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_RFOUT", "SMA-F 50R Cryo (32x)", "4K_flange", "S6.11-01", [
                ("1", "HEMT32_OUT[0:31]", "OUT", "G=38 dB, Tn=2.0 K, Tsys=0.672 K"),
                ("2", "CRYO_4K_GND", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_DC", "Micro-D 2x16 Cryo Bias Header", "4K_flange", "S3.2-06", [
                ("1", "VD_CH[0:31]", "IN", "+0.65 V @ 12 mA/ch (7.8 mW/ch)"),
                ("2", "VG_CH[0:31]", "IN", "-0.15 V gate bias"),
                ("3", "AGND_CRYO", "PWR", "0 V star ground"),
            ]),
        ],
        "mating_part_ids": ["S6.11-01", "S6.11-02", "S6.11-04", "S3.2-06"],
        "interlock_hooks": [_hook("CRYO_4K_OVERTEMP", "S6.2-03", "Disable HEMT bias if T_4K > 8 K", 100.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "4 K post-TWPA LNA stage"},
    }

    specs["S6.11-04"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "96x 0.86 mm CuNi/NbTi cryo coax loom (32 RO-in, 32 RO-out, 32 XY) anchored 50K/4K/Still/CP/MXC.",
        "supply_rails": [_rail("PASSIVE_96LINE_LOOM", 0.0, "RF", 0.001, 0.0, 0.001, "S6.11-01")],
        "connectors_and_pinout": [
            _conn("J_OVC_300K", "SMPM/SMA 96-Port Hermetic Flange Bank", "300K_OVC", "S6.11-01", [
                ("1-32", "RO_IN_300K[0:31]", "IN", "4-8 GHz readout probes"),
                ("33-64", "RO_OUT_300K[0:31]", "OUT", "4-8 GHz amplified readout"),
                ("65-96", "XY_DRV_300K[0:31]", "IN", "XY microwave drive"),
            ]),
            _conn("J_MXC_20MK", "SMP-M 96-Port Cryo Bulkhead", "20mK_MXC", "S6.11-02", [
                ("1-32", "RO_IN_MXC[0:31]", "OUT", "-60 dB attenuated"),
                ("33-64", "RO_OUT_MXC[0:31]", "IN", "NbTi superconducting (<0.1 dB/m)"),
                ("65-96", "XY_DRV_MXC[0:31]", "OUT", "-60 dB attenuated"),
            ]),
        ],
        "mating_part_ids": ["S6.11-01", "S6.11-02", "S6.11-03", "S6.8-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "96-line cryo RF harness"},
    }

    specs["S9.3-02"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "4-chain spare 4 K InP HEMT + cryo isolator + attenuator field-service replacement kit.",
        "supply_rails": [_rail("SPARE_HEMT_KIT", 0.60, "DC", 0.02, 0.0, 0.031, "S3.2-06")],
        "connectors_and_pinout": [
            _conn("J_SPARE_RF", "SMA-F 50R Cryo (4x chains)", "spares_storage", "S6.6-01", [
                ("1", "SPARE_RF_IN/OUT[0:3]", "BIDIR", "Drop-in for S6.6-01/02"),
                ("2", "CRYO_4K_GND", "PWR", "0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S6.6-01", "S6.6-02", "S6.6-03"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Shelf spare replacement kit"},
    }

    specs["S9.4-01"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Option-Q CF63 hermetic 4x SMA (4-8 GHz) + 1x 1550 nm SMF-28 vacuum feedthrough on OVC -X wall.",
        "supply_rails": [_rail("PASSIVE_CF63_FEEDTHROUGH", 0.0, "RF", 0.0, 0.0, 0.0, "S9.4-03")],
        "connectors_and_pinout": [
            _conn("J_EXT_RF", "SMA-F Hermetic 50R (4x) + FC/APC SMF-28 (1x)", "300K_OVC_minusX", "S6.11-01", [
                ("1-4", "QRAM_RF_EXT[0:3]", "BIDIR", "4-8 GHz 50 Ohm, He<=1e-10"),
                ("5", "ER167_OPT_1550NM", "BIDIR", "1536/1550 nm SMF-28 single-mode"),
                ("SHD", "CF63_OVC_SHELL", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_VAC_RF", "SMA-F Cryo Vacuum Side (4x) + FC/APC (1x)", "vacuum_side", "S9.4-03", [
                ("1-4", "QRAM_RF_VAC[0:3]", "BIDIR", "Mates to S9.4-03 NbTi/CuNi loom"),
                ("5", "ER167_OPT_VAC", "BIDIR", "Mates to S9.4-03 cryo fiber"),
            ]),
        ],
        "mating_part_ids": ["S6.8-04", "S9.4-03", "S6.11-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Option-Q hermetic OVC interface"},
    }

    specs["S9.4-02"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "20 mK NbTiN 5-stage Chebyshev 50 <-> 3000 Ohm bridge (max |S11|=-39.55 dB @ 4-8 GHz); 0.78 uW MXC.",
        "supply_rails": [_rail("PASSIVE_CHEBYSHEV_BRIDGE", 0.0, "RF", 0.0, 0.0, 0.0, "S9.4-03")],
        "connectors_and_pinout": [
            _conn("J_50R", "SMP-M 50R Non-Mag (4x)", "20mK_MXC", "S9.4-03", [
                ("1-4", "QRAM_50R_PORT[0:3]", "BIDIR", "4-8 GHz, Z0=50 Ohm, |S11|<-39.5 dB"),
                ("GND", "OFHC_NB_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_3KR", "High-Z NbTiN Wirebond/Flip-Chip (4x)", "20mK_MXC", "S6.10-01", [
                ("1-4", "QRAM_3KOHM_BUS[0:3]", "BIDIR", "Z_L=3000 Ohm M4 cavity-QED bus"),
                ("GND", "NBTIN_GND", "PWR", "0 V MXC superconducting ground"),
            ]),
        ],
        "mating_part_ids": ["S9.4-03", "S6.10-01", "S6.11-02"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "5-stage Chebyshev quantum bus matcher"},
    }

    specs["S9.4-03"] = {
        "electrical_class": "E2",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "4x NbTi superconducting qRAM coaxes + 1x SMF-28 cryo fiber anchored 300K->50K->4K->100mK->20mK.",
        "supply_rails": [_rail("PASSIVE_QRAM_LOOM", 0.0, "RF", 0.0, 0.0, 0.0, "S9.4-01")],
        "connectors_and_pinout": [
            _conn("J_300K", "SMA-M (4x) + FC/APC (1x)", "300K_OVC", "S9.4-01", [
                ("1-4", "QRAM_COAX_TOP[0:3]", "BIDIR", "4-8 GHz CuNi/NbTi (<0.1 dB/m)"),
                ("5", "SMF28_TOP", "BIDIR", "1550 nm optical link"),
            ]),
            _conn("J_20MK", "SMP-F (4x) + Cryo FC/APC (1x)", "20mK_MXC", "S9.4-02", [
                ("1-4", "QRAM_COAX_MXC[0:3]", "BIDIR", "0.185 uW/port @ 20 mK"),
                ("5", "SMF28_MXC", "BIDIR", "0.040 uW @ 20 mK"),
            ]),
        ],
        "mating_part_ids": ["S9.4-01", "S9.4-02", "S6.8-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Option-Q cryo coax & optical loom"},
    }

    # =========================================================================
    # E3 — 35 COTS RACK HV / MAGNET / RF / MW / AWG / COMPUTE / TIMING / UPS
    # =========================================================================

    specs["S1.1-05"] = {
        "electrical_class": "E3",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "15 kV solid-insulated isolation transformer & fiber-optic control deck; chassis to FACILITY_PE.",
        "supply_rails": [
            _rail("AC_MAINS_230V", 230.0, "AC_1PH", 6.5, 950.0, 1400.0, "S7.4-03"),
            _rail("HV_EXTRACT_15KV", 15000.0, "HV_DC", 0.015, 150.0, 225.0, "S1.1-05"),
        ],
        "connectors_and_pinout": [
            _conn("J_AC", "IEC C14 230VAC", "rack_rear", "S7.4-03", [
                ("L", "AC_LINE_SHED", "IN", "230 VAC 50/60 Hz"),
                ("N", "AC_NEUTRAL", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Safety earth"),
            ]),
            _conn("J_HV_OUT", "SHV-20kV Silicon-Free Solid HV", "hv_deck_top", "S1.1-03", [
                ("1", "HV_EXTRACT_POS_15KV", "OUT", "0-15 kV <0.01% ripple"),
                ("2", "ARC_FILAMENT_RETURN", "BIDIR", "Floating on HV deck"),
            ]),
            _conn("J_FO_ILK", "ST Fiber-Optic Duplex", "rack_rear", "S7.SAFETY-03", [
                ("TX", "HV_STATUS_FO", "OUT", "Optical status"),
                ("RX", "HV_ENABLE_SIL3_FO", "IN", "Fail-safe 18.3 ms crowbar trip"),
            ]),
        ],
        "mating_part_ids": ["S1.1-01", "S1.1-02", "S1.1-03", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("HV_DECK_ENABLE_1OO2D", "S7.SAFETY-03", "Inhibit 15 kV deck & fire 2 MOhm crowbar (<18.3 ms)", 18.3)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "DC/CW HV source supply"},
    }

    specs["S1.2-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "Bipolar +/-5 kV ultra-low-noise Wien E-field PSU (<5 mVpp, <10 ppm); chassis to FACILITY_PE.",
        "supply_rails": [
            _rail("AC_MAINS_230V", 230.0, "AC_1PH", 1.5, 180.0, 280.0, "S7.4-03"),
            _rail("WIEN_HV_BIPOLAR", 5000.0, "HV_DC", 0.005, 25.0, 50.0, "S1.2-03"),
        ],
        "connectors_and_pinout": [
            _conn("J_HV_P", "SHV-10kV (2x)", "rack_rear", "S1.2-02", [
                ("1", "WIEN_E_POS", "OUT", "0 to +5 kV <5 mVpp"),
                ("2", "HV_RET_SHIELD", "PWR", "AGND star"),
            ]),
            _conn("J_HV_N", "SHV-10kV (2x)", "rack_rear", "S1.2-02", [
                ("1", "WIEN_E_NEG", "OUT", "0 to -5 kV <5 mVpp"),
                ("2", "HV_RET_SHIELD", "PWR", "AGND star"),
            ]),
            _conn("J_CTRL", "DB9 + Interlock", "rack_rear", "S1.3-03", [
                ("1-2", "HV_INHIBIT_NC", "IN", "24 V dry-contact interlock"),
                ("3-5", "RS485_CTRL", "BIDIR", "Isolated telemetry"),
            ]),
        ],
        "mating_part_ids": ["S1.2-02", "S1.3-03", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("WIEN_HV_INHIBIT", "S7.SAFETY-03", "Crowbar & zero Wien E-plates", 18.3)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "DC mass-filter supply"},
    }

    specs["S1.4-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "2x Keithley 6485/6517-class picoammeters (10 fA res); triaxial guard tied to AGND.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 0.5, 60.0, 90.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_TRIAX", "Triax-BNC 3-Lug (2x)", "rack_front", "S1.4-01", [
                ("CTR", "FARADAY_I_IN", "IN", "1 fA - 10 uA beam current"),
                ("GRD", "DRIVEN_GUARD", "OUT", "Low-leakage driven guard"),
                ("SHD", "AGND_CHASSIS", "PWR", "0 V AGND"),
            ]),
            _conn("J_LAN", "RJ45 GbE / GPIB", "rack_rear", "S1.4-03", [
                ("1-8", "SCPI_TELEMETRY", "BIDIR", "100BASE-TX isolated"),
            ]),
        ],
        "mating_part_ids": ["S1.4-01", "S1.4-03", "S7.1-01"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Beam-dose metrology"},
    }

    specs["S1.5-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "Bipolar HDA-HiRes analyzer PSU (<50 mVpp, 10 ppm) referenced to -5 kV column liner deck.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 1.0, 120.0, 180.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_HDA_HV", "SHV-10kV Pair", "rack_rear", "S1.5-01", [
                ("1", "HDA_INNER_HEMI", "OUT", "V_pass + dV (<50 mVpp)"),
                ("2", "HDA_OUTER_HEMI", "OUT", "V_pass - dV (<50 mVpp)"),
            ]),
            _conn("J_FO", "ST Optical Control", "rack_rear", "S7.SAFETY-03", [
                ("RX", "HDA_HV_INHIBIT_FO", "IN", "Optical safety inhibit"),
            ]),
        ],
        "mating_part_ids": ["S1.5-01", "S1.3-03", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("HDA_HV_INHIBIT", "S7.SAFETY-03", "Inhibit HDA pass-energy HV", 18.3)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "DC energy filter supply"},
    }

    specs["S3.2-06"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "Linear (zero-switching) ±5 V / ±12 V (<100 uVrms) PSU feeding IBIC & cryo HEMT/TWPA bias.",
        "supply_rails": [
            _rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.5, 40.0, 80.0, "S7.SAFETY-04"),
            _rail("ANALOG_PM5V", 5.0, "DC", 2.0, 10.0, 20.0, "S3.2-06"),
            _rail("ANALOG_PM12V", 12.0, "DC", 1.5, 18.0, 36.0, "S3.2-06"),
        ],
        "connectors_and_pinout": [
            _conn("J_AC", "IEC C14 Tier-1 UPS", "rack_rear", "S7.SAFETY-04", [
                ("L", "UPS_T1_L", "IN", "230 VAC Tier-1"),
                ("N", "UPS_T1_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Chassis earth"),
            ]),
            _conn("J_DC_OUT", "LEMO 1B 6-Pin Shielded (2x)", "rack_rear", "S3.2-02", [
                ("1", "+5V_LIN", "OUT", "+5.00 V <100 uVrms"),
                ("2", "-5V_LIN", "OUT", "-5.00 V <100 uVrms"),
                ("3", "+12V_LIN", "OUT", "+12.00 V <100 uVrms"),
                ("4", "-12V_LIN", "OUT", "-12.00 V <100 uVrms"),
                ("5", "AGND_STAR", "PWR", "0 V AGND star"),
                ("6", "SHIELD", "PWR", "Chassis shield"),
            ]),
        ],
        "mating_part_ids": ["S3.2-01", "S3.2-02", "S6.6-01", "S6.11-03", "S7.SAFETY-04"],
        "interlock_hooks": [],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 40.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Ultra-low-noise analog power"},
    }

    specs["S3.3-04"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "1U EMI-shielded IBIC counting FPGA chassis; 10 MHz Rb Ch-13 + White Rabbit trigger.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.3, 25.0, 45.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_10MHZ", "SMA-F 50R Clock In", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB", "IN", "+13 dBm 10 MHz Rb ref"),
                ("2", "DGND", "PWR", "0 V DGND"),
            ]),
            _conn("J_WR_TRIG", "SFP+ / SMA Trigger In", "rack_rear", "S7.4-02", [
                ("1", "WR_TRIG_SYNC", "IN", "<200 ps skew trigger"),
                ("2", "DGND", "PWR", "0 V DGND"),
            ]),
        ],
        "mating_part_ids": ["S3.3-01", "S3.3-03", "S7.4-01", "S7.4-02", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("WATCHDOG_ABORT_OUT", "S7.SAFETY-03", "Blank beam if FPGA watchdog trips", 1.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 25.0,
        "timing_sync": {"rb_10mhz_port": "CH13", "white_rabbit_port": "WR_COAX_1", "sync_role": "IBIC counting-gate clock/trigger"},
    }

    specs["S4.2-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "6-DOF MIMO active vibration isolation DSP & piezo amplifier (10 kHz loop).",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 1.5, 160.0, 260.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_SENS", "DB25 Shielded Analog In", "rack_rear", "S4.2-02", [
                ("1-6", "GEOPHONE_XYZ_DIFF", "IN", "3-axis seismic feedback <1 ng/rtHz"),
                ("7", "AGND", "PWR", "0 V AGND"),
            ]),
            _conn("J_ACT", "MIL-DTL-38999 12-Pin HV Piezo", "rack_rear", "S4.2-01", [
                ("1-12", "PIEZO_6DOF_DRV", "OUT", "0-150 V active isolation"),
            ]),
        ],
        "mating_part_ids": ["S4.2-01", "S4.2-02", "S6.9-04"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "10 kHz MIMO vibration servo"},
    }

    specs["S4.3-04"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "6-ch 24-bit piezo servo controller (E-712 class, <0.1 nm noise); EtherCAT/SPI to host.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 1.8, 220.0, 350.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_PIEZO_HV", "LEMO 2B 12-Pin HV", "rack_rear", "S4.3-01", [
                ("1-12", "PIEZO_FINE_6DOF", "OUT", "-20 to +120 V low-noise servo"),
            ]),
            _conn("J_CAP_FB", "LEMO 00 Coax (6x)", "rack_rear", "S4.3-03", [
                ("1-6", "CAP_SENS_FB[0:5]", "IN", "Sub-nm capacitive feedback"),
            ]),
            _conn("J_ECAT", "RJ45 EtherCAT", "rack_rear", "S7.1-01", [
                ("1-8", "ETHERCAT_SYNC", "BIDIR", "100BASE-TX deterministic motion"),
            ]),
        ],
        "mating_part_ids": ["S4.3-01", "S4.3-02", "S4.3-03", "S4.5-03", "S7.1-01"],
        "interlock_hooks": [_hook("STAGE_LIMIT_INTERLOCK", "S7.4-04", "Clamp piezo drive on collision/E-Stop", 5.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_COAX_5", "sync_role": "Wafer stage step-and-settle sync"},
    }

    specs["S4.4-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "3-axis stabilized 632.8 nm He-Ne laser interferometer (Renishaw XL-80/RLE class, ±0.05 ppm).",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 0.6, 75.0, 120.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_OPT", "PM Fiber FC/APC (3x)", "front_panel", "S4.4-02", [
                ("1-3", "HENE_632NM_XYZ", "OUT", "3-axis stabilized 632.8 nm fiber"),
            ]),
            _conn("J_QUAD", "DB25 A/B-Quad + Parallel", "rack_rear", "S4.5-03", [
                ("1-12", "INTF_XYZ_LVDS", "OUT", "<=0.05 nm position stream"),
            ]),
            _conn("J_10MHZ", "SMA-F 50R", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB", "IN", "Shared with S4.5-03 via CH15"),
            ]),
        ],
        "mating_part_ids": ["S4.4-02", "S4.5-03", "S7.4-01"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH15", "white_rabbit_port": None, "sync_role": "Interferometer phase-locked sampling"},
    }

    specs["S5.2-04"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "Full-range Pirani/cold-cathode gauge controller & 1-100 amu RGA on Tier-1 UPS.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.6, 95.0, 140.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_GAUGE", "FCC68 / RJ45 Sensor Bus (4x)", "rack_rear", "S5.1-01", [
                ("1-4", "PIRANI_CC_24V_SIG", "BIDIR", "1000 to 1e-11 mbar readout"),
            ]),
            _conn("J_RGA", "CF40 RGA Head Cable", "rack_rear", "S5.1-01", [
                ("1-10", "RGA_QUAD_RF_FIL", "BIDIR", "H2O/PH3/He partial pressure"),
            ]),
            _conn("J_ILK", "Phoenix 4-Pin Safety Relay", "rack_rear", "S7.SAFETY-03", [
                ("1-2", "UHV_OK_NC_A", "OUT", "Trips if P > 1e-8 Torr"),
                ("3-4", "UHV_OK_NC_B", "OUT", "Diverse channel B"),
            ]),
        ],
        "mating_part_ids": ["S5.1-01", "S7.SAFETY-03", "S7.SAFETY-04", "S7.4-04"],
        "interlock_hooks": [_hook("UHV_PRESSURE_GT_1E8", "S7.SAFETY-03", "Close UHV gate valves & inhibit HV/laser", 10.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 95.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "1 Hz SCADA vacuum telemetry"},
    }

    specs["S5.3-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "In-situ rapid flash optical annealing lamp/capacitor bank; interlocked via S5.5-04/S7.SAFETY-03.",
        "supply_rails": [_rail("AC_3PH_FACILITY", 400.0, "AC_3PH", 16.0, 1200.0, 4500.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_PWR", "IEC 60309 3P+N+PE 16A", "facility_feed", "S7.4-03", [
                ("L1-L3", "AC_400V_3PH", "IN", "Flash capacitor charger"),
                ("PE", "FACILITY_PE", "PWR", "Safety earth"),
            ]),
            _conn("J_ILK", "Dual-Channel Interlock Phoenix", "rack_rear", "S7.SAFETY-03", [
                ("1-4", "FLASH_ENABLE_1OO2D", "IN", "Cut within 3.2 ms on fault"),
            ]),
        ],
        "mating_part_ids": ["S5.3-02", "S5.3-03", "S5.5-04", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("FLASH_ANNEAL_CUT", "S7.SAFETY-03", "Dump flash bank & close shutter", 3.2)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_COAX_6", "sync_role": "ms-pulse anneal trigger"},
    }

    specs["S5.3-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "Dual-wavelength InGaAs/Si optical pyrometer & closed-loop anneal controller (<100 us).",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 0.4, 45.0, 70.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_OPT", "SMA-905 Multimode Fiber", "front_panel", "S5.3-02", [
                ("1", "PYRO_IR_OPT", "IN", "300-1200 C thermal emission"),
            ]),
            _conn("J_CTRL", "BNC Analog Out + RJ45", "rack_rear", "S5.3-01", [
                ("1", "ANNEAL_PID_CMD", "OUT", "0-10 V closed-loop command"),
                ("2", "ETH_CERT_LOG", "OUT", "Wafer anneal profile log"),
            ]),
        ],
        "mating_part_ids": ["S5.3-01", "S5.3-02", "S7.1-02"],
        "interlock_hooks": [_hook("OVERTEMP_1200C_TRIP", "S7.SAFETY-03", "Abort flash anneal on over-temperature", 1.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Real-time anneal feedback"},
    }

    specs["S6.2-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Lake Shore 372/336 AC-resistance bridge & 8x Cernox/RuO2 thermometry on Tier-1 UPS.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.4, 60.0, 100.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_THERM", "Fischer 104 / Micro-D 25-Pin Cryo", "rack_rear", "S6.8-04", [
                ("1-16", "CERNOX_RUO2_4W[0:7]", "IN", "50K/4K/Still/CP/MXC 10 mK-300 K"),
                ("17-20", "MXC_PID_HEATER", "OUT", "0-100 mW PID heater"),
                ("21", "CRYO_OVC_SHIELD", "PWR", "0 V CRYO_OVC"),
            ]),
            _conn("J_ILK", "DB9 Alarm Relay", "rack_rear", "S7.SAFETY-03", [
                ("1-2", "MXC_LT_1K_INTERLOCK", "OUT", "Blocks S5.5 laser when MXC < 1 K"),
            ]),
        ],
        "mating_part_ids": ["S6.2-01", "S6.8-01", "S6.8-04", "S5.5-04", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("MXC_BELOW_1K_LASER_BLOCK", "S5.5-04", "Hard-inhibit 808 nm flash laser while cold", 5.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 60.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "1 Hz 5-stage cryo thermometry"},
    }

    specs["S6.3-05"] = {
        "electrical_class": "E3",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Bipolar ±100 A (10 ppm) magnet ramp PSU + Bi-2223 HTS current leads; off/zeroed in persistent mode.",
        "supply_rails": [
            _rail("AC_MAINS_230V", 230.0, "AC_1PH", 8.0, 120.0, 1600.0, "S7.4-03"),
            _rail("MAGNET_RAMP_DC", 10.0, "DC", 100.0, 0.0, 1000.0, "S6.3-05"),
        ],
        "connectors_and_pinout": [
            _conn("J_HIGH_I", "M10 Copper Busbar + HTS Lead Pair", "rack_rear", "S6.3-04", [
                ("1", "MAG_I_POS", "OUT", "±100 A ramp (±255.9 A bank eq.)"),
                ("2", "MAG_I_NEG", "OUT", "Return lead"),
            ]),
            _conn("J_VTAP", "LEMO 1B 4-Pin Voltage Tap", "rack_rear", "S6.3-04", [
                ("1-2", "VTAP_QUENCH_SENSE", "IN", "400 V isolated quench sense"),
                ("3-4", "PCS_HEATER_DRV", "OUT", "50 mA persistent switch heater"),
            ]),
        ],
        "mating_part_ids": ["S6.3-01", "S6.3-02", "S6.3-04", "S7.SAFETY-05"],
        "interlock_hooks": [_hook("QUENCH_DETECT_DUMP", "S7.SAFETY-05", "Open breaker & dump 18.94 kJ into 1.563 Ohm", 30.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "DC/persistent magnet charger"},
    }

    specs["S6.4-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "4x 10-45 GHz low-phase-noise ESR VSGs (<-120 dBc/Hz) locked to 10 MHz Rb Ch 3-6.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 2.5, 440.0, 600.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_MW_OUT", "2.92mm-K 50R (4x)", "front_panel", "S6.4-02", [
                ("1", "ESR_LO_OUT[0:3]", "OUT", "10-45 GHz +15 dBm"),
            ]),
            _conn("J_10MHZ", "BNC-F 50R (4x)", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB[3:6]", "IN", "+13 dBm Rb atomic clock"),
            ]),
        ],
        "mating_part_ids": ["S6.4-02", "S7.4-01", "S7.4-03"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH3-CH6", "white_rabbit_port": None, "sync_role": "Coherent ESR LO synthesis"},
    }

    specs["S6.4-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "4x wideband I/Q mixers, >60 dB fast RF switches & RT driver amps (Marki/Mini-Circuits).",
        "supply_rails": [_rail("DC_12V_RF", 12.0, "DC", 3.5, 36.0, 48.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_IF_IQ", "SMA-F 50R I/Q Pair (4x2)", "front_panel", "S7.2-01", [
                ("1", "AWG_I_IN[0:3]", "IN", "200 MHz IF GRAPE I-quadrature"),
                ("2", "AWG_Q_IN[0:3]", "IN", "200 MHz IF GRAPE Q-quadrature"),
            ]),
            _conn("J_RF_OUT", "2.92mm-K 50R (4x)", "front_panel", "S6.4-03", [
                ("1", "ESR_MOD_OUT[0:3]", "OUT", "10-45 GHz shaped ESR pulses"),
            ]),
            _conn("J_SW_GATE", "SMA-F TTL Marker (4x)", "front_panel", "S7.2-02", [
                ("1", "MW_BLANK_GATE[0:3]", "IN", ">60 dB on/off switch gate"),
            ]),
        ],
        "mating_part_ids": ["S6.4-01", "S6.4-03", "S7.2-01", "S7.2-02"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Fast pulse blanking via S7.2-02"},
    }

    specs["S6.5-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "4x phase-coherent 1-200 MHz RF/ENDOR DDS sources (1 Hz res) locked to 10 MHz Rb Ch 7-10.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 1.0, 110.0, 160.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_DDS_OUT", "SMA-F 50R (4x)", "front_panel", "S6.5-02", [
                ("1", "ENDOR_DDS_OUT[0:3]", "OUT", "1-200 MHz 0 dBm"),
            ]),
            _conn("J_10MHZ", "BNC-F 50R (4x)", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB[7:10]", "IN", "+13 dBm Rb ref"),
            ]),
        ],
        "mating_part_ids": ["S6.5-02", "S7.2-02", "S7.4-01"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH7-CH10", "white_rabbit_port": None, "sync_role": "Coherent 31P/29Si ENDOR DDS"},
    }

    specs["S6.5-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "4x 1-200 MHz 10 W Class-A linear RF power amps & directional couplers (harmonics <-30 dBc).",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 2.0, 240.0, 360.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_RF_IN", "SMA-F 50R (4x)", "front_panel", "S6.5-01", [
                ("1", "RFPA_IN[0:3]", "IN", "0 dBm 1-200 MHz"),
            ]),
            _conn("J_RF_OUT", "N-Type / SMA-F 50R (4x)", "front_panel", "S6.5-03", [
                ("1", "RFPA_OUT[0:3]", "OUT", "Up to +40 dBm pulsed ENDOR"),
            ]),
        ],
        "mating_part_ids": ["S6.5-01", "S6.5-03", "S7.2-02"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Gated RF power stage"},
    }

    specs["S6.6-05"] = {
        "electrical_class": "E3",
        "grounding_domain": "AGND",
        "grounding_notes": "56x room-temp Mini-Circuits ZX60-14LN-S+ LNAs (20 dB gain, NF <1.5 dB, +12 V linear rail).",
        "supply_rails": [_rail("DC_12V_LNA_56X", 12.0, "DC", 4.5, 45.0, 54.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_IN", "SMA-F 50R (56x)", "rack_panel", "S6.6-04", [
                ("1", "RTLNA_IN[0:55]", "IN", "4-8 GHz from OVC flange"),
            ]),
            _conn("J_OUT", "SMA-F 50R (56x)", "rack_panel", "S6.6-06", [
                ("1", "RTLNA_OUT[0:55]", "OUT", "+20 dB, P1dB>+15 dBm"),
            ]),
        ],
        "mating_part_ids": ["S6.6-04", "S6.6-06", "S7.4-03"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Warm readout LNA bank"},
    }

    specs["S6.6-06"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "14x AMD ZCU216 RFSoC digitizer/AWG boards (56 chains, 14-bit ADC/DAC) locked to Rb Ch-12 & WR.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 4.5, 630.0, 840.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_RF_ADC", "XM655/SMPM 50R (56x ADC + 56x DAC)", "rack_front", "S6.6-05", [
                ("1-56", "RFSOC_ADC_IN[0:55]", "IN", "4-8 GHz multiplexed readout"),
                ("57-112", "RFSOC_DAC_OUT[0:55]", "OUT", "Multi-tone probe combs"),
            ]),
            _conn("J_CLK_10M", "SMA-F 50R Splitter Tree", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB_CH12", "IN", "Locked LMK04828 PLL"),
            ]),
            _conn("J_WR", "SFP+ Optical Trigger", "rack_rear", "S7.4-02", [
                ("1", "WR_SYNC_FIBER[2]", "IN", "<200 ps SYSREF/trigger"),
            ]),
        ],
        "mating_part_ids": ["S6.6-03", "S6.6-05", "S7.4-01", "S7.4-02", "S7.1-01"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH12", "white_rabbit_port": "WR_SFP_2", "sync_role": "56-chain RFSoC readout/AWG"},
    }

    specs["S6.8-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Closed-cycle 3He/4He GHS cabinet; recovery valves & turbo controller backed by Tier-1 UPS (260 W hold).",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 6.0, 260.0, 1200.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_AC", "IEC C20 230VAC Tier-1 UPS", "cabinet_rear", "S7.SAFETY-04", [
                ("L", "UPS_T1_L", "IN", "230 VAC 260 W dump-recovery hold"),
                ("N", "UPS_T1_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Safety earth"),
            ]),
            _conn("J_ILK", "DB15 Safety & Telemetry", "cabinet_rear", "S7.SAFETY-03", [
                ("1-2", "GHS_DUMP_RECOVER_CMD", "IN", "Auto-recover 3He/4He at t=300 s"),
                ("3-4", "OVC_OVERPRESSURE_ALM", "OUT", "Monitors <0.1 barg during recovery"),
            ]),
        ],
        "mating_part_ids": ["S6.8-01", "S6.8-03", "S7.SAFETY-03", "S7.SAFETY-04", "S7.SAFETY-05"],
        "interlock_hooks": [_hook("GHS_SAFE_MIXTURE_RECOVERY", "S7.SAFETY-03", "Recover 3He/4He into dump tank on EPO/outage (t=300 s)", 300000.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 260.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Cryo circulation & recovery PLC"},
    }

    specs["S7.1-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "2x Lambda Vector 2xRTX4500Ada host workstations (1200 W active GRAPE; 360 W Tier-1 hold on UPS).",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 6.5, 360.0, 1200.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_AC", "2x IEC C14 Tier-1 UPS", "rack_rear", "S7.SAFETY-04", [
                ("L", "UPS_T1_L", "IN", "230 VAC (throttles GPUs on outage)"),
                ("N", "UPS_T1_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Safety earth"),
            ]),
            _conn("J_NIC", "Dual 10GbE SFP+ / RJ45", "rack_rear", "S7.1-02", [
                ("1-2", "CTRL_SCADA_LAN", "BIDIR", "To S7.1-02, S6.11-01, S7.2, S7.4"),
            ]),
        ],
        "mating_part_ids": ["S7.1-02", "S6.11-01", "S7.2-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("UPS_ON_BATTERY_THROTTLE", "S7.SAFETY-04", "Pause GPU GRAPE & enter 360 W safe-log mode", 100.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 360.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "NTP/PTP host orchestrator"},
    }

    specs["S7.1-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "2U 30 TB NVMe RAID-10 immutable wafer/certificate database server on Tier-1 UPS.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 1.8, 220.0, 380.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_AC_RED", "2x IEC C14 Redundant PSU", "rack_rear", "S7.SAFETY-04", [
                ("L", "UPS_T1_L", "IN", "230 VAC Tier-1"),
                ("N", "UPS_T1_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Safety earth"),
            ]),
            _conn("J_SFP28", "Dual 25GbE SFP28", "rack_rear", "S7.1-01", [
                ("1-2", "CERT_DB_LAN", "BIDIR", "SHA-256 certificate ingest"),
            ]),
        ],
        "mating_part_ids": ["S7.1-01", "S6.11-01", "S9.HPC-02", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("UPS_GRACEFUL_FLUSH", "S7.SAFETY-04", "Flush RAID journal & seal cert DB", 1000.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 220.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_SFP_7", "sync_role": "Timestamped cert ledger"},
    }

    specs["S7.1-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Secondary 6 kVA instrumentation UPS / metered smart PDU subordinate to S7.SAFETY-04.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.3, 20.0, 60.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_IN", "IEC C20 PDU Input", "rack_rear", "S7.SAFETY-04", [
                ("L", "UPS_BUS_L", "IN", "230 VAC metered branch"),
                ("N", "UPS_BUS_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Earth"),
            ]),
            _conn("J_SNMP", "RJ45 SNMP/Modbus", "rack_front", "S7.1-01", [
                ("1-8", "PDU_BRANCH_TELEMETRY", "OUT", "Per-outlet current/shed API"),
            ]),
        ],
        "mating_part_ids": ["S7.SAFETY-04", "S7.4-03", "S7.1-01"],
        "interlock_hooks": [_hook("PDU_TIER2_SHED_CMD", "S7.SAFETY-04", "Switch off Tier-2 PDU bank on utility loss", 500.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 20.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Smart PDU telemetry"},
    }

    specs["S7.2-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "4x PXIe 4-ch 1.25 GS/s 16-bit AWG modules (16 ch GRAPE/ENDOR) hosted in S7.2-03 backplane.",
        "supply_rails": [_rail("PXIE_BACKPLANE_12V", 12.0, "DC", 15.0, 140.0, 180.0, "S7.2-03")],
        "connectors_and_pinout": [
            _conn("J_BP", "PXIe Hybrid Backplane (4 slots)", "chassis_back", "S7.2-03", [
                ("CLK10", "PXIE_10MHZ_RB", "IN", "Locked via S7.4-01 CH11"),
                ("TRIG", "PXIE_STAR_TRIG", "IN", "From S7.2-02 / WR"),
            ]),
            _conn("J_AWG_OUT", "SMA-F 50R (16x)", "front_panel", "S6.4-02", [
                ("1-16", "AWG_CH[0:15]", "OUT", "1.25 GS/s 16-bit <10 ps jitter"),
            ]),
        ],
        "mating_part_ids": ["S7.2-03", "S7.2-02", "S6.4-02", "S6.5-01"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH11 (via S7.2-03)", "white_rabbit_port": "WR_COAX_4 (via S7.2-02)", "sync_role": "16-ch GRAPE/ENDOR AWG"},
    }

    specs["S7.2-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "2x FPGA 1 ns digital marker & pulse sequencer PXIe modules synced to WR + 10 MHz Rb.",
        "supply_rails": [_rail("PXIE_BACKPLANE_12V", 12.0, "DC", 4.0, 35.0, 50.0, "S7.2-03")],
        "connectors_and_pinout": [
            _conn("J_MARK", "SMA-F 50R LVTTL Markers (16x)", "front_panel", "S6.4-02", [
                ("1-16", "SEQ_MARKER[0:15]", "OUT", "1 ns resolution ESR/ENDOR/RO gates"),
            ]),
            _conn("J_WR_IN", "SMA-F 50R Trigger", "front_panel", "S7.4-02", [
                ("1", "WR_COAX_TRIG_4", "IN", "<200 ps trigger epoch"),
            ]),
        ],
        "mating_part_ids": ["S7.2-03", "S7.2-01", "S7.4-02", "S6.4-02"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH11 (via S7.2-03)", "white_rabbit_port": "WR_COAX_4", "sync_role": "1 ns pulse sequencer"},
    }

    specs["S7.2-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "18-slot 19-in PXIe chassis with <1 ps backplane skew locked to S7.4-01 CH11.",
        "supply_rails": [_rail("AC_MAINS_230V", 230.0, "AC_1PH", 3.5, 320.0, 600.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_10MHZ", "BNC-F 50R External Ref", "rack_rear", "S7.4-01", [
                ("1", "CLK_10MHZ_RB_CH11", "IN", "Backplane 10 MHz / 100 MHz PLL"),
            ]),
            _conn("J_PCIE", "MXI-Express Fiber/Copper", "front_panel", "S7.1-01", [
                ("1-8", "PXIE_HOST_LINK", "BIDIR", "Gen3 x8 host control"),
            ]),
        ],
        "mating_part_ids": ["S7.2-01", "S7.2-02", "S7.4-01", "S7.1-01", "S7.4-03"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": "CH11", "white_rabbit_port": None, "sync_role": "PXIe 10 MHz backplane distribution"},
    }

    specs["S7.4-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "10 MHz Rubidium atomic clock (SRS FS725/PRS10, <5e-11, <-140 dBc/Hz) + 16-ch isolated amp on Tier-1 UPS.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.5, 45.0, 85.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_10M_OUT", "16x Isolated BNC/SMA 50R (+13 dBm)", "rack_rear", "S7.4-02", [
                ("CH1-2", "ZU48DR_RFSOC_CLK", "OUT", "To S6.11-01 (2x boards)"),
                ("CH3-6", "ESR_VSG_CLK", "OUT", "To S6.4-01 (4x VSGs)"),
                ("CH7-10", "ENDOR_DDS_CLK", "OUT", "To S6.5-01 (4x DDS)"),
                ("CH11", "PXIE_BP_CLK", "OUT", "To S7.2-03 chassis"),
                ("CH12", "ZCU216_TREE_CLK", "OUT", "To S6.6-06 (14x ZCU216)"),
                ("CH13", "IBIC_FPGA_CLK", "OUT", "To S3.3-04 / S3.3-01"),
                ("CH14", "WR_GM_10M_1PPS", "OUT", "To S7.4-02 White Rabbit"),
                ("CH15", "INTF_DSP_CLK", "OUT", "To S4.4-01 / S4.5-03"),
                ("CH16", "SPARE_MON_CLK", "OUT", "Phase-noise test port"),
            ]),
        ],
        "mating_part_ids": ["S6.11-01", "S6.4-01", "S6.5-01", "S7.2-03", "S6.6-06", "S3.3-04", "S7.4-02", "S4.4-01", "S7.SAFETY-04"],
        "interlock_hooks": [],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 45.0,
        "timing_sync": {"rb_10mhz_port": "MASTER_SOURCE", "white_rabbit_port": "GM_REF_IN", "sync_role": "Primary 10 MHz + 1 PPS atomic master"},
    }

    specs["S7.4-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "White Rabbit <200 ps sub-ns trigger fan-out switch (8x SFP+ optical + 8x 50R coax) on Tier-1 UPS.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.4, 35.0, 55.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_GM_REF", "2x SMA-F (10 MHz + 1 PPS)", "rack_front", "S7.4-01", [
                ("1", "RB_10MHZ_IN", "IN", "From S7.4-01 CH14"),
                ("2", "RB_1PPS_IN", "IN", "1 PPS epoch sync"),
            ]),
            _conn("J_WR_SFP", "8x SFP+ 1000BASE-BX Single-Mode", "rack_front", "S6.11-01", [
                ("SFP1", "WR_ZU48DR_BOED", "OUT", "To S6.11-01"),
                ("SFP2", "WR_ZCU216_BANK", "OUT", "To S6.6-06"),
                ("SFP3", "WR_BLANKER_ISO", "OUT", "To S3.3-02 (-5 kV optical)"),
                ("SFP4", "WR_QEC_100G_SW", "OUT", "To S9.HPC-02"),
                ("SFP5", "WR_PYRO_AOM", "OUT", "To S5.5-03"),
                ("SFP6", "WR_TRIM_DSP", "OUT", "To S4.5-03"),
                ("SFP7", "WR_CERT_DB", "OUT", "To S7.1-02"),
                ("SFP8", "WR_SPARE_OPT", "OUT", "Expansion port"),
            ]),
            _conn("J_WR_COAX", "8x SMA-F 50R LVTTL Trigger", "rack_rear", "S3.3-04", [
                ("COAX1", "TRIG_IBIC_FPGA", "OUT", "To S3.3-04 / S3.3-01"),
                ("COAX2", "TRIG_BEAM_DOSE", "OUT", "To S1.4-03"),
                ("COAX3", "TRIG_PT420_FF", "OUT", "To S6.9-04"),
                ("COAX4", "TRIG_PXIE_SEQ", "OUT", "To S7.2-02"),
                ("COAX5", "TRIG_PIEZO_STG", "OUT", "To S4.3-04"),
                ("COAX6", "TRIG_FLASH_ANN", "OUT", "To S5.3-01"),
                ("COAX7", "TRIG_SAFETY_LOG", "OUT", "To S7.SAFETY-03"),
                ("COAX8", "TRIG_SPARE_COAX", "OUT", "Scope verification port"),
            ]),
        ],
        "mating_part_ids": ["S7.4-01", "S6.11-01", "S6.6-06", "S3.3-02", "S3.3-04", "S7.2-02", "S9.HPC-02", "S7.SAFETY-04"],
        "interlock_hooks": [],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 35.0,
        "timing_sync": {"rb_10mhz_port": "CH14", "white_rabbit_port": "MASTER_DISTRIBUTOR", "sync_role": "Sub-200 ps deterministic trigger switch"},
    }

    specs["S7.4-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "2x 42U EMI-shielded (>60 dB @ 1 GHz) RF & control cabinets + water/air HX; bonded to FACILITY_PE.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.4, 35.0, 120.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_GND_BAR", "Copper PE Grounding Busbar (2x)", "cabinet_base", "S7.SAFETY-04", [
                ("PE", "FACILITY_PE_STAR", "PWR", "<0.1 Ohm to facility earth"),
            ]),
            _conn("J_ENV", "RJ45 Thermal/Fan Telemetry", "cabinet_top", "S7.1-01", [
                ("1-8", "CAB_TEMP_FLOW_MON", "OUT", "±1 C thermal control loop"),
            ]),
        ],
        "mating_part_ids": ["S7.SAFETY-04", "S7.1-03", "S7.1-01", "S6.11-01"],
        "interlock_hooks": [_hook("CABINET_OVERTEMP_45C", "S7.4-04", "Alarm & shed non-critical rack power", 500.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 35.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "EMI shielded enclosure & cooling"},
    }

    specs["S7.SAFETY-04"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "15 kVA / 13.5 kW / 10 kWh Online Double-Conversion LFP UPS (0 ms transfer) + tiered load-shed PDU.",
        "supply_rails": [
            _rail("AC_FACILITY_IN_3PH", 400.0, "AC_3PH", 32.0, 350.0, 13850.0, "S7.SAFETY-04"),
            _rail("UPS_TIER1_BUS_230V", 230.0, "AC_1PH", 16.0, 2533.0, 3500.0, "S7.SAFETY-04"),
            _rail("UPS_TIER2_SHED_BUS", 230.0, "AC_1PH", 32.0, 2775.0, 10967.0, "S7.SAFETY-04"),
        ],
        "connectors_and_pinout": [
            _conn("J_MAINS_IN", "IEC 60309 3P+N+PE 32A", "facility_bay", "S7.4-03", [
                ("L1-L3", "UTILITY_400V_3PH", "IN", "400 VAC 3-phase input"),
                ("N", "UTILITY_N", "IN", "Neutral"),
                ("PE", "FACILITY_PE", "PWR", "Main earth bond"),
            ]),
            _conn("J_PDU_T1", "Tier-1 Critical Outlet Bank (IEC C13/C19)", "pdu_tier1", "S7.SAFETY-03", [
                ("1-16", "UPS_TIER1_230V", "OUT", "2.533 kW critical (213.2 min runtime)"),
            ]),
            _conn("J_PDU_T2", "Tier-2 Sheddable Outlet Bank (IEC C19)", "pdu_tier2", "S9.HPC-01", [
                ("1-8", "UPS_TIER2_SHED_230V", "OUT", "Shed cleanly on outage"),
            ]),
            _conn("J_EPO_DRY", "Phoenix 6-Pin EPO & Status", "front_ctrl", "S7.SAFETY-03", [
                ("1-2", "EPO_NC_LOOP", "IN", "Hardwired EPO trip"),
                ("3-4", "ON_BATTERY_OUT", "OUT", "Triggers Tier-2 shed at t=0.5 s"),
            ]),
        ],
        "mating_part_ids": ["S7.SAFETY-03", "S7.SAFETY-01", "S7.1-03", "S7.4-03", "S9.HPC-01", "S6.8-02"],
        "interlock_hooks": [_hook("UTILITY_LOSS_0MS_HOLD", "S7.SAFETY-03", "Zero-ms hold Tier-1; trigger Tier-2 load-shed", 0.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "UPS_INTERNAL_LOSS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Master facility UPS & load-shed PDU"},
    }

    specs["S7.SAFETY-05"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Cleanroom O2 monitor (19.5% alarm), ASME DN50 0.5 barg OVC burst disk & 1.563 Ohm quench dump bank.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.3, 35.0, 50.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_O2_ALM", "Phoenix 6-Pin 4-20 mA + Dual NC", "wall_mount", "S7.SAFETY-03", [
                ("1-2", "O2_4_20MA", "OUT", "0-25% O2 sensor loop"),
                ("3-6", "O2_LT_19P5_1OO2D", "OUT", "Dual-channel SIL-3 target alarm"),
            ]),
            _conn("J_DUMP_BUS", "M10 Insulated 500V Studs", "dump_bay", "S6.3-04", [
                ("1", "DUMP_1P563_POS", "IN", "1.563 Ohm, 18.94 kJ, Vpeak<=400 V"),
                ("2", "DUMP_1P563_NEG", "IN", "2.5 kg bank, Tpeak=38.1 C < 55 C"),
            ]),
        ],
        "mating_part_ids": ["S6.3-04", "S6.3-05", "S6.8-04", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [
            _hook("O2_DEFICIENCY_19P5PCT", "S7.SAFETY-03", "Activate cleanroom ODH beacon/exhaust & safe halt", 500.0),
            _hook("QUENCH_DUMP_THERMAL_55C", "S7.SAFETY-03", "Inhibit magnet recharge until dump bank cools", 100.0),
        ],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 35.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "ODH monitor & passive 1.563 Ohm quench dump"},
    }

    specs["S9.HPC-01"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "2x 2U QEC decoder nodes (2x H100/Alveo-U280 + Dual-100G ConnectX-7 RoCEv2); Tier-2 graceful halt.",
        "supply_rails": [_rail("AC_UPS_TIER2_SHED", 230.0, "AC_1PH", 12.0, 2100.0, 2500.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_AC", "4x IEC C19 Redundant PSU", "rack_rear", "S9.HPC-03", [
                ("L-N-PE", "UPS_T2_SHED_230V", "IN", "2100 W total (2 nodes), shed @ t=60 s"),
            ]),
            _conn("J_100G", "4x QSFP28-100G-SR4", "rack_rear", "S9.HPC-02", [
                ("1-4", "ROCEV2_100G_OM4", "BIDIR", "Surface d=37 6.34 us / qLDPC 2.32 us"),
            ]),
        ],
        "mating_part_ids": ["S9.HPC-02", "S9.HPC-03", "S6.11-01", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("UPS_TIER2_GRACEFUL_HALT", "S7.SAFETY-04", "Checkpoint syndromes & power down within 60 s", 60000.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 2100.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_SFP_4 (via S9.HPC-02)", "sync_role": "Real-time QEC decoder cluster"},
    }

    specs["S9.HPC-02"] = {
        "electrical_class": "E3",
        "grounding_domain": "DGND",
        "grounding_notes": "1U cut-through 100GbE RoCEv2 optical switch + 4x QSFP28-SR4 + 20 m OM4 (0.777 us ingest); Tier-2.",
        "supply_rails": [_rail("AC_UPS_TIER2_SHED", 230.0, "AC_1PH", 0.8, 95.0, 140.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_QSFP28", "4x QSFP28-100G-SR4 MPO-12", "rack_front", "S9.HPC-01", [
                ("P1-P2", "QEC_NODE_100G[0:1]", "BIDIR", "To S9.HPC-01 ConnectX-7"),
                ("P3-P4", "ZU48DR_CMAC_100G[0:1]", "BIDIR", "To S6.11-01 RFSoC CMAC"),
            ]),
            _conn("J_WR", "SFP+ PTP/WR Sync", "rack_front", "S7.4-02", [
                ("1", "WR_SFP_4", "IN", "Deterministic RDMA epoch"),
            ]),
        ],
        "mating_part_ids": ["S9.HPC-01", "S9.HPC-03", "S6.11-01", "S7.4-02", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("UPS_TIER2_SHED", "S7.SAFETY-04", "Power down after S9.HPC-01 halt", 60000.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 95.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_SFP_4", "sync_role": "Cut-through 100G QEC fabric"},
    }

    specs["S9.HPC-03"] = {
        "electrical_class": "E3",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Redundant 2.6 kW 80+ Titanium PSU modules, sliding rails & ZU48DR 100G CMAC kit (0 W added load).",
        "supply_rails": [_rail("AC_UPS_TIER2_SHED", 230.0, "AC_1PH", 12.0, 0.0, 2600.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_PSU_BAY", "CRPS Redundant Backplane + IEC C19", "rack_rear", "S9.HPC-01", [
                ("1", "12V_HPC_REDUNDANT", "OUT", "99.99% N+1 PSU backing S9.HPC-01"),
            ]),
        ],
        "mating_part_ids": ["S9.HPC-01", "S9.HPC-02", "S6.11-01", "S7.SAFETY-04"],
        "interlock_hooks": [],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Redundant HPC PSU & CMAC kit"},
    }

    # =========================================================================
    # E4 — 43 ELECTRO-MECHANICAL / HV-ELECTRODE / VACUUM / PIEZO / HEATER / SENSOR
    # =========================================================================

    specs["S1.1-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "31P+ PH3 duoplasmatron plasma chamber floating on +5..+15 kV source deck; water-cooled.",
        "supply_rails": [
            _rail("ARC_DISCHARGE_DC", 120.0, "DC", 3.0, 240.0, 360.0, "S1.1-05"),
            _rail("CATHODE_FILAMENT", 12.0, "DC", 15.0, 140.0, 180.0, "S1.1-05"),
        ],
        "connectors_and_pinout": [
            _conn("J_ARC_HV", "CF40 HV Ceramic Power Feedthrough", "source_head", "S1.1-05", [
                ("1", "ANODE_POS", "IN", "+120 V arc over HV deck"),
                ("2", "CATHODE_FIL_A", "IN", "15 A filament"),
                ("3", "CATHODE_FIL_B", "IN", "Filament return"),
                ("4", "INTERMEDIATE_ELEC", "IN", "Duoplasmatron Z-focus"),
            ]),
        ],
        "mating_part_ids": ["S1.1-03", "S1.1-04", "S1.1-05", "S1.6-01"],
        "interlock_hooks": [_hook("COOLING_WATER_FLOW_OK", "S7.4-04", "Cut arc/filament on water-flow loss", 50.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "CW 31P+ plasma ion source"},
    }

    specs["S1.1-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "29Si+/28Si+ SiF4 duoplasmatron plasma chamber floating on HV source deck (Mode A line).",
        "supply_rails": [
            _rail("ARC_DISCHARGE_DC", 120.0, "DC", 3.0, 240.0, 360.0, "S1.1-05"),
            _rail("CATHODE_FILAMENT", 12.0, "DC", 15.0, 140.0, 180.0, "S1.1-05"),
        ],
        "connectors_and_pinout": [
            _conn("J_ARC_HV", "CF40 HV Ceramic Power Feedthrough", "source_head", "S1.1-05", [
                ("1", "ANODE_POS_SI", "IN", "+120 V arc over HV deck"),
                ("2-3", "FILAMENT_SI", "IN", "15 A cathode heater"),
                ("4", "INTERMEDIATE_ELEC_SI", "IN", "Plasma constriction bias"),
            ]),
        ],
        "mating_part_ids": ["S1.1-03", "S1.1-04", "S1.1-05", "S1.6-01"],
        "interlock_hooks": [_hook("COOLING_WATER_FLOW_SI", "S7.4-04", "Cut Si-source arc on water loss", 50.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "CW 29Si+/28Si+ ion source"},
    }

    specs["S1.1-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "2x Mo/Ti-6Al-4V/sapphire 10-15 keV HV extraction electrode stacks (Exp124).",
        "supply_rails": [_rail("HV_EXTRACT_15KV", 15000.0, "HV_DC", 0.002, 10.0, 30.0, "S1.1-05")],
        "connectors_and_pinout": [
            _conn("J_EXT_HV", "CF40 20 kV Ceramic HV Feedthrough (2x)", "source_column", "S1.1-05", [
                ("1", "V_EXTRACT_10_15KV", "IN", "10-15 kV extraction lens"),
                ("2", "V_PULLER_FOCUS", "IN", "Puller focus trim"),
                ("3", "SUPPRESSOR_ELEC", "IN", "Secondary electron suppressor"),
            ]),
        ],
        "mating_part_ids": ["S1.1-01", "S1.1-02", "S1.1-05", "S1.2-01"],
        "interlock_hooks": [_hook("HV_CROWBAR_EXTRACT", "S7.SAFETY-03", "Discharge <50 V in 18.3 ms", 18.3)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Electrostatic extraction optics"},
    }

    specs["S1.1-04"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "2x UHV VCR 0.1-10 sccm PH3/SiF4 mass flow controllers & manifold; Chassis PE + isolated 24 V.",
        "supply_rails": [_rail("DC_24V_CTRL", 24.0, "DC", 0.5, 10.0, 15.0, "S1.6-01")],
        "connectors_and_pinout": [
            _conn("J_MFC", "DB15 Shielded MFC Bus (2x)", "gas_manifold", "S1.4-03", [
                ("1", "+24V_MFC", "IN", "+24 VDC"),
                ("2", "FLOW_SET_0_5V", "IN", "0.1-10 sccm setpoint"),
                ("3", "FLOW_MON_0_5V", "OUT", "±1% FS readback"),
                ("4", "VALVE_CLOSE_ILK", "IN", "Hardwired slam-shut on PH3/EPO"),
            ]),
        ],
        "mating_part_ids": ["S1.1-01", "S1.1-02", "S1.4-03", "S1.6-01", "S7.SAFETY-01"],
        "interlock_hooks": [_hook("PH3_MFC_SLAM_SHUT", "S7.SAFETY-03", "Force-close MFC valves on PH3 >0.02 ppm or EPO", 45.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Source gas flow control"},
    }

    specs["S1.2-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "2x Wien ExB 0.45 T SmCo/electromagnet pole yokes (L=150 mm, m/dm>=60); trim coil grounded via PE.",
        "supply_rails": [_rail("WIEN_B_TRIM_DC", 24.0, "DC", 2.0, 30.0, 48.0, "S1.2-03")],
        "connectors_and_pinout": [
            _conn("J_BTRIM", "Binder M12 4-Pin (2x)", "column_side", "S1.2-03", [
                ("1-2", "B_TRIM_COIL_PN", "IN", "±0.1% B fine trim"),
                ("3-4", "HALL_PROBE_SENSE", "OUT", "0.45 T closed-loop B feedback"),
            ]),
        ],
        "mating_part_ids": ["S1.2-02", "S1.2-03", "S1.1-03"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Static ExB mass-filter magnet"},
    }

    specs["S1.2-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "2x OFHC/Mo/Macor Wien electrostatic deflector plate pairs (±20 kV/m, ±10 um parallelism).",
        "supply_rails": [_rail("WIEN_HV_BIPOLAR", 5000.0, "HV_DC", 0.001, 0.5, 2.0, "S1.2-03")],
        "connectors_and_pinout": [
            _conn("J_CF40_SHV", "CF40 Dual SHV-10kV Feedthrough (2x)", "column_uhv", "S1.2-03", [
                ("1", "WIEN_PLATE_POS", "IN", "+E_Wien balanced"),
                ("2", "WIEN_PLATE_NEG", "IN", "-E_Wien balanced"),
            ]),
        ],
        "mating_part_ids": ["S1.2-01", "S1.2-03", "S1.2-04"],
        "interlock_hooks": [_hook("WIEN_HV_SAFE", "S7.SAFETY-03", "Zero plate HV via S1.2-03 on interlock", 18.3)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Electrostatic ExB balance plates"},
    }

    specs["S1.3-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "Arch-B 10->5 keV deceleration immersion lens (upper liner -5 kV, wafer 0 V, E_gap=10.60 MV/m).",
        "supply_rails": [_rail("DECEL_LINER_N5KV", -5000.0, "HV_DC", 0.002, 5.0, 10.0, "S1.3-03")],
        "connectors_and_pinout": [
            _conn("J_DECEL_HV", "CF40 Dual SHV-10kV UHV Feedthrough", "column_lower", "S1.3-03", [
                ("1", "UPPER_LINER_N5KV", "IN", "-5.000 kV ±0.5 V (dE/E <= 1e-4)"),
                ("2", "LENS_FOCUS_ELEC", "IN", "Immersion focus trim electrode"),
            ]),
        ],
        "mating_part_ids": ["S1.3-01", "S1.3-03", "S2.1-01"],
        "interlock_hooks": [_hook("COLUMN_HV_CROWBAR", "S7.SAFETY-03", "Discharge -5 kV liner via 2 MOhm crowbar", 18.3)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Precision deceleration optics"},
    }

    specs["S1.4-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "2x retractable UHV Faraday cups (1 fA-10 uA) with -100 V secondary-electron suppressor ring.",
        "supply_rails": [
            _rail("SUPPRESSOR_N100V", -100.0, "DC", 0.001, 0.1, 0.2, "S1.4-02"),
            _rail("PNEUMATIC_SOL_24V", 24.0, "DC", 0.4, 5.0, 10.0, "S1.4-03"),
        ],
        "connectors_and_pinout": [
            _conn("J_TRIAX", "CF16 Triax UHV Feedthrough (2x)", "column_uhv", "S1.4-02", [
                ("CTR", "CUP_CURRENT_OUT", "OUT", "1 fA - 10 uA"),
                ("GRD", "GUARD_SHIELD", "IN", "Driven guard"),
            ]),
            _conn("J_SUPP", "MHV/SHV Suppressor + Limit Switch", "column_uhv", "S1.4-03", [
                ("1", "SUPP_RING_N100V", "IN", "-100 V SE suppression"),
                ("2-3", "CUP_IN_OUT_SW", "OUT", "Pneumatic actuator end-stops"),
            ]),
        ],
        "mating_part_ids": ["S1.4-02", "S1.4-03", "S1.3-05"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Beam current calibration probe"},
    }

    specs["S1.5-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "HDA-HiRes hemispherical energy analyzer (R0=40 mm, dE_FWHM=0.453 eV) floating on column HV.",
        "supply_rails": [_rail("HDA_HEMI_HV", 5000.0, "HV_DC", 0.001, 2.0, 5.0, "S1.5-03")],
        "connectors_and_pinout": [
            _conn("J_HDA_FT", "CF40 Dual SHV-10kV Feedthrough", "column_mid", "S1.5-03", [
                ("1", "HEMI_INNER_V", "IN", "R_in hemisphere electrode"),
                ("2", "HEMI_OUTER_V", "IN", "R_out hemisphere electrode"),
            ]),
        ],
        "mating_part_ids": ["S1.5-02", "S1.5-03", "S1.3-01"],
        "interlock_hooks": [_hook("HDA_HV_CROWBAR", "S7.SAFETY-03", "Discharge via S1.5-03", 18.3)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Passive electrostatic monochromator"},
    }

    specs["S1.5-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "UHV piezo-driven 5-50 um HDA entrance/exit slits (±0.5 um step).",
        "supply_rails": [_rail("PIEZO_SLIT_100V", 100.0, "DC", 0.05, 2.0, 5.0, "S4.3-04")],
        "connectors_and_pinout": [
            _conn("J_SLIT", "CF16 9-Pin Sub-D UHV", "column_mid", "S4.3-04", [
                ("1-4", "SLIT_PIEZO_DRV", "IN", "0-100 V stick-slip piezo"),
                ("5-8", "SLIT_ENC_FB", "OUT", "±0.5 um width readback"),
            ]),
        ],
        "mating_part_ids": ["S1.5-01", "S4.3-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Motorized energy slit actuator"},
    }

    specs["S1.6-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Dual-cylinder exhausted PH3/SiF4 toxic gas cabinet (SEMI S2 / NFPA 318); interlocked to S7.SAFETY-01/03.",
        "supply_rails": [_rail("AC_FACILITY_230V", 230.0, "AC_1PH", 1.5, 180.0, 300.0, "S7.SAFETY-01")],
        "connectors_and_pinout": [
            _conn("J_PLC_CAB", "Phoenix 12-Pin Safety Bus", "gas_bay", "S7.SAFETY-03", [
                ("1-2", "N2_PURGE_STATUS", "OUT", "Auto N2 purge OK"),
                ("3-4", "EXHAUST_FLOW_OK", "OUT", "Negative-pressure cabinet switch"),
                ("5-6", "CYL_VALVE_CLOSE_1OO2D", "IN", "Pneumatic fail-close cylinder valve"),
            ]),
        ],
        "mating_part_ids": ["S1.1-04", "S1.6-02", "S7.SAFETY-01", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("GAS_CAB_EXHAUST_FAIL", "S7.SAFETY-03", "Slam-shut PH3 cylinder valve (<12 s)", 45.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Toxic gas cabinet controller"},
    }

    specs["S1.6-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Dry-bed catalytic PH3 scrubber & 50 ppb exhaust detector interlocked to S7.4-04 / S7.SAFETY-03.",
        "supply_rails": [_rail("DC_24V_SAFETY", 24.0, "DC", 1.0, 20.0, 30.0, "S7.SAFETY-01")],
        "connectors_and_pinout": [
            _conn("J_SCRUB", "Phoenix 6-Pin 4-20 mA + NC", "exhaust_line", "S7.4-04", [
                ("1-2", "PH3_EXHAUST_4_20MA", "OUT", "<50 ppb outlet monitor"),
                ("3-4", "PH3_ALARM_NC", "OUT", "Trips PLC <5 s if >=50 ppb"),
            ]),
        ],
        "mating_part_ids": ["S1.6-01", "S7.4-04", "S7.SAFETY-01", "S7.SAFETY-03"],
        "interlock_hooks": [_hook("PH3_EXHAUST_50PPB", "S7.4-04", "Close gas supply & alarm facility", 5000.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Exhaust PH3 safety monitor"},
    }

    specs["S1.7-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "S1-Multi 3-species quick-swap cartridge bay (31P/121Sb 450C oven/167Er); 180 W peak Tier-2 shed.",
        "supply_rails": [_rail("OVEN_HEATER_450C", 48.0, "DC", 4.0, 180.0, 180.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_OVEN_FT", "CF40 Power + Thermocouple Feedthrough", "s1_plusY_flange", "S1.1-05", [
                ("1-2", "PBN_OVEN_HTR_PN", "IN", "180 W peak @ 450 C (0 W cryo)"),
                ("3-4", "TYPE_K_TC", "OUT", "Oven temperature feedback"),
                ("5-6", "MICRO_PAUL_RF", "IN", "167Er trap RF feed"),
            ]),
        ],
        "mating_part_ids": ["S1.1-01", "S1.1-05", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("OPTION_Q_OVEN_CUT", "S7.SAFETY-03", "Cut 180 W oven power at t=45 ms on EPO/outage", 45.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 180.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Multi-species source oven"},
    }

    specs["S2.1-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "Au/Pt anti-charging aperture membrane (<1 Ohm/sq) bonded directly to -5 kV column liner.",
        "supply_rails": [_rail("LINER_REF_N5KV", -5000.0, "HV_DC", 0.001, 0.0, 0.1, "S1.3-03")],
        "connectors_and_pinout": [
            _conn("P_CLAMP", "BeCu Spring Grounding Clip", "write_head_uhv", "S2.1-01", [
                ("1", "MEMBRANE_LINER_TIE", "PWR", "-5 kV anti-charging drain"),
            ]),
        ],
        "mating_part_ids": ["S2.1-01", "S2.1-04", "S1.3-02"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Anti-charging drain tie"},
    }

    specs["S2.2-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "HV_MINUS_5KV_DECK",
        "grounding_notes": "32x32=1024-ch MEMS electrostatic blanker plate (V_blank~27-53.3 V) floating on -5 kV deck.",
        "supply_rails": [_rail("BLANKER_HV_DRV", 53.3, "DC", 0.05, 1.5, 3.0, "S2.4-02")],
        "connectors_and_pinout": [
            _conn("P_BUMP", "1024-Ch Micro-Bump Array (0.50 mm pitch)", "write_head_uhv", "S2.2-03", [
                ("1-1024", "V_DEFLECT[0:1023]", "IN", "0 V open / 27-53.3 V blanked (<100 ns)"),
                ("GND", "DECK_N5KV_REF", "PWR", "-5 kV floating reference"),
            ]),
        ],
        "mating_part_ids": ["S2.2-03", "S2.4-01", "S2.4-02", "S2.2-04"],
        "interlock_hooks": [_hook("GLOBAL_BLANK_OVERRIDE", "S7.SAFETY-03", "Force all 1024 plates HIGH (<1 us) on fault", 0.001)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_SFP_3 (via S3.3-02)", "sync_role": "1024-beamlet deterministic blanker"},
    }

    specs["S2.2-04"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "Graphite-coated Mo beam-stop Faraday plate capturing 10 mrad deflected ions; drain to AGND.",
        "supply_rails": [_rail("PASSIVE_FARADAY_STOP", 0.0, "PASSIVE", 0.001, 0.0, 0.0, "S1.4-02")],
        "connectors_and_pinout": [
            _conn("J_STOP_MON", "UHV Coax Lug", "write_head_uhv", "S1.4-02", [
                ("1", "BEAMSTOP_I_MON", "OUT", "Intercepted blanked beam current"),
                ("2", "AGND_CHAMBER", "PWR", "0 V AGND"),
            ]),
        ],
        "mating_part_ids": ["S2.2-01", "S1.4-02", "S2.3-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Deflected beam dump & monitor"},
    }

    specs["S2.3-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "32x32=1024 Arch-B electrostatic mini-lens array (WD=0.250 mm, E_gap=10.60 MV/m, wafer=0 V).",
        "supply_rails": [_rail("MINILENS_HV_3RAIL", 2000.0, "HV_DC", 0.001, 1.0, 2.0, "S2.3-04")],
        "connectors_and_pinout": [
            _conn("J_LENS_HV", "3x UHV Ceramic HV Clips", "write_head_uhv", "S2.3-04", [
                ("1", "LENS_TOP_ELEC", "IN", "±2 kV <2 mVpp"),
                ("2", "LENS_MID_FOCUS", "IN", "±2 kV <5 ppm"),
                ("3", "LENS_BOT_0V", "PWR", "0 V wafer-plane reference"),
            ]),
        ],
        "mating_part_ids": ["S2.3-03", "S2.3-04", "S2.2-04"],
        "interlock_hooks": [_hook("MINILENS_HV_CROWBAR", "S7.SAFETY-03", "Clamp mini-lens HV on interlock", 18.3)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Sub-2 nm electrostatic focus array"},
    }

    specs["S2.5-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "3-axis head-to-stage relative capacitive sensors (<=0.1 nm RMS, 10 kHz BW); Kapton coax.",
        "supply_rails": [_rail("CAP_SENSOR_EXC", 15.0, "DC", 0.05, 1.0, 2.0, "S4.5-03")],
        "connectors_and_pinout": [
            _conn("J_CAP3", "3x UHV Triax Coax", "write_head_uhv", "S4.5-03", [
                ("1-3", "HEAD_STAGE_CAP_XYZ", "OUT", "<=0.1 nm RMS relative gap"),
                ("SHD", "AGND_GUARD", "PWR", "Driven guard"),
            ]),
        ],
        "mating_part_ids": ["S2.5-02", "S4.5-01", "S4.5-03"],
        "interlock_hooks": [_hook("WD_COLLISION_GUARD", "S4.3-04", "Halt Z approach if WD < 0.200 mm", 0.5)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "10 kHz head-stage metrology"},
    }

    specs["S2.5-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "Kinematic Invar-36 UHV piezo tip/tilt/Z head aligner (f1>=2.59 MHz, ±0.1 urad).",
        "supply_rails": [_rail("PIEZO_HEAD_120V", 120.0, "DC", 0.05, 2.0, 6.0, "S4.3-04")],
        "connectors_and_pinout": [
            _conn("J_HEAD_PZT", "UHV 9-Pin Micro-D", "write_head_uhv", "S4.3-04", [
                ("1-6", "HEAD_PZT_TTZ[0:2]", "IN", "0-120 V tip/tilt/Z actuators"),
                ("7-9", "SG_FB_RETURN", "OUT", "Strain-gauge feedback"),
            ]),
        ],
        "mating_part_ids": ["S2.5-01", "S2.5-03", "S4.3-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Quasi-static head alignment"},
    }

    specs["S3.1-04"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "Non-magnetic Au-plated BeCu cantilever IBIC wafer contact ring (<50 mOhm, load-lock swap).",
        "supply_rails": [_rail("IBIC_BIAS_100V", 100.0, "DC", 0.0001, 0.0, 0.01, "S3.2-03")],
        "connectors_and_pinout": [
            _conn("P_RING", "Au/BeCu Spring Fingers", "cold_island_100K", "S3.1-01", [
                ("1", "WAFER_BACK_HV_BIAS", "IN", "0-100 V (<10 uVrms)"),
                ("2", "GUARD_RING_DRV", "IN", "Driven guard ring"),
                ("3-10", "IBIC_PIXEL_PAD[0:7]", "OUT", "To S3.2-04 micro-coax"),
            ]),
        ],
        "mating_part_ids": ["S3.1-01", "S3.1-02", "S3.2-03", "S3.2-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Removable IBIC wafer contact"},
    }

    specs["S3.2-05"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "4x CF63 hermetic 32-coax UHV feedthrough flanges (128 ch total) bridging 100 K CSA to 300 K shaper.",
        "supply_rails": [_rail("PASSIVE_CF63_COAX", 0.0, "PASSIVE", 0.01, 0.0, 0.0, "S3.2-01")],
        "connectors_and_pinout": [
            _conn("J_VAC", "32x SMB/SMA Cryo-UHV (per flange)", "uhv_side", "S3.2-01", [
                ("1-32", "CSA_COAX_VAC[0:31]", "IN", "50 Ohm driven CSA outputs"),
            ]),
            _conn("J_AIR", "32x SMA-F Air Side (per flange)", "air_side", "S3.2-02", [
                ("1-32", "CSA_COAX_AIR[0:31]", "OUT", "To 300 K ADA4817 shaper"),
            ]),
        ],
        "mating_part_ids": ["S3.2-01", "S3.2-02", "S3.2-04", "S5.1-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Hermetic 128-ch IBIC feedthrough"},
    }

    specs["S4.2-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "6-DOF active piezo vibration isolation table (0.5-100 Hz, >30 dB @ 10 Hz) bonded to PE.",
        "supply_rails": [_rail("PIEZO_TABLE_150V", 150.0, "DC", 0.5, 40.0, 80.0, "S4.2-03")],
        "connectors_and_pinout": [
            _conn("J_TBL", "MIL-DTL-38999 12-Pin", "table_side", "S4.2-03", [
                ("1-12", "ISO_ACT_6DOF", "IN", "Active piezo cancellation drive"),
            ]),
        ],
        "mating_part_ids": ["S4.2-02", "S4.2-03", "S4.1-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Active vibration actuator table"},
    }

    specs["S4.2-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "3-axis 4.5 Hz seismic geophone/accelerometer pack (<1 ng/rtHz @ 10 Hz) with shielded twisted pairs.",
        "supply_rails": [_rail("IEPE_24V_4MA", 24.0, "DC", 0.02, 0.5, 0.5, "S4.2-03")],
        "connectors_and_pinout": [
            _conn("J_GEO", "LEMO 1B 8-Pin Shielded", "granite_block", "S4.2-03", [
                ("1-6", "GEO_XYZ_DIFF", "OUT", "3-axis velocity/accel feedback"),
                ("7-8", "AGND_SHIELD", "PWR", "0 V AGND"),
            ]),
        ],
        "mating_part_ids": ["S4.2-01", "S4.2-03", "S4.1-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Seismic feedback sensor"},
    }

    specs["S4.3-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "6-DOF UHV non-magnetic Ti/Invar fine piezo flexure stage (200 um stroke, 0.2 nm res).",
        "supply_rails": [_rail("PIEZO_FINE_120V", 120.0, "DC", 0.2, 5.0, 24.0, "S4.3-04")],
        "connectors_and_pinout": [
            _conn("J_STAGE_UHV", "CF40 15-Pin Kapton UHV Feedthrough", "uhv_stage", "S4.3-04", [
                ("1-12", "FINE_PZT_6AXIS", "IN", "-20..+120 V closed-loop piezo"),
                ("13", "STAGE_AGND", "PWR", "0 V AGND"),
            ]),
        ],
        "mating_part_ids": ["S4.3-02", "S4.3-03", "S4.3-04", "S4.4-03"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Sub-nm wafer fine positioning"},
    }

    specs["S4.3-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "UHV non-magnetic coarse stick-slip XY piezo stepper stage (±25 mm, ±50 nm, zero holding power).",
        "supply_rails": [_rail("STICK_SLIP_60V", 60.0, "DC", 0.3, 1.0, 18.0, "S4.3-04")],
        "connectors_and_pinout": [
            _conn("J_COARSE", "CF40 9-Pin Sub-D UHV", "uhv_stage", "S4.3-04", [
                ("1-4", "XY_STICKSLIP_DRV", "IN", "Sawtooth 0-60 V stepping"),
                ("5-8", "OPT_ENC_ABZ", "OUT", "±50 nm coarse encoder"),
            ]),
        ],
        "mating_part_ids": ["S4.3-01", "S4.3-04", "S5.1-01"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Field-to-field stepping"},
    }

    specs["S4.3-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "In-stage capacitive position sensors & Kapton coax (<0.02% nonlinearity, ±0.2 nm).",
        "supply_rails": [_rail("CAP_FB_EXC", 10.0, "DC", 0.02, 0.2, 0.2, "S4.3-04")],
        "connectors_and_pinout": [
            _conn("J_CAP_UHV", "CF40 6x Coax UHV Feedthrough", "uhv_stage", "S4.3-04", [
                ("1-6", "STAGE_CAP_FB[0:5]", "OUT", "Sub-nm servo feedback"),
            ]),
        ],
        "mating_part_ids": ["S4.3-01", "S4.3-04"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Fine piezo closed-loop metrology"},
    }

    specs["S4.5-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "DGND",
        "grounding_notes": "Dark-field CMOS fiducial alignment microscope on UHV viewport (<=1 nm multi-frame centroid).",
        "supply_rails": [_rail("POE_OR_12V_CAM", 12.0, "DC", 0.8, 8.0, 10.0, "S7.1-01")],
        "connectors_and_pinout": [
            _conn("J_GIGE", "RJ45 GigE Vision PoE", "viewport_air", "S7.1-01", [
                ("1-8", "FIDUCIAL_GIGE", "OUT", "Raw dark-field frames to host"),
            ]),
        ],
        "mating_part_ids": ["S4.5-01", "S7.1-01", "S5.1-05"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Pre-write fiducial registration"},
    }

    specs["S5.1-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Removable 150 C 4-zone PID UHV bakeout heater jacket (non-simultaneous maintenance phase only).",
        "supply_rails": [_rail("AC_BAKEOUT_230V", 230.0, "AC_1PH", 10.0, 0.0, 2200.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_BAKE", "4x Harting / Type-K PID Channels", "chamber_ext", "S7.4-04", [
                ("1-8", "BAKE_HTR_Z[1:4]", "IN", "230 VAC SSR PID (off during ops)"),
                ("9-16", "BAKE_TC_K[1:4]", "OUT", "150 C ±3 C feedback + 170 C thermal cutoff"),
            ]),
        ],
        "mating_part_ids": ["S5.1-01", "S7.4-04"],
        "interlock_hooks": [_hook("BAKEOUT_170C_CUTOFF", "S7.4-04", "Hard-cut heater SSR if T > 170 C or cryo cold", 50.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Maintenance-only UHV bakeout"},
    }

    specs["S5.1-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Load-lock chamber & VAT all-metal CF100 gate valve actuator on Tier-1 UPS (65 W hold/control).",
        "supply_rails": [_rail("DC_24V_UPS_T1", 24.0, "DC", 3.0, 65.0, 90.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_VALVE", "DB15 Valve Controller", "loadlock", "S7.SAFETY-03", [
                ("1-2", "SOL_24V_OPEN", "IN", "De-energize-to-close fail-safe"),
                ("3-6", "OPEN_CLOSED_LIM", "OUT", "Dual reed-switch verification"),
            ]),
        ],
        "mating_part_ids": ["S5.1-01", "S5.1-04", "S7.SAFETY-03", "S7.SAFETY-04", "S7.SAFETY-06"],
        "interlock_hooks": [_hook("LL_VALVE_FAIL_CLOSE", "S7.SAFETY-03", "Spring-return seal in <=80 ms on EPO/outage", 80.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 65.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "UHV load-lock isolation"},
    }

    specs["S5.2-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "UHV magnetically-levitated TMP (HiPace 300 class, 260 L/s); Tier-1 UPS backed for controlled spindown.",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 1.5, 220.0, 320.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_TMP_PWR", "IEC C14 Tier-1 UPS", "pump_ctrl", "S7.SAFETY-04", [
                ("L-N-PE", "UPS_T1_230V", "IN", "220 W cruise / safe spindown"),
            ]),
            _conn("J_TMP_IO", "DB15 RS485 + Fault Relay", "pump_ctrl", "S7.4-04", [
                ("1-2", "TMP_AT_SPEED_OK", "OUT", "Interlock to foreline valve"),
                ("3-4", "TMP_STOP_CMD", "IN", "Controlled spindown on outage"),
            ]),
        ],
        "mating_part_ids": ["S5.1-01", "S5.2-03", "S7.4-04", "S7.SAFETY-04", "S7.SAFETY-06"],
        "interlock_hooks": [_hook("TMP_FAIL_VALVE_CLOSE", "S7.SAFETY-06", "Close foreline valve <80 ms on TMP fault", 80.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 220.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Main UHV pumping"},
    }

    specs["S5.2-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "VacIon 75 ion pump + TSP (zero-vibration write-mode pumping <=1e-10 mbar) on Tier-1 UPS (160 W).",
        "supply_rails": [
            _rail("AC_UPS_TIER1", 230.0, "AC_1PH", 1.2, 160.0, 260.0, "S7.SAFETY-04"),
            _rail("ION_PUMP_HV", 5000.0, "HV_DC", 0.02, 40.0, 100.0, "S5.2-02"),
        ],
        "connectors_and_pinout": [
            _conn("J_HV_ION", "StarCell HV Safety Cable", "pump_ctrl", "S5.1-01", [
                ("1", "ION_ANODE_5KV", "OUT", "3-7 kV current-limited HV"),
                ("2", "INTERLOCK_SHIELD", "IN", "Cable-disconnect interlock"),
            ]),
        ],
        "mating_part_ids": ["S5.1-01", "S5.2-04", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("ION_PUMP_OVERPRESSURE", "S5.2-04", "Disable 5 kV ion pump if P > 1e-5 mbar", 50.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 160.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Zero-vibration UHV hold pump"},
    }

    specs["S5.2-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Oil-free dry scroll backing pump (15 m3/h); facility mains with fast foreline isolation valve on outage.",
        "supply_rails": [_rail("AC_FACILITY_230V", 230.0, "AC_1PH", 3.0, 450.0, 650.0, "S7.4-03")],
        "connectors_and_pinout": [
            _conn("J_AC", "IEC C14 + Remote Start/Stop", "pump_base", "S7.4-03", [
                ("L-N-PE", "FACILITY_230V", "IN", "450 W scroll motor"),
                ("CTRL", "SCROLL_STATUS_OK", "OUT", "Trips foreline valve on loss"),
            ]),
        ],
        "mating_part_ids": ["S5.2-01", "S5.1-03", "S7.SAFETY-06"],
        "interlock_hooks": [_hook("BACKING_LOSS_SEAL", "S7.SAFETY-06", "Close foreline valve <80 ms on scroll power loss", 80.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Roughing/backing pump"},
    }

    specs["S5.6-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "CF100 crucible-free DC 28Si rod sublimation source & PSU (400 W growth, 0 uW cryo); Tier-2 shed.",
        "supply_rails": [_rail("DC_SUBLIMATION_400W", 20.0, "DC", 25.0, 400.0, 450.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_SUB_PWR", "CF100 High-Current Water-Cooled Feedthrough", "loadlock_plusZ", "S7.SAFETY-04", [
                ("1-2", "SI28_ROD_DC_PN", "IN", "400 W DC sublimation current"),
                ("3-4", "SHUTTER_SOL_24V", "IN", "Pneumatic shutter fail-close (45 ms)"),
            ]),
        ],
        "mating_part_ids": ["S5.1-03", "S5.6-02", "S5.6-04", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("MBE_SHUTTER_EPO_CUT", "S7.SAFETY-03", "Close pneumatic shutter & cut 400 W at t=45 ms", 45.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 400.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "In-situ 28Si MBE capper"},
    }

    specs["S5.6-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "AGND",
        "grounding_notes": "Enriched 28Si rod (<50 ppm 29Si) + UHV 6 MHz quartz QCM thickness monitor (±0.3 nm).",
        "supply_rails": [_rail("QCM_OSC_12V", 12.0, "DC", 0.2, 2.0, 3.0, "S5.6-01")],
        "connectors_and_pinout": [
            _conn("J_QCM", "CF16 BNC UHV Feedthrough", "loadlock_plusZ", "S5.6-01", [
                ("1", "QCM_6MHZ_RF", "BIDIR", "Real-time 0.10 nm/s thickness monitor"),
                ("2", "AGND_SHIELD", "PWR", "0 V AGND"),
            ]),
        ],
        "mating_part_ids": ["S5.6-01", "S5.1-03"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "QCM deposition metrology"},
    }

    specs["S5.6-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Load-lock 345 C PBN radiative heater (150 W, sequential w/ S5.6-01) + 5% H2/N2 FG leak-valve manifold.",
        "supply_rails": [_rail("PBN_HEATER_150W", 48.0, "DC", 3.5, 0.0, 150.0, "S5.6-01")],
        "connectors_and_pinout": [
            _conn("J_PBN", "CF40 Power + TC + Solenoid", "loadlock", "S5.6-01", [
                ("1-2", "PBN_HTR_PN", "IN", "150 W PID (RT-450 C ±2 C, sequential)"),
                ("3-4", "TYPE_C_TC", "OUT", "Wafer temperature feedback"),
                ("5-6", "FG_VALVE_24V", "IN", "ISO 10156 5% H2/N2 orifice valve"),
            ]),
        ],
        "mating_part_ids": ["S5.1-03", "S5.6-01", "S5.6-04", "S7.SAFETY-06"],
        "interlock_hooks": [_hook("FG_H2_VALVE_CLOSE", "S7.SAFETY-03", "Close 5% H2/N2 valve & cut PBN heater (45 ms)", 45.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "AUX_PROCESS_SHED_ON_OUTAGE",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Sequential epi/FG heater"},
    }

    specs["S5.6-04"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Load-lock 80 L/s compact TMP + ZrVFe NEG pump (<=1.5e-10 Torr recovery) on Tier-1 UPS (110 W).",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 0.8, 110.0, 180.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_TMP80", "IEC C14 Tier-1 + DB9 Ctrl", "loadlock_aux", "S7.SAFETY-04", [
                ("L-N-PE", "UPS_T1_230V", "IN", "110 W continuous load-lock UHV"),
                ("NEG", "NEG_ACT_CTRL", "IN", "NEG activation interlock"),
            ]),
        ],
        "mating_part_ids": ["S5.1-03", "S5.6-01", "S5.6-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("LL_TMP_FAULT", "S7.SAFETY-06", "Isolate load-lock gate valve on TMP fault", 80.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 110.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Load-lock MBE UHV recovery pump"},
    }

    specs["S6.1-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Water-cooled Cryomech CPA He compressor (9.42 kW 3-phase 400 VAC facility breaker; Tier-2 soft-shed 0.5 s).",
        "supply_rails": [_rail("AC_3PH_FACILITY_400V", 400.0, "AC_3PH", 18.0, 9420.0, 10500.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_3PH", "IEC 60309 3P+PE 32A", "facility_chiller", "S7.SAFETY-04", [
                ("L1-L3", "FACILITY_400V_3PH", "IN", "9.42 kW PT420 He compressor"),
                ("PE", "FACILITY_PE", "PWR", "Main earth bond"),
            ]),
            _conn("J_CTRL", "DB9 Remote Stop/Status", "compressor_panel", "S7.SAFETY-03", [
                ("1-2", "COMP_SOFT_STOP", "IN", "Controlled stop at t=0.5 s on utility loss"),
                ("3-4", "WATER_TEMP_OK", "OUT", "Chilled-water flow/temp switch"),
            ]),
        ],
        "mating_part_ids": ["S6.1-01", "S6.9-01", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("PT420_SOFT_SHED", "S7.SAFETY-04", "Controlled compressor stop on outage (0.5 s)", 500.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 9420.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "4 K pulse-tube He compressor"},
    }

    specs["S6.3-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Main 4.2 K NbTi 8-coil split-pair magnet (Bz=1.500 T, 17.8 ppm, E_mag=18.94 kJ, 5.48 km NbTi).",
        "supply_rails": [_rail("SC_MAGNET_BUS", 400.0, "DC", 256.0, 0.0, 1000.0, "S6.3-05")],
        "connectors_and_pinout": [
            _conn("J_SC_LEADS", "4.2 K Bi-2223 HTS / NbTi Splice Lugs", "4K_magnet", "S6.3-04", [
                ("1", "MAG_MAIN_POS", "IN", "Up to 255.9 A, V_quench <= 400 V"),
                ("2", "MAG_MAIN_NEG", "IN", "Return bus"),
                ("3-10", "COIL_VTAP[0:7]", "OUT", "Quench bridge voltage taps"),
            ]),
        ],
        "mating_part_ids": ["S6.3-02", "S6.3-03", "S6.3-04", "S6.3-05"],
        "interlock_hooks": [_hook("QUENCH_VTAP_TRIP", "S6.3-04", "Extract 18.94 kJ into 1.563 Ohm dump (tau=0.370 s)", 30.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Persistent-mode 1.50 T ESR magnet"},
    }

    specs["S6.3-02"] = {
        "electrical_class": "E4",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Active bucking/shielding coil pairs (A/B coils) series-coupled with S6.3-01 (B_res=22.3 uT).",
        "supply_rails": [_rail("SC_BUCKING_BUS", 400.0, "DC", 170.0, 0.0, 200.0, "S6.3-05")],
        "connectors_and_pinout": [
            _conn("J_BUCK", "4.2 K Superconducting Splice Bus", "4K_magnet", "S6.3-04", [
                ("1-2", "BUCK_AB_SERIES", "IN", "Active field cancellation (-168/-57/+84/+22 A)"),
                ("3-4", "BUCK_VTAP", "OUT", "Quench voltage-tap sense"),
            ]),
        ],
        "mating_part_ids": ["S6.3-01", "S6.3-03", "S6.3-04", "S6.3-05"],
        "interlock_hooks": [_hook("BUCKING_QUENCH_TAP", "S6.3-04", "Co-extract with S6.3-01 into 1.563 Ohm dump", 30.0)],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Active magnetic field shield"},
    }

    specs["S6.9-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "PT420 500 mm offset remote rotary valve acoustic box & stepper drive (80 W; paired w/ S6.1-02 = 9.5 kW).",
        "supply_rails": [_rail("AC_FACILITY_230V", 230.0, "AC_1PH", 0.6, 80.0, 120.0, "S6.1-02")],
        "connectors_and_pinout": [
            _conn("J_RV_MTR", "Binder M16 6-Pin Shielded", "remote_valve_box", "S6.1-02", [
                ("1-4", "ROTARY_VALVE_MTR", "IN", "1.4 Hz synchronous drive"),
                ("5-6", "PHASE_ENC_TAP", "OUT", "Feeds S6.9-04 25 dB harmonic FF"),
            ]),
        ],
        "mating_part_ids": ["S6.1-01", "S6.1-02", "S6.9-04"],
        "interlock_hooks": [_hook("PT420_VALVE_STOP", "S6.1-02", "Stops synchronously with compressor soft-shed", 500.0)],
        "ups_tier": "TIER2_SHED",
        "ups_budget_group": "EXP150_TIER2_SHED",
        "exp150_ups_allocation_w": 80.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": "WR_COAX_3 (via S6.9-04)", "sync_role": "1.4 Hz cryo rotary valve"},
    }

    specs["S7.3-03"] = {
        "electrical_class": "E4",
        "grounding_domain": "CRYO_OVC",
        "grounding_notes": "Non-magnetic PEEK/BeCu 4 K cryo-CMOS chip screening socket & test rig (offline screening).",
        "supply_rails": [_rail("SCREEN_VDD_1V8", 1.8, "DC", 0.2, 0.0, 0.5, "S3.2-06")],
        "connectors_and_pinout": [
            _conn("J_TEST_SKT", "Micro-D 37-Pin Cryo Probe", "test_dewar", "S7.3-01", [
                ("1-32", "SKY130_DUT_IO", "BIDIR", "4 K functional & kink screening"),
                ("33-37", "VDD_1V8_GND", "PWR", "1.8 V / 0 V CRYO_OVC"),
            ]),
        ],
        "mating_part_ids": ["S7.3-01", "S7.3-02", "S3.2-06"],
        "interlock_hooks": [],
        "ups_tier": "NONE",
        "ups_budget_group": "PASSIVE_ZERO_MAINS",
        "exp150_ups_allocation_w": 0.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Offline 4 K ASIC screening fixture"},
    }

    specs["S7.SAFETY-01"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Sub-atm SDS PH3 micro-cylinder cabinet (<650 Torr, 10 g), 250 CFM dry scrubber & dual 0.02 ppm sensors (480 W Tier-1).",
        "supply_rails": [_rail("AC_UPS_TIER1", 230.0, "AC_1PH", 3.0, 480.0, 620.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_AC_T1", "IEC C14 Tier-1 Critical UPS", "gas_bay", "S7.SAFETY-04", [
                ("L-N-PE", "UPS_T1_230V", "IN", "480 W continuous scrubber + sensors"),
            ]),
            _conn("J_PH3_1OO2D", "Phoenix 8-Pin SIL-3 Target Bus", "gas_bay", "S7.SAFETY-03", [
                ("1-2", "PH3_SENS_A_4_20MA", "OUT", "0.02 ppm alarm Ch-A"),
                ("3-4", "PH3_SENS_B_4_20MA", "OUT", "0.02 ppm alarm Ch-B (diverse)"),
                ("5-6", "SCRUBBER_FLOW_OK", "OUT", "250 CFM differential pressure switch"),
                ("7-8", "SDS_VALVE_CLOSE", "IN", "12 s SIL-3 target isolation"),
            ]),
        ],
        "mating_part_ids": ["S1.1-04", "S1.6-01", "S1.6-02", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("PH3_DUAL_0P02PPM_TRIP", "S7.SAFETY-03", "Slam-shut SDS PH3 valve & sound cleanroom alarm", 45.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 480.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Life-safety toxic gas abatement"},
    }

    specs["S7.SAFETY-06"] = {
        "electrical_class": "E4",
        "grounding_domain": "FACILITY_PE",
        "grounding_notes": "Fast spring-return UHV gate-valve actuators (<80 ms), ISO 10156 5% H2/N2 orifice & X-ray survey meter (60 W Tier-1).",
        "supply_rails": [_rail("DC_24V_UPS_T1", 24.0, "DC", 3.0, 60.0, 90.0, "S7.SAFETY-04")],
        "connectors_and_pinout": [
            _conn("J_ACT_SOL", "Phoenix 8-Pin De-Energize-To-Close", "uhv_manifolds", "S7.SAFETY-03", [
                ("1-2", "GV_LL_SOL_24V", "IN", "Load-lock gate valve (<=80 ms seal)"),
                ("3-4", "GV_FORE_SOL_24V", "IN", "Foreline gate valve (<=80 ms seal)"),
                ("5-6", "XRAY_DOSE_4_20MA", "OUT", "Area X-ray monitor (<0.01 uSv/h target)"),
                ("7-8", "VALVE_SEALED_FB", "OUT", "Closed-position proof switches"),
            ]),
        ],
        "mating_part_ids": ["S5.1-03", "S5.2-01", "S5.6-03", "S7.SAFETY-03", "S7.SAFETY-04"],
        "interlock_hooks": [_hook("UHV_GATE_VALVE_80MS", "S7.SAFETY-03", "De-energize pneumatic solenoids -> seal in 80 ms", 80.0)],
        "ups_tier": "TIER1_CRITICAL",
        "ups_budget_group": "EXP150_TIER1_CRITICAL",
        "exp150_ups_allocation_w": 60.0,
        "timing_sync": {"rb_10mhz_port": None, "white_rabbit_port": None, "sync_role": "Fast UHV isolation & X-ray survey"},
    }

    return specs


def load_bom_rows() -> dict[str, dict[str, str]]:
    with BOM_CSV.open("r", encoding="utf-8", newline="") as f:
        return {row["part_id"]: row for row in csv.DictReader(f)}


def _reconcile_part_power(pid: str, sp: dict[str, Any]) -> dict[str, Any]:
    """Compute exact zero-double-counting incremental mains power & reconciliation note for a part."""
    rails = sp["supply_rails"]
    raw_sum_w = round(sum(r["steady_power_w"] for r in rails), 4)
    ubg = sp["ups_budget_group"]
    utier = sp["ups_tier"]
    exp150_alloc_w = float(sp["exp150_ups_allocation_w"])

    ac_rails = [r for r in rails if r["current_type"].startswith("AC")]
    self_sec_rails = [r for r in rails if (not r["current_type"].startswith("AC")) and r["source_part_id"] == pid]

    if ubg == "PASSIVE_ZERO_MAINS":
        incr_w = 0.0
        note = (
            f"Passive or downstream sub-assembly ({raw_sum_w:.2f} W sub-rail power drawn from upstream source "
            f"{rails[0]['source_part_id']}); incremental_mains_w = 0.0 W (zero double-counting)."
        )
    elif ubg == "UPS_INTERNAL_LOSS":
        incr_w = 350.0
        note = (
            "S7.SAFETY-04 online double-conversion UPS: 350.0 W continuous internal conversion loss "
            "(accounted explicitly in conservative battery-draw runtime); output buses supply downstream loads."
        )
    elif ubg == "EXP150_TIER1_CRITICAL":
        incr_w = exp150_alloc_w
        sec_w = round(raw_sum_w - incr_w, 2)
        if sec_w > 0.0:
            note = (
                f"Exp150 Tier-1 critical UPS load: incremental_mains_w = exp150_ups_allocation_w = {incr_w:.1f} W; "
                f"{sec_w:.1f} W secondary output rail(s) derived internally from primary AC input (0.0 W double-count)."
            )
        else:
            note = f"Exp150 Tier-1 critical UPS load: incremental_mains_w = exp150_ups_allocation_w = {incr_w:.1f} W."
    elif ubg == "EXP150_TIER2_SHED":
        incr_w = exp150_alloc_w
        note = (
            f"Exp150 Tier-2 sheddable baseline load: incremental_mains_w = exp150_ups_allocation_w = {incr_w:.1f} W "
            f"(raw supply_rails sum = {raw_sum_w:.1f} W, shed cleanly on utility outage)."
        )
    else:  # AUX_PROCESS_SHED_ON_OUTAGE
        if ac_rails:
            incr_w = round(sum(r["steady_power_w"] for r in ac_rails), 2)
            sec_w = round(raw_sum_w - incr_w, 2)
            if sec_w > 0.0:
                sec_names = ", ".join(r["rail_name"] for r in self_sec_rails) or "secondary DC/HV rail"
                note = (
                    f"Non-Exp150 auxiliary sheddable rack/facility load ({utier}): incremental_mains_w = {incr_w:.1f} W AC mains "
                    f"(shed immediately on outage, exp150_ups_allocation_w = 0.0 W); {sec_w:.1f} W {sec_names} derived "
                    f"internally from own AC input (0.0 W double-count)."
                )
            else:
                note = (
                    f"Non-Exp150 auxiliary sheddable rack/facility load ({utier}): incremental_mains_w = {incr_w:.1f} W AC mains "
                    f"(mutually exclusive process/experiment mode, shed immediately on outage; exp150_ups_allocation_w = 0.0 W)."
                )
        elif all(r["source_part_id"] == "S7.2-03" for r in rails):
            incr_w = 0.0
            note = (
                f"PXIe plug-in card ({raw_sum_w:.1f} W DC backplane load) powered wholly by parent chassis S7.2-03 "
                f"(320.0 W AC mains): incremental_mains_w = 0.0 W, exp150_ups_allocation_w = 0.0 W (0.0 W double-count)."
            )
        elif raw_sum_w == 0.0:
            incr_w = 0.0
            note = (
                f"Sequential non-simultaneous process load (0.0 W steady concurrent draw; peak {max(r['peak_power_w'] for r in rails):.1f} W "
                f"interlocked against simultaneous peak): incremental_mains_w = 0.0 W, exp150_ups_allocation_w = 0.0 W."
            )
        else:
            incr_w = round(raw_sum_w, 2)
            note = (
                f"Non-Exp150 auxiliary sheddable rack DC load ({utier}, fed via S7.4-03 rack PSU): "
                f"incremental_mains_w = {incr_w:.1f} W (shed immediately on outage; exp150_ups_allocation_w = 0.0 W)."
            )

    sec_or_parent_w = round(max(0.0, raw_sum_w - incr_w), 4)
    non_exp150_aux_w = round(max(0.0, incr_w - exp150_alloc_w), 4) if utier == "TIER2_SHED" else 0.0
    return {
        "supply_rails_steady_sum_w": raw_sum_w,
        "incremental_mains_w": round(incr_w, 4),
        "secondary_or_parent_derived_w": sec_or_parent_w,
        "non_exp150_aux_shed_w": non_exp150_aux_w,
        "reconciliation_note": note,
    }


def build_all(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    bom_rows = load_bom_rows()
    specs = _build_part_specs()

    # Strict integrity checks before writing
    assert set(specs.keys()) == set(ALL_95_IDS), (
        f"Part coverage mismatch: missing={set(ALL_95_IDS)-set(specs)}, extra={set(specs)-set(ALL_95_IDS)}"
    )
    assert len(specs) == 95

    all_icds: list[dict[str, Any]] = []
    class_counts = {"E2": 0, "E3": 0, "E4": 0}
    grounding_map: dict[str, list[str]] = {g: [] for g in VALID_GROUNDING_DOMAINS}
    tier1_items_95: list[dict[str, Any]] = []
    tier2_items_95: list[dict[str, Any]] = []
    tier2_all_28_items: list[dict[str, Any]] = []
    aux_shed_items: list[dict[str, Any]] = []

    for pid in ALL_95_IDS:
        brow = bom_rows[pid]
        sp = specs[pid]
        eclass = sp["electrical_class"]
        gdom = sp["grounding_domain"]
        utier = sp["ups_tier"]
        assert gdom in VALID_GROUNDING_DOMAINS, f"Invalid grounding domain on {pid}: {gdom}"
        assert utier in VALID_UPS_TIERS, f"Invalid ups_tier on {pid}: {utier}"
        for mid in sp["mating_part_ids"]:
            assert mid in bom_rows, f"Invalid mating_part_id {mid!r} referenced by {pid}"

        pwr_rec = _reconcile_part_power(pid, sp)

        icd = {
            "schema_version": "1.0",
            "part_id": pid,
            "parent_bom_id": brow["parent_bom_id"],
            "subsystem": brow["subsystem"],
            "part_name": brow["part_name"],
            "qty": float(brow["qty"]) if "." in brow["qty"] else int(brow["qty"]),
            "unit": brow["unit"],
            "temp_stage": brow["temp_stage"],
            "vacuum_grade": brow["vacuum_grade"],
            "bom_key_spec": brow["key_spec"],
            "usd_nom": float(brow["usd_nom"]),
            "bom_epistemic_tag": brow["epistemic_tag"],
            "electrical_class": eclass,
            "grounding_domain": gdom,
            "grounding_notes": sp["grounding_notes"],
            "supply_rails": sp["supply_rails"],
            "connectors_and_pinout": sp["connectors_and_pinout"],
            "mating_part_ids": sp["mating_part_ids"],
            "interlock_hooks": sp["interlock_hooks"],
            "ups_tier": utier,
            "ups_budget_group": sp["ups_budget_group"],
            "exp150_ups_allocation_w": sp["exp150_ups_allocation_w"],
            "supply_rails_steady_sum_w": pwr_rec["supply_rails_steady_sum_w"],
            "incremental_mains_w": pwr_rec["incremental_mains_w"],
            "secondary_or_parent_derived_w": pwr_rec["secondary_or_parent_derived_w"],
            "non_exp150_aux_shed_w": pwr_rec["non_exp150_aux_shed_w"],
            "reconciliation_note": pwr_rec["reconciliation_note"],
            "timing_sync": sp["timing_sync"],
            "epistemic_flags": {
                "design_maturity": "M0_M1_ELECTRICAL_ICD_DESIGN_ONLY",
                "no_lab_measurement": True,
                "no_supplier_quotes": True,
                "iec61508_certified": False,
                "semi_s2_certified": False,
            },
        }
        (out_dir / f"{pid}.json").write_text(json.dumps(icd, indent=2) + "\n", encoding="utf-8")
        all_icds.append(icd)
        class_counts[eclass] += 1
        grounding_map[gdom].append(pid)

        if utier == "TIER2_SHED":
            tier2_all_28_items.append({
                "part_id": pid,
                "ups_budget_group": sp["ups_budget_group"],
                "supply_rails_steady_sum_w": pwr_rec["supply_rails_steady_sum_w"],
                "incremental_mains_w": pwr_rec["incremental_mains_w"],
                "exp150_ups_allocation_w": sp["exp150_ups_allocation_w"],
                "non_exp150_aux_shed_w": pwr_rec["non_exp150_aux_shed_w"],
                "secondary_or_parent_derived_w": pwr_rec["secondary_or_parent_derived_w"],
                "reconciliation_note": pwr_rec["reconciliation_note"],
            })

        if sp["ups_budget_group"] == "EXP150_TIER1_CRITICAL":
            tier1_items_95.append({"part_id": pid, "part_name": brow["part_name"], "electrical_class": eclass, "power_w": sp["exp150_ups_allocation_w"]})
        elif sp["ups_budget_group"] == "EXP150_TIER2_SHED":
            tier2_items_95.append({"part_id": pid, "part_name": brow["part_name"], "electrical_class": eclass, "power_w": sp["exp150_ups_allocation_w"]})
        elif sp["ups_budget_group"] == "AUX_PROCESS_SHED_ON_OUTAGE":
            aux_shed_items.append({
                "part_id": pid,
                "part_name": brow["part_name"],
                "electrical_class": eclass,
                "incremental_mains_w": pwr_rec["incremental_mains_w"],
                "sub_rail_power_w": pwr_rec["supply_rails_steady_sum_w"],
                "secondary_or_parent_derived_w": pwr_rec["secondary_or_parent_derived_w"],
            })

    # Reconcile exact Exp150 S7.SAFETY-04 15 kVA / 13.5 kW / 10 kWh Online LFP UPS budget
    # E1 boards in Tier-1 (designed by sibling Wave 2B workers): S7.SAFETY-03 (120.0 W) + S6.11-01 (88.0 W [87.96 W])
    e1_tier1_external = [
        {"part_id": "S7.SAFETY-03", "part_name": bom_rows["S7.SAFETY-03"]["part_name"], "electrical_class": "E1", "power_w": 120.0},
        {"part_id": "S6.11-01", "part_name": bom_rows["S6.11-01"]["part_name"], "electrical_class": "E1", "power_w": 88.0},
    ]
    t1_by_id = {x["part_id"]: x["power_w"] for x in tier1_items_95}
    t1_by_id.update({x["part_id"]: x["power_w"] for x in e1_tier1_external})
    t2_by_id = {x["part_id"]: x["power_w"] for x in tier2_items_95}
    aux_by_id = {x["part_id"]: x["incremental_mains_w"] for x in aux_shed_items}

    # Programmatically derive all 4 Exp150 Tier-1 buckets and 3 Tier-2 buckets directly from part allocations
    tier1_buckets = {
        "sil3_safety_plc_and_sensors": round(t1_by_id["S7.SAFETY-03"] + t1_by_id["S7.SAFETY-05"] + t1_by_id["S7.SAFETY-06"], 2),
        "uhv_gate_valves_and_ion_tmp_spindown": round(
            t1_by_id["S5.2-01"] + t1_by_id["S5.2-02"] + t1_by_id["S5.2-04"] + t1_by_id["S5.1-03"] + t1_by_id["S5.6-04"], 2
        ),
        "ph3_sds_cabinet_and_scrubber": round(t1_by_id["S7.SAFETY-01"], 2),
        "s7_host_rfsoc_logging_cryo_inst": round(
            t1_by_id["S6.11-01"] + t1_by_id["S7.1-01"] + t1_by_id["S7.1-02"] + t1_by_id["S6.2-03"]
            + t1_by_id["S6.8-02"] + t1_by_id["S7.4-01"] + t1_by_id["S7.4-02"] + t1_by_id["S3.2-06"]
            + t1_by_id["S3.3-04"] + t1_by_id["S7.4-03"] + t1_by_id["S7.1-03"], 2
        ),
    }
    tier2_buckets = {
        "pt420_compressor_controlled_stop": round(t2_by_id["S6.1-02"] + t2_by_id["S6.9-01"], 2),
        "s9hpc_100g_rdma_graceful_halt": round(t2_by_id["S9.HPC-01"] + t2_by_id["S9.HPC-02"] + t2_by_id["S9.HPC-03"], 2),
        "s56_mbe_pbn_and_option_q_cut": round(t2_by_id["S5.6-01"] + t2_by_id["S1.7-01"], 2),
    }

    tier1_95_w = round(sum(x["power_w"] for x in tier1_items_95), 2)
    tier1_e1_w = round(sum(x["power_w"] for x in e1_tier1_external), 2)
    tier1_total_w = round(tier1_95_w + tier1_e1_w, 2)  # 2533.0 W exact!
    assert round(sum(tier1_buckets.values()), 2) == tier1_total_w == 2533.0

    tier2_total_w = round(sum(x["power_w"] for x in tier2_items_95), 2)  # 12275.0 W exact!
    assert round(sum(tier2_buckets.values()), 2) == tier2_total_w == 12275.0
    exp150_combined_w = round(tier1_total_w + tier2_total_w, 2)          # 14808.0 W exact!

    # Exact 28-part TIER2_SHED watt-for-watt reconciliation (zero discrepancy!)
    t2_28_raw_rails_w = round(sum(x["supply_rails_steady_sum_w"] for x in tier2_all_28_items), 2)
    t2_28_exp150_w = round(sum(x["exp150_ups_allocation_w"] for x in tier2_all_28_items), 2)
    t2_28_aux_incr_w = round(sum(x["non_exp150_aux_shed_w"] for x in tier2_all_28_items), 2)
    t2_28_overlap_w = round(sum(x["secondary_or_parent_derived_w"] for x in tier2_all_28_items), 2)
    t2_28_total_incr_w = round(sum(x["incremental_mains_w"] for x in tier2_all_28_items), 2)
    t2_28_discrepancy_w = round(t2_28_raw_rails_w - (t2_28_exp150_w + t2_28_aux_incr_w + t2_28_overlap_w), 4)
    assert len(tier2_all_28_items) == 28
    assert t2_28_raw_rails_w == 18026.0
    assert t2_28_exp150_w == 12275.0
    assert t2_28_discrepancy_w == 0.0
    assert round(t2_28_total_incr_w - (t2_28_exp150_w + t2_28_aux_incr_w), 4) == 0.0

    # UPS runtime formulas: BOTH Exp150 nominal reference AND conservative incl. 350 W idle loss + LFP DoD
    ups_kva = 15.0
    ups_pf = 0.90
    ups_rated_kw = ups_kva * ups_pf      # 13.5 kW
    ups_batt_kwh = 10.0
    ups_usable_dod = 0.90
    ups_usable_kwh = ups_batt_kwh * ups_usable_dod  # 9.0 kWh @ 90% DoD
    ups_inv_eff = 0.90
    ups_internal_loss_w = 350.0

    # (a) Exp150 reference formula (10 kWh * 0.90 / P_load)
    runtime_rated_min = round((ups_batt_kwh * ups_inv_eff / ups_rated_kw) * 60.0, 1)              # 40.0 min
    runtime_tier1_exp150_min = round((ups_batt_kwh * ups_inv_eff / (tier1_total_w / 1e3)) * 60.0, 1)  # 213.2 min

    # (b) Conservative battery DC draw INCLUDING 350 W continuous double-conversion idle loss:
    #     P_batt_dc = P_load / eta_inv + P_internal_loss
    p_batt_tier1_w = tier1_total_w / ups_inv_eff + ups_internal_loss_w                             # 3164.44 W
    runtime_tier1_100dod_min = round((ups_batt_kwh * 1e3 / p_batt_tier1_w) * 60.0, 1)              # 189.6 min
    runtime_tier1_90dod_min = round((ups_usable_kwh * 1e3 / p_batt_tier1_w) * 60.0, 1)             # 170.6 min

    p_batt_rated_w = (ups_rated_kw * 1e3) / ups_inv_eff + ups_internal_loss_w                      # 15350.0 W
    runtime_rated_100dod_min = round((ups_batt_kwh * 1e3 / p_batt_rated_w) * 60.0, 1)              # 39.1 min
    runtime_rated_90dod_min = round((ups_usable_kwh * 1e3 / p_batt_rated_w) * 60.0, 1)             # 35.2 min

    req_lfp_kwh_180min_90dod = round((p_batt_tier1_w * 3.0 / ups_usable_dod) / 1e3, 2)             # 10.55 kWh
    max_tier1_kw_180min_90dod = round((((ups_usable_kwh * 1e3 / 3.0) - ups_internal_loss_w) * ups_inv_eff) / 1e3, 3)  # 2.385 kW

    ups_bus_pre_shed_kw = round((exp150_combined_w - tier2_buckets["pt420_compressor_controlled_stop"]) / 1e3, 3)

    aux_steady_total_w = round(sum(x["incremental_mains_w"] for x in aux_shed_items), 2)
    cryo_ro_aux_ids = ("S6.3-05", "S6.4-01", "S6.4-02", "S6.5-01", "S6.5-02", "S6.6-05", "S6.6-06", "S7.2-03")
    ion_write_aux_ids = ("S1.1-05", "S1.2-03", "S1.4-02", "S1.5-03", "S1.6-01", "S4.2-03", "S4.3-04", "S4.4-01", "S5.2-03")
    cryo_readout_mode_kw = round((tier1_total_w + tier2_buckets["s9hpc_100g_rdma_graceful_halt"] + sum(aux_by_id[p] for p in cryo_ro_aux_ids)) / 1e3, 3)
    ion_write_mode_kw = round((tier1_total_w + tier2_buckets["s56_mbe_pbn_and_option_q_cut"] + sum(aux_by_id[p] for p in ion_write_aux_ids)) / 1e3, 3)
    flash_anneal_ups_kw = round((tier1_total_w + aux_by_id["S5.3-03"] + aux_by_id["S5.2-03"]) / 1e3, 3)

    master = {
        "schema_version": "1.0",
        "title": "Master Electrical Power, 15 kVA LFP UPS Load-Shed, Grounding & 10 MHz Rb / White Rabbit Timing ICD",
        "epistemic_flags": {
            "design_maturity": "M0_M1_ELECTRICAL_ICD_DESIGN_ONLY",
            "no_lab_measurement": True,
            "no_supplier_quotes": True,
            "iec61508_certified": False,
            "semi_s2_certified": False,
        },
        "icd_coverage": {
            "total_per_part_icds": len(all_icds),
            "by_electrical_class": class_counts,
            "e1_custom_pcbs_note": "30 E1 custom PCBs are designed as full KiCad 8 + ngspice bundles in hardware/pcb/*",
            "total_usd_nom_covered_95": round(sum(x["usd_nom"] for x in all_icds), 2),
        },
        "ups_s7_safety_04": {
            "part_id": "S7.SAFETY-04",
            "topology": "Online Double-Conversion LFP UPS + Tiered Load-Shed PDU",
            "rating_kVA": ups_kva,
            "power_factor": ups_pf,
            "rated_real_power_kW": ups_rated_kw,
            "battery_energy_kWh": ups_batt_kwh,
            "usable_lfp_dod_fraction": ups_usable_dod,
            "usable_battery_energy_90pct_dod_kWh": ups_usable_kwh,
            "inverter_efficiency": ups_inv_eff,
            "internal_loss_W": ups_internal_loss_w,
            "transfer_time_ms": 0.0,
            "tier1_critical": {
                "total_W": tier1_total_w,
                "total_kW": round(tier1_total_w / 1e3, 3),
                "from_95_icds_W": tier1_95_w,
                "from_e1_boards_W": tier1_e1_w,
                "exp150_buckets_W": tier1_buckets,
                "runtime_min": runtime_tier1_exp150_min,
                "runtime_tier1_min_exp150_nominal_eta090": runtime_tier1_exp150_min,
                "battery_dc_draw_incl_350w_loss_W": round(p_batt_tier1_w, 2),
                "runtime_tier1_min_conservative_100pct_dod_incl_350w_loss": runtime_tier1_100dod_min,
                "runtime_tier1_min_conservative_90pct_dod_incl_350w_loss": runtime_tier1_90dod_min,
                "meets_180min_requirement": runtime_tier1_exp150_min >= 180.0,
                "tier1_conservative_100pct_dod_meets_180min": runtime_tier1_100dod_min >= 180.0,
                "tier1_conservative_90pct_dod_meets_180min": runtime_tier1_90dod_min >= 180.0,
                "conservative_sizing_requirements_for_180min_at_90pct_dod": {
                    "min_lfp_pack_kWh_at_2p533kW": req_lfp_kwh_180min_90dod,
                    "recommended_nominal_lfp_pack_kWh": 11.0,
                    "max_tier1_load_kW_at_10kWh": max_tier1_kw_180min_90dod,
                    "sizing_note": (
                        "Exp150 reference formula (10 kWh * 0.90 / 2.533 kW) gives 213.2 min. "
                        "Including continuous 350.0 W online double-conversion internal loss (P_batt_dc = 3164.44 W), "
                        "runtime is 189.6 min at 100% DoD (PASS >= 180 min) and 170.6 min at conservative 90% usable "
                        "LFP DoD (9.0 kWh, 9.4 min below 180 min). Meeting >= 180 min under 90% DoD + 350 W idle loss "
                        "requires either >= 10.6 kWh (11 kWh nominal) LFP pack or trimming Tier-1 outage hold load to <= 2.35 kW."
                    ),
                },
                "items_from_95_icds": tier1_items_95,
                "items_from_e1_boards": e1_tier1_external,
            },
            "tier2_sheddable": {
                "total_W": tier2_total_w,
                "total_kW": round(tier2_total_w / 1e3, 3),
                "exp150_buckets_W": tier2_buckets,
                "shed_timeline_note": "PT420 (9.5 kW, 3-ph breaker) soft-shed at t=0.5 s; S5.6/Opt-Q cut at t=45 ms; S9.HPC graceful halt at t=60 s.",
                "items": tier2_items_95,
                "tier2_shed_28part_reconciliation": {
                    "tier2_shed_part_count": len(tier2_all_28_items),
                    "raw_supply_rails_steady_sum_W": t2_28_raw_rails_w,
                    "exp150_tier2_ups_allocation_W": t2_28_exp150_w,
                    "non_exp150_aux_incremental_mains_W": t2_28_aux_incr_w,
                    "secondary_and_backplane_derived_overlap_W": t2_28_overlap_w,
                    "total_incremental_mains_tier2_W": t2_28_total_incr_w,
                    "reconciliation_discrepancy_W": t2_28_discrepancy_w,
                    "formula": "raw_supply_rails_steady_sum_W == exp150_tier2_ups_allocation_W + non_exp150_aux_incremental_mains_W + secondary_and_backplane_derived_overlap_W",
                    "per_part_breakdown": tier2_all_28_items,
                },
            },
            "reconciliation": {
                "exp150_combined_tier1_plus_tier2_W": exp150_combined_w,
                "exp150_combined_tier1_plus_tier2_kW": round(exp150_combined_w / 1e3, 3),
                "ups_bus_pre_shed_excl_3ph_pt420_kW": ups_bus_pre_shed_kw,
                "ups_bus_utilization_pre_shed_pct": round(ups_bus_pre_shed_kw / ups_rated_kw * 100.0, 2),
                "runtime_at_rated_13p5kW_min": runtime_rated_min,
                "runtime_at_rated_13p5kW_conservative_100pct_dod_incl_350w_min": runtime_rated_100dod_min,
                "runtime_at_rated_13p5kW_conservative_90pct_dod_incl_350w_min": runtime_rated_90dod_min,
                "meets_30min_full_load_requirement": runtime_rated_90dod_min >= 30.0,
                "aux_experiment_rack_sheddable_W": aux_steady_total_w,
                "aux_experiment_rack_items": aux_shed_items,
                "operational_phase_ups_load_kW": {
                    "cryo_readout_mode_excl_pt420_kW": cryo_readout_mode_kw,
                    "ion_write_mode_excl_pt420_kW": ion_write_mode_kw,
                    "flash_anneal_ups_mode_excl_3ph_flash_kW": flash_anneal_ups_kw,
                    "utility_outage_tier1_hold_kW": round(tier1_total_w / 1e3, 3),
                    "all_modes_within_13p5kW_ups": bool(
                        max(cryo_readout_mode_kw, ion_write_mode_kw, flash_anneal_ups_kw, tier1_total_w / 1e3) < ups_rated_kw
                    ),
                },
            },
        },
        "grounding_domains": {
            "domains": {
                "AGND": {"count": len(grounding_map["AGND"]), "description": "Quiet analog/metrology/IBIC star ground tied single-point to FACILITY_PE.", "part_ids": grounding_map["AGND"]},
                "DGND": {"count": len(grounding_map["DGND"]), "description": "Digital FPGA/RFSoC/AWG/HPC/timing ground isolated from AGND via single star tie.", "part_ids": grounding_map["DGND"]},
                "HV_MINUS_5KV_DECK": {"count": len(grounding_map["HV_MINUS_5KV_DECK"]), "description": "Floating -5 kV upper column / +15 kV source HV deck; 5 kV galvanic optical/transformer isolation.", "part_ids": grounding_map["HV_MINUS_5KV_DECK"]},
                "CRYO_OVC": {"count": len(grounding_map["CRYO_OVC"]), "description": "Dilution cryostat OVC/4K/MXC Faraday shield single-point tied to quiet cryo star.", "part_ids": grounding_map["CRYO_OVC"]},
                "FACILITY_PE": {"count": len(grounding_map["FACILITY_PE"]), "description": "Protective safety earth for 230/400 VAC mains, UHV chamber, pumps, gas cabinet & safety PLC.", "part_ids": grounding_map["FACILITY_PE"]},
            },
            "total_assigned": sum(len(v) for v in grounding_map.values()),
        },
        "timing_distribution": {
            "rb_10mhz_atomic_clock": {
                "source_part_id": "S7.4-01",
                "model_class": "SRS FS725 / PRS10 Rubidium + 16-Port Isolated Distribution Amp",
                "frequency_MHz": 10.0,
                "stability": "<5e-11",
                "phase_noise_1kHz_dBc_Hz": -140.0,
                "output_level_dBm": 13.0,
                "impedance_ohm": 50.0,
                "fanout_channels": [
                    {"ch": "CH1", "target_part_id": "S6.11-01", "role": "ZU48DR RFSoC Board-A LMK04828 PLL"},
                    {"ch": "CH2", "target_part_id": "S6.11-01", "role": "ZU48DR RFSoC Board-B LMK04828 PLL"},
                    {"ch": "CH3", "target_part_id": "S6.4-01", "role": "ESR Microwave VSG #1 (10-45 GHz)"},
                    {"ch": "CH4", "target_part_id": "S6.4-01", "role": "ESR Microwave VSG #2 (10-45 GHz)"},
                    {"ch": "CH5", "target_part_id": "S6.4-01", "role": "ESR Microwave VSG #3 (10-45 GHz)"},
                    {"ch": "CH6", "target_part_id": "S6.4-01", "role": "ESR Microwave VSG #4 (10-45 GHz)"},
                    {"ch": "CH7", "target_part_id": "S6.5-01", "role": "RF/ENDOR DDS #1 (1-200 MHz)"},
                    {"ch": "CH8", "target_part_id": "S6.5-01", "role": "RF/ENDOR DDS #2 (1-200 MHz)"},
                    {"ch": "CH9", "target_part_id": "S6.5-01", "role": "RF/ENDOR DDS #3 (1-200 MHz)"},
                    {"ch": "CH10", "target_part_id": "S6.5-01", "role": "RF/ENDOR DDS #4 (1-200 MHz)"},
                    {"ch": "CH11", "target_part_id": "S7.2-03", "role": "18-Slot PXIe Backplane (4x S7.2-01 AWG + 2x S7.2-02 Seq)"},
                    {"ch": "CH12", "target_part_id": "S6.6-06", "role": "14x ZCU216 RFSoC Clock Distribution Splitter"},
                    {"ch": "CH13", "target_part_id": "S3.3-04", "role": "1U IBIC Counting-Gate FPGA Chassis (S3.3-01)"},
                    {"ch": "CH14", "target_part_id": "S7.4-02", "role": "White Rabbit Grandmaster 10 MHz + 1 PPS Discipline"},
                    {"ch": "CH15", "target_part_id": "S4.4-01", "role": "He-Ne Interferometer & S4.5-03 Deflection Trim DSP"},
                    {"ch": "CH16", "target_part_id": "S7.4-01", "role": "Spare / Phase-Noise Calibration Monitor Port"},
                ],
            },
            "white_rabbit_trigger_fanout": {
                "source_part_id": "S7.4-02",
                "max_interchannel_skew_ps": 200.0,
                "optical_sfp_ports": [
                    {"port": "WR_SFP_1", "target_part_id": "S6.11-01", "medium": "SMF-28 1000BASE-BX", "role": "BOED-FPGA readout/syndrome epoch"},
                    {"port": "WR_SFP_2", "target_part_id": "S6.6-06", "medium": "SMF-28 1000BASE-BX", "role": "14x ZCU216 SYSREF alignment"},
                    {"port": "WR_SFP_3", "target_part_id": "S3.3-02", "medium": "SMF-28 5 kV Isolated", "role": "Blanker start_all & hit-gate across -5 kV barrier"},
                    {"port": "WR_SFP_4", "target_part_id": "S9.HPC-02", "medium": "SMF-28 1000BASE-BX", "role": "100G RoCEv2 QEC cycle timestamp"},
                    {"port": "WR_SFP_5", "target_part_id": "S5.5-03", "medium": "SMF-28 1000BASE-BX", "role": "808 nm flash-anneal pyrometer trigger"},
                    {"port": "WR_SFP_6", "target_part_id": "S4.5-03", "medium": "SMF-28 1000BASE-BX", "role": "On-the-fly beam-deflection trim strobe"},
                    {"port": "WR_SFP_7", "target_part_id": "S7.1-02", "medium": "SMF-28 1000BASE-BX", "role": "Immutable certificate DB epoch stamp"},
                    {"port": "WR_SFP_8", "target_part_id": "S7.4-02", "medium": "SMF-28 Spare", "role": "Multi-cryostat expansion link"},
                ],
                "coax_50ohm_ports": [
                    {"port": "WR_COAX_1", "target_part_id": "S3.3-04", "role": "IBIC 100 MHz blanker_gate trigger"},
                    {"port": "WR_COAX_2", "target_part_id": "S1.4-03", "role": "Beam-dose PID shutter strobe"},
                    {"port": "WR_COAX_3", "target_part_id": "S6.9-04", "role": "PT420 1.4 Hz harmonic FF phase sync"},
                    {"port": "WR_COAX_4", "target_part_id": "S7.2-02", "role": "PXIe 1 ns pulse sequencer epoch"},
                    {"port": "WR_COAX_5", "target_part_id": "S4.3-04", "role": "Piezo stage step-and-settle gate"},
                    {"port": "WR_COAX_6", "target_part_id": "S5.3-01", "role": "In-situ optical anneal strobe"},
                    {"port": "WR_COAX_7", "target_part_id": "S7.SAFETY-03", "role": "Safety event recorder timestamp"},
                    {"port": "WR_COAX_8", "target_part_id": "S7.4-02", "role": "Oscilloscope skew verification port"},
                ],
            },
        },
    }

    (out_dir / "master_electrical_power_ups_budget.json").write_text(
        json.dumps(master, indent=2) + "\n", encoding="utf-8"
    )

    readme = f"""# Per-Part Electrical ICD Suite & Master Power / UPS / Timing Budget (`hardware/icd/electrical/`)

> **Epistemic Status:** `M0_M1_ELECTRICAL_ICD_DESIGN_ONLY` (`no_lab_measurement=true`, `no_supplier_quotes=true`, `iec61508_certified=false`, `semi_s2_certified=false`).

## 1. Coverage (`95 / 95` Non-E1 Electrical BOM Parts)
- **`E2` (`17` parts):** Cryo-RF, microwave, superconducting readout/bus & cryo-wiring harnesses
- **`E3` (`35` parts):** COTS rack HV/magnet/RF/MW/AWG/compute/timing/UPS/safety instruments
- **`E4` (`43` parts):** Electro-mechanical, HV-electrode, vacuum, piezo, heater & sensor electrical interfaces
- **Total BOM value covered:** `${master['icd_coverage']['total_usd_nom_covered_95']:,.0f}` nominal (`100%` cross-referenced to `BOM_DETAILED.csv`).

## 2. `S7.SAFETY-04` `15 kVA / 13.5 kW / 10 kWh` Online LFP UPS Reconciliation (`Exp150` + Conservative Loss/DoD)
- **Tier-1 Critical Safety / UHV / Control:** **`{tier1_total_w:.1f} W` (`{tier1_total_w/1e3:.3f} kW`)** (`{tier1_95_w:.1f} W` from 95 ICDs + `{tier1_e1_w:.1f} W` E1 `S7.SAFETY-03`/`S6.11-01`):
  - **Exp150 Reference Formula (`10 kWh × 0.90 / 2.533 kW`):** **`{runtime_tier1_exp150_min:.1f} min`** (`>= 180 min`)
  - **Conservative Battery Draw (`P_batt = 2533/0.90 + 350 W idle loss = {p_batt_tier1_w:.2f} W`) @ `100%` DoD (`10 kWh`):** **`{runtime_tier1_100dod_min:.1f} min`** (`>= 180 min` PASS)
  - **Conservative Battery Draw @ `90%` Usable LFP DoD (`9.0 kWh`):** **`{runtime_tier1_90dod_min:.1f} min`** (`< 180 min` — `tier1_conservative_90pct_dod_meets_180min: false`; requires `>= {req_lfp_kwh_180min_90dod:.2f} kWh` [`11 kWh` nominal] LFP pack or `<= {max_tier1_kw_180min_90dod:.3f} kW` [`<= 2.35 kW`] Tier-1 trim)
- **Tier-2 Sheddable (`28` `TIER2_SHED` ICDs, `0.0 W` Discrepancy):**
  - Raw `supply_rails` steady sum (`28` parts) = **`{t2_28_raw_rails_w:.1f} W`** = **`{t2_28_exp150_w:.1f} W`** (`Exp150` Tier-2: `9.500 kW` PT420 + `2.195 kW` Option-HPC + `0.580 kW` S5.6/Option-Q) + **`{t2_28_aux_incr_w:.1f} W`** (non-Exp150 auxiliary rack/facility incremental mains) + **`{t2_28_overlap_w:.1f} W`** (secondary HV/PXIe backplane rails already inside parent AC input)
- **Combined `Exp150` Envelope:** **`{exp150_combined_w/1e3:.3f} kW`** (`{ups_bus_pre_shed_kw:.3f} kW` pre-shed UPS bus excl. 3-phase PT420; rated `13.5 kW` runtime `{runtime_rated_min:.1f} min` nominal / `{runtime_rated_100dod_min:.1f} min` @ 100% DoD+350 W / `{runtime_rated_90dod_min:.1f} min` @ 90% DoD+350 W, all `>= 30 min` PASS)

## 3. Grounding Domains & Timing Fan-Out
- **5 Grounding Domains:** `AGND` ({len(grounding_map['AGND'])}), `DGND` ({len(grounding_map['DGND'])}), `HV_MINUS_5KV_DECK` ({len(grounding_map['HV_MINUS_5KV_DECK'])}), `CRYO_OVC` ({len(grounding_map['CRYO_OVC'])}), `FACILITY_PE` ({len(grounding_map['FACILITY_PE'])}) — total `95/95`.
- **`10 MHz` Rubidium Clock (`S7.4-01`):** Complete `16`-channel isolated fan-out (`CH1–CH16`).
- **White Rabbit Trigger (`S7.4-02`):** Complete `16`-port (`8×` SFP+ optical + `8×` `50 Ω` coax, `<200 ps` skew) fan-out.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    return master


if __name__ == "__main__":
    m = build_all()
    print(json.dumps({
        "total_icds": m["icd_coverage"]["total_per_part_icds"],
        "by_class": m["icd_coverage"]["by_electrical_class"],
        "usd_nom_covered": m["icd_coverage"]["total_usd_nom_covered_95"],
        "ups_tier1_kW": m["ups_s7_safety_04"]["tier1_critical"]["total_kW"],
        "ups_tier1_runtime_exp150_min": m["ups_s7_safety_04"]["tier1_critical"]["runtime_tier1_min_exp150_nominal_eta090"],
        "ups_tier1_runtime_100dod_350w_min": m["ups_s7_safety_04"]["tier1_critical"]["runtime_tier1_min_conservative_100pct_dod_incl_350w_loss"],
        "ups_tier1_runtime_90dod_350w_min": m["ups_s7_safety_04"]["tier1_critical"]["runtime_tier1_min_conservative_90pct_dod_incl_350w_loss"],
        "ups_tier1_90dod_meets_180min": m["ups_s7_safety_04"]["tier1_critical"]["tier1_conservative_90pct_dod_meets_180min"],
        "ups_tier2_kW": m["ups_s7_safety_04"]["tier2_sheddable"]["total_kW"],
        "tier2_28part_reconciliation": {
            k: v for k, v in m["ups_s7_safety_04"]["tier2_sheddable"]["tier2_shed_28part_reconciliation"].items()
            if k != "per_part_breakdown"
        },
        "ups_combined_kW": m["ups_s7_safety_04"]["reconciliation"]["exp150_combined_tier1_plus_tier2_kW"],
        "grounding_total": m["grounding_domains"]["total_assigned"],
        "rb_10mhz_ports": len(m["timing_distribution"]["rb_10mhz_atomic_clock"]["fanout_channels"]),
        "wr_total_ports": (
            len(m["timing_distribution"]["white_rabbit_trigger_fanout"]["optical_sfp_ports"])
            + len(m["timing_distribution"]["white_rabbit_trigger_fanout"]["coax_50ohm_ports"])
        ),
    }, indent=2))
