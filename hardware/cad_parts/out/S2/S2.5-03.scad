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
// computed_mass_kg  : 0.00559
// envelope_mm       : 69.000 x 124.000 x 6.600
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 69.0000;
bbox_y = 124.0000;
bbox_z = 6.6000;

// Part-specific parametric dimensions
mirror_pcd = 116.0;
mirror_t = 8.0;
mirror_w = 14.0;
mirror_h = 6.6;
z_nat_center_mm = 14.3;
flatness_nm = 31.6;

// Interface / port parameters (mm)

module part_S2_5_03() {
  union() {
    // Zerodur λ/20 reference mirror #1 (0 deg, split-gap Z=514.3 mm)
    translate([58.000, 0.000, 0.000]) cube([8.000, 14.000, 6.600], center=true);
    // Zerodur λ/20 reference mirror #2 (90 deg, split-gap Z=514.3 mm)
    translate([0.000, 58.000, 0.000]) rotate([0.000, 0.000, 90.000]) cube([8.000, 14.000, 6.600], center=true);
    // Zerodur λ/20 reference mirror #3 (270 deg, split-gap Z=514.3 mm)
    translate([-0.000, -58.000, 0.000]) rotate([0.000, 0.000, 270.000]) cube([8.000, 14.000, 6.600], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 14.300]) rotate([0.000, 0.000, 0.000]) part_S2_5_03();

part_S2_5_03();
