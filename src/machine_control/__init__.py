"""Atom Lithography Machine control, BOED-FPGA DSP, Cloud-QPU & CellISA v4.0 stack.

Implements the write -> detect -> adaptive-BOED-measure -> select -> calibrate
factory loop (Exp57-145), bit-exact Q16.16 BOED-FPGA DSP engine (Exp140),
CellISA v4.0 (20 opcodes: single-cell, multi-cell M4 cavity-bus, echoed-CZ,
multiplexed readout, syndrome-cycle, QRAM_SWAP, QLDPC_ROUND, AUTO_RECAL),
zero-dependency native-ISA OpenQASM 3.0 IBM Quantum Platform 2026 REST bridge,
and autonomous closed-loop fault recalibration (Exp145).
"""
__all__ = [
    "config",
    "writer",
    "spectroscopy",
    "adaptive_spectroscopy",
    "fpga_boed_dsp",
    "selector",
    "pulse_engine",
    "calibrator",
    "programmer",
    "factory",
    "sim",
    "cloud_qpu_bridge",
    "auto_recal",
    "scada_telemetry",
]
__version__ = "4.0.0"
