// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.3-01)
// ============================================================================
// part_id           : S7.3-01
// parent_bom_id     : S7.3
// subsystem         : S7
// part_name         : SKY130 yerel 4 K kontrol cipleri (SEG8 / blanker_tile MPW tape-out partisi)
// material          : PEEK
// temp_stage        : 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : DRC/LVS/Ant=0
// computed_mass_kg  : 0.15326
// envelope_mm       : 88.000 x 88.000 x 17.300
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 88.0000;
bbox_y = 88.0000;
bbox_z = 17.3000;

// Part-specific parametric dimensions
body_sq_mm = 88.0;
die_size_mm = 8.0;
die_grid_n = 4;
cbore_m3_d = 6.2;

// Interface / port parameters (mm)
port_socket_mount_m3_bolts = 4;

module part_S7_3_01() {
  difference() {
    union() {
      // Non-magnetic PEEK 4K socket base
      cube([88.000, 88.000, 14.000], center=true);
      // BeCu spring-finger clamp frame
      translate([0.000, 0.000, 8.700]) cube([72.000, 72.000, 3.200], center=true);
    }
    // M3 mount hole #1
    translate([-36.000, -36.000, 0.000]) cylinder(d=3.400, h=18.000, center=true);
    // M3 mount hole #2
    translate([36.000, -36.000, 0.000]) cylinder(d=3.400, h=18.000, center=true);
    // M3 mount hole #3
    translate([36.000, 36.000, 0.000]) cylinder(d=3.400, h=18.000, center=true);
    // M3 mount hole #4
    translate([-36.000, 36.000, 0.000]) cylinder(d=3.400, h=18.000, center=true);
    // 4x4 SKY130 die pocket window
    translate([0.000, 0.000, 8.700]) {
      for (ix = [0 : 4 - 1])
        for (iy = [0 : 4 - 1])
          translate([(ix - 1.500) * 11.0000, (iy - 1.500) * 11.0000, 0])
            cylinder(d=7.5000, h=5.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([820.000, 780.000, 800.000]) rotate([0.000, 0.000, 0.000]) part_S7_3_01();

part_S7_3_01();
