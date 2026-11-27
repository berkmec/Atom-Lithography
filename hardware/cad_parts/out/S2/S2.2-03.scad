// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.2-03)
// ============================================================================
// part_id           : S2.2-03
// parent_bom_id     : S2.2
// subsystem         : S2
// part_name         : Yuksek yogunluklu mikro-bump / tel-bag seramik ara-dagitimci (interposer)
// material          : AlN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±15 um pad adimi
// computed_mass_kg  : 0.02016
// envelope_mm       : 82.000 x 82.000 x 1.340
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 82.0000;
bbox_y = 82.0000;
bbox_z = 1.3400;

// Part-specific parametric dimensions
od = 82.0;
bore_id = 28.0;
thickness = 1.34;
channels = 1024;
tie_rod_pcd_mm = 62.4;

// Interface / port parameters (mm)
port_microbump_to_blanker_od = 82.000;
port_microbump_to_blanker_bore = 28.000;
port_fanout_to_tiles_od = 82.000;

module part_S2_2_03() {
  difference() {
    union() {
      // Multilayer LTCC/AlN 1024-ch ceramic interposer
      difference() {
        cylinder(d=82.000, h=1.340, center=true);
        cylinder(d=28.000, h=3.340, center=true);
      }
    }
    // 8x precision alignment dowel bores
    for (i = [0 : 8 - 1])
      rotate([0, 0, i * 360 / 8])
        translate([37.000, 0, 0])
          cylinder(d=2.200, h=4.000, center=true);
    // 3x S2.3-03 stack tie-rod pass-through bores
    for (i = [0 : 3 - 1])
      rotate([0, 0, i * 360 / 3])
        translate([31.200, 0, 0])
          cylinder(d=2.500, h=4.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 6.780]) rotate([0.000, 0.000, 0.000]) part_S2_2_03();

part_S2_2_03();
