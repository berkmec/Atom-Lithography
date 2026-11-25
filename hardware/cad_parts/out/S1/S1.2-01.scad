// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.2-01)
// ============================================================================
// part_id           : S1.2-01
// parent_bom_id     : S1.2
// subsystem         : S1
// part_name         : Wien ExB kutle filtresi manyetik kutup ve boyunduruk
// material          : Soft Iron
// temp_stage        : 300 K
// vacuum_grade      : HV 1e-7 mbar
// tolerance         : ±0.1% B homojenlik
// computed_mass_kg  : 4.28935
// envelope_mm       : 110.000 x 110.000 x 115.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 110.0000;
bbox_y = 110.0000;
bbox_z = 115.0000;

// Part-specific parametric dimensions
od = 110.0;
yoke_h = 115.0;
pole_gap = 36.0;
b_tesla = 0.45;

// Interface / port parameters (mm)
port_wien_inlet_od = 110.000;
port_wien_inlet_bore = 84.000;
port_wien_inlet_pcd = 98.000;
port_wien_inlet_bolts = 12;
port_wien_exit_drift_od = 110.000;
port_wien_exit_drift_bore = 84.000;
port_wien_exit_drift_pcd = 98.000;
port_wien_exit_drift_bolts = 12;

module part_S1_2_01() {
  difference() {
    union() {
      // Soft-iron magnetic return yoke
      difference() {
        cylinder(d=110.000, h=115.000, center=true);
        cylinder(d=84.000, h=117.000, center=true);
      }
      // +X soft-iron pole shoe
      translate([23.900, 0.000, 0.000]) cube([11.800, 34.000, 84.000], center=true);
      // -X soft-iron pole shoe
      translate([-23.900, 0.000, 0.000]) cube([11.800, 34.000, 84.000], center=true);
    }
    // 12xM5 flange bolt circle
    for (i = [0 : 12 - 1])
      rotate([0, 0, i * 360 / 12])
        translate([49.000, 0, 0])
          cylinder(d=5.500, h=120.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 310.160]) rotate([0.000, 0.000, 0.000]) part_S1_2_01();

part_S1_2_01();
