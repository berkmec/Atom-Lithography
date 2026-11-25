// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.9-03)
// ============================================================================
// part_id           : S6.9-03
// parent_bom_id     : S6.9
// subsystem         : S6
// part_name         : DR tarafi Ø12x397 mm Cu bara + 4x paralel S-ilmek OFHC Cu orgu demeti (k=52.7 N/m, Exp133)
// material          : OFHC Cu
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : UHV / Kriyo-vakum
// tolerance         : k<=60 N/m, RRR>=200
// computed_mass_kg  : 0.41337
// envelope_mm       : 492.900 x 14.000 x 14.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 492.9000;
bbox_y = 14.0000;
bbox_z = 14.0000;

// Part-specific parametric dimensions
busbar_d = 12.0;
busbar_l = 397.0;
n_braids = 4;
k_braid_n_per_m = 52.7;
dt_mk = 3.7;

// Interface / port parameters (mm)
port_mxc_dr_clamp_od = 14.000;
port_mxc_dr_clamp_bolts = 4;
port_cold_island_braid_end_od = 12.000;

module part_S6_9_03() {
  union() {
    // DR-side Ø12x397 mm OFHC Cu busbar
    translate([-48.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=12.000, h=397.000, center=true);
    // S-loop OFHC Cu braid #1 w/ Au clamp lugs
    translate([199.000, -2.200, -2.800]) cube([95.600, 3.500, 2.200], center=true);
    // S-loop OFHC Cu braid #2 w/ Au clamp lugs
    translate([199.000, 2.200, -2.800]) cube([95.600, 3.500, 2.200], center=true);
    // S-loop OFHC Cu braid #3 w/ Au clamp lugs
    translate([199.000, -2.200, 2.800]) cube([95.600, 3.500, 2.200], center=true);
    // S-loop OFHC Cu braid #4 w/ Au clamp lugs
    translate([199.000, 2.200, 2.800]) cube([95.600, 3.500, 2.200], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-308.000, 0.000, 493.500]) rotate([0.000, 0.000, 0.000]) part_S6_9_03();

part_S6_9_03();
