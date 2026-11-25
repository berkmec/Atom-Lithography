// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.3-03)
// ============================================================================
// part_id           : S9.3-03
// parent_bom_id     : S9.3
// subsystem         : S9
// part_name         : Pulse-tube adsorber, scroll pompa tip-seal ve kriyo conta servis kiti
// material          : PTFE
// temp_stage        : 300 K / 4 K
// vacuum_grade      : Kriyo/Vakum
// tolerance         : ISO 2768-mK
// computed_mass_kg  : 18.00000
// envelope_mm       : 488.800 x 356.400 x 260.000
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
bbox_z = 260.0000;

// Part-specific parametric dimensions
chest_dx_mm = 460.0;
chest_dy_mm = 340.0;
chest_dz_mm = 260.0;

// Interface / port parameters (mm)

module part_S9_3_03() {
  difference() {
    union() {
      // Cleanroom ESD storage case outer envelope
      cube([460.000, 340.000, 260.000], center=true);
    }
    // Internal padded kit tray cavity
    hull() {
      translate([-60.000, 0, 0]) cylinder(d=324.000, h=229.400, center=true);
      translate([60.000, 0, 0]) cylinder(d=324.000, h=229.400, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([780.000, -1520.000, 130.000]) rotate([0.000, 0.000, 0.000]) part_S9_3_03();

part_S9_3_03();
