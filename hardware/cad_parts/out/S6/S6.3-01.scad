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
// computed_mass_kg  : 12.46476
// envelope_mm       : 351.660 x 321.774 x 330.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 351.6604;
bbox_y = 321.7736;
bbox_z = 330.0000;

// Part-specific parametric dimensions
bore_id = 152.0;
x_bore_id = 104.0;
former_od = 352.0;
b_inplane_max_t = 0.3;
b_m4_inplane_t = 0.1785;
b_perp_max_mt = 0.05;
orientation = "HORIZONTAL_SPLIT_HELMHOLTZ_IN_PLANE_X";
homogeneous_field_mm = 16.0;

// Interface / port parameters (mm)
port_inplane_x_bore_od = 352.000;
port_inplane_x_bore_bore = 104.000;
port_vertical_z_bore_od = 352.000;
port_vertical_z_bore_bore = 152.000;
port_pump_slot_neg_y_bore = 152.400;
port_chamber_mount_feet_pcd = 312.000;
port_chamber_mount_feet_bolts = 4;

module part_S6_3_01() {
  union() {
    // -X horizontal split-Helmholtz in-plane coil
    translate([-149.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=144.000, h=22.000, center=true);
        cylinder(d=104.000, h=24.000, center=true);
      }
    }
    // +X horizontal split-Helmholtz in-plane coil
    translate([149.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=144.000, h=22.000, center=true);
        cylinder(d=104.000, h=24.000, center=true);
      }
    }
    // Upper in-plane homogeneity saddle shim
    translate([0.000, 0.000, 91.500]) {
      difference() {
        cylinder(d=228.000, h=26.000, center=true);
        cylinder(d=152.000, h=28.000, center=true);
      }
    }
    // Lower in-plane homogeneity saddle shim
    translate([0.000, 0.000, -91.500]) {
      difference() {
        cylinder(d=228.000, h=26.000, center=true);
        cylinder(d=152.000, h=28.000, center=true);
      }
    }
    // Upper Ø352 structural former
    translate([0.000, 0.000, 93.500]) {
      difference() {
        cylinder(d=352.000, h=30.000, center=true);
        cylinder(d=338.000, h=32.000, center=true);
      }
    }
    // Lower Ø352 structural former
    translate([0.000, 0.000, -93.500]) {
      difference() {
        cylinder(d=352.000, h=30.000, center=true);
        cylinder(d=338.000, h=32.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 500.000]) rotate([0.000, 0.000, 0.000]) part_S6_3_01();

part_S6_3_01();
