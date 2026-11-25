// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-02)
// ============================================================================
// part_id           : S6.6-02
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : Kriyojenik izolator / sirkulator (56 zincir, Exp114)
// material          : OFHC Cu
// temp_stage        : 20 mK / 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.2 dB
// computed_mass_kg  : 1.68492
// envelope_mm       : 196.000 x 196.000 x 35.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 196.0000;
bbox_y = 196.0000;
bbox_z = 35.0000;

// Part-specific parametric dimensions
n_isolators = 56;
plate_od = 196.0;
isolation_db = 20.0;

// Interface / port parameters (mm)
port_mxc_hang_bolts_od = 196.000;
port_mxc_hang_bolts_pcd = 180.000;
port_mxc_hang_bolts_bolts = 12;

module part_S6_6_02() {
  difference() {
    union() {
      // OFHC 56-ch isolator thermal plate
      translate([0.000, 0.000, 15.000]) {
        difference() {
          cylinder(d=196.000, h=6.000, center=true);
          cylinder(d=28.000, h=8.000, center=true);
        }
      }
      // 56x magnetically shielded cryo isolators
      translate([0.000, 0.000, -3.000]) {
        difference() {
          cylinder(d=170.000, h=28.000, center=true);
          cylinder(d=82.000, h=30.000, center=true);
        }
      }
    }
    // 12x M3 mounting bolt circle
    translate([0.000, 0.000, 15.000]) {
      for (i = [0 : 12 - 1])
        rotate([0, 0, i * 360 / 12])
          translate([90.000, 0, 0])
            cylinder(d=3.200, h=8.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 366.000]) rotate([0.000, 0.000, 0.000]) part_S6_6_02();

part_S6_6_02();
