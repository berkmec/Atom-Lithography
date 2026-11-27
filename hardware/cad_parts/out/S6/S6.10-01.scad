// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.10-01)
// ============================================================================
// part_id           : S6.10-01
// parent_bom_id     : S6.10
// subsystem         : S6
// part_name         : Yuksek-empedansli 3 kOhm NbTiN (L_sq=100 pH/sq) M4 kavite-QED veri yolu yongasi & NRE (Exp131)
// material          : OFHC Cu
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : UHV / Kriyo-vakum
// tolerance         : ±5 nm genislik, ±5% L_sq
// computed_mass_kg  : 0.25106
// envelope_mm       : 62.200 x 36.000 x 17.900
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 62.2000;
bbox_y = 36.0000;
bbox_z = 17.9000;

// Part-specific parametric dimensions
z_bus_ohm = 3000.0;
f_res_ghz = 5.0;
l_res_um = 300.0;
b_m4_t = 0.1785;
cavity_f1_ghz = 8.842;

// Interface / port parameters (mm)

module part_S6_10_01() {
  union() {
    // 20 mK 3 kOhm NbTiN M4 cavity-QED bus package
    cube([52.000, 36.000, 18.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 58.000, 408.000]) rotate([0.000, 0.000, 0.000]) part_S6_10_01();

part_S6_10_01();
