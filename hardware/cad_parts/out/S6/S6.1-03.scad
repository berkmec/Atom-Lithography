// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.1-03)
// ============================================================================
// part_id           : S6.1-03
// parent_bom_id     : S6.1
// subsystem         : S6
// part_name         : Titresim-ayrisik orgulu OFHC bakir termal baglanti seritleri (50K/4K)
// material          : OFHC Cu
// temp_stage        : 50 K / 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : <0.1 K/W
// computed_mass_kg  : 0.09179
// envelope_mm       : 161.168 x 161.168 x 132.774
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 161.1677;
bbox_y = 161.1677;
bbox_z = 132.7737;

// Part-specific parametric dimensions
n_braids_50k = 4;
n_braids_4k = 4;
rrr_min = 200;

// Interface / port parameters (mm)
port_pt420_45k_ring_od = 170.000;
port_pt420_4k_ring_od = 138.000;

module part_S6_1_03() {
  union() {
    // 50K OFHC thermal braid #1
    translate([57.097, 26.625, 60.000]) rotate([0.000, 0.000, 25.000]) cube([46.000, 12.500, 9.500], center=true);
    // 50K OFHC thermal braid #2
    translate([-26.625, 57.097, 60.000]) rotate([0.000, 0.000, 115.000]) cube([46.000, 12.500, 9.500], center=true);
    // 50K OFHC thermal braid #3
    translate([-57.097, -26.625, 60.000]) rotate([0.000, 0.000, 205.000]) cube([46.000, 12.500, 9.500], center=true);
    // 50K OFHC thermal braid #4
    translate([26.625, -57.097, 60.000]) rotate([0.000, 0.000, 295.000]) cube([46.000, 12.500, 9.500], center=true);
    // 4K OFHC thermal braid #1
    translate([33.234, 33.234, -59.000]) rotate([0.000, 0.000, 45.000]) cube([44.000, 11.200, 8.800], center=true);
    // 4K OFHC thermal braid #2
    translate([-33.234, 33.234, -59.000]) rotate([0.000, 0.000, 135.000]) cube([44.000, 11.200, 8.800], center=true);
    // 4K OFHC thermal braid #3
    translate([-33.234, -33.234, -59.000]) rotate([0.000, 0.000, 225.000]) cube([44.000, 11.200, 8.800], center=true);
    // 4K OFHC thermal braid #4
    translate([33.234, -33.234, -59.000]) rotate([0.000, 0.000, 315.000]) cube([44.000, 11.200, 8.800], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 802.000]) rotate([0.000, 0.000, 0.000]) part_S6_1_03();

part_S6_1_03();
