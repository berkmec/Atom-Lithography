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
// computed_mass_kg  : 0.10246
// envelope_mm       : 149.000 x 275.000 x 156.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 149.0000;
bbox_y = 275.0000;
bbox_z = 156.0000;

// Part-specific parametric dimensions
n_heads = 3;
relay_radius_mm = 128.0;
z_entry_mm = -133.0;
z_meas_mm = -9.0;
z_ref_mm = 14.3;

// Interface / port parameters (mm)

module part_S4_4_02() {
  union() {
    // Split-gap differential PBS head X-axis (Z_canon=[485, 517.5])
    translate([133.500, 0.000, 134.250]) cube([8.000, 14.000, 32.500], center=true);
    // Periscope optical relay mast X-axis
    translate([128.000, 9.500, 56.150]) cube([4.500, 4.000, 123.300], center=true);
    // Split-gap differential PBS head Y-axis (Z_canon=[485, 517.5])
    translate([0.000, 133.500, 134.250]) rotate([0.000, 0.000, 90.000]) cube([8.000, 14.000, 32.500], center=true);
    // Periscope optical relay mast Y-axis
    translate([-9.500, 128.000, 56.150]) rotate([0.000, 0.000, 90.000]) cube([4.500, 4.000, 123.300], center=true);
    // Split-gap differential PBS head Z-axis (Z_canon=[485, 517.5])
    translate([-0.000, -133.500, 134.250]) rotate([0.000, 0.000, 270.000]) cube([8.000, 14.000, 32.500], center=true);
    // Periscope optical relay mast Z-axis
    translate([9.500, -128.000, 56.150]) rotate([0.000, 0.000, 270.000]) cube([4.500, 4.000, 123.300], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -133.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_02();

part_S4_4_02();
