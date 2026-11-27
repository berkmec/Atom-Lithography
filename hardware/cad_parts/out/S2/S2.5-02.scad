// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.5-02)
// ============================================================================
// part_id           : S2.5-02
// parent_bom_id     : S2.5
// subsystem         : S2
// part_name         : Kinematik piezo egim/Z kafa hizalama tutucusu (2.59 MHz rijit)
// material          : Invar-36
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.1 urad
// computed_mass_kg  : 0.27962
// envelope_mm       : 104.000 x 104.000 x 7.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 104.0000;
bbox_y = 104.0000;
bbox_z = 7.5000;

// Part-specific parametric dimensions
od = 104.0;
bore_id = 28.0;
height = 7.5;
tip_tilt_mrad = 1.0;
z_stroke_um = 100.0;
f1_axial_kHz = 18.34;
f1_lateral_kHz = 51.87;

// Interface / port parameters (mm)
port_head_mate_bot_od = 104.000;
port_head_mate_bot_bore = 28.000;
port_head_mate_bot_pcd = 92.000;
port_head_mate_bot_bolts = 12;
port_column_mate_top_od = 104.000;
port_column_mate_top_bore = 28.000;
port_column_mate_top_pcd = 92.000;
port_column_mate_top_bolts = 12;

module part_S2_5_02() {
  difference() {
    union() {
      // Lower Invar-36 kinematic flange
      translate([0.000, 0.000, -2.650]) {
        difference() {
          cylinder(d=104.000, h=2.200, center=true);
          cylinder(d=28.000, h=4.200, center=true);
        }
      }
      // Upper Invar-36 column interface flange
      translate([0.000, 0.000, 2.650]) {
        difference() {
          cylinder(d=104.000, h=2.200, center=true);
          cylinder(d=28.000, h=4.200, center=true);
        }
      }
    }
    // 12xM4 mounting bolt circle
    for (i = [0 : 12 - 1])
      rotate([0, 0, i * 360 / 12])
        translate([46.000, 0, 0])
          cylinder(d=4.500, h=12.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 35.660]) rotate([0.000, 0.000, 0.000]) part_S2_5_02();

part_S2_5_02();
