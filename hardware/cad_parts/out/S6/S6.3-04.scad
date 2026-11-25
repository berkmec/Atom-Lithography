// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.3-04)
// ============================================================================
// part_id           : S6.3-04
// parent_bom_id     : S6.3
// subsystem         : S6
// part_name         : Kalici-mod (persistent) superiletken anahtar ve quench koruma devresi
// material          : OFHC Cu
// temp_stage        : 4.2 K / 300 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : <0.1 ppm/h
// computed_mass_kg  : 0.40359
// envelope_mm       : 36.000 x 46.000 x 53.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 36.0000;
bbox_y = 46.0000;
bbox_z = 53.9000;

// Part-specific parametric dimensions
r_dump_ohm = 1.563;
e_mag_kj = 18.9;
t_quench_peak_k = 64.6;

// Interface / port parameters (mm)
port_base_4k_mount_bolts = 4;

module part_S6_3_04() {
  union() {
    // 4.2 K persistent switch & cold-diode quench box
    cube([36.000, 46.000, 54.000], center=true);
    // NbTi persistent switch bobbin
    translate([0.000, -9.000, 0.000]) cylinder(d=18.000, h=32.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-598.000, 0.000, 792.500]) rotate([0.000, 0.000, 0.000]) part_S6_3_04();

part_S6_3_04();
