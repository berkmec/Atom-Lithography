// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.10-03)
// ============================================================================
// part_id           : S6.10-03
// parent_bom_id     : S6.10
// subsystem         : S6
// part_name         : 4 K SKY130 968-kapi capraz-anahtar coklama karti ve M4 DC kapi dagitim modulu (Exp131)
// material          : OFHC Cu
// temp_stage        : 4 K -> 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.2 mV kapi bias
// computed_mass_kg  : 0.24981
// envelope_mm       : 76.000 x 58.000 x 26.350
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
bbox_z = 26.3500;

// Part-specific parametric dimensions
n_gates = 968;
p_4k_mw = 15.4;
qty_sets = 2;
carrier_dx = 76.0;
carrier_dy = 58.0;

// Interface / port parameters (mm)
port_thermal_4k_top_bolts = 4;

module part_S6_10_03() {
  union() {
    // 4 K OFHC thermal carrier
    translate([0.000, 0.000, 10.000]) cube([76.000, 58.000, 6.000], center=true);
    // Dual SKY130 968-gate crossbar PCB stack
    translate([0.000, 0.000, -2.000]) cube([72.000, 54.000, 16.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 703.000]) rotate([0.000, 0.000, 0.000]) part_S6_10_03();

part_S6_10_03();
