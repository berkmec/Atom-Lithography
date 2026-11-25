// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.1-01)
// ============================================================================
// part_id           : S4.1-01
// parent_bom_id     : S4.1
// subsystem         : S4
// part_name         : Hassas taslanmis siyah granit izolasyon blogu (s=0.5 zarf)
// material          : Granite
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : ±2 um duzlemlik
// computed_mass_kg  : 176.38897
// envelope_mm       : 900.000 x 700.000 x 120.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 900.0000;
bbox_y = 700.0000;
bbox_z = 120.0000;

// Part-specific parametric dimensions
granite_x_mm = 900.0;
granite_y_mm = 700.0;
granite_z_mm = 120.0;
dr_clear_bore_d_mm = 420.0;
m6_insert_count = 42;
m6_grid_pitch_mm = 100.0;
bom_reconciled_from = "600x450x150";

// Interface / port parameters (mm)
port_top_active_table_deck_bore = 420.000;
port_dr_central_clear_bore_bore = 420.000;

module part_S4_1_01() {
  difference() {
    union() {
      // Reconciled 900x700x120 mm DIN 876/00 black diabase granite block
      cube([900.000, 700.000, 120.000], center=true);
    }
    // Central Ø420 mm (R=210 mm) clear bore for lower DR OVC / cryo access
    cylinder(d=420.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, -300)
    translate([-400.000, -300.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, -200)
    translate([-400.000, -200.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, -100)
    translate([-400.000, -100.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, 0)
    translate([-400.000, 0.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, 100)
    translate([-400.000, 100.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, 200)
    translate([-400.000, 200.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-400, 300)
    translate([-400.000, 300.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-300, -300)
    translate([-300.000, -300.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-300, -200)
    translate([-300.000, -200.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-300, -100)
    translate([-300.000, -100.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-300, 0)
    translate([-300.000, 0.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
    // M6 stainless insert grid (-300, 100)
    translate([-300.000, 100.000, 0.000]) cylinder(d=8.000, h=124.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -361.000]) rotate([0.000, 0.000, 0.000]) part_S4_1_01();

part_S4_1_01();
