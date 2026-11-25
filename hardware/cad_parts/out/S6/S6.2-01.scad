// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.2-01)
// ============================================================================
// part_id           : S6.2-01
// parent_bom_id     : S6.2
// subsystem         : S6
// part_name         : OFHC bakir soguk parmak ve yonga adasi termal tutucusu
// material          : OFHC Cu
// temp_stage        : 20 mK - 4 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.05 mm
// computed_mass_kg  : 0.72486
// envelope_mm       : 118.400 x 116.000 x 22.100
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 118.4000;
bbox_y = 116.0000;
bbox_z = 22.1000;

// Part-specific parametric dimensions
chuck_od = 116.0;
chuck_h = 7.6;
vespel_d = 9.0;
vespel_h = 14.3;

// Interface / port parameters (mm)
port_wafer_carrier_seat_od = 116.000;
port_wafer_carrier_seat_bore = 16.000;
port_wafer_carrier_seat_pcd = 96.000;
port_wafer_carrier_seat_bolts = 8;
port_braid_clamp_west_od = 18.000;
port_stage_kinematic_base_pcd = 90.510;
port_stage_kinematic_base_bolts = 4;

module part_S6_2_01() {
  difference() {
    union() {
      // 20 mK Au-OFHC cold island
      translate([0.000, 0.000, 6.800]) {
        difference() {
          cylinder(d=116.000, h=7.600, center=true);
          cylinder(d=16.000, h=9.600, center=true);
        }
      }
      // Vespel SP-22 strut #1
      translate([-32.000, -32.000, -4.350]) cylinder(d=9.000, h=14.300, center=true);
      // Vespel SP-22 strut #2
      translate([32.000, -32.000, -4.350]) cylinder(d=9.000, h=14.300, center=true);
      // Vespel SP-22 strut #3
      translate([32.000, 32.000, -4.350]) cylinder(d=9.000, h=14.300, center=true);
      // Vespel SP-22 strut #4
      translate([-32.000, 32.000, -4.350]) cylinder(d=9.000, h=14.300, center=true);
    }
    // 8x M3 wafer carrier clamp bolts
    translate([0.000, 0.000, 6.800]) {
      for (i = [0 : 8 - 1])
        rotate([0, 0, i * 360 / 8])
          translate([48.000, 0, 0])
            cylinder(d=3.400, h=10.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 483.000]) rotate([0.000, 0.000, 0.000]) part_S6_2_01();

part_S6_2_01();
