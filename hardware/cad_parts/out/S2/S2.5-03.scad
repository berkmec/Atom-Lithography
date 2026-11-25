// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.5-03)
// ============================================================================
// part_id           : S2.5-03
// parent_bom_id     : S2.5
// subsystem         : S2
// part_name         : Kafa cercevesi referans optik aynasi ve lazer hedef prizmasi
// material          : Zerodur
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±2 arcsec
// computed_mass_kg  : 0.01153
// envelope_mm       : 98.112 x 113.121 x 13.600
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 98.1122;
bbox_y = 113.1211;
bbox_z = 13.6000;

// Part-specific parametric dimensions
mirror_pcd = 115.0;
mirror_t = 8.0;
mirror_w = 14.0;
mirror_h = 13.6;
flatness_nm = 31.6;

// Interface / port parameters (mm)

module part_S2_5_03() {
  union() {
    // Zerodur λ/20 reference mirror #1 (60 deg)
    translate([28.750, 49.796, 0.000]) rotate([0.000, 0.000, 60.000]) cube([8.000, 14.000, 13.600], center=true);
    // Zerodur λ/20 reference mirror #2 (180 deg)
    translate([-57.500, 0.000, 0.000]) rotate([0.000, 0.000, 180.000]) cube([8.000, 14.000, 13.600], center=true);
    // Zerodur λ/20 reference mirror #3 (300 deg)
    translate([28.750, -49.796, 0.000]) rotate([0.000, 0.000, 300.000]) cube([8.000, 14.000, 13.600], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 20.000]) rotate([0.000, 0.000, 0.000]) part_S2_5_03();

part_S2_5_03();
