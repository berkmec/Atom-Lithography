// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.3-02)
// ============================================================================
// part_id           : S3.3-02
// parent_bom_id     : S3.3
// subsystem         : S3
// part_name         : Yuksek hizli LVDS / optik galvanik izole blanker geri-besleme hatti
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : Jitter <1 ns
// computed_mass_kg  : 2.44621
// envelope_mm       : 482.600 x 333.000 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 333.0000;
bbox_z = 42.4500;

// Part-specific parametric dimensions
n_optical_ports = 16;
rack_u_height = 1;
depth_mm = 300.0;

// Interface / port parameters (mm)

module part_S3_3_02() {
  difference() {
    union() {
      // 19-inch EIA-310 1U front faceplate (482.6 x 42.5 mm, facing -Y)
      translate([0.000, -148.000, 0.000]) cube([482.600, 4.000, 42.450], center=true);
      // Hollow EMI-shielded chassis body
      translate([0.000, 0.350, 0.000]) cube([438.000, 292.500, 40.950], center=true);
    }
    // EIA-310 upper-left rack ear slot
    translate([-232.500, -148.000, 11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 upper-right rack ear slot
    translate([232.500, -148.000, 11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-left rack ear slot
    translate([-232.500, -148.000, -11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
    // EIA-310 lower-right rack ear slot
    translate([232.500, -148.000, -11.225]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
        translate([1.800, 0, 0]) cylinder(d=6.400, h=8.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -260.000, 723.475]) rotate([0.000, 0.000, 0.000]) part_S3_3_02();

part_S3_3_02();
