// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.6-07)
// ============================================================================
// part_id           : S6.6-07
// parent_bom_id     : S6.6
// subsystem         : S6
// part_name         : NbTiN superiletken spiral cogullamali rezonator yongalari ve paketleme (9000 kanal)
// material          : OFHC Cu
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : UHV / Kriyo-vakum
// tolerance         : sigma_f <= 0.27%
// computed_mass_kg  : 0.12574
// envelope_mm       : 50.000 x 50.000 x 23.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 50.0000;
bbox_y = 50.0000;
bbox_z = 23.0000;

// Part-specific parametric dimensions
pkg_od = 50.0;
n_resonators = 9000;
b_max_ut = 22.3;
ql_nom = 1000;

// Interface / port parameters (mm)
port_smp_4port_top_od = 36.000;
port_thermal_20mk_stem_od = 16.000;

module part_S6_6_07() {
  difference() {
    union() {
      // Ø50 mm OFHC resonator carrier
      translate([0.000, 0.000, -1.050]) cylinder(d=50.000, h=7.900, center=true);
      // 20 mK thermal stem
      translate([0.000, 0.000, -9.800]) cylinder(d=16.000, h=9.400, center=true);
    }
    // 4x M2 package clamp bolts
    for (i = [0 : 4 - 1])
      rotate([0, 0, i * 360 / 4])
        translate([20.000, 0, 0])
          cylinder(d=2.200, h=8.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 345.000]) rotate([0.000, 0.000, 0.000]) part_S6_6_07();

part_S6_6_07();
