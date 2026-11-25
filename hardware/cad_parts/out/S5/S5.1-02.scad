// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.1-02)
// ============================================================================
// part_id           : S5.1-02
// parent_bom_id     : S5.1
// subsystem         : S5
// part_name         : Ust kolon montaj flansi ve cikarilabilir 150 C bakeout isitma ceketi
// material          : 316LN
// temp_stage        : 300-423 K
// vacuum_grade      : UHV / Dis yuzey
// tolerance         : ±3 C
// computed_mass_kg  : 12.71976
// envelope_mm       : 425.740 x 426.000 x 412.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 425.7405;
bbox_y = 426.0000;
bbox_z = 412.0000;

// Part-specific parametric dimensions
jacket_r_in = 195.0;
jacket_r_out = 213.0;
col_bore_mm = 128.0;
bake_temp_C = 150;

// Interface / port parameters (mm)
port_chamber_top_cf250_mate_od = 305.000;
port_chamber_top_cf250_mate_bore = 128.000;
port_chamber_top_cf250_mate_pcd = 284.200;
port_chamber_top_cf250_mate_bolts = 32;
port_column_mount_bore_od = 172.000;
port_column_mount_bore_bore = 128.000;

module part_S5_1_02() {
  union() {
    // Upper CF250 column mounting flange (Dia 128 bore)
    translate([0.000, 0.000, 181.250]) rotate([180.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=305.000, h=24.500, center=true);
        cylinder(d=128.000, h=26.500, center=true);
        translate([0, 0, 11.000]) cylinder(d=272.900, h=1.750);
        for (i = [0 : 32 - 1])
          rotate([0, 0, i * 360 / 32])
            translate([142.100, 0, 0])
              cylinder(d=8.400, h=26.500, center=true);
      }
    }
    // Ion column alignment collar
    translate([0.000, 0.000, 199.300]) {
      difference() {
        cylinder(d=172.000, h=11.400, center=true);
        cylinder(d=128.000, h=13.400, center=true);
      }
    }
    // Zone 1 lower 150 C bakeout jacket ring
    translate([0.000, 0.000, -189.500]) {
      difference() {
        cylinder(d=426.000, h=35.000, center=true);
        cylinder(d=390.000, h=37.000, center=true);
      }
    }
    // Zone 2 upper 150 C bakeout jacket ring
    translate([0.000, 0.000, 88.250]) {
      difference() {
        cylinder(d=426.000, h=16.500, center=true);
        cylinder(d=390.000, h=18.500, center=true);
      }
    }
    // Zone 4 top dome bakeout collar
    translate([0.000, 0.000, 136.250]) {
      difference() {
        cylinder(d=426.000, h=12.500, center=true);
        cylinder(d=390.000, h=14.500, center=true);
      }
    }
    // 4-zone PID thermocouple & heater junction box
    translate([161.928, -161.928, -190.000]) rotate([0.000, 0.000, 315.000]) cube([30.000, 48.000, 32.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_1_02();

part_S5_1_02();
