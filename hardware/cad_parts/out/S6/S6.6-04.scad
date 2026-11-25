// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-04)
// ============================================================================
// part_id           : S6.6-04
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : Cikis superiletken NbTi / SS koaksiyel hatlari (56 zincir, Exp114)
// material          : NbTi
// temp_stage        : 20 mK -> 300 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : <0.1 dB/m
// computed_mass_kg  : 0.39960
// envelope_mm       : 44.000 x 22.000 x 334.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 44.0000;
bbox_y = 22.0000;
bbox_z = 334.0000;

// Part-specific parametric dimensions
n_chains = 56;
loss_db_per_m = 0.1;
superconducting_span = "MXC_to_4K";

// Interface / port parameters (mm)

module part_S6_6_04() {
  union() {
    // Stage 50k_4k thermalized cryo coax loom
    translate([0.000, 0.000, 125.000]) cube([44.000, 22.000, 84.000], center=true);
    // Stage 4k_still thermalized cryo coax loom
    translate([0.000, 0.000, -1.000]) cube([44.000, 22.000, 100.000], center=true);
    // Stage still_cp thermalized cryo coax loom
    translate([0.000, 0.000, -91.000]) cube([44.000, 22.000, 48.000], center=true);
    // Stage cp_mxc thermalized cryo coax loom
    translate([0.000, 0.000, -148.000]) cube([44.000, 22.000, 38.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, -76.000, 669.000]) rotate([0.000, 0.000, 0.000]) part_S6_6_04();

part_S6_6_04();
