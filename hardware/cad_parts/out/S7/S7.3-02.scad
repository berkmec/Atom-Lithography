// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.3-02)
// ============================================================================
// part_id           : S7.3-02
// parent_bom_id     : S7.3
// subsystem         : S7
// part_name         : Kriyojenik 4 K BGA/tel-bag cip tasiyici PCB ve ara-katmanlari
// material          : Invar-36
// temp_stage        : 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±25 um
// computed_mass_kg  : 0.41889
// envelope_mm       : 61.000 x 61.000 x 46.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 61.0000;
bbox_y = 61.0000;
bbox_z = 46.0000;

// Part-specific parametric dimensions
qty_carriers = 10;
carrier_sq_mm = 46.0;
cavity_sq_mm = 16.0;
carrier_t_mm = 2.6;

// Interface / port parameters (mm)
port_cic_thermal_base_bolts = 4;

module part_S7_3_02() {
  difference() {
    union() {
      // Cu-Invar-Cu / Rogers carrier unit
      cube([46.000, 46.000, 2.600], center=true);
    }
    // M2.5 hole #1
    translate([-18.000, -18.000, 0.000]) cylinder(d=2.700, h=6.000, center=true);
    // M2.5 hole #2
    translate([18.000, -18.000, 0.000]) cylinder(d=2.700, h=6.000, center=true);
    // M2.5 hole #3
    translate([18.000, 18.000, 0.000]) cylinder(d=2.700, h=6.000, center=true);
    // M2.5 hole #4
    translate([-18.000, 18.000, 0.000]) cylinder(d=2.700, h=6.000, center=true);
    // 16x16 mm wirebond cavity
    translate([0.000, 0.000, 0.800]) {
      hull() {
        translate([-0.000, 0, 0]) cylinder(d=16.000, h=2.000, center=true);
        translate([0.000, 0, 0]) cylinder(d=16.000, h=2.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([960.000, 780.000, 810.000]) rotate([0.000, 0.000, 0.000]) part_S7_3_02();

part_S7_3_02();
