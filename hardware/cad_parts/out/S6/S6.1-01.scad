// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.1-01)
// ============================================================================
// part_id           : S6.1-01
// parent_bom_id     : S6.1
// subsystem         : S6
// part_name         : Kapali cevrim 4 K pulse-tube sogutucu (PT420 2.0 W @ 4.2 K sinifi, yeni)
// material          : 316LN
// temp_stage        : 50 K / 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.05 K
// computed_mass_kg  : 10.37608
// envelope_mm       : 180.000 x 180.000 x 478.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 180.0000;
bbox_y = 180.0000;
bbox_z = 478.0000;

// Part-specific parametric dimensions
head_od = 128.0;
stage1_od = 80.0;
stage2_od = 48.0;
cooling_4k_w = 2.0;

// Interface / port parameters (mm)
port_dr_top_isok_od = 180.000;
port_dr_top_isok_bore = 153.000;
port_dr_top_isok_bolts = 4;
port_he_flex_inlet_od = 28.000;
port_he_flex_inlet_bore = 16.000;
port_thermal_45k_od = 80.000;
port_thermal_4k_od = 48.000;

module part_S6_1_01() {
  union() {
    // ISO-K DN160 flange
    translate([0.000, 0.000, 7.000]) cylinder(d=180.000, h=12.000, center=true);
    // PT420 300K reservoir
    translate([0.000, 0.000, 124.000]) cylinder(d=128.000, h=222.000, center=true);
    // 45 K 1st stage
    translate([0.000, 0.000, -71.250]) cylinder(d=80.000, h=141.500, center=true);
    // 4.2 K 2nd stage
    translate([0.000, 0.000, -192.750]) cylinder(d=48.000, h=100.500, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 985.000]) rotate([0.000, 0.000, 0.000]) part_S6_1_01();

part_S6_1_01();
