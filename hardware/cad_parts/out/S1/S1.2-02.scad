// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.2-02)
// ============================================================================
// part_id           : S1.2-02
// parent_bom_id     : S1.2
// subsystem         : S1
// part_name         : Wien filtresi elektrostatik saptirma plakalari
// material          : OFHC Cu
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-8 mbar
// tolerance         : ±10 um paralellik
// computed_mass_kg  : 0.17276
// envelope_mm       : 28.000 x 46.000 x 80.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 28.0000;
bbox_y = 46.0000;
bbox_z = 80.0000;

// Part-specific parametric dimensions
plate_l = 80.0;
plate_w = 28.0;
e_gap = 12.0;
e_field_kV_m = 112.32;
v_plate_nom_V = 1347.85;
nominal_steer_mrad = 0.0;

// Interface / port parameters (mm)
port_eplate_hv_pos_od = 6.400;
port_eplate_hv_neg_od = 6.400;

module part_S1_2_02() {
  union() {
    // +Y E-field deflection plate (12.0 mm gap)
    translate([0.000, 8.000, 0.000]) cube([28.000, 4.000, 80.000], center=true);
    // -Y E-field deflection plate (12.0 mm gap)
    translate([0.000, -8.000, 0.000]) cube([28.000, 4.000, 80.000], center=true);
    // Macor HV standoff
    translate([0.000, 16.600, 25.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=6.400, h=12.800, center=true);
    // Macor HV standoff
    translate([0.000, -16.600, -25.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=6.400, h=12.800, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 310.000]) rotate([0.000, 0.000, 0.000]) part_S1_2_02();

part_S1_2_02();
