// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.4-01)
// ============================================================================
// part_id           : S7.4-01
// parent_bom_id     : S7.4
// subsystem         : S7
// part_name         : 10 MHz Rubidyum atomik saat referansi ve dusuk-jitter saat dagiticisi
// material          : Steel
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±5e-11
// computed_mass_kg  : 11.50000
// envelope_mm       : 482.600 x 473.300 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 473.3000;
bbox_z = 42.4500;

// Part-specific parametric dimensions
u_start = 36;
u_count = 1;
bnc_outputs = 16;
depth_mm = 450.0;

// Interface / port parameters (mm)

module part_S7_4_01() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -223.000, 0.000]) cube([482.600, 4.000, 42.450], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 445.900, 40.450], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -223.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -223.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -223.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -223.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -213.000, 1667.975]) rotate([0.000, 0.000, 0.000]) part_S7_4_01();

part_S7_4_01();
