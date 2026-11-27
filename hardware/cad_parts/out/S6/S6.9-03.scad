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
// computed_mass_kg  : 2.63460
// envelope_mm       : 493.250 x 34.000 x 34.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 493.2500;
bbox_y = 34.0000;
bbox_z = 34.0000;

// Part-specific parametric dimensions
busbar_d = 30.0;
busbar_l = 397.0;
n_braids = 8;
a_braid_mm2 = 88.0;
rrr_min = 200;
k_braid_n_per_m = 240.0;
t_chuck_7uw_mk = 21.75;
t_chuck_14uw_mk = 23.36;

// Interface / port parameters (mm)
port_mxc_dr_clamp_od = 34.000;
port_mxc_dr_clamp_bolts = 4;
port_cold_island_braid_end_od = 26.000;

module part_S6_9_03() {
  union() {
    // DR-side Ø30x397 mm RRR>=200 OFHC Cu busbar
    translate([-48.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=30.000, h=397.000, center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #1 (11 mm^2)
    translate([198.600, -10.000, -4.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #2 (11 mm^2)
    translate([198.600, -3.500, -4.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #3 (11 mm^2)
    translate([198.600, 3.500, -4.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #4 (11 mm^2)
    translate([198.600, 10.000, -4.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #5 (11 mm^2)
    translate([198.600, -10.000, 1.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #6 (11 mm^2)
    translate([198.600, -3.500, 1.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #7 (11 mm^2)
    translate([198.600, 3.500, 1.800]) cube([82.800, 5.500, 4.400], center=true);
    // E-beam-welded OFHC Cu multi-leaf S-braid #8 (11 mm^2)
    translate([198.600, 10.000, 1.800]) cube([82.800, 5.500, 4.400], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-308.000, 0.000, 493.500]) rotate([0.000, 0.000, 0.000]) part_S6_9_03();

part_S6_9_03();
