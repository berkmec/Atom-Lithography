// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.4-01)
// ============================================================================
// part_id           : S2.4-01
// parent_bom_id     : S2.4
// subsystem         : S2
// part_name         : SKY130 blanker_tile 64-kanalli surucu ASIC yongalari (16 aktif karo + yedek, 1024 ch)
// material          : Si
// temp_stage        : 300 K (aktif sogutmali; 20 mK disinda)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : Anten ECO / PDN pre-foundry
// computed_mass_kg  : 0.00114
// envelope_mm       : 101.152 x 101.152 x 0.850
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 101.1521;
bbox_y = 101.1521;
bbox_z = 0.8500;

// Part-specific parametric dimensions
active_tiles = 16;
spare_tiles = 8;
ch_per_tile = 64;
tile_pcd = 96.0;
pkg_xy = 6.0;

// Interface / port parameters (mm)
port_tile_solder_pad_ring_od = 104.500;
port_tile_solder_pad_ring_bore = 87.500;
port_tile_solder_pad_ring_pcd = 96.000;
port_tile_solder_pad_ring_bolts = 16;

module part_S2_4_01() {
  union() {
    // SKY130 tile #1
    translate([47.078, 9.364, 0.000]) rotate([0.000, 0.000, 11.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([39.911, 26.667, 0.000]) rotate([0.000, 0.000, 33.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([26.667, 39.911, 0.000]) rotate([0.000, 0.000, 56.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([9.364, 47.078, 0.000]) rotate([0.000, 0.000, 78.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([-9.364, 47.078, 0.000]) rotate([0.000, 0.000, 101.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([-26.667, 39.911, 0.000]) rotate([0.000, 0.000, 123.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([-39.911, 26.667, 0.000]) rotate([0.000, 0.000, 146.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([-47.078, 9.364, 0.000]) rotate([0.000, 0.000, 168.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([-47.078, -9.364, 0.000]) rotate([0.000, 0.000, 191.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([-39.911, -26.667, 0.000]) rotate([0.000, 0.000, 213.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([-26.667, -39.911, 0.000]) rotate([0.000, 0.000, 236.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([-9.364, -47.078, 0.000]) rotate([0.000, 0.000, 258.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([9.364, -47.078, 0.000]) rotate([0.000, 0.000, 281.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([26.667, -39.911, 0.000]) rotate([0.000, 0.000, 303.750]) cube([6.000, 6.000, 0.850], center=true);
    translate([39.911, -26.667, 0.000]) rotate([0.000, 0.000, 326.250]) cube([6.000, 6.000, 0.850], center=true);
    translate([47.078, -9.364, 0.000]) rotate([0.000, 0.000, 348.750]) cube([6.000, 6.000, 0.850], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 5.825]) rotate([0.000, 0.000, 0.000]) part_S2_4_01();

part_S2_4_01();
