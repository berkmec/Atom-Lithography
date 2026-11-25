// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.2-06)
// ============================================================================
// part_id           : S3.2-06
// parent_bom_id     : S3.2
// subsystem         : S3
// part_name         : EMI kalkanli analog on-uc sasisi ve ultra-dusuk gurultulu lineer PSU
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±0.1%
// computed_mass_kg  : 9.56166
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
n_psu_bays = 2;
rack_u_height = 2;
depth_mm = 420.0;

// Interface / port parameters (mm)

module part_S3_2_06() {
  difference() {
    union() {
      // 19-inch EIA-310 2U front faceplate (482.6 x 86.9 mm, facing -Y)
      translate([0.000, -208.000, 0.000]) cube([482.600, 4.000, 86.900], center=true);
      // Hollow EMI-shielded chassis body
      translate([0.000, 0.350, 0.000]) cube([438.000, 412.500, 85.400], center=true);
    }
    // EIA-310 upper-left rack ear slot
    translate([-232.500, -208.000, 33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 upper-right rack ear slot
    translate([232.500, -208.000, 33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-left rack ear slot
    translate([-232.500, -208.000, -33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-right rack ear slot
    translate([232.500, -208.000, -33.450]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -200.000, 390.100]) rotate([0.000, 0.000, 0.000]) part_S3_2_06();

part_S3_2_06();
