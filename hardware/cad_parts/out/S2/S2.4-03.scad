// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.4-03)
// ============================================================================
// part_id           : S2.4-03
// parent_bom_id     : S2.4
// subsystem         : S2
// part_name         : UHV esnek serit kablo demeti ve CF100 yuksek-pinli vakum gecisleri
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : He <=1e-9 mbar*L/s
// computed_mass_kg  : 4.92803
// envelope_mm       : 622.000 x 152.000 x 101.865
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 622.0000;
bbox_y = 152.0000;
bbox_z = 101.8647;

// Part-specific parametric dimensions
cf_size = "CF100";
qty_flanges = 2;
signal_pins = 256;
bakeout_C = 150.0;

// Interface / port parameters (mm)
port_feedthrough_ne_cf100_od = 152.000;
port_feedthrough_ne_cf100_bore = 88.000;
port_feedthrough_ne_cf100_pcd = 130.200;
port_feedthrough_ne_cf100_bolts = 16;
port_feedthrough_nw_cf100_od = 152.000;
port_feedthrough_nw_cf100_bore = 88.000;
port_feedthrough_nw_cf100_pcd = 130.200;
port_feedthrough_nw_cf100_bolts = 16;

module part_S2_4_03() {
  union() {
    // +X CF100 128-pin hermetic feedthrough
    translate([235.000, 0.000, 0.000]) rotate([180.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=88.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // -X CF100 128-pin hermetic feedthrough
    translate([-235.000, 0.000, 0.000]) rotate([180.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=88.000, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // +X 4x68-pin ceramic D-sub cluster
    translate([235.000, 0.000, 27.500]) cube([64.000, 48.000, 24.500], center=true);
    // -X 4x68-pin ceramic D-sub cluster
    translate([-235.000, 0.000, 27.500]) cube([64.000, 48.000, 24.500], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 235.000, 175.000]) rotate([0.000, 0.000, 0.000]) part_S2_4_03();

part_S2_4_03();
