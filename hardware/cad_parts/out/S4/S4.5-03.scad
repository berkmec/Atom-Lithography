// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.5-03)
// ============================================================================
// part_id           : S4.5-03
// parent_bom_id     : S4.5
// subsystem         : S4
// part_name         : Atis-ani sapma telafi arayuzu (interferometre -> demet saptirici DSP)
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.1 nm
// computed_mass_kg  : 2.93539
// envelope_mm       : 482.600 x 373.000 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 373.0000;
bbox_z = 42.4500;

// Part-specific parametric dimensions
rack_u_height = 1;
depth_mm = 340.0;
max_latency_us = 5.0;

// Interface / port parameters (mm)

module part_S4_5_03() {
  difference() {
    union() {
      // 19-inch EIA-310 1U front bezel (facing -Y)
      translate([0.000, -168.000, 0.000]) cube([482.600, 4.000, 42.450], center=true);
      // Hollow EMI rack body
      translate([0.000, 0.350, 0.000]) cube([438.000, 332.500, 40.950], center=true);
    }
    // EIA-310 upper-left ear slot
    translate([-232.500, -168.000, 11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 upper-right ear slot
    translate([232.500, -168.000, 11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-left ear slot
    translate([-232.500, -168.000, -11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-right ear slot
    translate([232.500, -168.000, -11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -240.000, 323.425]) rotate([0.000, 0.000, 0.000]) part_S4_5_03();

part_S4_5_03();
