// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.4-01)
// ============================================================================
// part_id           : S1.4-01
// parent_bom_id     : S1.4
// subsystem         : S1
// part_name         : Geri cekilebilir UHV Faraday kupasi (ikincil elektron bastirmali)
// material          : OFHC Cu
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.5% kalibrasyon
// computed_mass_kg  : 2.10332
// envelope_mm       : 453.000 x 69.500 x 69.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 453.0000;
bbox_y = 69.5000;
bbox_z = 69.5000;

// Part-specific parametric dimensions
qty_cups = 2;
suppressor_V = -100.0;
bellows_conv = 14;
cf_size = "CF40";

// Interface / port parameters (mm)
port_fc1_cf40_pos_x_od = 69.500;
port_fc1_cf40_pos_x_bore = 26.000;
port_fc1_cf40_pos_x_pcd = 58.700;
port_fc1_cf40_pos_x_bolts = 6;
port_fc2_cf40_neg_x_od = 69.500;
port_fc2_cf40_neg_x_bore = 26.000;
port_fc2_cf40_neg_x_pcd = 58.700;
port_fc2_cf40_neg_x_bolts = 6;
port_triax_out_pos_x_od = 12.000;

module part_S1_4_01() {
  union() {
    // +X CF40 Faraday cup flange
    translate([94.350, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=26.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // -X CF40 Faraday cup flange
    translate([-94.350, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=26.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // +X OFHC Faraday cup
    translate([76.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=23.000, h=20.000, center=true);
    // -X OFHC Faraday cup
    translate([-76.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=23.000, h=20.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 255.000]) rotate([0.000, 0.000, 0.000]) part_S1_4_01();

part_S1_4_01();
