// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.11-03)
// ============================================================================
// part_id           : S6.11-03
// parent_bom_id     : S6.11
// subsystem         : S6
// part_name         : 4 K Ultra-Dusuk-Gurultulu HEMT Bankasi (LNF-LNC4_8C sinifi, 32 adet, 7.8 mW/hat, Exp140 S6.5-03, 1.02 kg)
// material          : OFHC Cu
// temp_stage        : 4 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : T_n<=2.0 K
// computed_mass_kg  : 0.73817
// envelope_mm       : 252.000 x 252.000 x 38.250
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 252.0000;
bbox_y = 252.0000;
bbox_z = 38.2500;

// Part-specific parametric dimensions
n_hemt = 32;
p_4k_w = 0.2496;
tn_k = 2.0;
mass_kg = 1.02;

// Interface / port parameters (mm)
port_hemt32_4k_thermal_od = 252.000;
port_hemt32_4k_thermal_bore = 196.000;
port_hemt32_4k_thermal_pcd = 224.000;
port_hemt32_4k_thermal_bolts = 12;

module part_S6_11_03() {
  union() {
    // 32x 4 K LNF-LNC4_8C HEMT ring
    difference() {
      cylinder(d=252.000, h=40.000, center=true);
      cylinder(d=196.000, h=42.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 654.000]) rotate([0.000, 0.000, 0.000]) part_S6_11_03();

part_S6_11_03();
