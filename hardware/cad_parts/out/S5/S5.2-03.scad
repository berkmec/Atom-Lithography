// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.2-03)
// ============================================================================
// part_id           : S5.2-03
// parent_bom_id     : S5.2
// subsystem         : S5
// part_name         : Yagsiz kuru scroll on-vakum pompasi ve geri-akis tutucu
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Kaba vakum
// tolerance         : ISO 2768-mK
// computed_mass_kg  : 26.86204
// envelope_mm       : 270.000 x 360.000 x 350.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 270.0000;
bbox_y = 360.0000;
bbox_z = 350.2000;

// Part-specific parametric dimensions
speed_m3_h = 15.0;
base_mbar = 0.01;
head_od_mm = 210.0;

// Interface / port parameters (mm)
port_kf25_inlet_od = 40.000;
port_kf25_inlet_bore = 25.000;
port_kf25_exhaust_bore = 25.000;

module part_S5_2_03() {
  union() {
    // Vibration-isolated cast Al baseplate
    translate([0.000, 0.000, 33.200]) cube([270.000, 350.000, 18.000], center=true);
    // Finned dry-scroll compression head
    translate([0.000, 96.500, 148.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=210.000, h=103.000, center=true);
    // 15 m^3/h oil-free TEFC drive motor
    translate([0.000, -49.000, 148.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=164.000, h=180.000, center=true);
    // KF25 molecular-sieve foreline backstream trap
    translate([0.000, 102.000, 296.000]) {
      difference() {
        cylinder(d=68.000, h=88.000, center=true);
        cylinder(d=52.000, h=90.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, -780.000, 0.000]) rotate([0.000, 0.000, 0.000]) part_S5_2_03();

part_S5_2_03();
