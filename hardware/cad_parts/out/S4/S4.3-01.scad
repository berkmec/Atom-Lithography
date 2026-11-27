// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.3-01)
// ============================================================================
// part_id           : S4.3-01
// parent_bom_id     : S4.3
// subsystem         : S4
// part_name         : 6-DOF UHV ince piezo flekstur kademesi (PI PIMars P-562/563 UHV sinifi)
// material          : Ti-6Al-4V
// temp_stage        : 300 K (UHV)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 nm RMS
// computed_mass_kg  : 0.54888
// envelope_mm       : 90.000 x 90.000 x 24.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 90.0000;
bbox_y = 90.0000;
bbox_z = 24.5000;

// Part-specific parametric dimensions
stage_xy_mm = 90.0;
stage_h_mm = 24.5;
stroke_um = 200.0;
blade_tx_mm = 1.96;
blade_ty_mm = 1.29;
k_eff_target_MN_m = 2.174;
n_flexure_slots = 8;
n_pzt_stacks = 8;
top_deck_gap_mm = 0.0;
bore_d_mm = 36.0;

// Interface / port parameters (mm)
port_vespel_standoff_deck_bore = 36.000;
port_coarse_stage_mount_bolts = 4;

module part_S4_3_01() {
  difference() {
    union() {
      // Ti-6Al-4V monolithic double-compound serpentine EDM flexure body (k_eff~2.17 MN/m)
      translate([0.000, 0.000, -2.400]) cube([90.000, 90.000, 19.200], center=true);
      // Invar-36 6-DOF moving stage platform (0.000 mm flush mate)
      translate([0.000, 0.000, 9.600]) cube([76.000, 76.000, 4.800], center=true);
      // Embedded UHV PZT X-axis actuator stack
      translate([0.000, 33.250, -2.400]) cube([16.000, 3.200, 14.000], center=true);
      // Embedded UHV PZT Y-axis actuator stack
      translate([24.500, 0.000, -2.400]) cube([3.200, 16.000, 14.000], center=true);
    }
    // Central Ø36 mm axial clear aperture
    cylinder(d=36.000, h=28.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -41.000]) rotate([0.000, 0.000, 0.000]) part_S4_3_01();

part_S4_3_01();
