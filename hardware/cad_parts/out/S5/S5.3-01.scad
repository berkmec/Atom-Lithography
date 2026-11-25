// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.3-01)
// ============================================================================
// part_id           : S5.3-01
// parent_bom_id     : S5.3
// subsystem         : S5
// part_name         : Yerinde hizli termal / flas optik tavlama modulu (Exp66/91)
// material          : Al 6061
// temp_stage        : 300 K -> 1000 C (ms)
// vacuum_grade      : UHV (optik giris)
// tolerance         : ±5 C / ms darbe
// computed_mass_kg  : 3.60974
// envelope_mm       : 148.200 x 147.000 x 185.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 148.2000;
bbox_y = 147.0000;
bbox_z = 185.0000;

// Part-specific parametric dimensions
head_l = 148.2;
aperture_d = 96.0;
pulse_ms = 1.0;

// Interface / port parameters (mm)
port_optical_exit_aperture_bore = 96.000;

module part_S5_3_01() {
  difference() {
    union() {
      // Finned Al-6061 Xe flash/RTA lamp housing
      translate([64.000, 0.000, 0.000]) cube([128.000, 126.000, 126.000], center=true);
      // Rear cooling blower shroud
      translate([138.200, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=104.000, h=20.000, center=true);
      // HV Xe flash trigger transformer block
      translate([74.000, 0.000, 81.500]) cube([68.000, 56.000, 36.000], center=true);
    }
    // Elliptical optical reflector cavity
    translate([50.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=96.000, h=110.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-271.563, 227.868, 500.000]) rotate([0.000, 0.000, 140.000]) part_S5_3_01();

part_S5_3_01();
