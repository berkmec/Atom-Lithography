// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.4-03)
// ============================================================================
// part_id           : S9.4-03
// parent_bom_id     : S9.4
// subsystem         : S9
// part_name         : Option-Q 4x NbTi Superiletken qRAM Kopru Koaksiyel + 1x 1550 nm SMF-28 Kriyo-Fiber Demeti (Exp142 S9.1-03, 0.82 kg)
// material          : OFHC Cu
// temp_stage        : 300 K -> 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : <=0.1 dB/m (NbTi)
// computed_mass_kg  : 0.11718
// envelope_mm       : 10.000 x 30.000 x 308.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 10.0000;
bbox_y = 30.0000;
bbox_z = 308.0000;

// Part-specific parametric dimensions
n_nbti_coax = 4;
n_smf28_fiber = 1;
n_clamps = 4;
mass_kg = 0.82;

// Interface / port parameters (mm)

module part_S9_4_03() {
  union() {
    // 1550 nm SMF-28 cryo-fiber jacket
    cylinder(d=3.200, h=308.000, center=true);
    // Cryo-fiber thermal anchor clamp #1
    translate([0.000, 0.000, -148.000]) cube([10.000, 30.000, 10.000], center=true);
    // Cryo-fiber thermal anchor clamp #2
    translate([0.000, 0.000, -50.000]) cube([10.000, 30.000, 10.000], center=true);
    // Cryo-fiber thermal anchor clamp #3
    translate([0.000, 0.000, 50.000]) cube([10.000, 30.000, 10.000], center=true);
    // Cryo-fiber thermal anchor clamp #4
    translate([0.000, 0.000, 148.000]) cube([10.000, 30.000, 10.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-793.000, 0.000, 560.000]) rotate([0.000, 0.000, 0.000]) part_S9_4_03();

part_S9_4_03();
