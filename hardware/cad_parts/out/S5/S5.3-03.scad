// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.3-03)
// ============================================================================
// part_id           : S5.3-03
// parent_bom_id     : S5.3
// subsystem         : S5
// part_name         : Yuksek hizli optik pirometre ve kapali-cevrim tavlama kontroloru
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer (optik)
// tolerance         : ±3 C
// computed_mass_kg  : 1.03810
// envelope_mm       : 142.000 x 69.500 x 74.950
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 142.0000;
bbox_y = 69.5000;
bbox_z = 74.9500;

// Part-specific parametric dimensions
response_us = 100;
temp_min_C = 300;
temp_max_C = 1200;

// Interface / port parameters (mm)
port_chamber_cf40_mate_od = 69.500;
port_chamber_cf40_mate_bore = 28.000;
port_chamber_cf40_mate_pcd = 58.700;
port_chamber_cf40_mate_bolts = 6;

module part_S5_3_03() {
  union() {
    // CF40 optical sight viewport flange
    translate([6.350, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=28.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // IR collection optics barrel
    translate([39.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=46.000, h=52.000, center=true);
        cylinder(d=32.000, h=54.000, center=true);
      }
    }
    // Dual-wavelength InGaAs/Si pyrometer head
    translate([92.500, 0.000, 0.000]) cube([54.000, 50.000, 52.000], center=true);
    // Closed-loop <100 us anneal controller module
    translate([131.000, 0.000, 0.000]) cube([22.000, 48.000, 48.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([205.198, -143.681, 500.000]) rotate([0.000, 0.000, -35.000]) part_S5_3_03();

part_S5_3_03();
