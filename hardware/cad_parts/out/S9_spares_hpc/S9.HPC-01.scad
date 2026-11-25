// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.HPC-01)
// ============================================================================
// part_id           : S9.HPC-01
// parent_bom_id     : S9.HPC
// subsystem         : S9
// part_name         : 2U Cift-Hizlandiricili QEC Dekoder Dugumu (2x H100/Alveo-U280 Sinifi + Cift-100G ConnectX-7 RoCEv2 NIC, Exp143, 56.00 kg)
// material          : Steel
// temp_stage        : 300 K (HPC rafi)
// vacuum_grade      : Atmosfer
// tolerance         : <6.7 us d=37 / <2.6 us qLDPC
// computed_mass_kg  : 56.00000
// envelope_mm       : 482.600 x 818.400 x 177.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 818.4000;
bbox_z = 177.9000;

// Part-specific parametric dimensions
qty_nodes = 2;
u_per_node = 2;
depth_mm = 780.0;
power_W = 2100;

// Interface / port parameters (mm)

module part_S9_HPC_01() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -388.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 775.900, 84.900], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -388.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -388.000, 27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -388.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -388.000, -27.808]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2750.000, -700.000, 174.250]) rotate([0.000, 0.000, 0.000]) part_S9_HPC_01();

part_S9_HPC_01();
