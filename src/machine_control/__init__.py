"""Atom Lithography Machine control, BOED spectroscopy & CellISA v3.0 stack.

Implements the write -> detect -> adaptive-BOED-measure -> select -> calibrate
factory loop (Exp57-132) plus the CellISA v3.0 single-cell and multi-cell (M4)
cavity-bus compiler, heterogeneous wafer router, and Exp126 32D provenance bridge.
No physical hardware exists; all device parameters are model-anchored ({Model}).
"""
__all__ = [
    "config",
    "writer",
    "spectroscopy",
    "adaptive_spectroscopy",
    "selector",
    "pulse_engine",
    "calibrator",
    "programmer",
    "factory",
    "sim",
]
__version__ = "3.0.0"
