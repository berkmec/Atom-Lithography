// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.4-01)
// ============================================================================
// part_id           : S6.4-01
// parent_bom_id     : S6.4
// subsystem         : S6
// part_name         : Mikrodalga ESR vektor sinyal ureticileri (10-45 GHz, dusuk faz gurultusu)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : <-120 dBc/Hz
// computed_mass_kg  : 19.89746
// envelope_mm       : 482.600 x 512.050 x 175.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 512.0500;
bbox_z = 175.8000;

// Part-specific parametric dimensions
rack_u = 4;
qty_units = 4;
f_max_ghz = 45.0;

// Interface / port parameters (mm)

module part_S6_4_01() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -248.000, 0.000]) cube([482.600, 4.000, 175.800], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 495.900, 174.800], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -248.000, -56.256]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -248.000, 56.256]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -248.000, -56.256]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -248.000, 56.256]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -248.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -248.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 712.300]) rotate([0.000, 0.000, 0.000]) part_S6_4_01();

part_S6_4_01();
