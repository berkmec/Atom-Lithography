// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.1-03)
// ============================================================================
// part_id           : S4.1-03
// parent_bom_id     : S4.1
// subsystem         : S4
// part_name         : Yapisal celik alt-sase ve titresim sonumlu terazi ayaklari
// material          : Steel
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : ±0.5 mm
// computed_mass_kg  : 200.03671
// envelope_mm       : 932.200 x 720.000 x 157.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 932.2000;
bbox_y = 720.0000;
bbox_z = 157.0000;

// Part-specific parametric dimensions
frame_x_mm = 920.0;
frame_y_mm = 720.0;
bay_x_mm = 640.0;
bay_y_mm = 480.0;
load_capacity_kg = 1000;
min_f1_hz = 80.0;

// Interface / port parameters (mm)

module part_S4_1_03() {
  difference() {
    union() {
      // Sand-filled welded 140x116 mm RHS structural steel sub-frame
      translate([0.000, 0.000, 20.500]) cube([920.000, 720.000, 116.000], center=true);
      // M24 vibration-damped leveling soleplate #1
      translate([-380.000, -280.000, -58.100]) cylinder(d=92.000, h=40.800, center=true);
      // M24 vibration-damped leveling soleplate #2
      translate([380.000, -280.000, -58.100]) cylinder(d=92.000, h=40.800, center=true);
      // M24 vibration-damped leveling soleplate #3
      translate([380.000, 280.000, -58.100]) cylinder(d=92.000, h=40.800, center=true);
      // M24 vibration-damped leveling soleplate #4
      translate([-380.000, 280.000, -58.100]) cylinder(d=92.000, h=40.800, center=true);
    }
    // Open 640x480 mm central bay clearing R=210 mm DR OVC bore
    translate([0.000, 0.000, 20.500]) {
      hull() {
        translate([-80.000, 0, 0]) cylinder(d=480.000, h=122.000, center=true);
        translate([80.000, 0, 0]) cylinder(d=480.000, h=122.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -581.500]) rotate([0.000, 0.000, 0.000]) part_S4_1_03();

part_S4_1_03();
