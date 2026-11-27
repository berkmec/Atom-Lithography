// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.1-05)
// ============================================================================
// part_id           : S5.1-05
// parent_bom_id     : S5.1
// subsystem         : S5
// part_name         : UHV tam-metal aci vanalari, gozlem pencereleri ve CF baglanti seti
// material          : OFHC Cu
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : He <=1e-10 mbar*L/s
// computed_mass_kg  : 8.48547
// envelope_mm       : 385.000 x 260.000 x 87.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 385.0000;
bbox_y = 260.0000;
bbox_z = 87.0000;

// Part-specific parametric dimensions
tray_x = 360.0;
tray_y = 260.0;
cf100_gask_od = 120.5;
cf63_gask_od = 82.4;

// Interface / port parameters (mm)

module part_S5_1_05() {
  difference() {
    union() {
      // UHV CF hardware & gasket kit tray
      translate([0.000, 0.000, 17.000]) cube([360.000, 260.000, 34.000], center=true);
      // OFHC Cu CF100 gasket stack
      translate([-102.000, 48.000, 13.000]) {
        difference() {
          cylinder(d=120.500, h=12.000, center=true);
          cylinder(d=101.600, h=14.000, center=true);
        }
      }
      // OFHC Cu CF63 gasket stack
      translate([18.000, 62.000, 13.000]) {
        difference() {
          cylinder(d=82.400, h=12.000, center=true);
          cylinder(d=63.500, h=14.000, center=true);
        }
      }
      // OFHC Cu CF40 gasket stack
      translate([118.000, 72.000, 14.000]) {
        difference() {
          cylinder(d=48.100, h=14.000, center=true);
          cylinder(d=38.000, h=16.000, center=true);
        }
      }
      // All-metal bakeable CF40 angle valve #1
      translate([25.000, -66.000, 14.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=38.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
      // All-metal bakeable CF40 angle valve #2
      translate([118.000, -66.000, 14.000]) {
        difference() {
          cylinder(d=69.500, h=12.700, center=true);
          cylinder(d=38.000, h=14.700, center=true);
          translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
          for (i = [0 : 6 - 1])
            rotate([0, 0, i * 360 / 6])
              translate([29.350, 0, 0])
                cylinder(d=6.600, h=14.700, center=true);
        }
      }
    }
    // CF100 gasket ID bore
    translate([-102.000, 48.000, 13.000]) cylinder(d=101.600, h=16.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([780.000, -480.000, 0.000]) rotate([0.000, 0.000, 0.000]) part_S5_1_05();

part_S5_1_05();
