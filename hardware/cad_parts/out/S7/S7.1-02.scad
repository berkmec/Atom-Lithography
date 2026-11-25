// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.1-02)
// ============================================================================
// part_id           : S7.1-02
// parent_bom_id     : S7.1
// subsystem         : S7
// part_name         : Yuksek hizli NVMe RAID sertifika ve spektroskopi veri sunucusu
// material          : Steel
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : 99.99% yedekli
// computed_mass_kg  : 21.00000
// envelope_mm       : 482.600 x 698.400 x 86.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 698.4000;
bbox_z = 86.9000;

// Part-specific parametric dimensions
u_start = 8;
u_count = 2;
nvme_bays = 12;
depth_mm = 660.0;

// Interface / port parameters (mm)

module part_S7_1_02() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -328.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 655.900, 84.900], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -328.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -328.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -328.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -328.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -108.000, 445.600]) rotate([0.000, 0.000, 0.000]) part_S7_1_02();

part_S7_1_02();
