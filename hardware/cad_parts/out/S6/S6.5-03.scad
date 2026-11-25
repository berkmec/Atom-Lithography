// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.5-03)
// ============================================================================
// part_id           : S6.5-03
// parent_bom_id     : S6.5
// subsystem         : S6
// part_name         : Kriyojenik RF koaksiyel hatlar, bias-tee ve Eccosorb dusuk-geciren filtreler
// material          : CuNi
// temp_stage        : 300 K -> 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : ISO 2768-mK
// computed_mass_kg  : 0.24094
// envelope_mm       : 20.000 x 18.000 x 334.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 20.0000;
bbox_y = 18.0000;
bbox_z = 334.0000;

// Part-specific parametric dimensions
n_lines = 8;
eccosorb_grade = "CR-124";
ir_atten_db = 40.0;

// Interface / port parameters (mm)

module part_S6_5_03() {
  union() {
    // Stage 50k_4k thermalized cryo coax loom
    translate([0.000, 0.000, 125.000]) cube([20.000, 18.000, 84.000], center=true);
    // Stage 4k_still thermalized cryo coax loom
    translate([0.000, 0.000, -1.000]) cube([20.000, 18.000, 100.000], center=true);
    // Stage still_cp thermalized cryo coax loom
    translate([0.000, 0.000, -91.000]) cube([20.000, 18.000, 48.000], center=true);
    // Stage cp_mxc thermalized cryo coax loom
    translate([0.000, 0.000, -148.000]) cube([20.000, 18.000, 38.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-588.000, -40.000, 669.000]) rotate([0.000, 0.000, 0.000]) part_S6_5_03();

part_S6_5_03();
