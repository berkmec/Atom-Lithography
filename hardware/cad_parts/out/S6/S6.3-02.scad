// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.3-02)
// ============================================================================
// part_id           : S6.3-02
// parent_bom_id     : S6.3
// subsystem         : S6
// part_name         : Aktif karsi-sargili (bucking) bobin ciftleri (A/B karsi-bobin, Exp125 delta)
// material          : Al-Bronze
// temp_stage        : 4.2 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.1 mm eksen
// computed_mass_kg  : 11.75596
// envelope_mm       : 334.677 x 306.233 x 321.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 334.6768;
bbox_y = 306.2334;
bbox_z = 321.9000;

// Part-specific parametric dimensions
a_r_in = 144.0;
a_r_out = 167.5;
b_r_in = 56.0;
b_r_out = 82.0;
n_lorentz_ties = 8;
lorentz_rating_kn = 200.0;

// Interface / port parameters (mm)
port_a_former_fit_od = 335.000;
port_a_former_fit_bore = 288.000;
port_b_resonator_bore_od = 164.000;
port_b_resonator_bore_bore = 112.000;

module part_S6_3_02() {
  union() {
    // Anchored A_upper active shield coil
    translate([0.000, 0.000, 93.500]) {
      difference() {
        cylinder(d=335.000, h=29.000, center=true);
        cylinder(d=288.000, h=31.000, center=true);
      }
    }
    // Anchored A_lower active shield coil
    translate([0.000, 0.000, -93.500]) {
      difference() {
        cylinder(d=335.000, h=29.000, center=true);
        cylinder(d=288.000, h=31.000, center=true);
      }
    }
    // B_upper bucking coil
    translate([0.000, 0.000, -133.000]) {
      difference() {
        cylinder(d=164.000, h=24.000, center=true);
        cylinder(d=112.000, h=26.000, center=true);
      }
    }
    // B_lower bucking coil
    translate([0.000, 0.000, -172.000]) {
      difference() {
        cylinder(d=164.000, h=24.000, center=true);
        cylinder(d=112.000, h=26.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S6_3_02();

part_S6_3_02();
