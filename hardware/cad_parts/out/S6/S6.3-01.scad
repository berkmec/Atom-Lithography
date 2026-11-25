// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.3-01)
// ============================================================================
// part_id           : S6.3-01
// parent_bom_id     : S6.3
// subsystem         : S6
// part_name         : Ana NbTi superiletken ESR miknatis bobinleri (8-bobinli cift-yarik, Exp125 delta)
// material          : NbTi
// temp_stage        : 4.2 K
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±17.8 ppm Bz
// computed_mass_kg  : 38.17239
// envelope_mm       : 352.000 x 352.000 x 333.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 352.0000;
bbox_y = 352.0000;
bbox_z = 333.5000;

// Part-specific parametric dimensions
bore_id = 150.0;
former_od = 352.0;
split_gap = 36.0;
b_sample_t = 1.5;

// Interface / port parameters (mm)
port_clear_bore_150_od = 352.000;
port_clear_bore_150_bore = 150.000;
port_split_gap_36mm_bore = 36.000;
port_chamber_mount_feet_pcd = 312.000;
port_chamber_mount_feet_bolts = 4;

module part_S6_3_01() {
  union() {
    // M_upper coil
    translate([0.000, 0.000, 45.000]) {
      difference() {
        cylinder(d=224.000, h=54.000, center=true);
        cylinder(d=150.000, h=56.000, center=true);
      }
    }
    // M_lower coil
    translate([0.000, 0.000, -45.000]) {
      difference() {
        cylinder(d=224.000, h=54.000, center=true);
        cylinder(d=150.000, h=56.000, center=true);
      }
    }
    // S_upper shim coil
    translate([0.000, 0.000, 94.000]) {
      difference() {
        cylinder(d=232.000, h=36.000, center=true);
        cylinder(d=150.000, h=38.000, center=true);
      }
    }
    // S_lower shim coil
    translate([0.000, 0.000, -94.000]) {
      difference() {
        cylinder(d=232.000, h=36.000, center=true);
        cylinder(d=150.000, h=38.000, center=true);
      }
    }
    // Upper Ø352 former
    translate([0.000, 0.000, 62.000]) {
      difference() {
        cylinder(d=352.000, h=84.000, center=true);
        cylinder(d=338.000, h=86.000, center=true);
      }
    }
    // Lower Ø352 former
    translate([0.000, 0.000, -62.000]) {
      difference() {
        cylinder(d=352.000, h=84.000, center=true);
        cylinder(d=338.000, h=86.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S6_3_01();

part_S6_3_01();
