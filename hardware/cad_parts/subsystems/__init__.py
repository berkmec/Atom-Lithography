"""Subsystem mechanical CAD builder registry (Wave 2B/2C, 164/164 physical BOM parts).

Each subsystem module owns a disjoint subset of ``list_physical_part_ids()`` from
``research/atom_lithography_machine/BOM_DETAILED.csv`` (v7.0) and exports all 6
per-part artifacts (``.stl``, ``.step``, ``.scad``, ``.dxf``, ``.svg``, ``.json``)
under ``hardware/cad_parts/out/<group>/``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import (
    s1_ion_column,
    s2_mems_head,
    s3_ibic_mech,
    s4_stage_metrology,
    s5_optics_mbe,
    s5_uhv_pumps,
    s6_dr_readout_optq,
    s6_magnet_shields,
    s7_racks_safety,
    s9_spares_hpc,
)


@dataclass(frozen=True)
class SubsystemGroupSpec:
    """Descriptor binding a subsystem CAD group to its builder, out dir, and mesh frame."""

    group_id: str
    bom_subsystem: str
    out_subdir: str
    work_package: str
    mesh_frame: str  # "world_mesh_method" | "local_with_world_origin" | "already_world"
    build_fn: Callable[[], dict[str, Any]]
    export_fn: Callable[..., Any]
    expected_part_count: int


SUBSYSTEM_GROUPS: tuple[SubsystemGroupSpec, ...] = (
    SubsystemGroupSpec(
        group_id="S1",
        bom_subsystem="S1",
        out_subdir="S1",
        work_package="WP-M1",
        mesh_frame="already_world",
        build_fn=s1_ion_column.build_s1_parts,
        export_fn=s1_ion_column.export_all,
        expected_part_count=23,
    ),
    SubsystemGroupSpec(
        group_id="S2",
        bom_subsystem="S2",
        out_subdir="S2",
        work_package="WP-M1",
        mesh_frame="already_world",
        build_fn=s2_mems_head.build_s2_parts,
        export_fn=s2_mems_head.export_all,
        expected_part_count=15,
    ),
    SubsystemGroupSpec(
        group_id="S3",
        bom_subsystem="S3",
        out_subdir="S3",
        work_package="WP-M2",
        mesh_frame="world_mesh_method",
        build_fn=s3_ibic_mech.build_s3_parts,
        export_fn=s3_ibic_mech.export_all,
        expected_part_count=14,
    ),
    SubsystemGroupSpec(
        group_id="S4",
        bom_subsystem="S4",
        out_subdir="S4",
        work_package="WP-M2",
        mesh_frame="world_mesh_method",
        build_fn=s4_stage_metrology.build_s4_parts,
        export_fn=s4_stage_metrology.export_all,
        expected_part_count=17,
    ),
    SubsystemGroupSpec(
        group_id="S5",
        bom_subsystem="S5",
        out_subdir="S5",
        work_package="WP-M3",
        mesh_frame="local_with_world_origin",
        build_fn=s5_uhv_pumps.build_s5_parts,
        export_fn=s5_uhv_pumps.export_all,
        expected_part_count=23,
    ),
    SubsystemGroupSpec(
        group_id="S6",
        bom_subsystem="S6",
        out_subdir="S6",
        work_package="WP-M4",
        mesh_frame="world_mesh_method",
        build_fn=s6_magnet_shields.build_s6_parts,
        export_fn=s6_magnet_shields.export_all,
        expected_part_count=40,
    ),
    SubsystemGroupSpec(
        group_id="S7",
        bom_subsystem="S7",
        out_subdir="S7",
        work_package="WP-M5",
        mesh_frame="already_world",
        build_fn=s7_racks_safety.build_s7_parts,
        export_fn=s7_racks_safety.export_all,
        expected_part_count=19,
    ),
    SubsystemGroupSpec(
        group_id="S9_optq",
        bom_subsystem="S9",
        out_subdir="S9_optq",
        work_package="WP-M4",
        mesh_frame="world_mesh_method",
        build_fn=s6_magnet_shields.build_s9_optq_parts,
        export_fn=s6_magnet_shields.export_all,
        expected_part_count=3,
    ),
    SubsystemGroupSpec(
        group_id="S9_spares_hpc",
        bom_subsystem="S9",
        out_subdir="S9_spares_hpc",
        work_package="WP-M5",
        mesh_frame="already_world",
        build_fn=s9_spares_hpc.build_s9_spares_hpc_parts,
        export_fn=s9_spares_hpc.export_all,
        expected_part_count=10,
    ),
)

SUBSYSTEM_GROUP_MAP: dict[str, SubsystemGroupSpec] = {
    spec.group_id: spec for spec in SUBSYSTEM_GROUPS
}


def build_all_subsystem_parts() -> dict[str, dict[str, Any]]:
    """Build in-memory part registries for all 9 subsystem groups (164 physical parts)."""
    return {spec.group_id: spec.build_fn() for spec in SUBSYSTEM_GROUPS}


__all__ = [
    "SubsystemGroupSpec",
    "SUBSYSTEM_GROUPS",
    "SUBSYSTEM_GROUP_MAP",
    "build_all_subsystem_parts",
    "s1_ion_column",
    "s2_mems_head",
    "s3_ibic_mech",
    "s4_stage_metrology",
    "s5_uhv_pumps",
    "s5_optics_mbe",
    "s6_magnet_shields",
    "s6_dr_readout_optq",
    "s7_racks_safety",
    "s9_spares_hpc",
]
