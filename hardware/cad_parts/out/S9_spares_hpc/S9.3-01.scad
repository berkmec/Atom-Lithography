// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.3-01)
// ============================================================================
// part_id           : S9.3-01
// parent_bom_id     : S9.3
// subsystem         : S9
// part_name         : Yedek MEMS apertur ve blanker plaka seti (2 eslesik takim)
// material          : Si
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±50 nm CD
// computed_mass_kg  : 6.80000
// envelope_mm       : 368.800 x 296.400 x 140.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 368.8000;
bbox_y = 296.4000;
bbox_z = 140.0000;

// Part-specific parametric dimensions
qty_sets = 2;
case_dx_mm = 340.0;
case_dy_mm = 280.0;
case_dz_mm = 140.0;

// Interface / port parameters (mm)

module part_S9_3_01() {
  difference() {
    union() {
      // Cleanroom ESD storage case outer envelope
      cube([340.000, 280.000, 140.000], center=true);
    }
    // Internal padded kit tray cavity
    hull() {
      translate([-30.000, 0, 0]) cylinder(d=264.000, h=109.400, center=true);
      translate([30.000, 0, 0]) cylinder(d=264.000, h=109.400, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-160.000, -1520.000, 70.000]) rotate([0.000, 0.000, 0.000]) part_S9_3_01();

part_S9_3_01();
