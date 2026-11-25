// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.3-02)
// ============================================================================
// part_id           : S9.3-02
// parent_bom_id     : S9.3
// subsystem         : S9
// part_name         : Yedek 4 K kriyo-LNA ve izolator saha servis kiti (4 zincir)
// material          : OFHC Cu
// temp_stage        : 4 K / 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : P_DC <= 2.8 mW
// computed_mass_kg  : 9.20000
// envelope_mm       : 448.800 x 336.400 x 180.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 448.8000;
bbox_y = 336.4000;
bbox_z = 180.0000;

// Part-specific parametric dimensions
qty_chains = 4;
case_dx_mm = 420.0;
case_dy_mm = 320.0;
case_dz_mm = 180.0;

// Interface / port parameters (mm)

module part_S9_3_02() {
  difference() {
    union() {
      // Cleanroom ESD storage case outer envelope
      cube([420.000, 320.000, 180.000], center=true);
    }
    // Internal padded kit tray cavity
    hull() {
      translate([-50.000, 0, 0]) cylinder(d=304.000, h=149.400, center=true);
      translate([50.000, 0, 0]) cylinder(d=304.000, h=149.400, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([280.000, -1520.000, 90.000]) rotate([0.000, 0.000, 0.000]) part_S9_3_02();

part_S9_3_02();
