// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.1-01)
// ============================================================================
// part_id           : S7.1-01
// parent_bom_id     : S7.1
// subsystem         : S7
// part_name         : Ana kontrol ve GPU GRAPE sentez is istasyonlari (2x Lambda Vector 2xRTX4500Ada)
// material          : Steel
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : 24/7 calisma
// computed_mass_kg  : 38.00000
// envelope_mm       : 482.600 x 718.400 x 175.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 718.4000;
bbox_z = 175.8000;

// Part-specific parametric dimensions
qty_nodes = 2;
u_per_node = 2;
u_start = 4;
depth_mm = 680.0;

// Interface / port parameters (mm)

module part_S7_1_01() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -338.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 675.900, 84.900], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -338.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -338.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -338.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -338.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -98.000, 312.250]) rotate([0.000, 0.000, 0.000]) part_S7_1_01();

part_S7_1_01();
