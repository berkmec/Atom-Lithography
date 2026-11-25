// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.4-01)
// ============================================================================
// part_id           : S4.4-01
// parent_bom_id     : S4.4
// subsystem         : S4
// part_name         : 3-eksenli frekans-kararli He-Ne lazer interferometre kafasi (Renishaw XL-80/RLE)
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer (fiber cikiş)
// tolerance         : ±0.05 ppm
// computed_mass_kg  : 1.30534
// envelope_mm       : 162.200 x 84.000 x 65.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 162.2000;
bbox_y = 84.0000;
bbox_z = 65.8000;

// Part-specific parametric dimensions
wavelength_nm = 632.8;
freq_stab_ppm = 0.05;
n_fiber_axes = 3;

// Interface / port parameters (mm)

module part_S4_4_01() {
  union() {
    // Stabilized 632.8 nm He-Ne laser unit (Renishaw XL-80/RLE)
    cube([136.000, 84.000, 52.000], center=true);
    // FC/APC Fiber Launch X
    translate([-75.100, -22.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=11.000, h=14.000, center=true);
    // FC/APC Fiber Launch Y
    translate([-75.100, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=11.000, h=14.000, center=true);
    // FC/APC Fiber Launch Z
    translate([-75.100, 22.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=11.000, h=14.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([330.000, 245.000, -205.000]) rotate([0.000, 0.000, 0.000]) part_S4_4_01();

part_S4_4_01();
