// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.2-01)
// ============================================================================
// part_id           : S7.2-01
// parent_bom_id     : S7.2
// subsystem         : S7
// part_name         : Cok-kanalli keyfi dalga formu uretici (AWG) kartlari (GRAPE XY/ENDOR)
// material          : Rogers
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : 16-bit, <10 ps
// computed_mass_kg  : 3.20000
// envelope_mm       : 78.460 x 393.200 x 133.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 78.4600;
bbox_y = 393.2000;
bbox_z = 133.8000;

// Part-specific parametric dimensions
n_cards = 4;
slot_pitch_mm = 20.32;
card_depth_mm = 380.0;

// Interface / port parameters (mm)

module part_S7_2_01() {
  union() {
    // PXIe slot 2 card module
    translate([-30.480, 0.000, 0.000]) cube([17.500, 384.000, 133.800], center=true);
    // PXIe slot 3 card module
    translate([-10.160, 0.000, 0.000]) cube([17.500, 384.000, 133.800], center=true);
    // PXIe slot 4 card module
    translate([10.160, 0.000, 0.000]) cube([17.500, 384.000, 133.800], center=true);
    // PXIe slot 5 card module
    translate([30.480, 0.000, 0.000]) cube([17.500, 384.000, 133.800], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1378.400, -242.400, 578.950]) rotate([0.000, 0.000, 0.000]) part_S7_2_01();

part_S7_2_01();
