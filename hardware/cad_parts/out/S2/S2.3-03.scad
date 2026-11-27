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
// computed_mass_kg  : 0.00191
// envelope_mm       : 61.250 x 59.000 x 9.930
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 61.2500;
bbox_y = 59.0000;
bbox_z = 9.9300;

// Part-specific parametric dimensions
od = 59.0;
id = 48.0;
thickness = 0.5;
tierod_pcd = 62.4;
tierod_d = 1.1;
tierod_h = 9.93;
hv_standoff_kV = 6.0;

// Interface / port parameters (mm)
port_spacer_bot_to_lens_od = 59.000;
port_spacer_bot_to_lens_bore = 48.000;
port_spacer_bot_to_lens_pcd = 53.500;
port_spacer_bot_to_lens_bolts = 6;
port_spacer_top_to_stop_od = 59.000;
port_spacer_top_to_stop_bore = 48.000;
port_spacer_top_to_stop_pcd = 53.500;
port_spacer_top_to_stop_bolts = 6;
port_stack_tierods_to_cassette_pcd = 62.400;
port_stack_tierods_to_cassette_bolts = 3;

module part_S2_3_03() {
  difference() {
    union() {
      // Lapped sapphire 6 kV insulator ring
      translate([0.000, 0.000, -2.705]) {
        difference() {
          cylinder(d=59.000, h=0.500, center=true);
          cylinder(d=48.000, h=2.500, center=true);
        }
      }
      // Full-stack sapphire structural tie-rod #1
      translate([31.200, 0.000, 0.000]) cylinder(d=1.100, h=9.930, center=true);
      // Full-stack sapphire structural tie-rod #2
      translate([-15.600, 27.020, 0.000]) cylinder(d=1.100, h=9.930, center=true);
      // Full-stack sapphire structural tie-rod #3
      translate([-15.600, -27.020, 0.000]) cylinder(d=1.100, h=9.930, center=true);
    }
    // 6x precision dowel registration bores
    translate([0.000, 0.000, -2.705]) {
      for (i = [0 : 6 - 1])
        rotate([0, 0, i * 360 / 6])
          translate([26.750, 0, 0])
            cylinder(d=2.200, h=2.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 5.215]) rotate([0.000, 0.000, 0.000]) part_S2_3_03();

part_S2_3_03();
