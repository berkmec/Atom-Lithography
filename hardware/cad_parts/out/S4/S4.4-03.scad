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
// computed_mass_kg  : 0.03833
// envelope_mm       : 78.000 x 130.000 x 41.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 78.0000;
bbox_y = 130.0000;
bbox_z = 41.0000;

// Part-specific parametric dimensions
n_mirrors = 3;
bar_len_mm = 26.0;
bar_thk_mm = 5.5;
bar_h_mm = 10.0;
mirror_r_face_mm = 65.0;
mirror_z_nat_mm = -9.0;

// Interface / port parameters (mm)

module part_S4_4_03() {
  union() {
    // Split-gap Zerodur lambda/20 bar mirror X-axis (Z_canon=491 mm)
    translate([62.250, 0.000, 32.000]) cube([5.500, 26.000, 10.000], center=true);
    // Split-gap Zerodur lambda/20 bar mirror Y-axis (Z_canon=491 mm)
    translate([0.000, 62.250, 32.000]) rotate([0.000, 0.000, 90.000]) cube([5.500, 26.000, 10.000], center=true);
    // Split-gap Zerodur lambda/20 bar mirror Z-axis (Z_canon=491 mm)
    translate([-0.000, -62.250, 32.000]) rotate([0.000, 0.000, 270.000]) cube([5.500, 26.000, 10.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -41.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_03();

part_S4_4_03();
