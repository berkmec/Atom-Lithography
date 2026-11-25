// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.6-01)
// ============================================================================
// part_id           : S1.6-01
// parent_bom_id     : S1.6
// subsystem         : S1
// part_name         : Cift-tuplu egzozlu PH3/SiF4 toksik gaz kabini (SEMI S2, Exp81/83)
// material          : Steel
// temp_stage        : 300 K (tesis)
// vacuum_grade      : Atmosfer (negatif basinc)
// tolerance         : He <=1e-9 mbar*L/s
// computed_mass_kg  : 139.16831
// envelope_mm       : 500.000 x 600.000 x 1799.750
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 500.0000;
bbox_y = 600.0000;
bbox_z = 1799.7500;

// Part-specific parametric dimensions
cab_dx = 500.0;
cab_dy = 600.0;
cab_h = 1800.0;
semi_s2_ref = "UNVERIFIED_M0_DESIGN";

// Interface / port parameters (mm)
port_exhaust_duct_top_od = 152.000;
port_exhaust_duct_top_bore = 146.000;
port_ph3_coax_outlet_od = 12.700;
port_ph3_coax_outlet_bore = 6.400;

module part_S1_6_01() {
  difference() {
    union() {
      // SEMI S2 dual-cylinder steel cabinet shell
      translate([0.000, 0.000, -20.000]) cube([500.000, 600.000, 1680.000], center=true);
      // Top Ø150 mm negative-pressure exhaust collar
      translate([0.000, 0.000, 860.000]) {
        difference() {
          cylinder(d=152.000, h=80.000, center=true);
          cylinder(d=146.000, h=82.000, center=true);
        }
      }
    }
    // Self-closing door sight-glass cutout
    translate([248.000, 0.000, 200.000]) rotate([0.000, 90.000, 0.000]) {
      hull() {
        translate([-70.000, 0, 0]) cylinder(d=320.000, h=20.000, center=true);
        translate([70.000, 0, 0]) cylinder(d=320.000, h=20.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1350.000, 1050.000, 400.000]) rotate([0.000, 0.000, 0.000]) part_S1_6_01();

part_S1_6_01();
