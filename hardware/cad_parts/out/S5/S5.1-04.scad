// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.1-04)
// ============================================================================
// part_id           : S5.1-04
// parent_bom_id     : S5.1
// subsystem         : S5
// part_name         : Manyetik kuplajli UHV lineer/doner yonga transfer kolu ve catal
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 mm
// computed_mass_kg  : 8.73961
// envelope_mm       : 650.000 x 152.000 x 576.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 650.0000;
bbox_y = 152.0000;
bbox_z = 576.0000;

// Part-specific parametric dimensions
stroke_mm = 500.0;
tube_len_mm = 540.0;
tube_od_mm = 38.0;
fork_span_mm = 68.0;

// Interface / port parameters (mm)
port_loadlock_cf100_mate_od = 152.000;
port_loadlock_cf100_mate_bore = 101.600;
port_loadlock_cf100_mate_pcd = 130.200;
port_loadlock_cf100_mate_bolts = 16;

module part_S5_1_04() {
  union() {
    // Mating CF100 flange
    translate([9.900, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=101.600, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // 500 mm stroke 316LN magnetic guide tube
    translate([347.800, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=38.000, h=540.000, center=true);
        cylinder(d=34.000, h=542.000, center=true);
      }
    }
    // External SmCo magnetic linear/rotary shuttle
    translate([515.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=68.000, h=96.000, center=true);
        cylinder(d=40.400, h=98.000, center=true);
      }
    }
    // Ti-6Al-4V wafer fork left prong
    translate([44.000, -29.000, 0.000]) cube([64.000, 10.000, 5.000], center=true);
    // Ti-6Al-4V wafer fork right prong
    translate([44.000, 29.000, 0.000]) cube([64.000, 10.000, 5.000], center=true);
    // End support floor stanchion
    translate([595.000, 0.000, -258.000]) cylinder(d=28.000, h=456.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([510.500, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_1_04();

part_S5_1_04();
