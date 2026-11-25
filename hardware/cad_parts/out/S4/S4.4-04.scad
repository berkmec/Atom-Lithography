// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.4-04)
// ============================================================================
// part_id           : S4.4-04
// parent_bom_id     : S4.4
// subsystem         : S4
// part_name         : 632.8 nm AR-kapli CF40 optik vakum pencereleri ve fiber lansmanlar
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : lambda/10
// computed_mass_kg  : 1.45627
// envelope_mm       : 317.900 x 561.400 x 69.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 317.9000;
bbox_y = 561.4000;
bbox_z = 69.5000;

// Part-specific parametric dimensions
n_viewports = 3;
cf40_od_mm = 69.5;
cf40_pcd_mm = 58.7;
cf40_bolts = 6;
clear_aperture_mm = 28.0;

// Interface / port parameters (mm)
port_cf40_ar_viewport_X_od = 69.500;
port_cf40_ar_viewport_X_bore = 28.000;
port_cf40_ar_viewport_X_pcd = 58.700;
port_cf40_ar_viewport_X_bolts = 6;
port_cf40_ar_viewport_Y_od = 69.500;
port_cf40_ar_viewport_Y_bore = 28.000;
port_cf40_ar_viewport_Y_pcd = 58.700;
port_cf40_ar_viewport_Y_bolts = 6;
port_cf40_ar_viewport_Z_od = 69.500;
port_cf40_ar_viewport_Z_bore = 28.000;
port_cf40_ar_viewport_Z_pcd = 58.700;
port_cf40_ar_viewport_Z_bolts = 6;

module part_S4_4_04() {
  union() {
    // ISO 3669 CF40 632.8 nm AR viewport (X-axis)
    translate([246.850, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=28.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // External 45-deg beam bender & fiber launcher (X-axis)
    translate([267.700, 0.000, 0.000]) cube([26.000, 26.000, 26.000], center=true);
    // ISO 3669 CF40 632.8 nm AR viewport (Y-axis)
    translate([0.000, 246.850, 0.000]) rotate([0.000, -90.000, 90.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=28.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // External 45-deg beam bender & fiber launcher (Y-axis)
    translate([0.000, 267.700, 0.000]) rotate([0.000, 0.000, 90.000]) cube([26.000, 26.000, 26.000], center=true);
    // ISO 3669 CF40 632.8 nm AR viewport (Z-axis)
    translate([-0.000, -246.850, 0.000]) rotate([0.000, -90.000, 270.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=28.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // External 45-deg beam bender & fiber launcher (Z-axis)
    translate([-0.000, -267.700, 0.000]) rotate([0.000, 0.000, 270.000]) cube([26.000, 26.000, 26.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -133.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_04();

part_S4_4_04();
