// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.1-03)
// ============================================================================
// part_id           : S2.1-03
// parent_bom_id     : S2.1
// subsystem         : S2
// part_name         : Anti-sarj altin/Pt iletken ust membran kaplama ve koruma cercevesi
// material          : Mo
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±10 um hizalama
// computed_mass_kg  : 0.03677
// envelope_mm       : 55.528 x 57.500 x 2.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 55.5275;
bbox_y = 57.5000;
bbox_z = 2.2000;

// Part-specific parametric dimensions
bore_id = 28.0;
frame_od = 54.0;
thickness = 2.2;
au_ti_coat_nm = 50.0;

// Interface / port parameters (mm)
port_aperture_clamp_bot_od = 54.000;
port_aperture_clamp_bot_bore = 28.000;
port_aperture_clamp_bot_pcd = 46.000;
port_aperture_clamp_bot_bolts = 6;
port_cassette_seat_top_od = 54.000;
port_cassette_seat_top_bore = 28.000;
port_cassette_seat_top_pcd = 46.000;
port_cassette_seat_top_bolts = 6;

module part_S2_1_03() {
  difference() {
    union() {
      // Au/Ti-coated Mo anti-charge guard frame
      difference() {
        cylinder(d=54.000, h=2.200, center=true);
        cylinder(d=28.000, h=4.200, center=true);
      }
    }
    // 6xM2 clamping bolt holes
    for (i = [0 : 6 - 1])
      rotate([0, 0, i * 360 / 6])
        translate([23.000, 0, 0])
          cylinder(d=2.400, h=5.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 9.040]) rotate([0.000, 0.000, 0.000]) part_S2_1_03();

part_S2_1_03();
