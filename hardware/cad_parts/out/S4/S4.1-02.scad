// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.1-02)
// ============================================================================
// part_id           : S4.1-02
// parent_bom_id     : S4.1
// subsystem         : S4
// part_name         : Pnomatik dusuk-frekansli hava yayli izolatör seti (4 ayak)
// material          : 304 SS
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : ±0.1 mm seviye
// computed_mass_kg  : 6.64907
// envelope_mm       : 858.000 x 612.000 x 80.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 858.0000;
bbox_y = 612.0000;
bbox_z = 80.0000;

// Part-specific parametric dimensions
n_isolators = 4;
span_x_mm = 700.0;
span_y_mm = 500.0;
isolator_h_mm = 80.0;
corner_freq_hz = 1.5;

// Interface / port parameters (mm)

module part_S4_1_02() {
  union() {
    // Pneumatic air-spring isolator #1 (1.0-2.0 Hz)
    translate([-350.000, -250.000, 0.000]) cylinder(d=108.000, h=80.000, center=true);
    // Pneumatic air-spring isolator #2 (1.0-2.0 Hz)
    translate([350.000, -250.000, 0.000]) cylinder(d=108.000, h=80.000, center=true);
    // Pneumatic air-spring isolator #3 (1.0-2.0 Hz)
    translate([350.000, 250.000, 0.000]) cylinder(d=108.000, h=80.000, center=true);
    // Pneumatic air-spring isolator #4 (1.0-2.0 Hz)
    translate([-350.000, 250.000, 0.000]) cylinder(d=108.000, h=80.000, center=true);
    // Auto-leveling pneumatic valve #1
    translate([-418.000, -250.000, 0.000]) cube([22.000, 32.000, 36.000], center=true);
    // Auto-leveling pneumatic valve #2
    translate([418.000, -250.000, 0.000]) cube([22.000, 32.000, 36.000], center=true);
    // Auto-leveling pneumatic valve #3
    translate([418.000, 250.000, 0.000]) cube([22.000, 32.000, 36.000], center=true);
    // Perimeter structural tie-bar #1
    translate([0.000, -250.000, -24.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=20.000, h=584.000, center=true);
    // Perimeter structural tie-bar #2
    translate([0.000, 250.000, -24.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=20.000, h=584.000, center=true);
    // Perimeter structural tie-bar #3
    translate([-350.000, 0.000, -24.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=20.000, h=384.000, center=true);
    // Perimeter structural tie-bar #4
    translate([350.000, 0.000, -24.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=20.000, h=384.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -462.000]) rotate([0.000, 0.000, 0.000]) part_S4_1_02();

part_S4_1_02();
