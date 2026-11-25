// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.4-02)
// ============================================================================
// part_id           : S2.4-02
// parent_bom_id     : S2.4
// subsystem         : S2
// part_name         : Cok-karolu seramik/poliimid blanker surucu anakart duzenegi
// material          : Rogers
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : 50 Ohm ±5%
// computed_mass_kg  : 0.03846
// envelope_mm       : 127.825 x 127.825 x 2.400
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 127.8246;
bbox_y = 127.8246;
bbox_z = 2.4000;

// Part-specific parametric dimensions
pcb_od = 128.0;
pcb_id = 67.0;
thickness = 2.4;
quadrants = 4;
z0_ohm = 50.0;

// Interface / port parameters (mm)
port_asic_mount_top_od = 128.000;
port_asic_mount_top_bore = 67.000;
port_asic_mount_top_pcd = 118.000;
port_asic_mount_top_bolts = 12;
port_kapton_flex_edge_od = 128.000;

module part_S2_4_02() {
  difference() {
    union() {
      // 4-quadrant modular UHV Rogers/Polyimide blanker PCB
      difference() {
        cylinder(d=128.000, h=2.400, center=true);
        cylinder(d=67.000, h=4.400, center=true);
      }
    }
    // X-axis inter-quadrant thermal split
    hull() {
      translate([-64.250, 0, 0]) cylinder(d=3.500, h=5.000, center=true);
      translate([64.250, 0, 0]) cylinder(d=3.500, h=5.000, center=true);
    }
    // Y-axis inter-quadrant thermal split
    rotate([0.000, 0.000, 90.000]) {
      hull() {
        translate([-64.250, 0, 0]) cylinder(d=3.500, h=5.000, center=true);
        translate([64.250, 0, 0]) cylinder(d=3.500, h=5.000, center=true);
      }
    }
    // 12xM3 quadrant mounting holes
    for (i = [0 : 12 - 1])
      rotate([0, 0, i * 360 / 12])
        translate([59.000, 0, 0])
          cylinder(d=3.200, h=5.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 3.950]) rotate([0.000, 0.000, 0.000]) part_S2_4_02();

part_S2_4_02();
