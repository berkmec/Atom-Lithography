// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.2-02)
// ============================================================================
// part_id           : S4.2-02
// parent_bom_id     : S4.2
// subsystem         : S4
// part_name         : Cok-eksenli dusuk gurultulu jeofon / ivmeolcer sensor paketi
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : ±2% hassasiyet
// computed_mass_kg  : 1.25645
// envelope_mm       : 742.000 x 550.000 x 46.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 742.0000;
bbox_y = 550.0000;
bbox_z = 46.0000;

// Part-specific parametric dimensions
n_geophone_pods = 3;
pod_od_mm = 60.0;
pod_h_mm = 46.0;
resonant_freq_hz = 4.5;

// Interface / port parameters (mm)
port_table_sensor_mount_od = 60.000;

module part_S4_2_02() {
  union() {
    // 3-axis 4.5 Hz seismic geophone pod #1
    translate([-340.000, -245.000, 0.000]) cylinder(d=56.000, h=46.000, center=true);
    // 3-axis 4.5 Hz seismic geophone pod #2
    translate([340.000, -245.000, 0.000]) cylinder(d=56.000, h=46.000, center=true);
    // 3-axis 4.5 Hz seismic geophone pod #3
    translate([-340.000, 245.000, 0.000]) cylinder(d=56.000, h=46.000, center=true);
    // Low-noise triaxial geophone junction box
    translate([-345.000, 0.000, -9.500]) cube([54.000, 84.000, 26.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -216.000]) rotate([0.000, 0.000, 0.000]) part_S4_2_02();

part_S4_2_02();
