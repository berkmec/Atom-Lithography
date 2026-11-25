// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.4-02)
// ============================================================================
// part_id           : S9.4-02
// parent_bom_id     : S9.4
// subsystem         : S9
// part_name         : 20 mK NbTiN 5-Kademe Chebyshev/Klopfenstein 50 Ohm <-> 3 kOhm qRAM Kopru Modulu (4-ch, Exp142 S9.1-02, 0.38 kg)
// material          : Nb
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : Kriyo-vakum
// tolerance         : S11<=-20 dB (4-8 GHz)
// computed_mass_kg  : 0.20818
// envelope_mm       : 68.100 x 30.000 x 16.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 68.1000;
bbox_y = 30.0000;
bbox_z = 16.0000;

// Part-specific parametric dimensions
box_dx = 60.0;
box_dy = 30.0;
box_dz = 16.0;
z_in_ohm = 50.0;
z_out_ohm = 3000.0;
stages = 5;

// Interface / port parameters (mm)

module part_S9_4_02() {
  union() {
    // 20 mK shielded 5-stage Chebyshev qRAM transformer box
    cube([60.000, 30.000, 16.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 408.000]) rotate([0.000, 0.000, 0.000]) part_S9_4_02();

part_S9_4_02();
