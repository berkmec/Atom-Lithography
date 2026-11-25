// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.4-02)
// ============================================================================
// part_id           : S7.4-02
// parent_bom_id     : S7.4
// subsystem         : S7
// part_name         : White Rabbit / sub-ns donanim tetikleme (trigger) fan-out modulu
// material          : Steel
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : <200 ps
// computed_mass_kg  : 5.20000
// envelope_mm       : 482.600 x 403.300 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 403.3000;
bbox_z = 42.4500;

// Part-specific parametric dimensions
u_start = 37;
u_count = 1;
sfp_ports = 18;
depth_mm = 380.0;

// Interface / port parameters (mm)

module part_S7_4_02() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -188.000, 0.000]) cube([482.600, 4.000, 42.450], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 375.900, 40.450], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -188.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -188.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -188.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -188.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -248.000, 1712.425]) rotate([0.000, 0.000, 0.000]) part_S7_4_02();

part_S7_4_02();
