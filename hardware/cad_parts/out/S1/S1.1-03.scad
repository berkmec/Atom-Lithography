// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.1-03)
// ============================================================================
// part_id           : S1.1-03
// parent_bom_id     : S1.1
// subsystem         : S1
// part_name         : Yuksek gerilim cikarim elektrot yigini (10-15 keV, Exp124)
// material          : Mo
// temp_stage        : 300 K
// vacuum_grade      : HV 1e-7 mbar
// tolerance         : ±5 um es-eksenlilik
// computed_mass_kg  : 1.73499
// envelope_mm       : 84.000 x 84.000 x 45.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 84.0000;
bbox_y = 84.0000;
bbox_z = 45.0000;

// Part-specific parametric dimensions
od = 84.0;
bore = 20.0;
height = 45.0;
v_extract_kV = 10.0;

// Interface / port parameters (mm)
port_extract_inlet_od = 84.000;
port_extract_inlet_bore = 20.000;
port_extract_outlet_od = 84.000;
port_extract_outlet_bore = 20.000;

module part_S1_1_03() {
  union() {
    // Upper Pierce extraction electrode
    translate([0.000, 0.000, 17.000]) {
      difference() {
        cylinder(d=84.000, h=11.000, center=true);
        cylinder(d=20.000, h=13.000, center=true);
      }
    }
    // Middle Einzel condenser electrode
    difference() {
      cylinder(d=84.000, h=13.000, center=true);
      cylinder(d=20.000, h=15.000, center=true);
    }
    // Lower collimator electrode
    translate([0.000, 0.000, -17.000]) {
      difference() {
        cylinder(d=84.000, h=11.000, center=true);
        cylinder(d=20.000, h=13.000, center=true);
      }
    }
    // Upper sapphire centering ring
    translate([0.000, 0.000, 9.000]) {
      difference() {
        cylinder(d=62.000, h=4.000, center=true);
        cylinder(d=50.000, h=6.000, center=true);
      }
    }
    // Lower sapphire centering ring
    translate([0.000, 0.000, -9.000]) {
      difference() {
        cylinder(d=62.000, h=4.000, center=true);
        cylinder(d=50.000, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 396.160]) rotate([0.000, 0.000, 0.000]) part_S1_1_03();

part_S1_1_03();
