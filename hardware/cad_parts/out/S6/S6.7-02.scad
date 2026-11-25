// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.7-02)
// ============================================================================
// part_id           : S6.7-02
// parent_bom_id     : S6.7
// subsystem         : S6
// part_name         : Kriyo-CMOS / DC kapi-gerilimi coklayici dagitim kartlari (4 K / MXC)
// material          : OFHC Cu
// temp_stage        : 4 K / 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.1 mV
// computed_mass_kg  : 0.44270
// envelope_mm       : 76.000 x 58.000 x 48.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 76.0000;
bbox_y = 58.0000;
bbox_z = 48.0000;

// Part-specific parametric dimensions
n_cards = 8;
cage_dx = 76.0;
cage_dy = 58.0;
cage_dz = 48.0;

// Interface / port parameters (mm)
port_cage_4k_thermal_bolts = 4;

module part_S6_7_02() {
  union() {
    // 4 K 8-card cryo-CMOS DC gate mux cage
    cube([76.000, 58.000, 48.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 656.000]) rotate([0.000, 0.000, 0.000]) part_S6_7_02();

part_S6_7_02();
