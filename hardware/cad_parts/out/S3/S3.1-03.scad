// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.1-03)
// ============================================================================
// part_id           : S3.1-03
// parent_bom_id     : S3.1
// subsystem         : S3
// part_name         : Dusuk kapasitansli safir/AlN yonga yalitkan tasiyici tabani
// material          : AlN
// temp_stage        : 20 mK - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±5 um duzlemlik
// computed_mass_kg  : 0.09572
// envelope_mm       : 80.000 x 80.000 x 5.700
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 80.0000;
bbox_y = 80.0000;
bbox_z = 5.7000;

// Part-specific parametric dimensions
carrier_size_mm = 80.0;
wafer_pocket_id_mm = 50.4;
thermal_boss_od_mm = 34.0;
align_pin_pcd_mm = 66.0;

// Interface / port parameters (mm)
port_wafer_pocket_bore = 50.400;
port_rear_thermal_boss_od = 34.000;
port_rear_thermal_boss_pcd = 66.000;
port_rear_thermal_boss_bolts = 3;

module part_S3_1_03() {
  difference() {
    union() {
      // 80x80 mm AlN/Sapphire carrier plate (Exp80 BC1)
      translate([0.000, 0.000, 0.425]) cube([80.000, 80.000, 4.850], center=true);
      // Rear central thermal boss Ø34 mm
      translate([0.000, 0.000, -2.440]) {
        difference() {
          cylinder(d=34.000, h=0.820, center=true);
          cylinder(d=10.000, h=2.820, center=true);
        }
      }
    }
    // Ø50.4 mm stepped wafer pocket
    translate([0.000, 0.000, 2.500]) cylinder(d=50.400, h=1.000, center=true);
    // 3x Ø3.0 H7 kinematic alignment pin holes
    for (i = [0 : 3 - 1])
      rotate([0, 0, i * 360 / 3])
        translate([33.000, 0, 0])
          cylinder(d=3.000, h=7.000, center=true);
    // Corner M3 mount #1
    translate([-33.500, -33.500, 0.000]) cylinder(d=3.400, h=7.000, center=true);
    // Corner M3 mount #2
    translate([33.500, -33.500, 0.000]) cylinder(d=3.400, h=7.000, center=true);
    // Corner M3 mount #3
    translate([33.500, 33.500, 0.000]) cylinder(d=3.400, h=7.000, center=true);
    // Corner M3 mount #4
    translate([-33.500, 33.500, 0.000]) cylinder(d=3.400, h=7.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -3.000]) rotate([0.000, 0.000, 0.000]) part_S3_1_03();

part_S3_1_03();
