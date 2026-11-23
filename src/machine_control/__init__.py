"""Atom Lithography Machine control, BOED-FPGA DSP & CellISA v3.5 stack.

Implements the write -> detect -> adaptive-BOED-measure -> select -> calibrate
factory loop (Exp57-140), bit-exact Q16.16 BOED-FPGA DSP engine (Exp140), plus
the CellISA v3.5 single-cell, multi-cell (M4) cavity-bus, echoed-CZ, multiplexed
readout, and syndrome-cycle compiler with Exp126 32D provenance bridge.
No physical hardware exists; all device parameters are model-anchored ({Model}).
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
]
__version__ = "3.5.0"
