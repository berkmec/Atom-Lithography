// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.3-03)
// ============================================================================
// part_id           : S2.3-03
// parent_bom_id     : S2.3
// subsystem         : S2
// part_name         : Hassas yalitkan ara halkalar ve optik eksen pim seti
// material          : Sapphire
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.5 um paralellik
// computed_mass_kg  : 0.00180
// envelope_mm       : 59.000 x 59.000 x 0.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 59.0000;
bbox_y = 59.0000;
bbox_z = 0.5000;

// Part-specific parametric dimensions
od = 59.0;
id = 48.0;
thickness = 0.5;
hv_standoff_kV = 3.0;

// Interface / port parameters (mm)
port_spacer_bot_to_lens_od = 59.000;
port_spacer_bot_to_lens_bore = 48.000;
port_spacer_bot_to_lens_pcd = 53.500;
port_spacer_bot_to_lens_bolts = 6;
port_spacer_top_to_stop_od = 59.000;
port_spacer_top_to_stop_bore = 48.000;
port_spacer_top_to_stop_pcd = 53.500;
port_spacer_top_to_stop_bolts = 6;

module part_S2_3_03() {
  difference() {
    union() {
      // Lapped sapphire 3 kV insulator ring
      difference() {
        cylinder(d=59.000, h=0.500, center=true);
        cylinder(d=48.000, h=2.500, center=true);
      }
    }
    // 6x precision dowel registration bores
    for (i = [0 : 6 - 1])
      rotate([0, 0, i * 360 / 6])
        translate([26.750, 0, 0])
          cylinder(d=2.200, h=2.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 2.510]) rotate([0.000, 0.000, 0.000]) part_S2_3_03();

part_S2_3_03();
