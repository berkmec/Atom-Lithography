// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.3-04)
// ============================================================================
// part_id           : S4.3-04
// parent_bom_id     : S4.3
// subsystem         : S4
// part_name         : 6-kanalli dusuk gurultulu piezo servo denetleyici ve HV surucu
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.1 nm
// computed_mass_kg  : 10.41037
// envelope_mm       : 482.600 x 463.000 x 86.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 463.0000;
bbox_z = 86.9000;

// Part-specific parametric dimensions
rack_u_height = 2;
n_piezo_channels = 6;
dac_bits = 24;
depth_mm = 420.0;

// Interface / port parameters (mm)

module part_S4_3_04() {
  difference() {
    union() {
      // 19-inch EIA-310 2U front bezel (facing -Y)
      translate([0.000, -208.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Hollow EMI rack body
      translate([0.000, 0.350, 0.000]) cube([438.000, 412.500, 85.400], center=true);
    }
    // EIA-310 upper-left ear slot
    translate([-232.500, -208.000, 33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 upper-right ear slot
    translate([232.500, -208.000, 33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-left ear slot
    translate([-232.500, -208.000, -33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-right ear slot
    translate([232.500, -208.000, -33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -200.000, 256.750]) rotate([0.000, 0.000, 0.000]) part_S4_3_04();

part_S4_3_04();
