// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.5-02)
// ============================================================================
// part_id           : S1.5-02
// parent_bom_id     : S1.5
// subsystem         : S1
// part_name         : Piezo-tahrikli hassas enerji suzgeci giris/cikis yariklari
// material          : Mo
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.5 um adim
// computed_mass_kg  : 0.63724
// envelope_mm       : 86.000 x 86.000 x 110.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 86.0000;
bbox_y = 86.0000;
bbox_z = 110.5000;

// Part-specific parametric dimensions
cassette_od = 86.0;
slit_nom_mm = 0.35;
step_um = 0.5;

// Interface / port parameters (mm)
port_exit_slit_plane_od = 86.000;
port_exit_slit_plane_bore = 0.350;
port_entrance_slit_plane_od = 86.000;
port_entrance_slit_plane_bore = 0.350;

module part_S1_5_02() {
  difference() {
    union() {
      // Lower HDA exit piezo slit cassette
      translate([0.000, 0.000, -52.000]) {
        difference() {
          cylinder(d=86.000, h=7.000, center=true);
          cylinder(d=40.000, h=9.000, center=true);
        }
      }
      // Upper HDA entrance piezo slit cassette
      translate([0.000, 0.000, 52.000]) {
        difference() {
          cylinder(d=86.000, h=6.000, center=true);
          cylinder(d=40.000, h=8.000, center=true);
        }
      }
    }
    // 8xM3 cassette mounting bolts
    for (i = [0 : 8 - 1])
      rotate([0, 0, i * 360 / 8])
        translate([38.000, 0, 0])
          cylinder(d=3.400, h=120.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 161.660]) rotate([0.000, 0.000, 0.000]) part_S1_5_02();

part_S1_5_02();
