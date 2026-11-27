// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.5-03)
// ============================================================================
// part_id           : S5.5-03
// parent_bom_id     : S5.5
// subsystem         : S5
// part_name         : Dikroik ustu 10 us iki-renkli InGaAs/Si pirometre ve ±1.5% kapali-cevrim enerji integratori (Exp130)
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer (optik)
// tolerance         : ±1.5% enerji / 10 us
// computed_mass_kg  : 0.32739
// envelope_mm       : 100.400 x 58.000 x 56.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 100.4000;
bbox_y = 58.0000;
bbox_z = 56.2000;

// Part-specific parametric dimensions
dt_us = 10.0;
dichroic_deg = 45.0;
energy_tol_pct = 1.5;

// Interface / port parameters (mm)
port_optical_tap_in_bore = 28.000;

module part_S5_5_03() {
  union() {
    // 45 deg dichroic beam-splitter turret cube
    cube([56.000, 58.000, 46.000], center=true);
    // 45 deg dichroic mirror element
    rotate([0.000, 45.000, 0.000]) cylinder(d=30.000, h=3.000, center=true);
    // InGaAs 10 us fast photodiode barrel
    translate([-39.200, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=22.000, h=22.000, center=true);
    // Si 10 us fast photodiode barrel
    translate([39.200, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=22.000, h=22.000, center=true);
    // Closed-loop +/-1.5% energy integrator FPGA
    translate([0.000, 0.000, 28.200]) cube([50.000, 50.000, 10.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 182.216, 717.059]) rotate([36.000, 0.000, 0.000]) part_S5_5_03();

part_S5_5_03();
