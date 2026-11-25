// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-01)
// ============================================================================
// part_id           : S6.6-01
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : 4 K kriyojenik dusuk-guclu InP HEMT LNA (56 okuma zinciri, Exp111/114)
// material          : OFHC Cu
// temp_stage        : 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : P_DC <= 2.8 mW
// computed_mass_kg  : 1.12891
// envelope_mm       : 252.000 x 252.000 x 35.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 252.0000;
bbox_y = 252.0000;
bbox_z = 35.0000;

// Part-specific parametric dimensions
n_hemt = 56;
ring_id = 196.0;
ring_od = 252.0;
p_dc_mw_per_ch = 2.1;

// Interface / port parameters (mm)
port_ring_4k_mount_od = 252.000;
port_ring_4k_mount_bore = 196.000;
port_ring_4k_mount_pcd = 224.000;
port_ring_4k_mount_bolts = 16;

module part_S6_6_01() {
  difference() {
    union() {
      // 4 K OFHC HEMT ring
      translate([0.000, 0.000, 15.000]) {
        difference() {
          cylinder(d=252.000, h=6.000, center=true);
          cylinder(d=196.000, h=8.000, center=true);
        }
      }
      // 56x InP HEMT module array envelope
      translate([0.000, 0.000, -3.000]) {
        difference() {
          cylinder(d=248.000, h=28.000, center=true);
          cylinder(d=200.000, h=30.000, center=true);
        }
      }
    }
    // 16x M3 thermal clamp bolts
    translate([0.000, 0.000, 15.000]) {
      for (i = [0 : 16 - 1])
        rotate([0, 0, i * 360 / 16])
          translate([112.000, 0, 0])
            cylinder(d=3.200, h=8.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 700.000]) rotate([0.000, 0.000, 0.000]) part_S6_6_01();

part_S6_6_01();
