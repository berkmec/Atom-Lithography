// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.3-04)
// ============================================================================
// part_id           : S5.3-04
// parent_bom_id     : S5.3
// subsystem         : S5
// part_name         : Su sogutmali koruma surgu ve tavlama isi kalkani
// material          : OFHC Cu
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 mm
// computed_mass_kg  : 1.20746
// envelope_mm       : 208.000 x 69.500 x 69.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 208.0000;
bbox_y = 69.5000;
bbox_z = 69.5000;

// Part-specific parametric dimensions
blade_l = 42.0;
blade_w = 26.0;
stroke_mm = 175.0;
bellows_conv = 16;

// Interface / port parameters (mm)
port_chamber_cf40_mate_od = 69.500;
port_chamber_cf40_mate_bore = 38.000;
port_chamber_cf40_mate_pcd = 58.700;
port_chamber_cf40_mate_bolts = 6;

module part_S5_3_04() {
  union() {
    // Chamber-mating CF40 flange (212 deg, Z=510 mm)
    translate([6.350, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=38.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // Retracted shutter blade parking spool
    translate([38.300, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=49.000, h=51.000, center=true);
        cylinder(d=40.000, h=53.000, center=true);
      }
    }
    // Water-cooled OFHC Cu + Mo S2-head thermal shutter blade
    translate([38.000, 0.000, 0.000]) cube([42.000, 26.000, 3.000], center=true);
    // 16-conv UHV linear bellows
    translate([108.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=37.000, h=62.000, center=true);
        cylinder(d=22.000, h=64.000, center=true);
      }
    }
    // Pneumatic linear actuator
    translate([165.500, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=36.000, h=52.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([506.954, 128.915, 460.000]) rotate([0.000, 0.000, 56.000]) part_S5_3_04();

part_S5_3_04();
