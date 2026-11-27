"""Verification tests for S8.4-02 SCADA Telemetry, OPC-UA Schema & Interlock Logger."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from src.machine_control.auto_recal import AutoRecalController
from src.machine_control.scada_telemetry import (
    CSR_BLK_STATUS,
    CSR_CHIP_ID,
    CSR_EPISTEMIC_STATUS,
    CSR_IL_EPISTEMIC_CSR,
    CSR_IL_FAULT_LATCH,
    CSR_IL_LIVE_SENSORS,
    CSR_IL_STATUS,
    CSR_PID_STATUS,
    CSR_SPI_STATUS,
    EPISTEMIC_METADATA,
    EXPECTED_CHIP_ID,
    EXPECTED_EPISTEMIC_CSR,
    OPCUA_BAD_DEVICE_FAILURE,
    OPCUA_BAD_OUT_OF_RANGE,
    OPCUA_BAD_SENSOR_FAILURE,
    OPCUA_GOOD,
    SCADATelemetryManager,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BOM_CSV = REPO_ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"


def _bom_ids() -> set[str]:
    with BOM_CSV.open(encoding="utf-8") as fh:
        return {row["part_id"] for row in csv.DictReader(fh)}


def test_default_catalog_covers_s1_to_s9_and_valid_bom_ids() -> None:
    mgr = SCADATelemetryManager()
    addr = mgr.export_opcua_address_space()
    assert addr["subsystems_covered"] == ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
    assert addr["total_channels"] >= 30

    # Verify all 5 cryogenic temperature stages + vacuum + PH3 + B-field (S8.4-02 key_spec)
    required = {
        "S6.T_50K",
        "S6.T_4K",
        "S6.T_STILL_800MK",
        "S6.T_CP_100MK",
        "S6.T_MXC_20MK",
        "S5.P_MAIN_UHV_TORR",
        "S7.PH3_LEVEL_PPM",
        "S7.O2_ROOM_PCT",
        "S6.B_FIELD_T",
        "S6.QUENCH_VOLT_V",
        "S5.PYRO_TEMP_K",
    }
    assert required.issubset(set(mgr.channel_ids))

    # Every BOM part ID cited in the SCADA catalog must exist in BOM_DETAILED.csv
    valid_bom = _bom_ids()
    for cid in mgr.channel_ids:
        spec = mgr.get_channel_spec(cid)
        assert spec.bom_part_ids, f"{cid} missing bom_part_ids"
        for pid in spec.bom_part_ids:
            assert pid in valid_bom, f"Invalid BOM ID {pid} referenced by {cid}"
        assert spec.opcua_node_id == f"ns=2;s=ALM.{cid}"

    # Strict epistemic lock
    epi = addr["epistemic"]
    assert epi["bom_part_id"] == "S8.4-02"
    assert epi["design_maturity"] == "M0_M1_DESIGN_ONLY"
    assert epi["no_lab_measurement"] is True
    assert epi["iec61508_certified"] is False
    assert epi["semi_s2_certified"] is False
    assert EPISTEMIC_METADATA["opcua_live_server_connected"] is False


def test_ring_buffer_historian_eviction_and_stats() -> None:
    mgr = SCADATelemetryManager(ring_capacity=5, frame_capacity=10)
    for t in range(1, 9):
        s = mgr.record_sample("S6.T_MXC_20MK", 20.0 + 0.5 * t, timestamp_s=float(t))
        assert s.status_code == OPCUA_GOOD
        assert s.severity == "NORMAL"

    hist = mgr.get_history("S6.T_MXC_20MK")
    assert len(hist) == 5
    assert [h.timestamp_s for h in hist] == [4.0, 5.0, 6.0, 7.0, 8.0]

    sub = mgr.get_history("S6.T_MXC_20MK", t_start_s=5.0, t_end_s=7.0)
    assert [h.timestamp_s for h in sub] == [5.0, 6.0, 7.0]

    stats = mgr.get_channel_stats("S6.T_MXC_20MK")
    assert stats["count"] == 5
    assert math.isclose(stats["min"], 22.0)
    assert math.isclose(stats["max"], 24.0)
    assert math.isclose(stats["mean"], 23.0)

    # Non-finite sensor reading must trip sensor-failure alarm
    bad = mgr.record_sample("S6.T_4K", float("nan"), timestamp_s=9.0)
    assert bad.status_code == OPCUA_BAD_SENSOR_FAILURE
    assert bad.severity == "INTERLOCK_TRIP"


def test_isa18_alarm_latching_and_acknowledgement_lifecycle() -> None:
    mgr = SCADATelemetryManager()

    # Path A: Trigger -> Physical Clear -> Remains Latched (UNACK_CLEARED) -> Ack -> NORMAL
    s_trip = mgr.record_sample("S7.PH3_LEVEL_PPM", 0.06, timestamp_s=10.0)
    assert s_trip.severity == "INTERLOCK_TRIP"
    assert s_trip.status_code == OPCUA_BAD_OUT_OF_RANGE

    latched = mgr.get_latched_alarms()
    assert len(latched) == 1
    aid = latched[0].alarm_id
    assert latched[0].isa18_state == "UNACK_ACTIVE"

    # Fault clears physically, but operator has not acknowledged yet -> MUST stay latched
    mgr.record_sample("S7.PH3_LEVEL_PPM", 0.0, timestamp_s=12.0)
    latched_after_clear = mgr.get_latched_alarms()
    assert len(latched_after_clear) == 1
    assert latched_after_clear[0].active is False
    assert latched_after_clear[0].latched is True
    assert latched_after_clear[0].isa18_state == "UNACK_CLEARED"

    # Operator acknowledges -> releases latch
    rec = mgr.acknowledge_alarm(aid, operator="shift_eng_01", timestamp_s=15.0)
    assert rec.isa18_state == "NORMAL"
    assert rec.latched is False
    assert mgr.get_latched_alarms() == []

    # Path B: Trigger -> Ack while still active (ACK_ACTIVE) -> Physical Clear -> NORMAL
    s_door = mgr.record_sample("S7.LASER_ENCL_OK", 0.0, timestamp_s=20.0)
    assert s_door.status_code == OPCUA_BAD_DEVICE_FAILURE
    aid2 = mgr.get_latched_alarms()[0].alarm_id

    rec2 = mgr.acknowledge_alarm(aid2, operator="safety_officer", timestamp_s=21.0)
    assert rec2.isa18_state == "ACK_ACTIVE"
    assert rec2.active is True
    assert rec2.latched is True

    mgr.record_sample("S7.LASER_ENCL_OK", 1.0, timestamp_s=25.0)
    assert rec2.isa18_state == "NORMAL"
    assert mgr.get_latched_alarms() == []


def test_fpga_uhv_interlock_csr_decode_and_sensor_vector_bridge() -> None:
    mgr = SCADATelemetryManager()
    # Nominal healthy frame -> all 8 interlock bits healthy (0xFF, 0xFF)
    mgr.record_frame(
        {
            "S5.P_MAIN_UHV_TORR": 1.5e-10,
            "S7.LASER_ENCL_OK": 1.0,
            "S7.O2_ROOM_PCT": 20.9,
            "S7.PH3_LEVEL_PPM": 0.0,
            "S1.V_LANDING_KV": 5.0,
            "S1.V_EXTRACT_KV": 12.0,
            "S6.QUENCH_VOLT_V": 0.0,
            "S7.ESTOP_LOOP_OK": 1.0,
        },
        timestamp_s=100.0,
    )
    assert mgr.build_il_sensor_vectors_from_telemetry() == (0xFF, 0xFF)

    # Inject ODH O2 < 19.5% + UHV spike > 1e-8 Torr -> bits 0 and 2 drop low
    mgr.record_sample("S7.O2_ROOM_PCT", 19.1, timestamp_s=101.0)
    mgr.record_sample("S5.P_MAIN_UHV_TORR", 3.5e-8, timestamp_s=101.0)
    ch_a, ch_b = mgr.build_il_sensor_vectors_from_telemetry()
    assert ch_a == (0xFF & ~((1 << 0) | (1 << 2)))
    assert ch_b == ch_a

    # Decode bit-exact FPGA CSR snapshot matching rtl/machine_ctrl/REGMAP.md:
    # FSM=FAULT_LATCHED (1), trip_out=1 (bit 3), safe_enables=0, first_fault=3 (ODH_O2_LOW),
    # CERTIFIED=0 (bit 14), DESIGN_ONLY=1 (bit 15), trip_counter=4 (bits 31:16)
    il_status = (1) | (1 << 3) | (3 << 10) | (1 << 15) | (4 << 16)
    # sensor_fault_latched bit 2 (ODH) + discrep bit 8 + discrep ch bit 2 (bit 18) + WDT bit 9
    il_fault = (1 << 2) | (1 << 8) | (1 << 9) | (1 << 18)
    il_live = (0xFB) | (0xFF << 8) | (0x04 << 16)
    pid_status = (1 << 4) | (1690 << 16)  # abort_active=1, last_temp_k=1690 K (>=1687 K!)
    regs = {
        CSR_CHIP_ID: EXPECTED_CHIP_ID,
        CSR_EPISTEMIC_STATUS: EXPECTED_EPISTEMIC_CSR,
        CSR_IL_EPISTEMIC_CSR: EXPECTED_EPISTEMIC_CSR,
        CSR_IL_STATUS: il_status,
        CSR_IL_FAULT_LATCH: il_fault,
        CSR_IL_LIVE_SENSORS: il_live,
        CSR_BLK_STATUS: 0x00000002,  # safe_blanked=1
        CSR_PID_STATUS: pid_status,
        CSR_SPI_STATUS: 0x00000004,  # hw_hv_clamp=1
    }
    snap = mgr.ingest_fpga_csr_snapshot(regs, timestamp_s=102.0)
    assert snap.chip_id == EXPECTED_CHIP_ID
    assert snap.certified is False
    assert snap.design_only_not_certified is True
    assert snap.no_lab_measurement is True
    assert snap.no_vendor_vivado_pnr is True
    assert snap.fsm_state_name == "FAULT_LATCHED"
    assert snap.interlock_trip_out is True
    assert all(not v for v in snap.safe_enables.values())
    assert snap.first_fault_name == "ODH_O2_LOW"
    assert snap.trip_counter == 4
    assert snap.sensor_fault_latched["ODH_O2_LOW"] is True
    assert snap.discrep_fault_latched is True
    assert snap.wdt_fault_latched is True
    assert snap.live_discrep_mask == 0x04
    assert snap.blanker_safe_blanked is True
    assert snap.pid_abort_active is True
    assert snap.pid_last_temp_k == 1690
    assert snap.spi_hw_hv_clamp is True

    # Confirm FPGA faults + T=1690 K melt limit latched alarms in SCADA
    breached = {a.limit_breached for a in mgr.get_latched_alarms()}
    assert "FPGA_IL_BIT2_ODH_O2_LOW" in breached
    assert "FPGA_1OO2D_DISCREPANCY" in breached
    assert "FPGA_WDT_TIMEOUT" in breached
    assert "HI_HI" in breached  # S5.PYRO_TEMP_K >= 1687 K


def test_auto_recal_integration_and_jsonl_roundtrip(tmp_path: Path) -> None:
    mgr = SCADATelemetryManager()
    recal = AutoRecalController(seed=42)
    report = recal.run_all_fault_scenarios()
    assert report["all_passed"] is True

    ev = mgr.ingest_auto_recal_report(report, timestamp_s=500.0)
    assert ev["all_passed"] is True
    assert len(ev["modes_ingested"]) == 4
    assert "S5.P_MAIN_UHV_TORR" in ev["channels_updated"]
    assert "S2.BLANKER_LIVE_CH" in ev["channels_updated"]
    assert "S5.PYRO_TEMP_K" in ev["channels_updated"]
    assert "S8.BOED_RESID_ERR_HZ" in ev["channels_updated"]

    # Mode B injected 3.5e-8 Torr spike then recovered -> alarm must be latched UNACK_CLEARED
    uhv_alarms = [a for a in mgr.get_latched_alarms() if a.channel_id == "S5.P_MAIN_UHV_TORR"]
    assert len(uhv_alarms) == 1
    assert uhv_alarms[0].isa18_state == "UNACK_CLEARED"

    # JSONL export & deterministic reload
    out_file = tmp_path / "scada_hist.jsonl"
    meta = mgr.export_jsonl(out_file)
    assert len(meta["sha256"]) == 64
    assert meta["records_written"] >= 8

    rows = SCADATelemetryManager.load_jsonl(out_file)
    assert rows[0]["record_type"] == "HEADER"
    assert rows[0]["epistemic"]["no_lab_measurement"] is True
    assert rows[0]["epistemic"]["iec61508_certified"] is False
    record_types = {r["record_type"] for r in rows}
    assert {"HEADER", "SAMPLE", "ALARM", "EVENT"}.issubset(record_types)

    # Validation edge cases
    with pytest.raises(KeyError):
        mgr.record_sample("NO.SUCH.CH", 1.0, timestamp_s=1.0)
    with pytest.raises(ValueError):
        SCADATelemetryManager(ring_capacity=0)


def test_obs080_nan_inf_failsafe_interlock_superseded_latches_and_thread_safety() -> None:
    import threading

    mgr = SCADATelemetryManager()
    # Start from nominal healthy state
    mgr.record_frame(
        {
            "S5.P_MAIN_UHV_TORR": 1.5e-10,
            "S7.LASER_ENCL_OK": 1.0,
            "S7.O2_ROOM_PCT": 20.9,
            "S7.PH3_LEVEL_PPM": 0.0,
            "S1.V_LANDING_KV": 5.0,
            "S1.V_EXTRACT_KV": 12.0,
            "S6.QUENCH_VOLT_V": 0.0,
            "S7.ESTOP_LOOP_OK": 1.0,
        },
        timestamp_s=1.0,
    )
    assert mgr.build_il_sensor_vectors_from_telemetry() == (0xFF, 0xFF)

    # 1) NaN and +Inf on UHV vacuum MUST fail-safe trip bit 0 (bit0_healthy == False)
    s_nan = mgr.record_sample("S5.P_MAIN_UHV_TORR", float("nan"), timestamp_s=2.0)
    assert s_nan.severity == "INTERLOCK_TRIP"
    ch_a, ch_b = mgr.build_il_sensor_vectors_from_telemetry()
    assert (ch_a & (1 << 0)) == 0
    assert ch_a == ch_b

    mgr.record_sample("S5.P_MAIN_UHV_TORR", 1.5e-10, timestamp_s=3.0)
    assert (mgr.build_il_sensor_vectors_from_telemetry()[0] & (1 << 0)) != 0

    mgr.record_sample("S5.P_MAIN_UHV_TORR", float("inf"), timestamp_s=4.0)
    assert (mgr.build_il_sensor_vectors_from_telemetry()[0] & (1 << 0)) == 0
    mgr.record_sample("S5.P_MAIN_UHV_TORR", 1.5e-10, timestamp_s=5.0)

    # 2) Superseded HI_HI -> HI transition clears HI_HI active flag so ack releases latch cleanly
    mgr.record_sample("S7.PH3_LEVEL_PPM", 0.06, timestamp_s=10.0)
    mgr.record_sample("S7.PH3_LEVEL_PPM", 0.03, timestamp_s=11.0)
    ph3_alarms = {a.limit_breached: a for a in mgr.get_all_alarms() if a.channel_id == "S7.PH3_LEVEL_PPM"}
    assert "HI_HI" in ph3_alarms and "HI" in ph3_alarms
    assert ph3_alarms["HI_HI"].active is False
    assert ph3_alarms["HI_HI"].isa18_state == "UNACK_CLEARED"
    assert ph3_alarms["HI"].active is True
    assert ph3_alarms["HI"].isa18_state == "UNACK_ACTIVE"

    # Acknowledging cleared HI_HI alarm releases its latch to NORMAL
    rec_hihi = mgr.acknowledge_alarm(ph3_alarms["HI_HI"].alarm_id, operator="eng_01", timestamp_s=12.0)
    assert rec_hihi.latched is False
    assert rec_hihi.isa18_state == "NORMAL"

    # 3) Thread safety with RLock and bounded _event_log deque
    assert isinstance(mgr._lock, type(threading.RLock()))
    errs: list[Exception] = []

    def _worker(tid: int) -> None:
        try:
            for k in range(40):
                val = 0.06 if (k % 3 == 0) else (0.03 if (k % 3 == 1) else 0.0)
                mgr.record_sample("S7.PH3_LEVEL_PPM", val, timestamp_s=100.0 + tid * 100 + k)
                _ = mgr.build_il_sensor_vectors_from_telemetry()
                _ = mgr.get_latched_alarms()
        except Exception as exc:
            errs.append(exc)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errs == []
    assert mgr._event_log.maxlen is not None and len(mgr._event_log) <= mgr._event_log.maxlen
