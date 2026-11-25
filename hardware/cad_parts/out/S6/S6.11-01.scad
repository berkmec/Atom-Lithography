// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.11-01)
// ============================================================================
// part_id           : S6.11-01
// parent_bom_id     : S6.11
// subsystem         : S6
// part_name         : ZU48DR RFSoC Q16.16 BOED-FPGA 2U Raf Sasisi (2x Kart, 32 Direct-RF Zinciri, Exp140 S6.5-01, 11.50 kg)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : 0.050 Hz RMS
// computed_mass_kg  : 11.62594
// envelope_mm       : 482.600 x 532.050 x 88.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 532.0500;
bbox_z = 88.9000;

// Part-specific parametric dimensions
rack_u = 2;
u_start = 22;
rf_chains = 32;
power_w = 87.96;
mass_kg = 11.5;

// Interface / port parameters (mm)

module part_S6_11_01() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -258.000, 0.000]) cube([482.600, 4.000, 88.900], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 515.900, 87.900], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -258.000, -28.448]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -258.000, 28.448]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -258.000, -28.448]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -258.000, 28.448]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 1069.000]) rotate([0.000, 0.000, 0.000]) part_S6_11_01();

part_S6_11_01();
