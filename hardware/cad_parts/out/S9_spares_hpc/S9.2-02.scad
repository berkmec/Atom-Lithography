// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.2-02)
// ============================================================================
// part_id           : S9.2-02
// parent_bom_id     : S9.2
// subsystem         : S9
// part_name         : Yedek duoplasmatron katot/filaman, TSP kartus ve CF bakir conta kiti
// material          : OFHC Cu
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ISO 2768-mK
// computed_mass_kg  : 14.50000
// envelope_mm       : 488.800 x 356.400 x 240.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 488.8000;
bbox_y = 356.4000;
bbox_z = 240.0000;

// Part-specific parametric dimensions
chest_dx_mm = 460.0;
chest_dy_mm = 340.0;
chest_dz_mm = 240.0;

// Interface / port parameters (mm)

module part_S9_2_02() {
  difference() {
    union() {
      // Cleanroom ESD storage case outer envelope
      cube([460.000, 340.000, 240.000], center=true);
    }
    // Internal padded kit tray cavity
    hull() {
      translate([-60.000, 0, 0]) cylinder(d=324.000, h=209.400, center=true);
      translate([60.000, 0, 0]) cylinder(d=324.000, h=209.400, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-620.000, -1520.000, 120.000]) rotate([0.000, 0.000, 0.000]) part_S9_2_02();

part_S9_2_02();
