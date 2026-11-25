// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.1-04)
// ============================================================================
// part_id           : S2.1-04
// parent_bom_id     : S2.1
// subsystem         : S2
// part_name         : Hassas seramik/Si kinematik apertur alt-tasiyici cerceve
// material          : AlN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±5 um duzlemlik
// computed_mass_kg  : 0.42615
// envelope_mm       : 100.000 x 100.000 x 21.270
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 100.0000;
bbox_y = 100.0000;
bbox_z = 21.2700;

// Part-specific parametric dimensions
od = 100.0;
bore_id = 28.0;
height = 21.27;
cte_ppm_K = 4.5;

// Interface / port parameters (mm)
port_guard_mount_bot_od = 100.000;
port_guard_mount_bot_bore = 28.000;
port_guard_mount_bot_pcd = 46.000;
port_guard_mount_bot_bolts = 6;
port_kinematic_top_od = 100.000;
port_kinematic_top_bore = 28.000;
port_kinematic_top_pcd = 88.000;
port_kinematic_top_bolts = 12;

module part_S2_1_04() {
  difference() {
    union() {
      // Ti-6Al-4V kinematic cassette outer ring
      difference() {
        cylinder(d=100.000, h=21.270, center=true);
        cylinder(d=64.600, h=23.270, center=true);
      }
      // AlN CTE-matched inner core
      translate([0.000, 0.000, -3.330]) {
        difference() {
          cylinder(d=64.000, h=14.610, center=true);
          cylinder(d=28.000, h=16.610, center=true);
        }
      }
    }
    // 12xM4 kinematic flange bolts
    for (i = [0 : 12 - 1])
      rotate([0, 0, i * 360 / 12])
        translate([44.000, 0, 0])
          cylinder(d=4.500, h=26.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 21.025]) rotate([0.000, 0.000, 0.000]) part_S2_1_04();

part_S2_1_04();
