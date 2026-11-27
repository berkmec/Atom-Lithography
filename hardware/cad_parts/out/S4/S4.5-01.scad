// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.5-01)
// ============================================================================
// part_id           : S4.5-01
// parent_bom_id     : S4.5
// subsystem         : S4
// part_name         : Invar-36 / Zerodur ultra-dusuk CTE metroloji referans cercevesi
// material          : Invar-36
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±5 um
// computed_mass_kg  : 2.99371
// envelope_mm       : 264.000 x 264.000 x 90.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 264.0000;
bbox_y = 264.0000;
bbox_z = 90.0000;

// Part-specific parametric dimensions
ring_id_mm = 208.0;
ring_od_mm = 264.0;
ring_h_mm = 18.0;
optical_window_deg = 20.0;
optical_window_h_mm = 13.0;
col_radius_mm = 118.0;
n_columns = 4;

// Interface / port parameters (mm)
port_interf_head_ring_od = 264.000;
port_interf_head_ring_bore = 208.000;
port_interf_head_ring_pcd = 236.000;
port_interf_head_ring_bolts = 8;

module part_S4_5_01() {
  difference() {
    union() {
      // Invar-36 / Zerodur metrology reference ring (Ø208/Ø264)
      translate([0.000, 0.000, 36.000]) {
        difference() {
          cylinder(d=264.000, h=18.000, center=true);
          cylinder(d=208.000, h=20.000, center=true);
        }
      }
      // Invar-36 metrology bridge column #1
      translate([83.439, 83.439, -9.000]) cylinder(d=15.000, h=72.000, center=true);
      // Invar-36 metrology bridge column #2
      translate([-83.439, 83.439, -9.000]) cylinder(d=15.000, h=72.000, center=true);
      // Invar-36 metrology bridge column #3
      translate([-83.439, -83.439, -9.000]) cylinder(d=15.000, h=72.000, center=true);
      // Invar-36 metrology bridge column #4
      translate([83.439, -83.439, -9.000]) cylinder(d=15.000, h=72.000, center=true);
    }
    // 8x M5 precision bolted ring joints
    translate([0.000, 0.000, 36.000]) {
      for (i = [0 : 8 - 1])
        rotate([0, 0, i * 360 / 8])
          translate([118.000, 0, 0])
            cylinder(d=5.500, h=22.000, center=true);
    }
    // 0-deg X interferometer optical pass-through bore
    translate([118.000, 0.000, 36.000]) rotate([0.000, 90.000, 0.000]) {
      hull() {
        translate([-11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
        translate([11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
      }
    }
    // 90-deg Y interferometer optical pass-through bore
    translate([0.000, 118.000, 36.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
        translate([11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
      }
    }
    // 270-deg Z interferometer optical pass-through bore
    translate([0.000, -118.000, 36.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
        translate([11.500, 0, 0]) cylinder(d=13.000, h=36.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -169.000]) rotate([0.000, 0.000, 0.000]) part_S4_5_01();

part_S4_5_01();
