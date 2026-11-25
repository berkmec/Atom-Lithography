// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.9-04)
// ============================================================================
// part_id           : S6.9-04
// parent_bom_id     : S6.9
// subsystem         : S6
// part_name         : PT420 doner-vana faz kodlayicisi ve n=1..15 (1.4-21 Hz) 25 dB harmonik feedforward DSP (Exp133)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.1 deg faz
// computed_mass_kg  : 3.83862
// envelope_mm       : 482.600 x 392.050 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 392.0500;
bbox_z = 42.4500;

// Part-specific parametric dimensions
rack_u = 1;
u_start = 6;
harmonics_n = 15;
ff_suppression_db = 25.0;

// Interface / port parameters (mm)

module part_S6_9_04() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -188.000, 0.000]) cube([482.600, 4.000, 42.450], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 375.900, 41.450], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -188.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -188.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -188.000, -13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -188.000, 13.584]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 334.475]) rotate([0.000, 0.000, 0.000]) part_S6_9_04();

part_S6_9_04();
