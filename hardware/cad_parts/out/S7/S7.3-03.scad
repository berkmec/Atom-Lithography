// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.3-03)
// ============================================================================
// part_id           : S7.3-03
// parent_bom_id     : S7.3
// subsystem         : S7
// part_name         : Kriyojenik cip tarama (screening) test soketi ve karakterizasyon duzenegi
// material          : OFHC Cu
// temp_stage        : 4 K / 300 K
// vacuum_grade      : Kriyo-test
// tolerance         : ISO 2768-mK
// computed_mass_kg  : 2.82584
// envelope_mm       : 113.500 x 113.500 x 183.100
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 113.5000;
bbox_y = 113.5000;
bbox_z = 183.1000;

// Part-specific parametric dimensions
cf_size = "CF63";
chuck_od_mm = 92.0;
strut_len_mm = 114.0;

// Interface / port parameters (mm)
port_cryo_dipstick_cf63_od = 113.500;
port_cryo_dipstick_cf63_bore = 63.500;
port_cryo_dipstick_cf63_pcd = 92.100;
port_cryo_dipstick_cf63_bolts = 8;

module part_S7_3_03() {
  union() {
    // ISO 3669 CF63 hermetic top flange
    translate([0.000, 0.000, 72.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=50.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // 4K OFHC Cu thermal anchor chuck
    translate([0.000, 0.000, -62.000]) cylinder(d=92.000, h=24.000, center=true);
    // PEEK probe clamp bridge
    translate([0.000, 0.000, -51.800]) cube([68.000, 24.000, 8.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1120.000, 780.000, 880.000]) rotate([0.000, 0.000, 0.000]) part_S7_3_03();

part_S7_3_03();
