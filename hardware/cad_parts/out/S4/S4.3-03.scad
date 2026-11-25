// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.3-03)
// ============================================================================
// part_id           : S4.3-03
// parent_bom_id     : S4.3
// subsystem         : S4
// part_name         : Kademe ici kapasitif konum geri-besleme sensorleri ve UHV kablolari
// material          : Au
// temp_stage        : 300 K (UHV)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 nm
// computed_mass_kg  : 0.02225
// envelope_mm       : 110.500 x 84.500 x 40.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 110.5000;
bbox_y = 84.5000;
bbox_z = 40.0000;

// Part-specific parametric dimensions
n_sensor_pods = 4;
pod_x_mm = 51.0;
pod_y_mm = 38.0;

// Interface / port parameters (mm)

module part_S4_3_03() {
  union() {
    // Sub-nm capacitive feedback sensor pod #1
    translate([51.000, 38.000, 0.000]) cube([8.500, 8.500, 14.000], center=true);
    // Sub-nm capacitive feedback sensor pod #2
    translate([-51.000, 38.000, 0.000]) cube([8.500, 8.500, 14.000], center=true);
    // Sub-nm capacitive feedback sensor pod #3
    translate([-51.000, -38.000, 0.000]) cube([8.500, 8.500, 14.000], center=true);
    // Sub-nm capacitive feedback sensor pod #4
    translate([51.000, -38.000, 0.000]) cube([8.500, 8.500, 14.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -41.000]) rotate([0.000, 0.000, 0.000]) part_S4_3_03();

part_S4_3_03();
