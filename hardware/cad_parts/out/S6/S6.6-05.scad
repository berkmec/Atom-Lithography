// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-05)
// ============================================================================
// part_id           : S6.6-05
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : Oda-sicakligi dusuk gurultulu RF yukseltici (Mini-Circuits ZX60 sinifi, 56x)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.5 dB
// computed_mass_kg  : 12.66906
// envelope_mm       : 482.600 x 432.050 x 131.350
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 432.0500;
bbox_z = 131.3500;

// Part-specific parametric dimensions
rack_u = 3;
u_start = 19;
n_lna = 56;
gain_db = 20.0;

// Interface / port parameters (mm)

module part_S6_6_05() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -208.000, 0.000]) cube([482.600, 4.000, 131.350], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 415.900, 130.350], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -208.000, -42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -208.000, 42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -208.000, -42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -208.000, 42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -208.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -208.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 956.775]) rotate([0.000, 0.000, 0.000]) part_S6_6_05();

part_S6_6_05();
