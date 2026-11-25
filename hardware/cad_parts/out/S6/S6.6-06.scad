// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-06)
// ============================================================================
// part_id           : S6.6-06
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : RFSoC cogullamali sayisallastirici / AWG kartlari (AMD ZCU216, 14 kart = 56/4)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : 14-bit ADC/DAC
// computed_mass_kg  : 48.41227
// envelope_mm       : 482.600 x 552.050 x 620.300
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 552.0500;
bbox_z = 620.3000;

// Part-specific parametric dimensions
rack_u = 14;
u_start = 25;
n_zcu216_cards = 14;
n_2u_enclosures = 7;

// Interface / port parameters (mm)

module part_S6_6_06() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -268.000, 0.000]) cube([482.600, 4.000, 620.300], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 535.900, 619.300], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, -198.496]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, 198.496]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, -198.496]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, 198.496]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 1467.950]) rotate([0.000, 0.000, 0.000]) part_S6_6_06();

part_S6_6_06();
