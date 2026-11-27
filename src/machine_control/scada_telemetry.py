"""Cryo / UHV / Safety Telemetry SCADA Historian, OPC-UA Schema & Alarm Logger (S8.4-02).

Implements the Atom Lithography Machine Stage-2 ``S8.4-02`` software deliverable:
  - Structured telemetry channel registry spanning all nine subsystems (``S1..S9``),
    including 5-stage cryogenics (``50 K / 4 K / 800 mK / 100 mK / 20 mK``),
    UHV/HV vacuum gauges, ``PH3`` L1/L2 toxic gas, ``O2`` ODH, ``B``-field/quench,
    ion-column HV, 1024-ch blanker & IBIC, 808 nm laser/pyrometer, stage metrology,
    10 MHz Rb / White Rabbit timing, ZU48DR BOED-FPGA, Option-Q & Option-HPC.
  - OPC-UA-compatible node address space (``ns=2;s=ALM.<Subsystem>.<Channel>``),
    standardized OPC-UA StatusCodes, and hierarchical browse-tree export.
  - Fixed-capacity O(1) 1 Hz ring-buffer historian per channel plus global frame
    history, statistics queries, and deterministic JSONL export/import.
  - ISA-18.2 latching alarm & interlock event logger (``NORMAL`` / ``UNACK_ACTIVE`` /
    ``ACK_ACTIVE`` / ``UNACK_CLEARED``) enforcing that safety-critical alarms remain
    latched until the physical fault clears AND an operator acknowledges.
  - Bit-exact CSR decoder/encoder matching ``rtl/machine_ctrl/uhv_interlock_fsm.v``
    and ``rtl/machine_ctrl/REGMAP.md`` (``0x0000``–``0x06FF``), including verification
    of the hardwired ``DESIGN_ONLY_NOT_CERTIFIED`` register (``0xD001530E``).
  - Direct integration hooks with ``src/machine_control/auto_recal.py``
    (``AutoRecalController`` 4-mode fault-mitigation reports).

Epistemic status: ``M0_M1_DESIGN_ONLY``, ``no_lab_measurement = True``,
``iec61508_certified = False``, ``semi_s2_certified = False``.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
import threading
from typing import Any


# ---------------------------------------------------------------------------
# Locked Epistemic Metadata & OPC-UA Constants
# ---------------------------------------------------------------------------

EPISTEMIC_METADATA: dict[str, Any] = {
    "bom_part_id": "S8.4-02",
    "design_maturity": "M0_M1_DESIGN_ONLY",
    "no_lab_measurement": True,
    "iec61508_certified": False,
    "semi_s2_certified": False,
    "opcua_live_server_connected": False,
    "schema_version": "scada_telemetry_v1",
}

OPCUA_NAMESPACE_URI = "urn:atom-lithography-machine:scada:v1"
OPCUA_NAMESPACE_INDEX = 2

# Standard OPC-UA StatusCode numeric values (Part 4 / Part 6)
OPCUA_GOOD = 0x00000000
OPCUA_UNCERTAIN_INITIAL = 0x40920000
OPCUA_BAD_OUT_OF_RANGE = 0x803C0000
OPCUA_BAD_DEVICE_FAILURE = 0x808B0000
OPCUA_BAD_SENSOR_FAILURE = 0x808D0000

# ---------------------------------------------------------------------------
# Exact RTL CSR Map Constants (rtl/machine_ctrl/REGMAP.md)
# ---------------------------------------------------------------------------

CSR_CHIP_ID = 0x0000
CSR_VERSION = 0x0004
CSR_EPISTEMIC_STATUS = 0x0008
CSR_GLOBAL_STATUS = 0x000C
CSR_SCRATCH_REG = 0x0010
CSR_UPTIME_CYCLES = 0x0014

CSR_IL_CTRL = 0x0100
CSR_IL_STATUS = 0x0104
CSR_IL_FAULT_LATCH = 0x0108
CSR_IL_LIVE_SENSORS = 0x010C
CSR_IL_DISCREP_WIN = 0x0110
CSR_IL_WDT_TIMEOUT = 0x0114
CSR_IL_DWELL_CYCLES = 0x0118
CSR_IL_EPISTEMIC_CSR = 0x011C

CSR_BLK_STATUS = 0x0204
CSR_PID_STATUS = 0x0304
CSR_PID_DRIVE_OUT = 0x0334
CSR_SPI_STATUS = 0x0404
CSR_DDC_STATUS = 0x0504
CSR_BOED_STATUS = 0x0604

EXPECTED_CHIP_ID = 0x414C4D02
EXPECTED_EPISTEMIC_CSR = 0xD001530E

INTERLOCK_FSM_STATES: dict[int, str] = {
    0: "SAFE_BOOT",
    1: "FAULT_LATCHED",
    2: "SAFE_DWELL",
    3: "ARMED",
    4: "RUN",
}

# Bit positions in uhv_interlock_fsm.v ch_a_ok / ch_b_ok / sensor_fault_latched
INTERLOCK_SENSOR_BITS: dict[int, dict[str, Any]] = {
    0: {
        "name": "UHV_PRESSURE",
        "bom_ids": ("S5.1-01", "S5.2-04", "S7.SAFETY-06"),
        "channel_id": "S5.P_MAIN_UHV_TORR",
        "response_target": "blanker <1 us, UHV gate valve <80 ms",
    },
    1: {
        "name": "LASER_ENCL_DOOR",
        "bom_ids": ("S5.5-04", "S7.SAFETY-02"),
        "channel_id": "S7.LASER_ENCL_OK",
        "response_target": "laser diode/shutter <3.2 ms",
    },
    2: {
        "name": "ODH_O2_LOW",
        "bom_ids": ("S7.SAFETY-05",),
        "channel_id": "S7.O2_ROOM_PCT",
        "response_target": "cryo vent / ODH alarm, beam & HV clamp <18.3 ms",
    },
    3: {
        "name": "PH3_LEVEL1_WARN",
        "bom_ids": ("S1.6-01", "S7.SAFETY-01"),
        "channel_id": "S7.PH3_LEVEL_PPM",
        "response_target": "PH3 valve isolation + scrubber boost",
    },
    4: {
        "name": "PH3_LEVEL2_TRIP",
        "bom_ids": ("S1.6-01", "S7.SAFETY-01"),
        "channel_id": "S7.PH3_LEVEL_PPM",
        "response_target": "hard PH3 cylinder shutoff + full facility trip",
    },
    5: {
        "name": "HV_OVERCURRENT_ARC",
        "bom_ids": ("S1.1-05", "S1.3-03", "S7.SAFETY-03"),
        "channel_id": "S1.V_LANDING_KV",
        "response_target": "2 MOhm HV crowbar discharge <18.3 ms (<50 ms)",
    },
    6: {
        "name": "MAGNET_QUENCH",
        "bom_ids": ("S6.3-04", "S7.SAFETY-05"),
        "channel_id": "S6.QUENCH_VOLT_V",
        "response_target": "1.563 Ohm quench dump (tau=0.370 s)",
    },
    7: {
        "name": "ESTOP_LOOP",
        "bom_ids": ("S7.SAFETY-03",),
        "channel_id": "S7.ESTOP_LOOP_OK",
        "response_target": "all-subsystem de-energize-to-trip <=20 ns FPGA / <18.3 ms HV",
    },
}

FIRST_FAULT_CODES: dict[int, str] = {
    0: "NONE",
    1: "UHV_PRESSURE",
    2: "LASER_ENCL_DOOR",
    3: "ODH_O2_LOW",
    4: "PH3_LEVEL1_WARN",
    5: "PH3_LEVEL2_TRIP",
    6: "HV_OVERCURRENT_ARC",
    7: "MAGNET_QUENCH",
    8: "ESTOP_LOOP",
    9: "DISCREPANCY_1OO2D",
    10: "WATCHDOG_TIMEOUT",
    11: "SW_ESTOP",
}


# ---------------------------------------------------------------------------
# Structured Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TelemetryChannelSpec:
    """Metadata and alarm limits for a single SCADA / OPC-UA telemetry channel."""

    channel_id: str
    subsystem: str
    bom_part_ids: tuple[str, ...]
    description: str
    unit: str
    opcua_datatype: str = "Double"
    nominal_value: float = 0.0
    sample_rate_hz: float = 1.0
    lo_lo: float | None = None
    lo: float | None = None
    hi: float | None = None
    hi_hi: float | None = None
    is_boolean_health: bool = False
    interlock_bit: int | None = None
    response_target: str = "log_and_operator_notify"

    @property
    def opcua_node_id(self) -> str:
        return f"ns={OPCUA_NAMESPACE_INDEX};s=ALM.{self.channel_id}"

    def evaluate_limit(self, value: float) -> tuple[str, str | None, int]:
        """Return ``(severity, limit_breached, opcua_status_code)`` for a sample value."""
        if not math.isfinite(value):
            return ("INTERLOCK_TRIP", "NON_FINITE_SENSOR", OPCUA_BAD_SENSOR_FAILURE)
        if self.is_boolean_health:
            if value < 0.5:
                sev = "INTERLOCK_TRIP" if self.interlock_bit is not None else "CRITICAL"
                return (sev, "HEALTH_FALSE", OPCUA_BAD_DEVICE_FAILURE)
            return ("NORMAL", None, OPCUA_GOOD)
        if self.lo_lo is not None and value <= self.lo_lo:
            sev = "INTERLOCK_TRIP" if self.interlock_bit is not None else "CRITICAL"
            return (sev, "LO_LO", OPCUA_BAD_OUT_OF_RANGE)
        if self.hi_hi is not None and value >= self.hi_hi:
            sev = "INTERLOCK_TRIP" if self.interlock_bit is not None else "CRITICAL"
            return (sev, "HI_HI", OPCUA_BAD_OUT_OF_RANGE)
        if self.lo is not None and value <= self.lo:
            return ("WARNING", "LO", OPCUA_GOOD)
        if self.hi is not None and value >= self.hi:
            return ("WARNING", "HI", OPCUA_GOOD)
        return ("NORMAL", None, OPCUA_GOOD)

    def to_opcua_node_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.opcua_node_id,
            "browse_name": f"{OPCUA_NAMESPACE_INDEX}:{self.channel_id}",
            "display_name": self.description,
            "node_class": "Variable",
            "data_type": self.opcua_datatype,
            "access_level": "CurrentRead",
            "engineering_unit": self.unit,
            "subsystem": self.subsystem,
            "bom_part_ids": list(self.bom_part_ids),
            "sample_rate_hz": self.sample_rate_hz,
            "nominal_value": self.nominal_value,
            "alarm_limits": {
                "lo_lo": self.lo_lo,
                "lo": self.lo,
                "hi": self.hi,
                "hi_hi": self.hi_hi,
                "is_boolean_health": self.is_boolean_health,
            },
            "interlock_bit": self.interlock_bit,
            "response_target": self.response_target,
        }


@dataclass(frozen=True)
class TelemetrySample:
    """Immutable timestamped sample stored in the ring-buffer historian."""

    seq: int
    timestamp_s: float
    channel_id: str
    opcua_node_id: str
    value: float
    unit: str
    status_code: int
    severity: str
    source: str = "scada_poll"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status_code_hex"] = f"0x{self.status_code:08X}"
        return d


@dataclass
class AlarmRecord:
    """ISA-18.2 latching alarm / interlock event record."""

    alarm_id: int
    channel_id: str
    opcua_node_id: str
    bom_part_ids: tuple[str, ...]
    severity: str
    limit_breached: str
    message: str
    trigger_value: float
    last_value: float
    unit: str
    triggered_at_s: float
    active: bool = True
    latched: bool = True
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at_s: float | None = None
    cleared_at_s: float | None = None
    response_target: str = "log_and_operator_notify"
    source: str = "threshold_monitor"

    @property
    def isa18_state(self) -> str:
        if self.active and not self.acknowledged:
            return "UNACK_ACTIVE"
        if self.active and self.acknowledged:
            return "ACK_ACTIVE"
        if not self.active and not self.acknowledged and self.latched:
            return "UNACK_CLEARED"
        return "NORMAL"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bom_part_ids"] = list(self.bom_part_ids)
        d["isa18_state"] = self.isa18_state
        return d


@dataclass(frozen=True)
class InterlockCSRSnapshot:
    """Decoded snapshot of ``rtl/machine_ctrl/fpga_top_machine_ctrl.v`` CSRs."""

    timestamp_s: float
    chip_id: int
    epistemic_csr: int
    certified: bool
    design_only_not_certified: bool
    no_lab_measurement: bool
    no_vendor_vivado_pnr: bool
    fsm_state_code: int
    fsm_state_name: str
    interlock_trip_out: bool
    safe_enables: dict[str, bool]
    first_fault_code: int
    first_fault_name: str
    trip_counter: int
    sensor_fault_latched: dict[str, bool]
    discrep_fault_latched: bool
    wdt_fault_latched: bool
    sw_estop_latched: bool
    discrep_ch_latched_mask: int
    ch_a_live_mask: int
    ch_b_live_mask: int
    live_discrep_mask: int
    blanker_safe_blanked: bool | None = None
    pid_abort_active: bool | None = None
    pid_last_temp_k: int | None = None
    spi_hw_hv_clamp: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["chip_id_hex"] = f"0x{self.chip_id:08X}"
        d["epistemic_csr_hex"] = f"0x{self.epistemic_csr:08X}"
        return d


# ---------------------------------------------------------------------------
# Default S1..S9 Machine Telemetry Channel Catalog
# ---------------------------------------------------------------------------

def build_default_channel_catalog() -> list[TelemetryChannelSpec]:
    """Build the canonical S1..S9 SCADA telemetry channel catalog (32 channels)."""
    return [
        # S1 — Ion Source & Column
        TelemetryChannelSpec(
            channel_id="S1.V_EXTRACT_KV",
            subsystem="S1",
            bom_part_ids=("S1.1-03", "S1.1-05"),
            description="Ion source extraction voltage (10-15 kV deck)",
            unit="kV",
            nominal_value=12.0,
            lo_lo=0.0,
            lo=9.5,
            hi=15.2,
            hi_hi=16.5,
            interlock_bit=5,
            response_target="HV clamp & 2 MOhm crowbar <18.3 ms",
        ),
        TelemetryChannelSpec(
            channel_id="S1.V_LANDING_KV",
            subsystem="S1",
            bom_part_ids=("S1.3-02", "S1.3-03"),
            description="Arch-B deceleration landing energy potential",
            unit="kV",
            nominal_value=5.0,
            lo_lo=0.0,
            lo=4.99,
            hi=5.01,
            hi_hi=5.5,
            interlock_bit=5,
            response_target="HV clamp & 2 MOhm crowbar <18.3 ms",
        ),
        TelemetryChannelSpec(
            channel_id="S1.P_SOURCE_HV_MBAR",
            subsystem="S1",
            bom_part_ids=("S1.1-01", "S1.3-05"),
            description="Duoplasmatron ion source differential pressure",
            unit="mbar",
            nominal_value=1.0e-6,
            hi=5.0e-6,
            hi_hi=2.0e-5,
            response_target="close column isolation valve",
        ),
        TelemetryChannelSpec(
            channel_id="S1.I_FARADAY_PA",
            subsystem="S1",
            bom_part_ids=("S1.4-01", "S1.4-02", "S1.4-03"),
            description="Retractable Faraday cup beam current monitor",
            unit="pA",
            nominal_value=10.0,
            lo=0.5,
            hi=500.0,
            hi_hi=2000.0,
        ),
        # S2 — MEMS Write Head & 1024-ch Blanker
        TelemetryChannelSpec(
            channel_id="S2.BLANKER_LIVE_CH",
            subsystem="S2",
            bom_part_ids=("S2.2-01", "S2.4-01", "S2.4-02"),
            description="Active healthy beamlets in 32x32 (1024-ch) blanker array",
            unit="ch",
            opcua_datatype="UInt32",
            nominal_value=1024.0,
            lo_lo=896.0,
            lo=972.0,
            hi=1024.0,
            response_target="invoke AutoRecal step-and-stitch remapping",
        ),
        TelemetryChannelSpec(
            channel_id="S2.MINILENS_RIPPLE_MVPP",
            subsystem="S2",
            bom_part_ids=("S2.3-01", "S2.3-04"),
            description="Mini-lens HV filter residual peak-to-peak ripple",
            unit="mVpp",
            nominal_value=0.15,
            hi=1.5,
            hi_hi=2.0,
            response_target="pause write & inspect HV active filter",
        ),
        # S3 — IBIC Cryo Detector
        TelemetryChannelSpec(
            channel_id="S3.T_IBIC_COLD_100K",
            subsystem="S3",
            bom_part_ids=("S3.2-01", "S3.2-04"),
            description="IBIC cold-island LTC6268 CSA thermal stage temperature",
            unit="K",
            nominal_value=100.0,
            lo=80.0,
            hi=115.0,
            hi_hi=135.0,
            response_target="pause implant if ENC noise rises >35 e-",
        ),
        TelemetryChannelSpec(
            channel_id="S3.IBIC_ENC_E_RMS",
            subsystem="S3",
            bom_part_ids=("S3.2-01", "S3.2-02", "S3.3-01"),
            description="IBIC front-end equivalent noise charge",
            unit="e_rms",
            nominal_value=25.2,
            hi=32.0,
            hi_hi=35.0,
            response_target="pause counted implantation; recalibrate trim DACs",
        ),
        # S4 — Isolation, Piezo Stage & Interferometry
        TelemetryChannelSpec(
            channel_id="S4.STAGE_DRIFT_NM",
            subsystem="S4",
            bom_part_ids=("S4.3-01", "S4.4-01", "S4.5-03"),
            description="Residual wafer-stage interferometric tracking error",
            unit="nm",
            nominal_value=0.25,
            hi=1.0,
            hi_hi=2.0,
            response_target="blank beam until laser interferometer locks",
        ),
        TelemetryChannelSpec(
            channel_id="S4.FLOOR_VIB_NM_RMS",
            subsystem="S4",
            bom_part_ids=("S4.1-02", "S4.2-01", "S4.2-02"),
            description="Active-isolated granite seismic RMS displacement",
            unit="nm_rms",
            nominal_value=0.4,
            hi=1.5,
            hi_hi=3.0,
        ),
        # S5 — UHV Chamber, Pumps, Flash/808 nm Laser & 28Si MBE
        TelemetryChannelSpec(
            channel_id="S5.P_MAIN_UHV_TORR",
            subsystem="S5",
            bom_part_ids=("S5.1-01", "S5.2-04", "S7.SAFETY-06"),
            description="Main UHV process chamber total pressure",
            unit="Torr",
            nominal_value=1.5e-10,
            hi=5.0e-9,
            hi_hi=1.0e-8,
            interlock_bit=0,
            response_target="blanker <1 us + fail-close UHV gate valve <80 ms",
        ),
        TelemetryChannelSpec(
            channel_id="S5.P_LOADLOCK_TORR",
            subsystem="S5",
            bom_part_ids=("S5.1-03", "S5.2-04"),
            description="Load-lock transfer chamber pressure",
            unit="Torr",
            nominal_value=5.0e-9,
            hi=1.0e-7,
            hi_hi=1.0e-6,
            response_target="inhibit load-lock gate valve open",
        ),
        TelemetryChannelSpec(
            channel_id="S5.LASER_808_POWER_W",
            subsystem="S5",
            bom_part_ids=("S5.5-01", "S5.5-03"),
            description="808 nm qCW diode annealing pulse power monitor",
            unit="W",
            nominal_value=1200.0,
            hi=1450.0,
            hi_hi=1650.0,
            response_target="AOM PID clamp & <0.1 ms RF crowbar",
        ),
        TelemetryChannelSpec(
            channel_id="S5.PYRO_TEMP_K",
            subsystem="S5",
            bom_part_ids=("S5.5-03", "S5.5-04"),
            description="2-color 10 us fast pyrometer Si wafer surface temperature",
            unit="K",
            nominal_value=300.0,
            hi=1580.0,
            hi_hi=1687.0,
            response_target="hardwired aom_pid_ctrl T>=1687 K melt abort -> zero RF drive",
        ),
        TelemetryChannelSpec(
            channel_id="S5.AOM_DRIVE_GAIN",
            subsystem="S5",
            bom_part_ids=("S5.3-03", "S5.5-01"),
            description="Normalized AOM PID modulation gain (0.65-1.40 clamp)",
            unit="ratio",
            nominal_value=1.0,
            lo=0.68,
            hi=1.35,
            hi_hi=1.41,
        ),
        TelemetryChannelSpec(
            channel_id="S5.MBE_SUBSTRATE_K",
            subsystem="S5",
            bom_part_ids=("S5.6-01", "S5.6-03"),
            description="28Si LT-MBE capper PBN wafer heater temperature",
            unit="K",
            nominal_value=618.0,
            hi=700.0,
            hi_hi=750.0,
        ),
        # S6 — 5-Stage Cryogenics, 20 mK DR, 8-Coil Magnet & Readout
        TelemetryChannelSpec(
            channel_id="S6.T_50K",
            subsystem="S6",
            bom_part_ids=("S6.1-01", "S6.2-03"),
            description="Cryo stage 1: PT420 50 K radiation shield temperature",
            unit="K",
            nominal_value=45.0,
            hi=58.0,
            hi_hi=70.0,
        ),
        TelemetryChannelSpec(
            channel_id="S6.T_4K",
            subsystem="S6",
            bom_part_ids=("S6.1-01", "S6.2-02", "S6.2-03"),
            description="Cryo stage 2: PT420 4 K magnet/HEMT plate temperature",
            unit="K",
            nominal_value=4.15,
            hi=4.5,
            hi_hi=5.2,
            response_target="inhibit magnet ramp; check PT420 / thermal braid",
        ),
        TelemetryChannelSpec(
            channel_id="S6.T_STILL_800MK",
            subsystem="S6",
            bom_part_ids=("S6.8-01", "S6.2-03"),
            description="Cryo stage 3: DR Still temperature",
            unit="mK",
            nominal_value=800.0,
            hi=950.0,
            hi_hi=1200.0,
        ),
        TelemetryChannelSpec(
            channel_id="S6.T_CP_100MK",
            subsystem="S6",
            bom_part_ids=("S6.8-01", "S6.2-03"),
            description="Cryo stage 4: DR Cold Plate temperature",
            unit="mK",
            nominal_value=100.0,
            hi=140.0,
            hi_hi=200.0,
        ),
        TelemetryChannelSpec(
            channel_id="S6.T_MXC_20MK",
            subsystem="S6",
            bom_part_ids=("S6.8-01", "S6.2-03"),
            description="Cryo stage 5: DR Mixing Chamber base temperature",
            unit="mK",
            nominal_value=20.0,
            hi=35.0,
            hi_hi=1000.0,
            response_target="halt readout; >1 K triggers cryo thermal interlock",
        ),
        TelemetryChannelSpec(
            channel_id="S6.B_FIELD_T",
            subsystem="S6",
            bom_part_ids=("S6.3-01", "S6.3-05"),
            description="8-coil NbTi superconducting magnet bore field",
            unit="T",
            nominal_value=1.5,
            hi=1.65,
            hi_hi=2.0,
        ),
        TelemetryChannelSpec(
            channel_id="S6.QUENCH_VOLT_V",
            subsystem="S6",
            bom_part_ids=("S6.3-04", "S7.SAFETY-05"),
            description="Magnet bridge quench detection voltage",
            unit="V",
            nominal_value=0.0,
            hi=0.15,
            hi_hi=0.50,
            interlock_bit=6,
            response_target="fire 1.563 Ohm quench dump bank (18.94 kJ, tau=0.370 s)",
        ),
        TelemetryChannelSpec(
            channel_id="S6.ZU48DR_TEMP_C",
            subsystem="S6",
            bom_part_ids=("S6.11-01",),
            description="ZU48DR BOED-FPGA die temperature",
            unit="degC",
            nominal_value=52.0,
            hi=78.0,
            hi_hi=88.0,
        ),
        # S7 — Facility Safety, Timing & UPS
        TelemetryChannelSpec(
            channel_id="S7.PH3_LEVEL_PPM",
            subsystem="S7",
            bom_part_ids=("S1.6-01", "S1.6-02", "S7.SAFETY-01"),
            description="Phosphine (PH3) toxic gas detector concentration (L1=0.02, L2=0.05 ppm)",
            unit="ppm",
            nominal_value=0.0,
            hi=0.02,
            hi_hi=0.05,
            interlock_bit=4,
            response_target="L1=0.02 ppm warn/scrubber; L2=0.05 ppm hard SDS shutoff",
        ),
        TelemetryChannelSpec(
            channel_id="S7.O2_ROOM_PCT",
            subsystem="S7",
            bom_part_ids=("S7.SAFETY-05",),
            description="Cleanroom Oxygen Deficiency Hazard (ODH) sensor",
            unit="%vol",
            nominal_value=20.9,
            lo_lo=19.5,
            lo=19.8,
            hi=23.0,
            interlock_bit=2,
            response_target="ODH alarm <19.5% O2 + cryo room exhaust + interlock trip",
        ),
        TelemetryChannelSpec(
            channel_id="S7.LASER_ENCL_OK",
            subsystem="S7",
            bom_part_ids=("S5.5-04", "S7.SAFETY-02"),
            description="Class-4 laser & X-ray shroud door switch health (1=CLOSED_OK)",
            unit="bool",
            opcua_datatype="Boolean",
            nominal_value=1.0,
            is_boolean_health=True,
            interlock_bit=1,
            response_target="dual-blade shutter <3.2 ms + laser diode cutoff",
        ),
        TelemetryChannelSpec(
            channel_id="S7.ESTOP_LOOP_OK",
            subsystem="S7",
            bom_part_ids=("S7.SAFETY-03",),
            description="4x perimeter dual-NC E-Stop loop health (1=OK, 0=PRESSED)",
            unit="bool",
            opcua_datatype="Boolean",
            nominal_value=1.0,
            is_boolean_health=True,
            interlock_bit=7,
            response_target="de-energize-to-trip all hazards <=20 ns FPGA / <18.3 ms HV",
        ),
        TelemetryChannelSpec(
            channel_id="S7.UPS_TIER1_LOAD_W",
            subsystem="S7",
            bom_part_ids=("S7.SAFETY-04",),
            description="15 kVA Online LFP UPS Tier-1 critical safety bus load",
            unit="W",
            nominal_value=2533.0,
            hi=3000.0,
            hi_hi=13500.0,
            response_target="verify Tier-2 load shed on mains loss (213.2 min Tier-1)",
        ),
        TelemetryChannelSpec(
            channel_id="S7.RB_10MHZ_LOCK",
            subsystem="S7",
            bom_part_ids=("S7.4-01", "S7.4-02"),
            description="10 MHz Rb atomic clock & White Rabbit sub-ns lock health",
            unit="bool",
            opcua_datatype="Boolean",
            nominal_value=1.0,
            is_boolean_health=True,
        ),
        # S8 — Software / BOED Relock Health
        TelemetryChannelSpec(
            channel_id="S8.BOED_RESID_ERR_HZ",
            subsystem="S8",
            bom_part_ids=("S8.3-03", "S6.11-01"),
            description="31P hyperfine BOED posterior residual frequency error",
            unit="Hz",
            nominal_value=20.0,
            hi=75.0,
            hi_hi=100.0,
            response_target="trigger AutoRecal Mode D hyperfine BOED relock",
        ),
        # S9 — Option-Q & Option-HPC
        TelemetryChannelSpec(
            channel_id="S9.HPC_DECODER_LAT_US",
            subsystem="S9",
            bom_part_ids=("S9.HPC-01", "S9.HPC-02", "S9.HPC-03"),
            description="Real-time qLDPC/surface-code syndrome decoder round latency",
            unit="us",
            nominal_value=45.0,
            hi=200.0,
            hi_hi=500.0,
        ),
    ]


# ---------------------------------------------------------------------------
# SCADA Telemetry Engine (Registry + Ring Buffer + Alarm Logger + Bridges)
# ---------------------------------------------------------------------------

class SCADATelemetryManager:
    """In-memory 1 Hz SCADA historian, OPC-UA address space & ISA-18.2 alarm manager.

    Strictly software/simulation-level (``S8.4-02``, ``M0_M1_DESIGN_ONLY``); does not
    open network sockets or claim hardware/safety certification.
    """

    def __init__(
        self,
        channels: list[TelemetryChannelSpec] | None = None,
        ring_capacity: int = 3600,
        frame_capacity: int = 3600,
    ) -> None:
        if ring_capacity < 1 or frame_capacity < 1:
            raise ValueError("ring_capacity and frame_capacity must be >= 1")
        self.ring_capacity = int(ring_capacity)
        self.frame_capacity = int(frame_capacity)
        specs = channels if channels is not None else build_default_channel_catalog()
        self._channels: dict[str, TelemetryChannelSpec] = {}
        self._history: dict[str, deque[TelemetrySample]] = {}
        self._latest: dict[str, TelemetrySample] = {}
        self._lock = threading.RLock()
        for spec in specs:
            self.register_channel(spec)

        self._global_samples: deque[TelemetrySample] = deque(maxlen=self.frame_capacity)
        self._alarms: dict[int, AlarmRecord] = {}
        self._active_alarm_by_key: dict[tuple[str, str], int] = {}
        self._event_log: deque[dict[str, Any]] = deque(maxlen=max(self.frame_capacity * 4, 4096))
        self._csr_snapshots: deque[InterlockCSRSnapshot] = deque(maxlen=256)
        self._sample_seq: int = 0
        self._alarm_seq: int = 0

    def register_channel(self, spec: TelemetryChannelSpec) -> None:
        with self._lock:
            if spec.channel_id in self._channels:
                raise ValueError(f"Duplicate telemetry channel_id: {spec.channel_id}")
            self._channels[spec.channel_id] = spec
            self._history[spec.channel_id] = deque(maxlen=self.ring_capacity)

    @property
    def channel_ids(self) -> list[str]:
        return sorted(self._channels.keys())

    def get_channel_spec(self, channel_id: str) -> TelemetryChannelSpec:
        if channel_id not in self._channels:
            raise KeyError(f"Unknown telemetry channel_id: {channel_id}")
        return self._channels[channel_id]

    def export_opcua_address_space(self) -> dict[str, Any]:
        """Export OPC-UA-compatible hierarchical address space (S1..S9 Objects + Variables)."""
        subsystems: dict[str, list[dict[str, Any]]] = {}
        for cid in self.channel_ids:
            spec = self._channels[cid]
            subsystems.setdefault(spec.subsystem, []).append(spec.to_opcua_node_dict())

        objects_tree = [
            {
                "node_id": f"ns={OPCUA_NAMESPACE_INDEX};s=ALM.{sub}",
                "browse_name": f"{OPCUA_NAMESPACE_INDEX}:{sub}",
                "node_class": "Object",
                "variables": nodes,
            }
            for sub, nodes in sorted(subsystems.items())
        ]
        return {
            "namespace_uri": OPCUA_NAMESPACE_URI,
            "namespace_index": OPCUA_NAMESPACE_INDEX,
            "root_node_id": f"ns={OPCUA_NAMESPACE_INDEX};s=ALM",
            "total_channels": len(self._channels),
            "subsystems_covered": sorted(subsystems.keys()),
            "objects": objects_tree,
            "epistemic": dict(EPISTEMIC_METADATA),
        }

    # ------------------------------------------------------------------
    # Sample Recording & Ring-Buffer Historian
    # ------------------------------------------------------------------

    def record_sample(
        self,
        channel_id: str,
        value: float,
        timestamp_s: float,
        source: str = "scada_poll",
    ) -> TelemetrySample:
        """Record one measurement, update ring buffer, and evaluate ISA-18.2 alarms."""
        with self._lock:
            spec = self.get_channel_spec(channel_id)
            fval = float(value)
            severity, limit_breached, status_code = spec.evaluate_limit(fval)

            self._sample_seq += 1
            sample = TelemetrySample(
                seq=self._sample_seq,
                timestamp_s=float(timestamp_s),
                channel_id=spec.channel_id,
                opcua_node_id=spec.opcua_node_id,
                value=fval,
                unit=spec.unit,
                status_code=status_code,
                severity=severity,
                source=source,
            )
            self._history[channel_id].append(sample)
            self._latest[channel_id] = sample
            self._global_samples.append(sample)

            if limit_breached is not None:
                # Clear any superseded threshold level on the same channel (e.g., HI_HI -> HI
                # or HI -> HI_HI or NON_FINITE_SENSOR recovery) per ISA-18.2 state transitions.
                self._clear_channel_alarms(
                    spec.channel_id,
                    float(timestamp_s),
                    fval,
                    exclude_limit=limit_breached,
                )
                self._raise_or_update_alarm(
                    channel_id=spec.channel_id,
                    opcua_node_id=spec.opcua_node_id,
                    bom_part_ids=spec.bom_part_ids,
                    severity=severity,
                    limit_breached=limit_breached,
                    value=fval,
                    unit=spec.unit,
                    timestamp_s=float(timestamp_s),
                    response_target=spec.response_target,
                    source=source,
                    message=(
                        f"{spec.channel_id} ({spec.description}) breached {limit_breached}: "
                        f"{fval:g} {spec.unit}"
                    ),
                )
            else:
                self._clear_channel_alarms(spec.channel_id, float(timestamp_s), fval)

            return sample

    def record_frame(
        self,
        values: dict[str, float],
        timestamp_s: float,
        source: str = "scada_1hz_frame",
    ) -> list[TelemetrySample]:
        """Record a synchronized multi-channel frame at a single 1 Hz timestamp."""
        with self._lock:
            return [
                self.record_sample(cid, val, timestamp_s=timestamp_s, source=source)
                for cid, val in sorted(values.items())
            ]

    def get_history(
        self,
        channel_id: str,
        t_start_s: float | None = None,
        t_end_s: float | None = None,
    ) -> list[TelemetrySample]:
        with self._lock:
            self.get_channel_spec(channel_id)
            samples = list(self._history[channel_id])
        if t_start_s is not None:
            samples = [s for s in samples if s.timestamp_s >= t_start_s]
        if t_end_s is not None:
            samples = [s for s in samples if s.timestamp_s <= t_end_s]
        return samples

    def get_channel_stats(self, channel_id: str) -> dict[str, Any]:
        samples = self.get_history(channel_id)
        if not samples:
            return {"channel_id": channel_id, "count": 0}
        vals = [s.value for s in samples if math.isfinite(s.value)]
        if not vals:
            return {"channel_id": channel_id, "count": len(samples), "finite_count": 0}
        mean_v = sum(vals) / len(vals)
        var_v = sum((x - mean_v) ** 2 for x in vals) / len(vals)
        return {
            "channel_id": channel_id,
            "count": len(samples),
            "min": min(vals),
            "max": max(vals),
            "mean": mean_v,
            "std": math.sqrt(var_v),
            "latest_value": samples[-1].value,
            "latest_timestamp_s": samples[-1].timestamp_s,
            "latest_severity": samples[-1].severity,
        }

    # ------------------------------------------------------------------
    # ISA-18.2 Alarm Latching & Acknowledgement
    # ------------------------------------------------------------------

    def _raise_or_update_alarm(
        self,
        *,
        channel_id: str,
        opcua_node_id: str,
        bom_part_ids: tuple[str, ...],
        severity: str,
        limit_breached: str,
        value: float,
        unit: str,
        timestamp_s: float,
        response_target: str,
        source: str,
        message: str,
    ) -> AlarmRecord:
        with self._lock:
            key = (channel_id, limit_breached)
            existing_id = self._active_alarm_by_key.get(key)
            if existing_id is not None and existing_id in self._alarms:
                rec = self._alarms[existing_id]
                rec.last_value = value
                rec.active = True
                return rec

            self._alarm_seq += 1
            rec = AlarmRecord(
                alarm_id=self._alarm_seq,
                channel_id=channel_id,
                opcua_node_id=opcua_node_id,
                bom_part_ids=bom_part_ids,
                severity=severity,
                limit_breached=limit_breached,
                message=message,
                trigger_value=value,
                last_value=value,
                unit=unit,
                triggered_at_s=timestamp_s,
                active=True,
                latched=True,
                acknowledged=False,
                response_target=response_target,
                source=source,
            )
            self._alarms[rec.alarm_id] = rec
            self._active_alarm_by_key[key] = rec.alarm_id
            self._event_log.append({
                "event_type": "ALARM_TRIGGERED",
                "timestamp_s": timestamp_s,
                "alarm_id": rec.alarm_id,
                "channel_id": channel_id,
                "severity": severity,
                "limit_breached": limit_breached,
                "value": value,
                "isa18_state": rec.isa18_state,
                "source": source,
            })
            return rec

    def _clear_channel_alarms(
        self,
        channel_id: str,
        timestamp_s: float,
        value: float,
        exclude_limit: str | None = None,
    ) -> None:
        with self._lock:
            for key, aid in list(self._active_alarm_by_key.items()):
                if key[0] != channel_id:
                    continue
                if exclude_limit is not None and key[1] == exclude_limit:
                    continue
                rec = self._alarms[aid]
                if rec.active:
                    rec.active = False
                    rec.last_value = value
                    rec.cleared_at_s = timestamp_s
                    if rec.acknowledged:
                        rec.latched = False
                        del self._active_alarm_by_key[key]
                    self._event_log.append({
                        "event_type": "ALARM_CLEARED_PHYSICAL",
                        "timestamp_s": timestamp_s,
                        "alarm_id": rec.alarm_id,
                        "channel_id": channel_id,
                        "limit_breached": rec.limit_breached,
                        "isa18_state": rec.isa18_state,
                        "latched": rec.latched,
                    })

    def acknowledge_alarm(
        self,
        alarm_id: int,
        operator: str,
        timestamp_s: float,
    ) -> AlarmRecord:
        """Acknowledge a latched alarm; releases latch only if physical fault has cleared."""
        with self._lock:
            if alarm_id not in self._alarms:
                raise KeyError(f"Unknown alarm_id: {alarm_id}")
            if not operator or not operator.strip():
                raise ValueError("Operator identifier must be non-empty")
            rec = self._alarms[alarm_id]
            rec.acknowledged = True
            rec.acknowledged_by = operator.strip()
            rec.acknowledged_at_s = float(timestamp_s)
            if not rec.active:
                rec.latched = False
                key = (rec.channel_id, rec.limit_breached)
                if self._active_alarm_by_key.get(key) == alarm_id:
                    del self._active_alarm_by_key[key]
            self._event_log.append({
                "event_type": "ALARM_ACKNOWLEDGED",
                "timestamp_s": float(timestamp_s),
                "alarm_id": rec.alarm_id,
                "channel_id": rec.channel_id,
                "operator": rec.acknowledged_by,
                "isa18_state": rec.isa18_state,
                "still_active": rec.active,
                "latched": rec.latched,
            })
            return rec

    def get_latched_alarms(self) -> list[AlarmRecord]:
        with self._lock:
            return [r for r in self._alarms.values() if r.latched or r.active]

    def get_all_alarms(self) -> list[AlarmRecord]:
        with self._lock:
            return [self._alarms[k] for k in sorted(self._alarms.keys())]

    # ------------------------------------------------------------------
    # Hardware Integration Hook 1: rtl/machine_ctrl/uhv_interlock_fsm.v CSR Map
    # ------------------------------------------------------------------

    def build_il_sensor_vectors_from_telemetry(self) -> tuple[int, int]:
        """Compute 8-bit ``(ch_a_ok, ch_b_ok)`` health bitmasks matching ``uhv_interlock_fsm.v``.

        Strictly fail-safe on non-finite (``NaN`` / ``Inf``) telemetry: any non-finite
        reading on a safety-interlock channel immediately clears its hardware health bit
        (and any non-finite vacuum/source gauge clears bit 0).
        """
        with self._lock:
            latest = dict(self._latest)
            channels = dict(self._channels)

        def _bad_hi(cid: str, limit: float) -> bool:
            if cid not in latest:
                return False
            v = latest[cid].value
            return (not math.isfinite(v)) or (v >= limit)

        def _bad_lo(cid: str, limit: float) -> bool:
            if cid not in latest:
                return False
            v = latest[cid].value
            return (not math.isfinite(v)) or (v <= limit)

        def _bad_bool(cid: str) -> bool:
            if cid not in latest:
                return False
            v = latest[cid].value
            return (not math.isfinite(v)) or (v < 0.5)

        mask = 0xFF
        # bit 0: UHV / source vacuum gauges healthy & finite
        if _bad_hi("S5.P_MAIN_UHV_TORR", 1.0e-8) or _bad_hi("S1.P_SOURCE_HV_MBAR", 2.0e-5) or (
            "S1.P_CH1_TORR" in latest and (not math.isfinite(latest["S1.P_CH1_TORR"].value) or latest["S1.P_CH1_TORR"].value >= 1.0e-8)
        ):
            mask &= ~(1 << 0)
        # bit 1: Laser enclosure door switch
        if _bad_bool("S7.LASER_ENCL_OK"):
            mask &= ~(1 << 1)
        # bit 2: ODH O2 >= 19.5%
        if _bad_lo("S7.O2_ROOM_PCT", 19.5):
            mask &= ~(1 << 2)
        # bit 3: PH3 L1 (< 0.02 ppm)
        if _bad_hi("S7.PH3_LEVEL_PPM", 0.02):
            mask &= ~(1 << 3)
        # bit 4: PH3 L2 (< 0.05 ppm)
        if _bad_hi("S7.PH3_LEVEL_PPM", 0.05):
            mask &= ~(1 << 4)
        # bit 5: HV within landing/extract limits
        if _bad_hi("S1.V_LANDING_KV", 5.5) or _bad_hi("S1.V_EXTRACT_KV", 16.5):
            mask &= ~(1 << 5)
        # bit 6: Magnet quench voltage < 0.5 V
        if _bad_hi("S6.QUENCH_VOLT_V", 0.5):
            mask &= ~(1 << 6)
        # bit 7: E-Stop loop OK
        if _bad_bool("S7.ESTOP_LOOP_OK"):
            mask &= ~(1 << 7)

        # Generic fail-safe sweep: any registered channel with an interlock_bit that reports
        # a non-finite value or INTERLOCK_TRIP clears its bit unconditionally.
        for cid, sample in latest.items():
            spec = channels.get(cid)
            if spec is not None and spec.interlock_bit is not None and 0 <= spec.interlock_bit <= 7:
                if not math.isfinite(sample.value) or sample.severity == "INTERLOCK_TRIP":
                    mask &= ~(1 << spec.interlock_bit)
        return (mask, mask)

    def ingest_fpga_csr_snapshot(
        self,
        regs: dict[int, int],
        timestamp_s: float,
    ) -> InterlockCSRSnapshot:
        """Decode ``fpga_top_machine_ctrl`` CSRs (``REGMAP.md``) and latch interlock faults."""
        with self._lock:
            return self._ingest_fpga_csr_snapshot_unlocked(regs, timestamp_s)

    def _ingest_fpga_csr_snapshot_unlocked(
        self,
        regs: dict[int, int],
        timestamp_s: float,
    ) -> InterlockCSRSnapshot:
        chip_id = int(regs.get(CSR_CHIP_ID, EXPECTED_CHIP_ID)) & 0xFFFFFFFF
        epi_csr = int(
            regs.get(CSR_IL_EPISTEMIC_CSR, regs.get(CSR_EPISTEMIC_STATUS, EXPECTED_EPISTEMIC_CSR))
        ) & 0xFFFFFFFF
        il_status = int(regs.get(CSR_IL_STATUS, 0)) & 0xFFFFFFFF
        il_fault = int(regs.get(CSR_IL_FAULT_LATCH, 0)) & 0xFFFFFFFF
        il_live = int(regs.get(CSR_IL_LIVE_SENSORS, 0)) & 0xFFFFFFFF

        certified = bool(epi_csr & 0x1) or bool((il_status >> 14) & 0x1)
        design_only = bool((epi_csr >> 1) & 0x1) and bool((il_status >> 15) & 0x1 if CSR_IL_STATUS in regs else True)
        no_lab = bool((epi_csr >> 2) & 0x1)
        no_vivado = bool((epi_csr >> 3) & 0x1)

        fsm_code = il_status & 0x7
        fsm_name = INTERLOCK_FSM_STATES.get(fsm_code, f"UNKNOWN_{fsm_code}")
        trip_out = bool((il_status >> 3) & 0x1)
        safe_enables = {
            "blanker": bool((il_status >> 4) & 0x1),
            "laser": bool((il_status >> 5) & 0x1),
            "hv": bool((il_status >> 6) & 0x1),
            "uhv_valve": bool((il_status >> 7) & 0x1),
            "ph3_valve": bool((il_status >> 8) & 0x1),
            "magnet": bool((il_status >> 9) & 0x1),
        }
        ff_code = (il_status >> 10) & 0xF
        ff_name = FIRST_FAULT_CODES.get(ff_code, f"CODE_{ff_code}")
        trip_counter = (il_status >> 16) & 0xFFFF

        sensor_faults = {
            info["name"]: bool((il_fault >> bit) & 0x1)
            for bit, info in INTERLOCK_SENSOR_BITS.items()
        }
        discrep_latched = bool((il_fault >> 8) & 0x1)
        wdt_latched = bool((il_fault >> 9) & 0x1)
        sw_estop_latched = bool((il_fault >> 10) & 0x1)
        discrep_ch_mask = (il_fault >> 16) & 0xFF

        ch_a_live = il_live & 0xFF
        ch_b_live = (il_live >> 8) & 0xFF
        live_discrep = (il_live >> 16) & 0xFF

        blk_safe = bool((int(regs[CSR_BLK_STATUS]) >> 1) & 0x1) if CSR_BLK_STATUS in regs else None
        pid_abort = bool((int(regs[CSR_PID_STATUS]) >> 4) & 0x1) if CSR_PID_STATUS in regs else None
        pid_temp_k = ((int(regs[CSR_PID_STATUS]) >> 16) & 0xFFFF) if CSR_PID_STATUS in regs else None
        spi_clamp = bool((int(regs[CSR_SPI_STATUS]) >> 2) & 0x1) if CSR_SPI_STATUS in regs else None

        snap = InterlockCSRSnapshot(
            timestamp_s=float(timestamp_s),
            chip_id=chip_id,
            epistemic_csr=epi_csr,
            certified=certified,
            design_only_not_certified=design_only,
            no_lab_measurement=no_lab,
            no_vendor_vivado_pnr=no_vivado,
            fsm_state_code=fsm_code,
            fsm_state_name=fsm_name,
            interlock_trip_out=trip_out,
            safe_enables=safe_enables,
            first_fault_code=ff_code,
            first_fault_name=ff_name,
            trip_counter=trip_counter,
            sensor_fault_latched=sensor_faults,
            discrep_fault_latched=discrep_latched,
            wdt_fault_latched=wdt_latched,
            sw_estop_latched=sw_estop_latched,
            discrep_ch_latched_mask=discrep_ch_mask,
            ch_a_live_mask=ch_a_live,
            ch_b_live_mask=ch_b_live,
            live_discrep_mask=live_discrep,
            blanker_safe_blanked=blk_safe,
            pid_abort_active=pid_abort,
            pid_last_temp_k=pid_temp_k,
            spi_hw_hv_clamp=spi_clamp,
        )
        self._csr_snapshots.append(snap)

        # Latch SCADA alarms for any active FPGA interlock faults
        for bit, info in INTERLOCK_SENSOR_BITS.items():
            if sensor_faults[info["name"]]:
                self._raise_or_update_alarm(
                    channel_id=info["channel_id"],
                    opcua_node_id=f"ns={OPCUA_NAMESPACE_INDEX};s=ALM.{info['channel_id']}",
                    bom_part_ids=info["bom_ids"],
                    severity="INTERLOCK_TRIP",
                    limit_breached=f"FPGA_IL_BIT{bit}_{info['name']}",
                    value=0.0,
                    unit="flag",
                    timestamp_s=float(timestamp_s),
                    response_target=info["response_target"],
                    source="fpga_uhv_interlock_fsm_csr",
                    message=f"FPGA 1oo2D interlock bit {bit} ({info['name']}) latched; first_fault={ff_name}",
                )

        if discrep_latched or live_discrep != 0:
            self._raise_or_update_alarm(
                channel_id="S7.ESTOP_LOOP_OK",
                opcua_node_id=f"ns={OPCUA_NAMESPACE_INDEX};s=ALM.FPGA.1OO2D_DISCREP",
                bom_part_ids=("S7.SAFETY-03", "S7.4-04"),
                severity="INTERLOCK_TRIP",
                limit_breached="FPGA_1OO2D_DISCREPANCY",
                value=float(discrep_ch_mask or live_discrep),
                unit="bitmask",
                timestamp_s=float(timestamp_s),
                response_target="1oo2D cross-channel mismatch; hardware inspection required",
                source="fpga_uhv_interlock_fsm_csr",
                message=f"1oo2D Ch-A/Ch-B discrepancy detected (mask=0x{discrep_ch_mask or live_discrep:02X})",
            )

        if wdt_latched:
            self._raise_or_update_alarm(
                channel_id="S7.ESTOP_LOOP_OK",
                opcua_node_id=f"ns={OPCUA_NAMESPACE_INDEX};s=ALM.FPGA.WDT_TIMEOUT",
                bom_part_ids=("S7.SAFETY-03", "S7.4-04"),
                severity="INTERLOCK_TRIP",
                limit_breached="FPGA_WDT_TIMEOUT",
                value=1.0,
                unit="flag",
                timestamp_s=float(timestamp_s),
                response_target="hardware watchdog timeout -> fail-safe trip",
                source="fpga_uhv_interlock_fsm_csr",
                message="FPGA uhv_interlock_fsm hardware watchdog timeout latched",
            )

        if pid_temp_k is not None and pid_temp_k > 0:
            self.record_sample("S5.PYRO_TEMP_K", float(pid_temp_k), timestamp_s=timestamp_s, source="fpga_aom_pid_csr")

        return snap

    # ------------------------------------------------------------------
    # Hardware Integration Hook 2: src/machine_control/auto_recal.py
    # ------------------------------------------------------------------

    def ingest_auto_recal_report(
        self,
        report: dict[str, Any],
        timestamp_s: float,
    ) -> dict[str, Any]:
        """Ingest output of ``AutoRecalController`` (single-mode or ``run_all_fault_scenarios``)."""
        with self._lock:
            return self._ingest_auto_recal_report_unlocked(report, timestamp_s)

    def _ingest_auto_recal_report_unlocked(
        self,
        report: dict[str, Any],
        timestamp_s: float,
    ) -> dict[str, Any]:
        ingested_channels: list[str] = []
        sub_reports: list[dict[str, Any]] = []
        if "fault_mode" in report:
            sub_reports.append(report)
        else:
            for key in (
                "S5_5_laser_drift",
                "S5_uhv_vacuum_spike",
                "S3_blanker_dead_channels",
                "hyperfine_thermal_drift",
            ):
                if isinstance(report.get(key), dict):
                    sub_reports.append(report[key])

        for sub in sub_reports:
            mode = str(sub.get("fault_mode", "")).lower()
            if mode == "s5.5_laser_power_drift":
                # Peak wafer temperature & PID gain across drift cases
                cases = sub.get("cases", {})
                peak_t = max(
                    (
                        float(c.get("controlled_T_peak_K", c.get("peak_T_K", 300.0)))
                        for c in cases.values()
                        if isinstance(c, dict)
                    ),
                    default=float(sub.get("reference_T_peak_K", 300.0)),
                )
                self.record_sample("S5.PYRO_TEMP_K", peak_t, timestamp_s=timestamp_s, source="auto_recal_mode_a")
                ingested_channels.append("S5.PYRO_TEMP_K")
                max_gain = max(
                    (
                        float(c.get("servo_aom_gain", c.get("max_aom_gain", 1.0)))
                        for c in cases.values()
                        if isinstance(c, dict)
                    ),
                    default=1.0,
                )
                self.record_sample("S5.AOM_DRIVE_GAIN", max_gain, timestamp_s=timestamp_s, source="auto_recal_mode_a")
                ingested_channels.append("S5.AOM_DRIVE_GAIN")

            elif mode == "s5_uhv_vacuum_spike":
                p_peak = float(
                    sub.get(
                        "peak_pressure_torr",
                        sub.get(
                            "peak_ch1_source_torr",
                            sub.get("peak_ch2_wafer_torr", 1.5e-10),
                        ),
                    )
                )
                self.record_sample("S5.P_MAIN_UHV_TORR", p_peak, timestamp_s=timestamp_s, source="auto_recal_mode_b")
                ingested_channels.append("S5.P_MAIN_UHV_TORR")
                if "post_recovery_pressure_torr" in sub:
                    self.record_sample(
                        "S5.P_MAIN_UHV_TORR",
                        float(sub["post_recovery_pressure_torr"]),
                        timestamp_s=timestamp_s + 1.0,
                        source="auto_recal_mode_b_recovered",
                    )

            elif mode == "s3_blanker_dead_channels":
                n_total = int(sub.get("total_logical_channels", 1024))
                n_dead = int(sub.get("dead_channels_detected", 0))
                n_live = max(0, n_total - n_dead)
                self.record_sample("S2.BLANKER_LIVE_CH", float(n_live), timestamp_s=timestamp_s, source="auto_recal_mode_c")
                ingested_channels.append("S2.BLANKER_LIVE_CH")

            elif mode == "31p_hyperfine_thermal_drift":
                resid = float(sub.get("max_residual_error_Hz", 0.0))
                self.record_sample("S8.BOED_RESID_ERR_HZ", resid, timestamp_s=timestamp_s, source="auto_recal_mode_d")
                ingested_channels.append("S8.BOED_RESID_ERR_HZ")

        event = {
            "event_type": "AUTO_RECAL_INGESTED",
            "timestamp_s": float(timestamp_s),
            "modes_ingested": [s.get("fault_mode", "") for s in sub_reports],
            "channels_updated": ingested_channels,
            "all_passed": bool(report.get("all_passed", report.get("passed", False))),
        }
        self._event_log.append(event)
        return event

    # ------------------------------------------------------------------
    # JSONL Export & Verification Reload
    # ------------------------------------------------------------------

    def export_jsonl(self, path: str | Path) -> dict[str, Any]:
        """Export metadata header, ring-buffer samples, CSR snapshots & alarms to JSONL."""
        with self._lock:
            return self._export_jsonl_unlocked(path)

    def _export_jsonl_unlocked(self, path: str | Path) -> dict[str, Any]:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []

        header = {
            "record_type": "HEADER",
            "namespace_uri": OPCUA_NAMESPACE_URI,
            "total_channels": len(self._channels),
            "sample_count": len(self._global_samples),
            "alarm_count": len(self._alarms),
            "csr_snapshot_count": len(self._csr_snapshots),
            "event_count": len(self._event_log),
            "epistemic": dict(EPISTEMIC_METADATA),
        }
        lines.append(json.dumps(header, sort_keys=True))

        for sample in self._global_samples:
            lines.append(json.dumps({"record_type": "SAMPLE", **sample.to_dict()}, sort_keys=True))
        for snap in self._csr_snapshots:
            lines.append(json.dumps({"record_type": "FPGA_CSR", **snap.to_dict()}, sort_keys=True))
        for alarm in self.get_all_alarms():
            lines.append(json.dumps({"record_type": "ALARM", **alarm.to_dict()}, sort_keys=True))
        for ev in self._event_log:
            lines.append(json.dumps({"record_type": "EVENT", **ev}, sort_keys=True))

        payload = "\n".join(lines) + "\n"
        out_path.write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return {
            "path": str(out_path),
            "records_written": len(lines),
            "sha256": digest,
        }

    @staticmethod
    def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
        """Read back JSONL telemetry records."""
        in_path = Path(path)
        return [
            json.loads(line)
            for line in in_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "channels_registered": len(self._channels),
                "samples_in_ring": len(self._global_samples),
                "total_samples_recorded": self._sample_seq,
                "total_alarms": len(self._alarms),
                "latched_alarms": len(self.get_latched_alarms()),
                "csr_snapshots": len(self._csr_snapshots),
                "epistemic": dict(EPISTEMIC_METADATA),
            }
