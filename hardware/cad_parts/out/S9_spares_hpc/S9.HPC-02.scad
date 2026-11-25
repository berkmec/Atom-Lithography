// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.HPC-02)
// ============================================================================
// part_id           : S9.HPC-02
// parent_bom_id     : S9.HPC
// subsystem         : S9
// part_name         : 1U Ultra-Dusuk-Gecikmeli Cut-Through 100 GbE RoCEv2 Optik Kopru + 4x QSFP28-100G-SR4 + 20m OM4 MPO-12 (Exp143, 4.20 kg)
// material          : Al 6061
// temp_stage        : 300 K (HPC rafi)
// vacuum_grade      : Atmosfer
// tolerance         : tau_ingest <= 0.80 us
// computed_mass_kg  : 4.20000
// envelope_mm       : 482.600 x 420.400 x 42.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 420.4000;
bbox_z = 42.5000;

// Part-specific parametric dimensions
u_count = 1;
depth_mm = 380.0;
qsfp28_ports = 4;
ingest_us = 0.777;

// Interface / port parameters (mm)

module part_S9_HPC_02() {
  difference() {
    union() {
      // 19-inch EIA-310 front faceplate
      translate([0.000, -188.000, 0.000]) cube([482.600, 4.000, 42.500], center=true);
      // Main rack chassis enclosure
      translate([0.000, 2.000, 0.000]) cube([440.000, 375.900, 40.500], center=true);
    }
    // EIA-310 rack ear mounting slot (top-left)
    translate([-232.550, -188.000, 13.600]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (top-right)
    translate([232.550, -188.000, 13.600]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-left)
    translate([-232.550, -188.000, -13.600]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
    // EIA-310 rack ear mounting slot (bottom-right)
    translate([232.550, -188.000, -13.600]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.200, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2750.000, -900.000, 290.000]) rotate([0.000, 0.000, 0.000]) part_S9_HPC_02();

part_S9_HPC_02();
