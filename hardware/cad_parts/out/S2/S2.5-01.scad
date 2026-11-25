// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.5-01)
// ============================================================================
// part_id           : S2.5-01
// parent_bom_id     : S2.5
// subsystem         : S2
// part_name         : Kafa-kademe goreli kapasitif konum sensorleri (3 eksen)
// material          : Invar-36
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 nm
// computed_mass_kg  : 0.02311
// envelope_mm       : 96.250 x 109.593 x 16.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 96.2500;
bbox_y = 109.5929;
bbox_z = 16.0000;

// Part-specific parametric dimensions
probe_pcd = 115.0;
probe_od = 9.0;
rms_res_nm = 0.1;
bw_kHz = 10.0;

// Interface / port parameters (mm)
port_cap_probe_1_od = 9.000;
port_cap_probe_2_od = 9.000;
port_cap_probe_3_od = 9.000;

module part_S2_5_01() {
  union() {
    // Capacitive sensor probe #1 (0 deg)
    translate([57.500, 0.000, 0.000]) cylinder(d=9.000, h=16.000, center=true);
    // Capacitive sensor probe #2 (120 deg)
    translate([-28.750, 49.796, 0.000]) cylinder(d=9.000, h=16.000, center=true);
    // Capacitive sensor probe #3 (240 deg)
    translate([-28.750, -49.796, 0.000]) cylinder(d=9.000, h=16.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 20.000]) rotate([0.000, 0.000, 0.000]) part_S2_5_01();

part_S2_5_01();
