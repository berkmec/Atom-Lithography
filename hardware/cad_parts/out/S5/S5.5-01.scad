// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.5-01)
// ============================================================================
// part_id           : S5.5-01
// parent_bom_id     : S5.5
// subsystem         : S5
// part_name         : 808 nm qCW diyot-lazer bar istifi ve 84x88x84 mm duz-tepe homojenlestirici kafa (Exp130/139)
// material          : Al 6061
// temp_stage        : 300 K (su sogutmali)
// vacuum_grade      : Atmosfer (optik giris)
// tolerance         : ±2% akı duzgunlugu
// computed_mass_kg  : 1.67793
// envelope_mm       : 104.400 x 126.000 x 88.750
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 104.4000;
bbox_y = 126.0000;
bbox_z = 88.7500;

// Part-specific parametric dimensions
core_x = 84.0;
core_y = 88.0;
core_z = 84.0;
wavelength_nm = 808.0;

// Interface / port parameters (mm)
port_homogenized_808nm_out_bore = 44.000;
port_dichroic_diag_top_bore = 28.000;
port_fiber_bundle_in_od = 36.000;
port_fiber_bundle_in_bore = 22.000;

module part_S5_5_01() {
  difference() {
    union() {
      // 84x88x84 mm flat-top 808 nm homogenizer housing
      cube([84.000, 88.000, 84.000], center=true);
      // OFHC Cu micro-channel water cooler (-X)
      translate([-47.200, 0.000, 0.000]) cube([10.000, 68.000, 56.000], center=true);
      // OFHC Cu micro-channel water cooler (+X)
      translate([47.200, 0.000, 0.000]) cube([10.000, 68.000, 56.000], center=true);
      // 808 nm qCW fiber-bundle collimator
      translate([0.000, 63.100, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=36.000, h=37.800, center=true);
    }
    // Dia 44 mm 808 nm optical bore
    rotate([90.000, 0.000, 0.000]) cylinder(d=44.000, h=92.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 385.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_5_01();

part_S5_5_01();
