// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.2-05)
// ============================================================================
// part_id           : S3.2-05
// parent_bom_id     : S3.2
// subsystem         : S3
// part_name         : CF63 hermetik coklu-koaksiyel UHV analog gecis flanslari
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : He <=1e-9 mbar*L/s
// computed_mass_kg  : 5.33155
// envelope_mm       : 497.367 x 488.417 x 113.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 497.3667;
bbox_y = 488.4171;
bbox_z = 113.5000;

// Part-specific parametric dimensions
n_flanges = 4;
coax_per_flange = 32;
cf63_od_mm = 113.5;
cf63_pcd_mm = 92.1;
cf63_bolts = 8;
cf63_bolt_d_mm = 8.4;

// Interface / port parameters (mm)
port_cf63_feedthrough_1_od = 113.500;
port_cf63_feedthrough_1_bore = 63.500;
port_cf63_feedthrough_1_pcd = 92.100;
port_cf63_feedthrough_1_bolts = 8;
port_cf63_feedthrough_2_od = 113.500;
port_cf63_feedthrough_2_bore = 63.500;
port_cf63_feedthrough_2_pcd = 92.100;
port_cf63_feedthrough_2_bolts = 8;
port_cf63_feedthrough_3_od = 113.500;
port_cf63_feedthrough_3_bore = 63.500;
port_cf63_feedthrough_3_pcd = 92.100;
port_cf63_feedthrough_3_bolts = 8;
port_cf63_feedthrough_4_od = 113.500;
port_cf63_feedthrough_4_bore = 63.500;
port_cf63_feedthrough_4_pcd = 92.100;
port_cf63_feedthrough_4_bolts = 8;

module part_S3_2_05() {
  union() {
    // ISO 3669 CF63 32-coax hermetic feedthrough #1 (45 deg)
    translate([179.782, 179.782, 0.000]) rotate([0.000, -90.000, 45.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // ISO 3669 CF63 32-coax hermetic feedthrough #2 (115 deg)
    translate([-107.451, 230.429, 0.000]) rotate([0.000, -90.000, 115.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // ISO 3669 CF63 32-coax hermetic feedthrough #3 (162 deg)
    translate([-241.806, 78.568, 0.000]) rotate([0.000, -90.000, 162.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // ISO 3669 CF63 32-coax hermetic feedthrough #4 (315 deg)
    translate([179.782, -179.782, 0.000]) rotate([0.000, -90.000, 315.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -105.000]) rotate([0.000, 0.000, 0.000]) part_S3_2_05();

part_S3_2_05();
