// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.11-04)
// ============================================================================
// part_id           : S6.11-04
// parent_bom_id     : S6.11
// subsystem         : S6
// part_name         : Kriyo-Koaksiyel Demet & Zayiflatici Paketi (96 hat: CuNi/NbTi, 0.86 mm, Exp140 S6.5-04, 4.03 kg)
// material          : CuNi
// temp_stage        : 300 K -> 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : 0.86 mm, <=0.1 dB/m
// computed_mass_kg  : 0.70712
// envelope_mm       : 20.000 x 68.000 x 456.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 20.0000;
bbox_y = 68.0000;
bbox_z = 456.0000;

// Part-specific parametric dimensions
n_lines = 96;
coax_od_mm = 0.86;
mass_kg = 4.03;

// Interface / port parameters (mm)

module part_S6_11_04() {
  union() {
    // 48-line CuNi/NbTi cryo coax & Eccosorb bundle (south48)
    translate([0.000, -24.000, 0.000]) cube([20.000, 20.000, 456.000], center=true);
    // 48-line CuNi/NbTi cryo coax & Eccosorb bundle (north48)
    translate([0.000, 24.000, 0.000]) cube([20.000, 20.000, 456.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-716.000, 0.000, 730.000]) rotate([0.000, 0.000, 0.000]) part_S6_11_04();

part_S6_11_04();
