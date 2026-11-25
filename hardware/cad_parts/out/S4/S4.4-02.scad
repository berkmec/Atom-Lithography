// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.4-02)
// ============================================================================
// part_id           : S4.4-02
// parent_bom_id     : S4.4
// subsystem         : S4
// part_name         : UHV diferansiyel duzlem-ayna optik interferometre kafalari (X, Y, Z)
// material          : Invar-36
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.1 nm
// computed_mass_kg  : 0.05230
// envelope_mm       : 109.400 x 204.800 x 15.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 109.4000;
bbox_y = 204.8000;
bbox_z = 15.0000;

// Part-specific parametric dimensions
n_heads = 3;
mount_radius_mm = 93.0;
z_axis_mm = -133.0;

// Interface / port parameters (mm)

module part_S4_4_02() {
  union() {
    // UHV differential interferometer head X-axis
    translate([93.000, 0.000, 0.000]) cube([14.000, 14.000, 15.000], center=true);
    // UHV differential interferometer head Y-axis
    translate([0.000, 93.000, 0.000]) rotate([0.000, 0.000, 90.000]) cube([14.000, 14.000, 15.000], center=true);
    // UHV differential interferometer head Z-axis
    translate([-0.000, -93.000, 0.000]) rotate([0.000, 0.000, 270.000]) cube([14.000, 14.000, 15.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -133.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_02();

part_S4_4_02();
