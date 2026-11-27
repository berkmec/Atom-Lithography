// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.5-04)
// ============================================================================
// part_id           : S5.5-04
// parent_bom_id     : S5.5
// subsystem         : S5
// part_name         : Donanimsal lazer deklansor kilidi (MXC <1 K + UHV vana emniyet arayuzu, Exp130)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer / UHV arayuz
// tolerance         : <5 ms kesme
// computed_mass_kg  : 0.77911
// envelope_mm       : 124.600 x 25.000 x 90.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 124.6000;
bbox_y = 25.0000;
bbox_z = 90.2000;

// Part-specific parametric dimensions
body_xy = 74.0;
body_t = 20.0;
aperture_d = 46.0;
close_time_ms = 3.2;

// Interface / port parameters (mm)
port_viewport_side_ap_bore = 46.000;
port_laser_side_ap_bore = 46.000;

module part_S5_5_04() {
  difference() {
    union() {
      // 316LN fail-safe shutter housing (74x20x74 mm)
      cube([74.000, 20.000, 74.000], center=true);
      // Redundant fail-safe solenoid coil Ch-A
      translate([-49.800, 0.000, 0.000]) cylinder(d=25.000, h=48.000, center=true);
      // Redundant fail-safe solenoid coil Ch-B
      translate([49.800, 0.000, 0.000]) cylinder(d=25.000, h=48.000, center=true);
      // MXC<1 K & SIL-3 PLC interlock connector
      translate([0.000, 0.000, -45.200]) cube([36.000, 18.000, 16.000], center=true);
    }
    // Dia 46 mm clear 808 nm beam aperture
    rotate([90.000, 0.000, 0.000]) cylinder(d=46.000, h=24.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 175.557, 627.549]) rotate([36.000, 0.000, 0.000]) part_S5_5_04();

part_S5_5_04();
