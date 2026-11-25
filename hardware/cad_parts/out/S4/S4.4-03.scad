// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.4-03)
// ============================================================================
// part_id           : S4.4-03
// parent_bom_id     : S4.4
// subsystem         : S4
// part_name         : Zerodur/ULE yuksek duzlemlikli yonga-tasiyici bar aynalari
// material          : Zerodur
// temp_stage        : 4 K - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : lambda/20
// computed_mass_kg  : 0.04275
// envelope_mm       : 80.600 x 110.200 x 16.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 80.6000;
bbox_y = 110.2000;
bbox_z = 16.0000;

// Part-specific parametric dimensions
n_mirrors = 3;
bar_len_mm = 52.0;
bar_thk_mm = 6.0;
bar_h_mm = 16.0;

// Interface / port parameters (mm)

module part_S4_4_03() {
  union() {
    // Zerodur lambda/20 bar mirror X-axis
    translate([49.500, 0.000, 0.000]) cube([6.000, 52.000, 16.000], center=true);
    // Zerodur lambda/20 bar mirror Y-axis
    translate([0.000, 49.500, 0.000]) cube([52.000, 6.000, 16.000], center=true);
    // Zerodur lambda/20 fold bar mirror Z-axis
    translate([0.000, -50.000, 0.000]) cube([52.000, 7.000, 16.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -41.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_03();

part_S4_4_03();
